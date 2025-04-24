# back/apps/analysis/management/commands/find_all_duplicates.py

import time
from django.core.management.base import BaseCommand
from apps.testcases.models import TestCaseVersion
# 导入需要触发的任务
from apps.analysis.tasks import find_and_store_duplicate_pairs_task
from logging import getLogger
from itertools import islice # 用于批处理数据库查询迭代

logger = getLogger(__name__)

class Command(BaseCommand):
    help = '为所有已生成 embedding 的 TestCaseVersion 派发 Celery 任务以查找并存储潜在重复对。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.90, # 默认相似度阈值 (与任务中的默认值一致)
            help='相似度阈值 (0.0 到 1.0)，高于此阈值的才会被认为是潜在重复。传递给 Celery 任务。',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50, # 默认每个源查找的限制 (与任务中的默认值一致)
            help='对每个源用例，最多查找并存储多少个潜在重复项。传递给 Celery 任务。',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000, # 控制从数据库一次性获取多少 ID 进行迭代
            help='每次数据库迭代查询处理的版本 ID 数量。',
        )
        parser.add_argument(
            '--delay-ms',
            type=int,
            default=10, # 在派发每个任务之间添加少量延迟，防止瞬间冲击 Celery
            help='派发每个查找任务之间的延迟（毫秒）。',
        )

    def handle(self, *args, **options):
        similarity_threshold = options['threshold']
        limit_per_source = options['limit']
        db_batch_size = options['batch_size'] # DB query batch size
        delay_ms = options['delay_ms']
        delay_seconds = delay_ms / 1000.0

        # 参数校验
        if not (0.0 < similarity_threshold <= 1.0):
             self.stderr.write(self.style.ERROR("相似度阈值必须在 (0.0, 1.0] 范围内。"))
             return
        if limit_per_source <= 0:
             self.stderr.write(self.style.ERROR("每个源用例的限制数量必须大于 0。"))
             return
        if db_batch_size <= 0:
             self.stderr.write(self.style.ERROR("数据库查询批处理大小必须大于 0。"))
             return

        self.stdout.write(self.style.NOTICE(
            f"开始派发相似度查找任务。阈值: {similarity_threshold}, 每个源限制: {limit_per_source}, 派发延迟: {delay_ms}ms"
        ))

        # 查询所有 embedding 不为空的版本 ID
        version_ids_qs = TestCaseVersion.objects.filter(embedding__isnull=False).values_list('id', flat=True)
        total_versions = version_ids_qs.count() # 先获取总数

        if total_versions == 0:
            self.stdout.write(self.style.WARNING("没有找到任何已生成 embedding 的版本。"))
            return

        self.stdout.write(f"找到 {total_versions} 个已生成 embedding 的版本。开始派发查找任务...")

        total_dispatched = 0
        start_time = time.time()

        # 使用迭代器高效处理大量 ID
        version_ids_iterator = version_ids_qs.iterator(chunk_size=db_batch_size)

        # 遍历版本 ID 并派发任务
        for version_id in version_ids_iterator:
            try:
                # 异步调用 Celery 任务，传递参数
                find_and_store_duplicate_pairs_task.delay(
                    source_version_id=version_id,
                    similarity_threshold=similarity_threshold,
                    limit_per_source=limit_per_source
                )
                total_dispatched += 1

                # 减少输出，避免刷屏
                # self.stdout.write(f"已派发任务 - 源 TestCaseVersion ID: {version_id}")

                if delay_seconds > 0:
                    time.sleep(delay_seconds)

                # 定期报告进度
                if total_dispatched % db_batch_size == 0 or total_dispatched == total_versions:
                    elapsed_time = time.time() - start_time
                    self.stdout.write(self.style.SUCCESS(
                        f"已派发 {total_dispatched}/{total_versions} 个任务... (耗时: {elapsed_time:.2f} 秒)"
                    ))

            except Exception as e:
                # 记录并报告派发过程中的错误
                logger.error(f"派发查找任务时出错 - 源 TestCaseVersion ID {version_id}: {e}")
                self.stderr.write(self.style.ERROR(
                    f"派发查找任务失败 - 源 TestCaseVersion ID: {version_id}。错误: {e}"
                ))
                # 选择继续处理下一个 ID

        end_time = time.time()
        duration = end_time - start_time

        self.stdout.write(self.style.SUCCESS(
            f"\n查找任务派发完成。"
        ))
        self.stdout.write(f"总共派发的任务数: {total_dispatched}")
        self.stdout.write(f"总耗时: {duration:.2f} 秒")
        self.stdout.write(self.style.NOTICE(
            "Celery worker 现在将在后台处理这些相似度查找和存储任务。"
        )) 
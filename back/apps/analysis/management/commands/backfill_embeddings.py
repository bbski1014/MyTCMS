# back/apps/analysis/management/commands/backfill_embeddings.py

import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.testcases.models import TestCaseVersion
# 导入批量 Celery 任务
# from apps.analysis.tasks import generate_embeddings_batch_task # Commented out

# +++ 添加调试代码 +++
print("Attempting basic import from tasks...")
try:
    from apps.analysis.tasks import generate_version_embedding_task # Known existing task
    print("Successfully imported generate_version_embedding_task.")
    import apps.analysis.tasks
    print("Attributes found in tasks.py:", dir(apps.analysis.tasks))
except ImportError as e:
    print(f"Basic import failed: {e}")
# from apps.analysis.tasks import generate_embeddings_batch_task # Keep commented out
# +++ 结束调试代码 +++

from logging import getLogger
from itertools import islice # 用于批处理迭代

logger = getLogger(__name__)

# Helper function to chunk data
def chunked(iterable, size):
    iterator = iter(iterable)
    while True:
        chunk = tuple(islice(iterator, size))
        if not chunk:
            return
        yield chunk

class Command(BaseCommand):
    help = '为缺失 embedding 的现有 TestCaseVersion 派发批量 Celery 任务以生成 embedding。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-rebuild',
            action='store_true',
            help='强制为所有版本重新生成 embedding，即使它们已经有 embedding。',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500, # 默认批次大小可以调整
            help='发送给 Celery 任务的每个批次包含的版本 ID 数量。',
        )
        parser.add_argument(
            '--delay-ms',
            type=int,
            default=50, # 在批次之间添加少量延迟可能有助于 Celery 调度
            help='派发每个批次任务之间的延迟（毫秒）。',
        )

    def handle(self, *args, **options):
        force_rebuild = options['force_rebuild']
        batch_size = options['batch_size']
        delay_ms = options['delay_ms']
        delay_seconds = delay_ms / 1000.0

        if batch_size <= 0:
             self.stderr.write(self.style.ERROR("批处理大小必须大于 0。"))
             return

        self.stdout.write(self.style.NOTICE(
            f"开始派发批量 embedding 回填任务。强制重建: {force_rebuild}, Celery 批处理大小: {batch_size}, 批次间延迟: {delay_ms}ms"
        ))

        # 构建基础查询集
        queryset = TestCaseVersion.objects.all()
        if not force_rebuild:
            queryset = queryset.filter(embedding__isnull=True)
            self.stdout.write("将仅为 embedding 为空的版本生成任务。")
        else:
            self.stdout.write(self.style.WARNING("警告：将为所有版本强制重新生成 embedding！"))

        # 获取所有需要处理的 ID 列表 (一次性获取，对于超大数据量可能需要优化)
        # 对于百万级数据，values_list().iterator() 仍然是内存友好的
        all_version_ids = list(queryset.values_list('id', flat=True))
        total_versions = len(all_version_ids)

        if total_versions == 0:
            if not force_rebuild:
                 self.stdout.write(self.style.WARNING(
                "没有找到需要生成 embedding 的版本。如果需要为所有版本重新生成，请使用 --force-rebuild 参数。"
                ))
            else:
                self.stdout.write(self.style.WARNING("没有找到任何版本。"
                ))
            return

        self.stdout.write(f"找到 {total_versions} 个版本需要处理。将按每批 {batch_size} 个派发任务...")

        total_dispatched_tasks = 0
        total_dispatched_versions = 0
        start_time = time.time()

        # 将 ID 列表分块并派发批量任务
        for id_batch in chunked(all_version_ids, batch_size):
            try:
                generate_embeddings_batch_task.delay(list(id_batch))
                total_dispatched_tasks += 1
                current_batch_size = len(id_batch)
                total_dispatched_versions += current_batch_size
                self.stdout.write(f"已派发批次任务 {total_dispatched_tasks} (包含 {current_batch_size} 个版本, 累计: {total_dispatched_versions}/{total_versions})")

                if delay_seconds > 0:
                    time.sleep(delay_seconds)

            except Exception as e:
                # 记录并报告派发过程中的错误
                batch_start_id = id_batch[0] if id_batch else 'N/A'
                logger.error(f"派发批次任务时出错 (批次起始 ID: {batch_start_id}): {e}")
                self.stderr.write(self.style.ERROR(
                    f"派发批次任务失败 (批次起始 ID: {batch_start_id})。错误: {e}"
                ))

        end_time = time.time()
        duration = end_time - start_time

        self.stdout.write(self.style.SUCCESS(
            f"\n批量任务派发完成。"
        ))
        self.stdout.write(f"总共派发的批次任务数: {total_dispatched_tasks}")
        self.stdout.write(f"总共处理的版本数: {total_dispatched_versions}")
        self.stdout.write(f"总耗时: {duration:.2f} 秒")
        self.stdout.write(self.style.NOTICE(
            "Celery worker 现在将在后台处理这些批量任务。"
        )) 
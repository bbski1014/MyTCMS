from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.testcases.models import TestCaseVersion
from .tasks import generate_version_embedding_task
import logging

logger = logging.getLogger(__name__)

# 监听 TestCaseVersion 模型的 post_save 信号
@receiver(post_save, sender=TestCaseVersion)
def trigger_embedding_generation(sender, instance: TestCaseVersion, created: bool, update_fields=None, **kwargs):
    """
    当 TestCaseVersion 创建或更新时，触发 embedding 生成任务。
    只有在相关内容字段被更新时，或者新创建且 embedding 为空时才触发。
    """
    # 定义需要关注的内容字段 (这些字段的变化应该触发 embedding 更新)
    content_fields = {'title', 'precondition', 'steps_data'}

    # 检查是否应该触发任务
    should_trigger = False
    if created and not instance.embedding:
        # 如果是新创建的，并且还没有 embedding，则触发
        should_trigger = True
        logger.info(f"New TestCaseVersion {instance.id} created, triggering embedding generation.")
    elif update_fields is not None:
        # 如果提供了 update_fields (推荐的做法)，检查是否有内容字段被更新
        if any(field in content_fields for field in update_fields):
            should_trigger = True
            logger.info(f"Content fields {content_fields.intersection(update_fields)} updated for Version {instance.id}, triggering embedding generation.")
    else:
        # 如果没有提供 update_fields (意味着可能所有字段都更新了，或者 save() 没有指定 update_fields)，
        # 为了安全起见，也触发任务。
        # 更精确的做法可以在这里比较 instance 和旧值的差异 (如果需要且性能允许)
        should_trigger = True
        logger.warning(f"post_save for Version {instance.id} called without update_fields. Triggering embedding generation as a precaution.")

    # 如果需要触发，则异步调用 Celery 任务
    if should_trigger:
        try:
            generate_version_embedding_task.delay(instance.id)
            logger.info(f"Celery task generate_version_embedding_task dispatched for Version {instance.id}.")
        except Exception as e:
            # 处理调用 task.delay 可能出现的异常 (比如 Celery 连接问题)
            logger.error(f"Failed to dispatch Celery task for Version {instance.id}: {e}") 
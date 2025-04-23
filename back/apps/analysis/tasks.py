from celery import shared_task
from apps.testcases.models import TestCaseVersion
from .utils import generate_embedding, get_embedding_model, model_dimension # 导入工具函数和模型维度
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60) # 允许绑定实例，设置重试
def generate_version_embedding_task(self, version_id: int):
    """
    Celery 任务：为单个 TestCaseVersion 生成并保存 embedding。
    """
    # 检查模型是否已加载，如果未加载，则任务失败并稍后重试
    if not get_embedding_model():
        logger.error("Embedding model not loaded. Retrying task later.")
        raise self.retry(exc=RuntimeError("Embedding model not loaded"))

    try:
        version = TestCaseVersion.objects.get(pk=version_id)
    except TestCaseVersion.DoesNotExist:
        logger.error(f"TestCaseVersion with id {version_id} not found. Task cannot proceed.")
        return f"Version {version_id} not found."

    logger.info(f"Starting embedding generation for Version {version_id}...")
    embedding_vector = generate_embedding(version)

    if embedding_vector:
        # 确保向量维度与数据库字段匹配 (虽然 utils 中也检查了模型加载时的维度)
        if len(embedding_vector) == model_dimension:
            try:
                version.embedding = embedding_vector
                # 只更新 embedding 字段，避免触发不必要的信号或覆盖其他更改
                version.save(update_fields=['embedding'])
                logger.info(f"Successfully generated and saved embedding for Version {version_id}.")
                return f"Embedding generated for Version {version_id}."
            except Exception as e:
                logger.error(f"Error saving embedding for Version {version_id}: {e}")
                # 数据库保存失败也应该重试
                raise self.retry(exc=e)
        else:
            logger.error(f"Generated embedding dimension ({len(embedding_vector)}) does not match expected dimension ({model_dimension}) for Version {version_id}.")
            # 维度不匹配通常是严重问题，可能不需要重试，或者需要不同的处理逻辑
            return f"Dimension mismatch for Version {version_id}."
    else:
        # generate_embedding 返回 None 通常意味着提取文本失败或生成过程出错
        logger.error(f"Failed to generate embedding for Version {version_id} (returned None). Check previous logs.")
        # 可以根据具体情况决定是否重试
        # raise self.retry(exc=RuntimeError("Embedding generation failed"))
        return f"Failed to generate embedding for Version {version_id}."

# --- 后续可以添加批量生成任务和相似度检测任务 ---
# @shared_task
# def batch_generate_embeddings_task(project_id=None, force_update=False):
#     ...

# @shared_task
# def find_duplicate_versions_task(project_id):
#     ... 
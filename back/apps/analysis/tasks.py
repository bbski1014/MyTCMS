from celery import shared_task
from apps.testcases.models import TestCaseVersion
from .utils import generate_embedding, get_embedding_model, model_dimension, MODEL_NAME # 导入工具函数、模型维度和模型名称
import logging
from .models import PotentialDuplicatePair # 导入结果模型
from django.db import IntegrityError # 用于捕获唯一约束冲突

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
                # 同时设置模型版本
                version.embedding_model_version = MODEL_NAME
                # 更新 embedding 和 model_version 两个字段
                version.save(update_fields=['embedding', 'embedding_model_version'])
                logger.info(f"Successfully generated and saved embedding and model version for Version {version.id}.")
                return f"Embedding generated for Version {version.id} using model {MODEL_NAME}."
            except Exception as e:
                logger.error(f"Error saving embedding/model version for Version {version.id}: {e}")
                # 数据库保存失败也应该重试
                raise self.retry(exc=e)
        else:
            logger.error(f"Generated embedding dimension ({len(embedding_vector)}) does not match expected dimension ({model_dimension}) for Version {version.id}.")
            # 维度不匹配通常是严重问题，可能不需要重试，或者需要不同的处理逻辑
            return f"Dimension mismatch for Version {version.id}."
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

@shared_task(bind=True, max_retries=2, default_retry_delay=180) # 增加重试延迟
def find_and_store_duplicate_pairs_task(self, source_version_id: int, similarity_threshold: float = 0.90, limit_per_source: int = 50):
    """
    Celery 任务：查找与给定版本相似的版本，并将潜在的重复对存储到 PotentialDuplicatePair 模型。
    使用 update_or_create 来处理已存在记录的更新。
    """
    logger.info(f"Starting similarity search and storage for source version {source_version_id} with threshold {similarity_threshold}...")

    try:
        # 1. 查找相似版本 (limit 参数传递给 find_similar_testcases)
        similar_versions_qs = find_similar_testcases(
            source_version_id=source_version_id,
            similarity_threshold=similarity_threshold,
            limit=limit_per_source
        )

        # 检查是否有结果
        if not similar_versions_qs.exists():
            logger.info(f"No similar versions found for source version {source_version_id} above threshold {similarity_threshold}.")
            return f"No similar versions found for {source_version_id}."

        # 获取源版本对象，避免在循环中重复查询
        try:
            source_version = TestCaseVersion.objects.get(pk=source_version_id)
        except TestCaseVersion.DoesNotExist:
             logger.error(f"Source TestCaseVersion {source_version_id} disappeared during task execution.")
             return f"Source version {source_version_id} not found during pair creation."

        processed_count = 0
        created_count = 0
        updated_count = 0
        error_count = 0

        # 2. 遍历相似版本并存储配对信息
        for similar_version in similar_versions_qs:
            # 获取距离并计算相似度
            distance = getattr(similar_version, 'distance', None) # distance 是 annotate 添加的
            if distance is None:
                logger.warning(f"Could not find distance for similar version {similar_version.id}. Skipping.")
                error_count += 1
                continue
            similarity_score = 1.0 - distance

            # 确保 version_a.id < version_b.id 以满足 unique_together
            if source_version.id < similar_version.id:
                version_a = source_version
                version_b = similar_version
            else:
                version_a = similar_version
                version_b = source_version

            # 3. 使用 update_or_create 存储或更新记录
            try:
                pair, created = PotentialDuplicatePair.objects.update_or_create(
                    version_a=version_a,
                    version_b=version_b,
                    defaults={
                        'similarity_score': similarity_score,
                        'status': 'pending' # 每次找到都重置为待处理，或根据需求调整逻辑
                    }
                )
                processed_count += 1
                if created:
                    created_count += 1
                    # logger.info(f"Created pair: ({version_a.id}, {version_b.id}), Score: {similarity_score:.4f}")
                else:
                    updated_count += 1
                    # logger.info(f"Updated pair: ({version_a.id}, {version_b.id}), Score: {similarity_score:.4f}")

            except IntegrityError as e:
                # 理论上 update_or_create 能处理并发，但以防万一
                logger.error(f"Integrity error creating/updating pair ({version_a.id}, {version_b.id}): {e}")
                error_count += 1
            except Exception as e:
                logger.exception(f"Unexpected error creating/updating pair ({version_a.id}, {version_b.id})") # 使用 exception 记录 traceback
                error_count += 1

        summary = f"Finished for source {source_version_id}. Pairs created: {created_count}, updated: {updated_count}, errors: {error_count}."
        logger.info(summary)
        return summary

    except Exception as e:
        logger.exception(f"Error in find_and_store_duplicate_pairs_task for source version {source_version_id}")
        # 发生意外错误时重试整个任务
        raise self.retry(exc=e) 
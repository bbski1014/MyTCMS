from sentence_transformers import SentenceTransformer
from apps.testcases.models import TestCaseVersion
import numpy as np
import logging
from typing import Optional, List
from pgvector.django import CosineDistance
from django.db import models

logger = logging.getLogger(__name__)

# --- 模型加载 ---
MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
embedding_model = None
model_dimension = 768 # 预定义维度以供检查

try:
    embedding_model = SentenceTransformer(MODEL_NAME)
    loaded_dimension = embedding_model.get_sentence_embedding_dimension()
    if loaded_dimension != model_dimension:
        logger.warning(f"Model dimension mismatch! Expected {model_dimension}, but loaded model has {loaded_dimension}. Using loaded dimension.")
        model_dimension = loaded_dimension # 使用实际加载的维度
    logger.info(f"Sentence Transformer model '{MODEL_NAME}' loaded successfully. Dimension: {model_dimension}")
except Exception as e:
    logger.error(f"Failed to load Sentence Transformer model '{MODEL_NAME}': {e}")
    embedding_model = None

def get_embedding_model() -> Optional[SentenceTransformer]:
    """获取已加载的 embedding 模型实例"""
    return embedding_model

def extract_version_text(version: TestCaseVersion) -> str:
    """
    从 TestCaseVersion 实例中提取用于生成 embedding 的文本内容。
    """
    parts = []
    if version.title:
        parts.append(version.title.strip())
    if version.precondition:
        # TODO: Consider cleaning HTML/Markdown if content is rich text
        parts.append(version.precondition.strip())
    if version.steps_data and isinstance(version.steps_data, list):
        step_texts = []
        for step in version.steps_data:
            action = step.get('action', '')
            expected = step.get('expected_result', '')
            if action:
                # TODO: Consider cleaning HTML/Markdown
                step_texts.append(action.strip())
            if expected:
                # TODO: Consider cleaning HTML/Markdown
                step_texts.append(expected.strip())
        if step_texts:
            parts.append("\n".join(step_texts))
    full_text = "\n\n".join(filter(None, parts))
    return full_text

def generate_embedding(version: TestCaseVersion) -> Optional[List[float]]:
    """
    为给定的 TestCaseVersion 生成 embedding 向量。
    返回 float 列表或 None (如果失败)。
    pgvector Django 库通常期望接收列表而不是 numpy 数组。
    """
    model = get_embedding_model()
    if not model:
        logger.error("Embedding model is not available.")
        return None
    text_to_encode = extract_version_text(version)
    if not text_to_encode:
        logger.warning(f"No text content for TestCaseVersion {version.id}. Cannot generate embedding.")
        return None
    try:
        # encode() 返回 numpy 数组
        embedding_vector_np = model.encode(text_to_encode)
        # 转换为 Python 列表以存储到 VectorField
        embedding_vector_list = embedding_vector_np.tolist()
        # logger.info(f"Generated embedding for Version {version.id}")
        return embedding_vector_list
    except Exception as e:
        logger.error(f"Error generating embedding for TestCaseVersion {version.id}: {e}")
        return None

def find_similar_testcases(
    source_version_id: int,
    limit: int = 10,
    similarity_threshold: float = 0.90
) -> models.QuerySet[TestCaseVersion]:
    """
    查找与给定的 TestCaseVersion 语义相似的其他用例版本。

    Args:
        source_version_id: 源 TestCaseVersion 的 ID.
        limit: 最多返回多少个相似用例版本。
        similarity_threshold: 余弦相似度阈值 (值越高越相似, 1 为完全相同)。
                              对应数据库查询的距离阈值为 1 - similarity_threshold。

    Returns:
        一个包含相似 TestCaseVersion 对象的 QuerySet，按相似度（距离）排序。
        如果源版本不存在或没有 embedding，则返回空的 QuerySet。
    """
    try:
        source_version = TestCaseVersion.objects.get(pk=source_version_id)
    except TestCaseVersion.DoesNotExist:
        logger.error(f"Source TestCaseVersion {source_version_id} not found for similarity search.")
        return TestCaseVersion.objects.none() # 返回空 QuerySet

    if source_version.embedding is None:
        logger.warning(f"Source TestCaseVersion {source_version_id} does not have an embedding. Cannot perform similarity search.")
        return TestCaseVersion.objects.none()

    # 计算距离阈值 (pgvector 使用距离，0表示完全相同，值越小越相似)
    distance_threshold = 1.0 - similarity_threshold

    # 执行向量相似度查询
    # 使用 l2_distance, max_inner_product, or cosine_distance
    # cosine_distance 范围 0 到 2 (0 最相似)
    # 确保查询的字段是 'embedding'，并且与 source_version.embedding 比较
    similar_versions = TestCaseVersion.objects \
        .exclude(pk=source_version_id) \
        .filter(embedding__isnull=False) \
        .annotate(distance=CosineDistance('embedding', source_version.embedding)) \
        .filter(distance__lt=distance_threshold) \
        .order_by('distance')[:limit]

    count = similar_versions.count() # 获取实际找到的数量
    if count > 0:
         logger.info(f"Found {count} similar versions for Version {source_version_id} (threshold={similarity_threshold}, distance < {distance_threshold:.4f}).")
    # else:
    #      logger.info(f"No similar versions found for Version {source_version_id} above threshold {similarity_threshold}.")


    return similar_versions

# --- 使用示例 ---
# 在 Django shell 或视图/任务中:
# from apps.analysis.utils import find_similar_testcases
# potential_duplicates = find_similar_testcases(source_version_id=123, similarity_threshold=0.92, limit=5)
# for version in potential_duplicates:
#     # 注意这里的 version.distance 是 pgvector 计算出的距离，不是相似度
#     similarity = 1.0 - version.distance
#     print(f"Potential duplicate: ID={version.pk}, Title={version.title}, Distance={version.distance:.4f}, Similarity={similarity:.4f}") 
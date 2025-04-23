from sentence_transformers import SentenceTransformer
from apps.testcases.models import TestCaseVersion
import numpy as np
import logging
from typing import Optional, List

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
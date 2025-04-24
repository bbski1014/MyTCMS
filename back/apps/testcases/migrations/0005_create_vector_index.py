# back/apps/testcases/migrations/0005_create_vector_index.py
from django.db import migrations
from pgvector.django import HnswIndex

class Migration(migrations.Migration):

    # !!! 重要: 确保这里的依赖项指向你刚刚为添加 embedding 字段生成的那个迁移文件 !!!
    dependencies = [
        ('testcases', '0004_testcaseversion_embedding_and_more'), # <--- 用户需要确认或修改这里
    ]

    operations = [
        # 使用 migrations.AddIndex 来添加 HNSW 索引
        migrations.AddIndex(
            # 指定模型名称
            model_name='testcaseversion',
            # 将 HnswIndex 实例作为 index 参数传递
            index=HnswIndex(
                name='tcversion_emb_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]
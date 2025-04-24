# back/apps/analysis/models.py
from django.db import models
# 从 testcases 应用导入 TestCaseVersion 模型
from apps.testcases.models import TestCaseVersion

# Create your models here.

# We will define the PotentialDuplicatePair model here later.
class PotentialDuplicatePair(models.Model):
    """
    存储通过相似度分析识别出的潜在重复测试用例版本对。
    """
    version_a = models.ForeignKey(
        TestCaseVersion,
        on_delete=models.CASCADE,
        related_name='duplicate_pairs_a',
        verbose_name="测试用例版本 A"
    )
    version_b = models.ForeignKey(
        TestCaseVersion,
        on_delete=models.CASCADE,
        related_name='duplicate_pairs_b',
        verbose_name="测试用例版本 B"
    )
    similarity_score = models.FloatField(
        verbose_name="相似度分数",
        help_text="计算得到的嵌入向量间的相似度分数（例如余弦相似度）。"
    )
    # 状态字段，用于用户评审
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待处理'),
            ('confirmed', '已确认重复'),
            ('ignored', '非重复'),
        ],
        default='pending',
        verbose_name="状态"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="检测时间")

    class Meta:
        verbose_name = "潜在重复用例对"
        verbose_name_plural = verbose_name
        # 确保同一对版本（无论顺序）只存储一次。
        # 需要在创建记录的逻辑中保证 version_a 的 ID 总是小于 version_b 的 ID。
        unique_together = ('version_a', 'version_b')
        # 添加约束，防止一个版本与自身配对。
        constraints = [
            models.CheckConstraint(
                check=~models.Q(version_a=models.F('version_b')),
                name='prevent_self_pairing'
            )
        ]
        # 默认按相似度降序、检测时间降序排列
        ordering = ['-similarity_score', '-created_at']

    def __str__(self):
        # 提供更易读的字符串表示
        return f"潜在重复: {self.version_a} vs {self.version_b} (分数: {self.similarity_score:.4f})" 
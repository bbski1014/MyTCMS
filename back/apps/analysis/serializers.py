from rest_framework import serializers
from apps.testcases.models import TestCaseVersion
from .models import PotentialDuplicatePair

class NestedTestCaseVersionSerializer(serializers.ModelSerializer):
    """
    用于在 PotentialDuplicatePair 中嵌套显示的简化版 TestCaseVersion 序列化器。
    """
    # 可以根据前端需要添加更多字段，如 'version_number', 'project_id' 等
    class Meta:
        model = TestCaseVersion
        fields = ['id', 'title', 'version_number'] # 包含 ID, 标题, 版本号


class PotentialDuplicatePairSerializer(serializers.ModelSerializer):
    """
    序列化 PotentialDuplicatePair 模型，包含嵌套的版本信息。
    """
    # 使用嵌套序列化器来展示 version_a 和 version_b 的关键信息
    version_a = NestedTestCaseVersionSerializer(read_only=True)
    version_b = NestedTestCaseVersionSerializer(read_only=True)
    # 可以选择性地添加一个计算字段来表示相似度百分比
    similarity_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PotentialDuplicatePair
        fields = [
            'id',
            'version_a',
            'version_b',
            'similarity_score',
            'similarity_percentage', # 添加的计算字段
            'status',
            'created_at'
        ]
        read_only_fields = ['similarity_score', 'created_at'] # 这些字段通常由后端计算或自动生成

    def get_similarity_percentage(self, obj):
        # 将相似度分数转换为更易读的百分比，保留两位小数
        return f"{obj.similarity_score * 100:.2f}%" 
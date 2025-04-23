from django.shortcuts import render

# Create your views here.
import os
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser # 支持文件上传

class FileUploadView(APIView):
    """
    通用文件（图片）上传视图，适配 WangEditor V5
    """
    permission_classes = [IsAuthenticated] # 确保用户已登录
    parser_classes = [MultiPartParser, FormParser] # 支持 multipart/form-data

    def post(self, request, *args, **kwargs):
        # WangEditor V5 默认使用 'wangeditor-uploaded-image' 作为 field name
        # 如果前端配置了 fieldName，需要用 request.FILES.get(fieldName)
        file_obj = request.FILES.get('wangeditor-uploaded-image')

        if not file_obj:
            # 如果没找到，尝试用通用的 'file' (以防万一)
            file_obj = request.FILES.get('file')
            if not file_obj:
                return Response({
                    "errno": 1,
                    "message": "未找到上传的文件。"
                }, status=status.HTTP_400_BAD_REQUEST)

        # 1. 文件类型验证 (简单示例)
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file_obj.content_type not in allowed_types:
            return Response({
                "errno": 1,
                "message": f"不支持的文件类型: {file_obj.content_type}。请上传图片文件。"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. 文件大小验证 (例如：限制 5MB)
        max_size = 5 * 1024 * 1024 # 5MB
        if file_obj.size > max_size:
            return Response({
                "errno": 1,
                "message": f"文件大小不能超过 {max_size // 1024 // 1024}MB。"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. 生成唯一文件名并确定保存路径
        # 获取文件扩展名
        ext = os.path.splitext(file_obj.name)[1]
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}{ext}"
        # 定义保存子目录 (例如：uploads/images/年/月/)
        upload_dir = os.path.join('uploads', 'images') # 可根据需要添加日期等
        save_path = os.path.join(upload_dir, unique_filename)

        try:
            # 4. 保存文件
            # default_storage 会根据 settings.DEFAULT_FILE_STORAGE 处理文件存储
            # 默认是 FileSystemStorage，保存到 MEDIA_ROOT
            actual_path = default_storage.save(save_path, file_obj)

            # 5. 构造文件访问 URL
            file_url = default_storage.url(actual_path)
            # 如果是相对 URL，确保拼接上域名 (如果需要跨域或绝对 URL)
            # if not file_url.startswith(('http://', 'https://')):
            #    file_url = request.build_absolute_uri(file_url)

            # 6. 返回符合 WangEditor V5 格式的成功响应
            return Response({
                "errno": 0,
                "data": {
                    "url": file_url,
                    "alt": "", # alt 可以为空
                    "href": "" # href 可以为空
                }
            }, status=status.HTTP_201_CREATED) # 或者 status.HTTP_200_OK

        except Exception as e:
            # 处理保存文件过程中可能出现的异常
            print(f"文件上传失败: {e}") # 打印错误日志
            return Response({
                "errno": 1,
                "message": f"文件上传失败: {e}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

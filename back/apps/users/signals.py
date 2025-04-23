from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """当用户创建时，自动创建用户资料"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """当用户保存时，同步保存用户资料"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # 如果用户没有资料（可能是旧数据），则创建一个
        UserProfile.objects.create(user=instance) 
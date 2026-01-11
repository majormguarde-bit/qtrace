from rest_framework import viewsets, permissions
from .models import Media
from .serializers import MediaSerializer

class MediaViewSet(viewsets.ModelViewSet):
    """
    ViewSet для медиа-файлов.
    Сотрудники видят только свои файлы.
    Администраторы видят все файлы.
    """
    serializer_class = MediaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        from users_app.models import TenantUser
        
        if isinstance(user, TenantUser):
            if user.role == 'ADMIN':
                return Media.objects.all()
            return Media.objects.filter(uploaded_by=user)
        elif getattr(user, 'is_superuser', False):
            return Media.objects.all()
        return Media.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        from users_app.models import TenantUser
        
        if isinstance(user, TenantUser):
            serializer.save(uploaded_by=user)
        elif getattr(user, 'is_superuser', False):
            serializer.save()
        else:
            pass

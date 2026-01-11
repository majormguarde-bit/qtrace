from rest_framework import viewsets, permissions
from .models import Task
from .serializers import TaskSerializer
from users_app.permissions import IsTenantAdmin, IsTenantWorker

class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet для задач.
    Сотрудники видят только свои задачи.
    Администраторы видят все задачи.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        from users_app.models import TenantUser
        
        if isinstance(user, TenantUser):
            if user.role == 'ADMIN':
                return Task.objects.all()
            return Task.objects.filter(assigned_to=user)
        elif getattr(user, 'is_superuser', False):
            return Task.objects.all()
        return Task.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        from users_app.models import TenantUser
        
        if isinstance(user, TenantUser):
            serializer.save(assigned_to=user)
        elif getattr(user, 'is_superuser', False):
            serializer.save()
        else:
            # Не должен попадать сюда из-за прав доступа, но для безопасности
            pass

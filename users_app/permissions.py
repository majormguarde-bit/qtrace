from rest_framework import permissions

class IsTenantAdmin(permissions.BasePermission):
    """
    Разрешает доступ только администраторам тенанта или системным суперпользователям.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Разрешаем доступ администраторам тенанта
        if getattr(request.user, 'role', None) == 'ADMIN':
            return True
            
        # Разрешаем доступ системным суперпользователям
        if getattr(request.user, 'is_superuser', False):
            return True
            
        return False

class IsTenantWorker(permissions.BasePermission):
    """
    Разрешает доступ только работникам тенанта.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   getattr(request.user, 'role', None) == 'WORKER')

class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    Администраторы (тенанта или системные) могут редактировать, остальные - только смотреть.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
            
        if not (request.user and request.user.is_authenticated):
            return False
            
        if getattr(request.user, 'role', None) == 'ADMIN':
            return True
            
        if getattr(request.user, 'is_superuser', False):
            return True
            
        return False

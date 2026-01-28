from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import TenantUser
from .serializers import TenantUserSerializer, CustomTokenObtainPairSerializer
from .permissions import IsTenantAdmin, IsTenantAdminOrReadOnly


@api_view(['POST'])
@permission_classes([AllowAny])
def token_obtain_pair(request):
    """Endpoint для получения токена"""
    serializer = CustomTokenObtainPairSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями.
    Полный доступ только у Администратора тенанта.
    """
    queryset = TenantUser.objects.all()
    serializer_class = TenantUserSerializer
    permission_classes = (IsTenantAdmin,)
    
    def get_queryset(self):
        """
        Админ видит всех.
        Обычный пользователь - только себя (если разрешим list, но пока IsTenantAdmin блокирует).
        """
        return TenantUser.objects.all()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Получить данные текущего пользователя (доступно всем авторизованным)"""
        user = request.user
        if not isinstance(user, TenantUser):
            return Response({
                "username": getattr(user, 'username', 'unknown'),
                "is_system_user": True,
                "is_superuser": getattr(user, 'is_superuser', False)
            })
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsTenantAdmin])
    def create_employee(self, request):
        """
        Создание сотрудника администратором.
        """
        serializer = TenantUserSerializer(data=request.data)
        if serializer.is_valid():
            # Принудительно ставим роль WORKER, если не указана, или проверяем валидность
            role = request.data.get('role', 'WORKER')
            if role not in ['ADMIN', 'WORKER']:
                 return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
                 
            user = TenantUser(**serializer.validated_data)
            password = request.data.get('password')
            if not password:
                return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            user.set_password(password)
            user.role = role
            user.save()
            return Response(TenantUserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Удаляем метод register, так как регистрация теперь только через админа или при создании тенанта

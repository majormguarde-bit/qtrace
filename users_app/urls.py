from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, token_obtain_pair

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', token_obtain_pair, name='token_obtain_pair'),
]

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import TenantRegistrationViewSet, api_duration_units, api_materials, api_positions

router = DefaultRouter()
router.register(r'registration', TenantRegistrationViewSet, basename='tenant-registration')

urlpatterns = [
    *router.urls,
    path('duration-units/', api_duration_units, name='api_duration_units'),
    path('materials/', api_materials, name='api_materials'),
    path('positions/', api_positions, name='api_positions'),
    path('positions/create/', api_positions, name='api_positions_create'),
]

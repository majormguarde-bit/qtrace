from rest_framework.routers import DefaultRouter
from .views import TenantRegistrationViewSet

router = DefaultRouter()
router.register(r'registration', TenantRegistrationViewSet, basename='tenant-registration')

urlpatterns = router.urls

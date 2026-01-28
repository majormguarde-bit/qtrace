from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    ActivityCategoryViewSet,
    TaskTemplateViewSet,
    TemplateProposalViewSet,
    TemplateFilterPreferenceViewSet,
)

app_name = 'task_templates'

router = DefaultRouter()
router.register(r'categories', ActivityCategoryViewSet, basename='category')
router.register(r'templates', TaskTemplateViewSet, basename='template')
router.register(r'proposals', TemplateProposalViewSet, basename='proposal')
router.register(r'filter-preferences', TemplateFilterPreferenceViewSet, basename='filter-preference')

urlpatterns = [
    path('', include(router.urls)),
]

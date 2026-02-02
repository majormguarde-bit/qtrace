from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    TenantRegistrationViewSet, api_duration_units, api_materials, api_positions, api_units_of_measure,
    api_activity_categories,
    FeedbackListView, FeedbackDetailView, FeedbackUpdateView, create_feedback
)

router = DefaultRouter()
router.register(r'registration', TenantRegistrationViewSet, basename='tenant-registration')

urlpatterns = [
    *router.urls,
    path('activity-categories/', api_activity_categories, name='api_activity_categories'),
    path('duration-units/', api_duration_units, name='api_duration_units'),
    path('units-of-measure/', api_units_of_measure, name='api_units_of_measure'),
    path('materials/', api_materials, name='api_materials'),
    path('positions/', api_positions, name='api_positions'),
    path('positions/create/', api_positions, name='api_positions_create'),
    
    # Feedback URLs
    path('feedback/', FeedbackListView.as_view(), name='superuser_feedback_list'),
    path('feedback/<int:pk>/', FeedbackDetailView.as_view(), name='superuser_feedback_detail'),
    path('feedback/<int:pk>/edit/', FeedbackUpdateView.as_view(), name='superuser_feedback_edit'),
    path('api/feedback/create/', create_feedback, name='api_create_feedback'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.ai_chat_api, name='ai_chat_api'),
    path('api/analyze-photo/', views.ai_analyze_photo, name='ai_analyze_photo'),
]

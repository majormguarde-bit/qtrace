from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.TenantLoginView.as_view(), name='login'),
    path('logout/', views.TenantLogoutView.as_view(), name='logout'),
    path('help/', views.HelpView.as_view(), name='help'),
    
    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_edit'),
    
    # Media
    path('media/', views.MediaListView.as_view(), name='media_list'),
    path('media/upload/', views.MediaCreateView.as_view(), name='media_create'),
    path('media/record/', views.MediaVideoRecordView.as_view(), name='media_record'),
    path('media/<int:pk>/delete/', views.MediaDeleteView.as_view(), name='media_delete'),

    # Employees
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),

    # Departments
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),

    # Positions
    path('positions/', views.PositionListView.as_view(), name='position_list'),
    path('positions/<int:pk>/edit/', views.PositionUpdateView.as_view(), name='position_edit'),
    path('positions/<int:pk>/delete/', views.PositionDeleteView.as_view(), name='position_delete'),
    path('positions/create-ajax/', views.PositionCreateAjaxView.as_view(), name='position_create_ajax'),
    
    # Task AJAX Management
    path('tasks/<int:pk>/status-update-ajax/', views.TaskStatusUpdateAjaxView.as_view(), name='task_status_update_ajax'),

    # Stages
    path('stages/<int:pk>/toggle-ajax/', views.TaskStageToggleAjaxView.as_view(), name='task_stage_toggle_ajax'),
    path('stages/<int:pk>/status-update-ajax/', views.TaskStageStatusUpdateAjaxView.as_view(), name='task_stage_status_update_ajax'),
    path('stages/<int:pk>/media-upload-ajax/', views.TaskStageMediaUploadAjaxView.as_view(), name='task_stage_media_upload_ajax'),
    path('tasks/<int:pk>/stages/create-ajax/', views.TaskStageCreateAjaxView.as_view(), name='task_stage_create_ajax'),
]

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
    path('tasks/delete-selected/', views.delete_selected_tasks, name='delete_selected_tasks'),
    path('tasks/clear-all/', views.clear_all_tasks, name='clear_all_tasks'),

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
    path('positions/create/', views.PositionCreateView.as_view(), name='position_create'),
    path('positions/<int:pk>/edit/', views.PositionUpdateView.as_view(), name='position_edit'),
    path('positions/<int:pk>/delete/', views.PositionDeleteView.as_view(), name='position_delete'),
    path('positions/create-ajax/', views.PositionCreateAjaxView.as_view(), name='position_create_ajax'),
    
    # Duration Units (Единицы времени)
    path('duration-units/', views.DurationUnitListView.as_view(), name='duration_unit_list'),
    path('duration-units/create/', views.DurationUnitCreateView.as_view(), name='duration_unit_create'),
    path('duration-units/<int:pk>/edit/', views.DurationUnitUpdateView.as_view(), name='duration_unit_edit'),
    path('duration-units/<int:pk>/delete/', views.DurationUnitDeleteView.as_view(), name='duration_unit_delete'),
    
    # Materials (Материалы)
    path('materials/', views.MaterialListView.as_view(), name='material_list'),
    path('materials/create/', views.MaterialCreateView.as_view(), name='material_create'),
    path('materials/<int:pk>/edit/', views.MaterialUpdateView.as_view(), name='material_edit'),
    path('materials/<int:pk>/delete/', views.MaterialDeleteView.as_view(), name='material_delete'),
    
    # Task AJAX Management
    path('tasks/<int:pk>/status-update-ajax/', views.TaskStatusUpdateAjaxView.as_view(), name='task_status_update_ajax'),

    # Stages
    path('stages/<int:pk>/toggle-ajax/', views.TaskStageToggleAjaxView.as_view(), name='task_stage_toggle_ajax'),
    path('stages/<int:pk>/status-update-ajax/', views.TaskStageStatusUpdateAjaxView.as_view(), name='task_stage_status_update_ajax'),
    path('stages/<int:pk>/media-upload-ajax/', views.TaskStageMediaUploadAjaxView.as_view(), name='task_stage_media_upload_ajax'),
    path('tasks/<int:pk>/stages/create-ajax/', views.TaskStageCreateAjaxView.as_view(), name='task_stage_create_ajax'),
    
    # Task Templates (Global)
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/edit/', views.TemplateEditView.as_view(), name='template_edit'),
    path('templates/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('template/<int:pk>/stages/', views.get_template_stages, name='get_template_stages'),
    
    # Task Templates (Local)
    path('my-templates/', views.LocalTemplateListView.as_view(), name='local_template_list'),
    path('my-templates/create/', views.LocalTemplateCreateView.as_view(), name='local_template_create'),
    path('my-templates/<int:pk>/edit/', views.LocalTemplateEditView.as_view(), name='local_template_edit'),
    path('my-templates/<int:pk>/diagram/', views.LocalTemplateDiagramView.as_view(), name='local_template_diagram'),
    path('my-templates/<int:pk>/delete/', views.LocalTemplateDeleteView.as_view(), name='local_template_delete'),
    path('templates/<int:pk>/detail/', views.TemplateDetailAjaxView.as_view(), name='template_detail_ajax'),
    path('templates/copy/', views.CopyGlobalTemplateView.as_view(), name='copy_global_template'),
    
    # Template Proposals
    path('my-proposals/', views.MyProposalsView.as_view(), name='my_proposals'),
    path('proposals/', views.AllProposalsView.as_view(), name='all_proposals'),
    path('proposals/<int:pk>/approve/', views.approve_proposal, name='approve_proposal'),
    path('proposals/<int:pk>/reject/', views.reject_proposal, name='reject_proposal'),
    path('proposals/<int:pk>/withdraw/', views.withdraw_proposal, name='withdraw_proposal'),
    
    # Template Export/Import
    path('templates/<int:pk>/export/', views.export_template, name='export_template'),
    path('templates/import/', views.import_template, name='import_template'),
    
    # API для справочников
    path('api/positions/', views.api_get_positions, name='api_get_positions'),
    path('api/positions/create/', views.api_create_position, name='api_create_position'),
    path('api/duration-units/', views.api_get_duration_units, name='api_get_duration_units'),
    path('api/materials/', views.api_get_materials, name='api_get_materials'),
    path('api/units/', views.api_get_units, name='api_get_units'),
    path('api/employees/', views.api_get_employees, name='api_get_employees'),
    
    # Admin logging
    path('api/log-password-generation/', views.log_password_generation, name='log_password_generation'),
    path('logs/', views.admin_log_list, name='admin_log_list'),
    path('logs/clear-filtered/', views.clear_admin_logs_filtered, name='clear_admin_logs_filtered'),
    path('logs/clear-all/', views.clear_admin_logs_all, name='clear_admin_logs_all'),
]

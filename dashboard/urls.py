from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.TenantLoginView.as_view(), name='login'),
    path('quick-login/<str:token>/', views.quick_login, name='quick_login'),
    path('logout/', views.TenantLogoutView.as_view(), name='logout'),
    path('help/', views.HelpView.as_view(), name='help'),
    
    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_edit'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('tasks/<int:pk>/production-order/', views.ProductionOrderDetailView.as_view(), name='production_order'),
    
    # Media
    path('media/', views.MediaListView.as_view(), name='media_list'),
    path('media/upload/', views.MediaCreateView.as_view(), name='media_create'),
    path('media/record/', views.MediaVideoRecordView.as_view(), name='media_record'),
    path('media/<int:pk>/delete/', views.MediaDeleteView.as_view(), name='media_delete'),

    # Employees
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/qr/', views.generate_qr_code, name='employee_qr'),
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
    
    # Task AJAX Management
    path('tasks/<int:pk>/status-update-ajax/', views.TaskStatusUpdateAjaxView.as_view(), name='task_status_update_ajax'),
    
    # Task Templates
    path('templates/', views.TaskTemplateListView.as_view(), name='task_template_list'),
    path('templates/create/', views.TaskTemplateCreateView.as_view(), name='task_template_create'),
    path('templates/<int:pk>/edit/', views.TaskTemplateUpdateView.as_view(), name='task_template_edit'),
    path('templates/<int:pk>/delete/', views.TaskTemplateDeleteView.as_view(), name='task_template_delete'),
    path('templates/<int:pk>/create-task/', views.CreateTaskFromTemplateAjaxView.as_view(), name='create_task_from_template_ajax'),

    # Stages
    path('stages/<int:pk>/toggle-ajax/', views.TaskStageToggleAjaxView.as_view(), name='task_stage_toggle_ajax'),
    path('stages/<int:pk>/status-update-ajax/', views.TaskStageStatusUpdateAjaxView.as_view(), name='task_stage_status_update_ajax'),
    path('stages/<int:pk>/media-upload-ajax/', views.TaskStageMediaUploadAjaxView.as_view(), name='task_stage_media_upload_ajax'),
    path('tasks/<int:pk>/stages/create-ajax/', views.TaskStageCreateAjaxView.as_view(), name='task_stage_create_ajax'),

    # Reference Books (Справочники)
    # 1. Изделия
    path('references/products/', views.ProductListView.as_view(), name='product_list'),
    path('references/products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('references/products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('references/products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # 2. Спецификации
    path('references/specifications/', views.SpecificationListView.as_view(), name='specification_list'),
    path('references/specifications/create/', views.SpecificationCreateView.as_view(), name='specification_list_create'),
    path('references/specifications/<int:pk>/edit/', views.SpecificationUpdateView.as_view(), name='specification_edit'),
    path('references/specifications/<int:pk>/delete/', views.SpecificationDeleteView.as_view(), name='specification_delete'),
    
    # 3. Накладные
    path('references/transfer-notes/', views.TransferNoteListView.as_view(), name='transfer_note_list'),
    path('references/transfer-notes/create/', views.TransferNoteCreateView.as_view(), name='transfer_note_create'),
    path('references/transfer-notes/<int:pk>/edit/', views.TransferNoteUpdateView.as_view(), name='transfer_note_edit'),
    path('references/transfer-notes/<int:pk>/delete/', views.TransferNoteDeleteView.as_view(), name='transfer_note_delete'),
    
    # 4. Операции
    path('references/operations/', views.OperationListView.as_view(), name='operation_list'),
    path('references/operations/create/', views.OperationCreateView.as_view(), name='operation_create'),
    path('references/operations/<int:pk>/edit/', views.OperationUpdateView.as_view(), name='operation_edit'),
    path('references/operations/<int:pk>/delete/', views.OperationDeleteView.as_view(), name='operation_delete'),
    
    # 5. Заказы
    path('references/client-orders/', views.ClientOrderListView.as_view(), name='client_order_list'),
    path('references/client-orders/create/', views.ClientOrderCreateView.as_view(), name='client_order_create'),
    path('references/client-orders/<int:pk>/edit/', views.ClientOrderUpdateView.as_view(), name='client_order_edit'),
    path('references/client-orders/<int:pk>/delete/', views.ClientOrderDeleteView.as_view(), name='client_order_delete'),
]

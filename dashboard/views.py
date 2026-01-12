from django.shortcuts import render, redirect, get_object_or_404
import os
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django import forms
from django.forms import inlineformset_factory
from django.contrib import messages

from django.db.models import Sum, Max, Q, Prefetch
from tasks.models import (
    Task, TaskStage, TaskTemplate, TaskTemplateStage, TaskStagePause,
    Product, Specification, TransferNote, Operation, ClientOrder
)
from media_app.models import Media
from users_app.models import TenantUser, Department, Position
from users_app.utils import generate_quick_login_token, validate_quick_login_token
from django.contrib.auth import login
import qrcode
from io import BytesIO
import base64
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

# --- Mixins ---

class AdminRequiredMixin:
    """Ограничение доступа: только для администраторов тенанта или суперпользователей"""
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
            messages.error(request, "Доступ разрешен только администраторам.")
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)

class SearchableListViewMixin:
    """Примесь для поиска и пагинации в справочниках"""
    paginate_by = 10
    search_fields = []

    def get_paginate_by(self, queryset):
        return self.request.GET.get('paginate_by', self.paginate_by)

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        if q and self.search_fields:
            search_query = Q()
            for field in self.search_fields:
                search_query |= Q(**{f"{field}__icontains": q})
            queryset = queryset.filter(search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['paginate_by'] = self.get_paginate_by(None)
        
        # Сохраняем все GET-параметры
        params = self.request.GET.copy()
        context['current_params'] = params.urlencode()
        
        # Сохраняем параметры для пагинации (исключаем 'page')
        if 'page' in params:
            del params['page']
        context['page_params'] = params.urlencode()
        
        return context

class PreserveQueryParamsMixin:
    """Примесь для сохранения параметров поиска/пагинации при перенаправлениях после сохранения"""
    def get_success_url(self):
        url = super().get_success_url()
        params = self.request.GET.urlencode()
        if params:
            return f"{url}?{params}"
        return url


@login_required
def home(request):
    user = request.user
    tenant = getattr(request, 'tenant', None)
    
    # Цвета для карточек канбана
    status_colors = {
        'OPEN': {'border': '#B0BEC5', 'bg': '#F8F9FA'},
        'PAUSE': {'border': '#BA68C8', 'bg': '#F3E5F5'},
        'CONTINUE': {'border': '#64B5F6', 'bg': '#E3F2FD'},
        'IMPORTANT': {'border': '#E57373', 'bg': '#FFEBEE'},
        'CLOSE': {'border': '#81C784', 'bg': '#E8F5E9'},
        'DEFAULT': {'border': '#B0BEC5', 'bg': '#F8F9FA'}
    }

    # Context data
    context = {
        'tasks_count': 0,
        'media_count': 0,
        'employees_count': 0,
        'recent_tasks': [],
        'tenant': tenant,
        'storage_used_bytes': 0,
        'storage_used_mb': 0,
        'storage_limit_gb': 0,
        'storage_percent': 0,
        'users_limit': 0,
        'users_percent': 0,
        'subscription_end_date': None,
        'days_left': None,
        'status_colors': status_colors,
    }
    
    # Role-based data fetching
    user_role = None
    # 1. Проверяем, является ли пользователь TenantUser
    if hasattr(user, 'role'):
        user_role = user.role
    # 2. Если это системный пользователь (User), проверяем, суперпользователь ли он
    elif getattr(user, 'is_superuser', False):
        user_role = 'ADMIN'
    else:
        # Обычный системный пользователь не должен иметь доступа к данным тенанта
        return render(request, 'dashboard/home.html', context)
    
    context['user_role'] = user_role
    
    # Общая статистика и данные по тарифу
    tasks_qs = Task.objects.none()
    if user_role == 'ADMIN':
        tasks_qs = Task.objects.all().prefetch_related('stages', 'assigned_to')
    elif hasattr(user, 'role'):
        # Для всех не-администраторов фильтруем этапы по назначенному исполнителю
        stages_prefetch = Prefetch(
            'stages',
            queryset=TaskStage.objects.filter(assigned_executor=user),
            to_attr='visible_stages'
        )
        tasks_qs = Task.objects.filter(
            (Q(assigned_to=user) | Q(stages__assigned_executor=user)) & Q(production_manager_signed=True)
        ).distinct().prefetch_related(stages_prefetch, 'assigned_to')

    context['tasks_count'] = tasks_qs.count()
    context['media_count'] = Media.objects.count() if user_role == 'ADMIN' else Media.objects.filter(uploaded_by=user).count()
    context['employees_count'] = TenantUser.objects.count()
    context['recent_tasks'] = tasks_qs.order_by('-created_at')[:5]
    
    # Данные по тарифу (доступны всем, но расчеты общие для предприятия)
    if tenant and tenant.subscription_plan:
        plan = tenant.subscription_plan
        context['users_limit'] = plan.max_users
        if plan.max_users > 0:
            context['users_percent'] = min(int((context['employees_count'] / plan.max_users) * 100), 100)
        
        context['storage_limit_gb'] = plan.storage_gb
        # Расчет занимаемого места через поле file_size
        total_bytes = Media.objects.aggregate(total=Sum('file_size'))['total'] or 0
        context['storage_used_bytes'] = total_bytes
        context['storage_used_mb'] = round(total_bytes / (1024 * 1024), 2)
        if plan.storage_gb > 0:
            limit_bytes = plan.storage_gb * 1024 * 1024 * 1024
            context['storage_percent'] = min(int((total_bytes / limit_bytes) * 100), 100)
        
        context['subscription_end_date'] = tenant.subscription_end_date
        if tenant.subscription_end_date:
            from django.utils import timezone
            delta = tenant.subscription_end_date - timezone.now().date()
            context['days_left'] = delta.days
    
    # Filters
    assigned_to_id = request.GET.get('assigned_to')
    priority = request.GET.get('priority')
    is_important = request.GET.get('important') == 'on'
    is_overdue = request.GET.get('overdue') == 'on'
    
    if assigned_to_id:
        tasks_qs = tasks_qs.filter(assigned_to_id=assigned_to_id)
    if priority:
        tasks_qs = tasks_qs.filter(priority=priority)
    if is_important:
        tasks_qs = tasks_qs.filter(status='IMPORTANT')
    if is_overdue:
        tasks_qs = tasks_qs.filter(deadline__lt=timezone.now().date(), is_completed=False)

    # Kanban data
    kanban_data = {
        'OPEN': tasks_qs.filter(status='OPEN'),
        'CONTINUE': tasks_qs.filter(status='CONTINUE'),
        'PAUSE': tasks_qs.filter(status='PAUSE'),
        'IMPORTANT': tasks_qs.filter(status='IMPORTANT'),
        'CLOSE': tasks_qs.filter(status='CLOSE'),
    }
    
    # Calculate totals for each column
    column_totals = {}
    for status, qs in kanban_data.items():
        total = 0
        for task in qs:
            total += task.total_damage
        column_totals[status] = total
    
    context['kanban_tasks'] = kanban_data
    context['column_totals'] = column_totals
    context['all_users'] = TenantUser.objects.all()
    context['priority_choices'] = Task.PRIORITY_CHOICES
    context['today'] = timezone.now().date()
    
    return render(request, 'dashboard/home.html', context)

class TenantLoginView(auth_views.LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Определяем базовый домен для ссылки "На главную"
        host = self.request.get_host().split(':')[0]
        if '.localhost' in self.request.get_host() or host == 'localhost' or host == '127.0.0.1':
            context['base_url'] = f"http://localhost:{self.request.get_port()}"
        else:
            # Пытаемся выделить основной домен из текущего хоста (например, из apple.qtrace.ru получить qtrace.ru)
            parts = self.request.get_host().split('.')
            if len(parts) > 2:
                context['base_url'] = f"https://{'.'.join(parts[-2:])}"
            else:
                context['base_url'] = f"https://{self.request.get_host()}"
        return context
    
    def get_success_url(self):
        return '/'

class TenantLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            from django.contrib.auth import logout
            logout(request)
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

# --- Tasks ---

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'external_id', 'title', 'description', 'process_type', 
            'priority', 'control_object', 'source', 'assigned_to', 'manager', 'status', 'is_completed'
        ]
        labels = {
            'external_id': 'ID задачи (напр. QA-001)',
            'title': 'Заголовок',
            'description': 'Описание',
            'process_type': 'Тип процесса',
            'priority': 'Приоритет',
            'control_object': 'Объект контроля',
            'source': 'Источник',
            'assigned_to': 'Исполнитель',
            'manager': 'Ответственный менеджер',
            'status': 'Статус',
            'is_completed': 'Завершена'
        }
        widgets = {
            'external_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'QA-2026-XXXX'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'process_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'control_object': forms.TextInput(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if hasattr(user, 'role'):
            user_role = user.role
        elif getattr(user, 'is_superuser', False):
            user_role = 'ADMIN'
        else:
            user_role = 'WORKER'
            
        if user and user_role != 'ADMIN':
            if 'assigned_to' in self.fields:
                self.fields.pop('assigned_to')

TaskStageFormSet = inlineformset_factory(
    Task, TaskStage,
    fields=[
        'name', 'assigned_executor', 'planned_duration', 'actual_duration', 
        'status', 'reason_code', 'defect_criticality', 'damage_amount', 
        'order', 'data_type', 'data_value'
    ],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название этапа', 'list': 'stage-names-list'}),
        'assigned_executor': forms.Select(attrs={'class': 'form-select'}),
        'planned_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'План (мин)'}),
        'actual_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Факт (мин)'}),
        'status': forms.Select(attrs={'class': 'form-select'}),
        'reason_code': forms.Select(attrs={'class': 'form-select'}),
        'defect_criticality': forms.Select(attrs={'class': 'form-select'}),
        'damage_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '№'}),
        'data_type': forms.Select(attrs={'class': 'form-select'}),
        'data_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'placeholder': 'Результат (число, текст или JSON)'}),
    }
)

class ProductionOrderWorkerForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'external_id', 'deadline', 'client_name', 'manager', 'product_name', 'article_number',
            'pcb_revision', 'quantity', 'panel_type', 'bom_id', 'project_files_url',
            'firmware_version', 'stencil_id', 'description', 'transfer_note_number',
            'kit_status', 'deficit_list', 'kit_received_date', 'finished_goods_date', 'status', 'priority',
            'quality_defects', 'repair_quantity', 'scrap_quantity', 
            'actual_produced_quantity', 'leftover_components'
        ]
        widgets = {
            'quality_defects': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'repair_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'scrap_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_produced_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'leftover_components': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            
            # Read-only widgets
            'external_id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'type': 'date'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'manager': forms.Select(attrs={'class': 'form-select', 'disabled': 'disabled'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'article_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'pcb_revision': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'panel_type': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'bom_id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'project_files_url': forms.URLInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'firmware_version': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'stencil_id': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'readonly': 'readonly', 'rows': 2}),
            'transfer_note_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'kit_status': forms.Select(attrs={'class': 'form-select', 'disabled': 'disabled'}),
            'deficit_list': forms.Textarea(attrs={'class': 'form-control', 'readonly': 'readonly', 'rows': 2}),
            'kit_received_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'type': 'date'}),
            'finished_goods_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select', 'disabled': 'disabled'}),
            'priority': forms.Select(attrs={'class': 'form-select', 'disabled': 'disabled'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable fields that are not editable by worker
        editable_fields = ['quality_defects', 'repair_quantity', 'scrap_quantity', 'actual_produced_quantity', 'leftover_components']
        for name, field in self.fields.items():
            if name not in editable_fields:
                field.disabled = True

class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'external_id', 'deadline', 'client_name', 'manager', 'product_name', 'article_number',
            'pcb_revision', 'quantity', 'panel_type', 'bom_id', 'project_files_url',
            'firmware_version', 'stencil_id', 'description', 'transfer_note_number',
            'kit_status', 'deficit_list', 'kit_received_date', 'quality_defects',
            'repair_quantity', 'scrap_quantity', 'actual_produced_quantity',
            'leftover_components', 'finished_goods_date', 'production_manager_signed', 'status', 'priority'
        ]
        widgets = {
            'external_id': forms.TextInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'list': 'client-names-list'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'list': 'product-names-list'}),
            'article_number': forms.TextInput(attrs={'class': 'form-control', 'list': 'article-numbers-list'}),
            'pcb_revision': forms.TextInput(attrs={'class': 'form-control', 'list': 'pcb-revisions-list'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'panel_type': forms.TextInput(attrs={'class': 'form-control', 'list': 'panel-types-list'}),
            'bom_id': forms.TextInput(attrs={'class': 'form-control', 'list': 'bom-ids-list'}),
            'project_files_url': forms.URLInput(attrs={'class': 'form-control'}),
            'firmware_version': forms.TextInput(attrs={'class': 'form-control', 'list': 'firmware-versions-list'}),
            'stencil_id': forms.TextInput(attrs={'class': 'form-control', 'list': 'stencil-ids-list'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'transfer_note_number': forms.TextInput(attrs={'class': 'form-control', 'list': 'transfer-note-numbers-list'}),
            'kit_status': forms.Select(attrs={'class': 'form-select'}),
            'deficit_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'kit_received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quality_defects': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'repair_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'scrap_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_produced_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'leftover_components': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'finished_goods_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'production_manager_signed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class TaskListView(LoginRequiredMixin, SearchableListViewMixin, ListView):
    model = Task
    template_name = 'dashboard/task_list.html'
    context_object_name = 'tasks'
    search_fields = ['id', 'title', 'description', 'customer_order__order_number', 'product__name']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_role = None
        if hasattr(user, 'role'):
            user_role = user.role
        elif getattr(user, 'is_superuser', False):
            user_role = 'ADMIN'
        context['user_role'] = user_role
        context['title'] = 'Заказы и задачи'
        return context

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if user.role == 'ADMIN':
                qs = Task.objects.all()
            else:
                qs = Task.objects.filter(
                    (Q(assigned_to=user) | Q(stages__assigned_executor=user)) & Q(production_manager_signed=True)
                ).distinct()
        elif getattr(user, 'is_superuser', False):
            qs = Task.objects.all()
        else:
            qs = Task.objects.none()
        
        self.queryset = qs.prefetch_related('stages__media').order_by('-created_at')
        return super().get_queryset()

class TaskCreateView(LoginRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'dashboard/task_form.html'
    success_url = reverse_lazy('dashboard:task_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['back_url'] = reverse_lazy('dashboard:task_list')
        if self.request.POST:
            data['stages'] = TaskStageFormSet(self.request.POST)
        else:
            data['stages'] = TaskStageFormSet()
        
        # Unique stage names for datalist
        data['previous_stage_names'] = TaskStage.objects.values_list('name', flat=True).distinct().order_by('name')
        
        # Admin check for readonly "Fact" field
        user = self.request.user
        is_admin = (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)
        data['is_admin'] = is_admin
        
        return data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        user = self.request.user
        
        if hasattr(user, 'role'):
            if user.role != 'ADMIN':
                form.instance.assigned_to = user
        elif getattr(user, 'is_superuser', False):
            pass
        else:
            return redirect('dashboard:home')
            
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            # Preserve parameters on success redirect
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

class TaskUpdateView(LoginRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'dashboard/task_form.html'
    success_url = reverse_lazy('dashboard:task_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['back_url'] = reverse_lazy('dashboard:task_list')
        
        # Admin check for readonly "Fact" field
        user = self.request.user
        is_admin = (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)
        data['is_admin'] = is_admin
        
        # Filter stages if user is not admin
        if is_admin:
            stage_qs = TaskStage.objects.filter(task=self.object)
        else:
            stage_qs = TaskStage.objects.filter(task=self.object, assigned_executor=user)
        
        # Create custom formset with filtered queryset
        if self.request.POST:
            data['stages'] = TaskStageFormSet(self.request.POST, instance=self.object, queryset=stage_qs)
        else:
            data['stages'] = TaskStageFormSet(instance=self.object, queryset=stage_qs)
        
        # Unique stage names for datalist
        data['previous_stage_names'] = TaskStage.objects.values_list('name', flat=True).distinct().order_by('name')
        
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            # Preserve parameters on success redirect
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if user.role == 'ADMIN':
                return Task.objects.all()
            return Task.objects.filter(assigned_to=user)
        elif getattr(user, 'is_superuser', False):
            return Task.objects.all()
        return Task.objects.none()

class ProductionOrderDetailView(LoginRequiredMixin, UpdateView):
    """Рабочее место сотрудника: ЗАКАЗ НА ПРОИЗВОДСТВО"""
    model = Task
    template_name = 'dashboard/production_order.html'

    def get_form_class(self):
        user = self.request.user
        is_admin = (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)
        if is_admin:
            return ProductionOrderForm
        return ProductionOrderWorkerForm
    
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        
        # Unique stage names for datalist
        data['previous_stage_names'] = TaskStage.objects.values_list('name', flat=True).distinct().order_by('name')
        
        # Datalists for production order fields
        data['client_names'] = Task.objects.exclude(client_name='').values_list('client_name', flat=True).distinct().order_by('client_name')
        data['product_names'] = Task.objects.exclude(product_name='').values_list('product_name', flat=True).distinct().order_by('product_name')
        data['article_numbers'] = Task.objects.exclude(article_number='').values_list('article_number', flat=True).distinct().order_by('article_number')
        data['pcb_revisions'] = Task.objects.exclude(pcb_revision='').values_list('pcb_revision', flat=True).distinct().order_by('pcb_revision')
        data['panel_types'] = Task.objects.exclude(panel_type='').values_list('panel_type', flat=True).distinct().order_by('panel_type')
        data['bom_ids'] = Task.objects.exclude(bom_id='').values_list('bom_id', flat=True).distinct().order_by('bom_id')
        data['firmware_versions'] = Task.objects.exclude(firmware_version='').values_list('firmware_version', flat=True).distinct().order_by('firmware_version')
        data['stencil_ids'] = Task.objects.exclude(stencil_id='').values_list('stencil_id', flat=True).distinct().order_by('stencil_id')
        data['transfer_note_numbers'] = Task.objects.exclude(transfer_note_number='').values_list('transfer_note_number', flat=True).distinct().order_by('transfer_note_number')
        
        # Admin check for readonly fields
        user = self.request.user
        is_admin = (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)
        data['is_admin'] = is_admin

        # Filter stages if user is not admin or task assignee
        if is_admin:
            stage_qs = TaskStage.objects.filter(task=self.object)
        else:
            stage_qs = TaskStage.objects.filter(task=self.object, assigned_executor=user)
        
        # Отладочная информация
        print(f"DEBUG: User {user.username} (is_admin={is_admin}) sees {stage_qs.count()} stages out of {TaskStage.objects.filter(task=self.object).count()} total stages")

        StageFormSet = inlineformset_factory(
            Task, TaskStage,
            fields=['name', 'equipment', 'assigned_executor', 'start_timestamp', 'end_timestamp', 'actual_duration', 'quantity_good', 'status'],
            extra=0,
            can_delete=False,
            widgets={
                'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'list': 'stage-names-list'}),
                'equipment': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
                'assigned_executor': forms.Select(attrs={'class': 'form-select form-select-sm'}),
                'start_timestamp': forms.DateTimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'datetime-local'}),
                'end_timestamp': forms.DateTimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'datetime-local'}),
                'actual_duration': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
                'quantity_good': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
                'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            }
        )

        if self.request.POST:
            data['stages'] = StageFormSet(self.request.POST, instance=self.object, queryset=stage_qs)
        else:
            data['stages'] = StageFormSet(instance=self.object, queryset=stage_qs)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        if stages.is_valid():
            # Обработка подписи начальника производства
            if 'production_manager_signed' in form.changed_data:
                if form.cleaned_data.get('production_manager_signed'):
                    form.instance.production_manager_signed_at = timezone.now()
                else:
                    form.instance.production_manager_signed_at = None
            
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, "Данные заказа успешно обновлены")
            return redirect('dashboard:production_order', pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    success_url = reverse_lazy('dashboard:home')
    
    def get_queryset(self):
        user = self.request.user
        # Только администратор может удалять
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return Task.objects.all()
        return Task.objects.none()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Удаляем связанные файлы перед удалением объекта из БД
        for media in self.object.media.all():
            if media.file:
                if os.path.isfile(media.file.path):
                    os.remove(media.file.path)
        
        # Также удаляем медиа, привязанные к этапам этой задачи
        for stage in self.object.stages.all():
            for media in stage.media.all():
                if media.file:
                    if os.path.isfile(media.file.path):
                        os.remove(media.file.path)
        
        messages.success(request, f"Задача {self.object.external_id} и все связанные данные успешно удалены.")
        return super().delete(request, *args, **kwargs)

# --- Task Templates (Reference System) ---

class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        fields = ['code', 'title', 'description', 'process_type', 'category', 'related_resource_url', 'related_resource_name']
        labels = {
            'code': 'Код шаблона',
            'title': 'Название процесса',
            'description': 'Описание / Инструкция',
            'process_type': 'Тип процесса',
            'category': 'Категория',
            'related_resource_url': 'Ссылка на Wiki/Docs',
            'related_resource_name': 'Название ресурса',
        }
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. QC-MICRO-02'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'process_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. Электроника'}),
            'related_resource_url': forms.URLInput(attrs={'class': 'form-control'}),
            'related_resource_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

TaskTemplateStageFormSet = inlineformset_factory(
    TaskTemplate, TaskTemplateStage,
    fields=['name', 'executor_role', 'planned_duration', 'data_type', 'order'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название этапа'}),
        'executor_role': forms.Select(attrs={'class': 'form-select'}),
        'planned_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'План (мин)'}),
        'data_type': forms.Select(attrs={'class': 'form-select'}),
        'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '№'}),
    }
)

class TaskTemplateListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = TaskTemplate
    template_name = 'dashboard/task_template_list.html'
    context_object_name = 'templates'
    search_fields = ['code', 'title', 'description', 'category']

    def get_queryset(self):
        return super().get_queryset().prefetch_related('stages')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_admin = (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)
        context['is_admin'] = is_admin
        context['title'] = 'Шаблоны заказов'
        return context

class TaskTemplateCreateView(LoginRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = TaskTemplate
    form_class = TaskTemplateForm
    template_name = 'dashboard/task_template_form.html'
    success_url = reverse_lazy('dashboard:task_template_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['stages'] = TaskTemplateStageFormSet(self.request.POST)
        else:
            data['stages'] = TaskTemplateStageFormSet()
        data['back_url'] = reverse_lazy('dashboard:task_template_list')
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, f"Шаблон '{self.object.title}' успешно создан.")
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

class TaskTemplateUpdateView(LoginRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = TaskTemplate
    form_class = TaskTemplateForm
    template_name = 'dashboard/task_template_form.html'
    success_url = reverse_lazy('dashboard:task_template_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['stages'] = TaskTemplateStageFormSet(self.request.POST, instance=self.object)
        else:
            data['stages'] = TaskTemplateStageFormSet(instance=self.object)
        data['back_url'] = reverse_lazy('dashboard:task_template_list')
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, f"Шаблон '{self.object.title}' успешно обновлен.")
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

class TaskTemplateDeleteView(LoginRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = TaskTemplate
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:task_template_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление шаблона'
        context['message'] = f'Вы уверены, что хотите удалить шаблон "{self.object.title}"?'
        context['cancel_url'] = reverse_lazy('dashboard:task_template_list')
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        messages.success(request, f"Шаблон '{self.object.title}' успешно удален.")
        self.object.delete()
        return redirect(success_url)

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class CreateTaskFromTemplateAjaxView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        template_id = kwargs.get('pk')
        try:
            template = TaskTemplate.objects.get(pk=template_id)
            user = request.user
            
            # Проверка прав: либо админ, либо суперпользователь
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            # Создаем задачу на основе шаблона
            # Генерируем external_id
            prefix = template.code.split('-')[0]
            year = timezone.now().year
            last_task = Task.objects.filter(external_id__startswith=f"{prefix}-{year}").order_by('-external_id').first()
            if last_task and '-' in last_task.external_id:
                try:
                    num = int(last_task.external_id.split('-')[-1]) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            
            new_external_id = f"{prefix}-{year}-{num:03d}"
            
            task = Task.objects.create(
                template=template,
                external_id=new_external_id,
                title=template.title,
                description=template.description,
                process_type=template.process_type,
                source='TEMPLATE',
                status='OPEN'
            )
            
            # Копируем этапы
            for t_stage in template.stages.all():
                TaskStage.objects.create(
                    task=task,
                    name=t_stage.name,
                    executor_role=t_stage.executor_role,
                    planned_duration=t_stage.planned_duration,
                    order=t_stage.order,
                    data_type=t_stage.data_type,
                    status='PENDING'
                )
            
            # Определяем URL редиректа в зависимости от типа процесса
            if template.process_type == 'PRODUCTION':
                redirect_url = reverse_lazy('dashboard:production_order', kwargs={'pk': task.id})
            else:
                redirect_url = reverse_lazy('dashboard:task_edit', kwargs={'pk': task.id})
            
            return JsonResponse({
                'status': 'success',
                'task_id': task.id,
                'external_id': task.external_id,
                'redirect_url': str(redirect_url)
            })
            
        except TaskTemplate.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Template not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- Reference Books (Справочники) ---

# 1. Изделия
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'article', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'article': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ProductListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = Product
    template_name = 'dashboard/reference_list.html'
    context_object_name = 'items'
    search_fields = ['name', 'article', 'description']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Справочник изделий'
        context['create_url'] = 'dashboard:product_create'
        context['edit_url_name'] = 'dashboard:product_edit'
        context['delete_url_name'] = 'dashboard:product_delete'
        context['fields'] = ['article', 'name']
        context['field_labels'] = {'article': 'Артикул', 'name': 'Наименование'}
        return context

class ProductCreateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:product_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание изделия'
        context['back_url'] = reverse_lazy('dashboard:product_list')
        return context

class ProductUpdateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:product_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование: {self.object.name}'
        context['back_url'] = reverse_lazy('dashboard:product_list')
        return context

class ProductDeleteView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = Product
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:product_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление изделия'
        context['message'] = f'Вы уверены, что хотите удалить изделие "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:product_list')
        return context

# 2. Спецификации
class SpecificationForm(forms.ModelForm):
    class Meta:
        model = Specification
        fields = ['product', 'code', 'version', 'file_url']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'file_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class SpecificationListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = Specification
    template_name = 'dashboard/reference_list.html'
    context_object_name = 'items'
    search_fields = ['code', 'version', 'product__name', 'product__article']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Справочник спецификаций'
        context['create_url'] = 'dashboard:specification_list_create' # reused
        context['edit_url_name'] = 'dashboard:specification_edit'
        context['delete_url_name'] = 'dashboard:specification_delete'
        context['fields'] = ['code', 'version', 'product']
        context['field_labels'] = {'code': 'Код', 'version': 'Версия', 'product': 'Изделие'}
        return context

class SpecificationCreateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Specification
    form_class = SpecificationForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:specification_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание спецификации'
        context['back_url'] = reverse_lazy('dashboard:specification_list')
        return context

class SpecificationUpdateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Specification
    form_class = SpecificationForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:specification_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование: {self.object.code}'
        context['back_url'] = reverse_lazy('dashboard:specification_list')
        return context

class SpecificationDeleteView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = Specification
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:specification_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление спецификации'
        context['message'] = f'Вы уверены, что хотите удалить спецификацию "{self.object.code}"?'
        context['cancel_url'] = reverse_lazy('dashboard:specification_list')
        return context

# 3. Накладные
class TransferNoteForm(forms.ModelForm):
    class Meta:
        model = TransferNote
        fields = ['number', 'date', 'description']
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class TransferNoteListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = TransferNote
    template_name = 'dashboard/reference_list.html'
    context_object_name = 'items'
    search_fields = ['number', 'description']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Справочник накладных'
        context['create_url'] = 'dashboard:transfer_note_create'
        context['edit_url_name'] = 'dashboard:transfer_note_edit'
        context['delete_url_name'] = 'dashboard:transfer_note_delete'
        context['fields'] = ['number', 'date']
        context['field_labels'] = {'number': 'Номер', 'date': 'Дата'}
        return context

class TransferNoteCreateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = TransferNote
    form_class = TransferNoteForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:transfer_note_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание накладной'
        context['back_url'] = reverse_lazy('dashboard:transfer_note_list')
        return context

class TransferNoteUpdateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = TransferNote
    form_class = TransferNoteForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:transfer_note_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование: {self.object.number}'
        context['back_url'] = reverse_lazy('dashboard:transfer_note_list')
        return context

class TransferNoteDeleteView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = TransferNote
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:transfer_note_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление накладной'
        context['message'] = f'Вы уверены, что хотите удалить накладную "{self.object.number}"?'
        context['cancel_url'] = reverse_lazy('dashboard:transfer_note_list')
        return context

# 4. Операции (Шаблоны этапов)
class OperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = ['name', 'executor_role', 'data_type', 'default_duration', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'executor_role': forms.Select(attrs={'class': 'form-select'}),
            'data_type': forms.Select(attrs={'class': 'form-select'}),
            'default_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class OperationListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = Operation
    template_name = 'dashboard/reference_list.html'
    context_object_name = 'items'
    search_fields = ['name', 'description']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Шаблоны этапов'
        context['create_url'] = 'dashboard:operation_create'
        context['edit_url_name'] = 'dashboard:operation_edit'
        context['delete_url_name'] = 'dashboard:operation_delete'
        context['fields'] = ['name', 'executor_role', 'data_type', 'default_duration']
        context['field_labels'] = {
            'name': 'Название', 
            'executor_role': 'Исполнитель',
            'data_type': 'Тип данных',
            'default_duration': 'SLA (мин)'
        }
        return context

class OperationCreateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Operation
    form_class = OperationForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:operation_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание шаблона этапа'
        context['back_url'] = reverse_lazy('dashboard:operation_list')
        return context

class OperationUpdateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Operation
    form_class = OperationForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:operation_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование шаблона: {self.object.name}'
        context['back_url'] = reverse_lazy('dashboard:operation_list')
        return context

class OperationDeleteView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = Operation
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:operation_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление шаблона этапа'
        context['message'] = f'Вы уверены, что хотите удалить шаблон этапа "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:operation_list')
        return context

# 5. Заказы (справочник)
class ClientOrderForm(forms.ModelForm):
    class Meta:
        model = ClientOrder
        fields = ['order_number', 'client_name', 'date']
        widgets = {
            'order_number': forms.TextInput(attrs={'class': 'form-control'}),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class ClientOrderListView(LoginRequiredMixin, AdminRequiredMixin, SearchableListViewMixin, ListView):
    model = ClientOrder
    template_name = 'dashboard/reference_list.html'
    context_object_name = 'items'
    search_fields = ['order_number', 'client_name']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Справочник заказов'
        context['create_url'] = 'dashboard:client_order_create'
        context['edit_url_name'] = 'dashboard:client_order_edit'
        context['delete_url_name'] = 'dashboard:client_order_delete'
        context['fields'] = ['order_number', 'client_name', 'date']
        context['field_labels'] = {'order_number': '№ Заказа', 'client_name': 'Заказчик', 'date': 'Дата'}
        return context

class ClientOrderCreateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = ClientOrder
    form_class = ClientOrderForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:client_order_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание заказа'
        context['back_url'] = reverse_lazy('dashboard:client_order_list')
        return context

class ClientOrderUpdateView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = ClientOrder
    form_class = ClientOrderForm
    template_name = 'dashboard/reference_form.html'
    success_url = reverse_lazy('dashboard:client_order_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование: {self.object.order_number}'
        context['back_url'] = reverse_lazy('dashboard:client_order_list')
        return context

class ClientOrderDeleteView(LoginRequiredMixin, AdminRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = ClientOrder
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:client_order_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление заказа'
        context['message'] = f'Вы уверены, что хотите удалить заказ "{self.object.order_number}"?'
        context['cancel_url'] = reverse_lazy('dashboard:client_order_list')
        return context


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['title', 'file']
        labels = {
            'title': 'Название',
            'file': 'Файл'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название (необязательно)'}),
            'file': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'video/*,image/*',
                'capture': 'environment'  # Предлагает заднюю камеру на смартфонах
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False

class MediaListView(LoginRequiredMixin, ListView):
    model = Media
    template_name = 'dashboard/media_list.html'
    context_object_name = 'media_files'
    paginate_by = 12
    
    def get_queryset(self):
        user = self.request.user
        queryset = Media.objects.select_related('uploaded_by', 'task', 'stage')
        
        # Проверяем наличие атрибута role (для TenantUser)
        # Используем hasattr вместо isinstance для надежности с LazyObject
        if hasattr(user, 'role'):
            # Админ тенанта видит ВСЕ файлы предприятия
            if user.role == 'ADMIN':
                return queryset.order_by('-uploaded_at')
            # Обычный сотрудник видит только свои файлы
            return queryset.filter(uploaded_by=user).order_by('-uploaded_at')
        
        elif getattr(user, 'is_superuser', False):
            # Суперпользователь платформы видит всё
            return queryset.order_by('-uploaded_at')
            
        return Media.objects.none()

class MediaCreateView(LoginRequiredMixin, CreateView):
    model = Media
    form_class = MediaForm
    template_name = 'dashboard/media_form.html'
    success_url = reverse_lazy('dashboard:media_list')

    def form_valid(self, form):
        user = self.request.user
        if not form.cleaned_data.get('title'):
            form.instance.title = form.cleaned_data['file'].name
            
        if hasattr(user, 'role'):
            form.instance.uploaded_by = user
        elif getattr(user, 'is_superuser', False):
            # Системный суперпользователь не привязывается к TenantUser
            form.instance.uploaded_by = None
        else:
            return redirect('dashboard:home')
        return super().form_valid(form)

class MediaDeleteView(LoginRequiredMixin, DeleteView):
    model = Media
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:media_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление файла'
        context['message'] = f'Вы уверены, что хотите удалить файл "{self.object.title}"?'
        context['cancel_url'] = reverse_lazy('dashboard:media_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        obj = self.get_object()
        
        # 1. Суперпользователь платформы (is_superuser=True в public schema)
        if getattr(user, 'is_superuser', False):
            # Проверяем персональный флаг в профиле администратора платформы
            if hasattr(user, 'profile') and user.profile.can_delete_media:
                return super().dispatch(request, *args, **kwargs)
            
            # Если это главный admin, разрешаем всё (опционально, но обычно удобно)
            if user.username == 'admin':
                return super().dispatch(request, *args, **kwargs)

            messages.error(request, 'У вас нет разрешения на удаление файлов. Обратитесь к главному администратору.')
            return redirect('dashboard:media_list')
            
        # 2. Администратор тенанта (TenantUser с ролью ADMIN)
        if hasattr(user, 'role') and user.role == 'ADMIN':
            # Админ тенанта может удалять, только если у тенанта включен глобальный флаг
            if request.tenant.can_admin_delete_media:
                return super().dispatch(request, *args, **kwargs)
            else:
                messages.error(request, 'Удаление файлов запрещено системным администратором для всей организации.')
                return redirect('dashboard:media_list')
        
        # 3. Обычный пользователь (Worker)
        # После переноса флага в кабинет суперпользователя, обычные работники больше не могут удалять файлы,
        # так как флаг can_delete_media теперь есть только у профилей администраторов платформы.
        
        messages.error(request, 'У вас нет прав для удаления файлов.')
        return redirect('dashboard:media_list')

class MediaVideoRecordView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/video_record.html'

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class HelpView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/help.html'

# --- Positions (AJAX) ---

@method_decorator(csrf_exempt, name='dispatch')
class PositionCreateAjaxView(LoginRequiredMixin, CreateView):
    model = Position
    fields = ['name']

    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'status': 'success',
            'id': self.object.id,
            'name': self.object.name
        })

    def form_invalid(self, form):
        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        })

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

# --- Positions ---

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['name', 'description']
        labels = {
            'name': 'Название',
            'description': 'Описание'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PositionListView(LoginRequiredMixin, SearchableListViewMixin, ListView):
    model = Position
    template_name = 'dashboard/position_list.html'
    context_object_name = 'positions'
    search_fields = ['name', 'description']

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Справочник должностей'
        return context

class PositionCreateView(LoginRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = 'dashboard/position_form.html'
    success_url = reverse_lazy('dashboard:position_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:position_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class PositionUpdateView(LoginRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'dashboard/position_form.html'
    success_url = reverse_lazy('dashboard:position_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:position_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class PositionDeleteView(LoginRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = Position
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:position_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление должности'
        context['message'] = f'Вы уверены, что хотите удалить должность "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:position_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

# --- Departments ---

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'parent', 'description']
        labels = {
            'name': 'Название',
            'parent': 'Головное подразделение',
            'description': 'Описание'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class DepartmentListView(LoginRequiredMixin, SearchableListViewMixin, ListView):
    model = Department
    template_name = 'dashboard/department_list.html'
    context_object_name = 'departments'
    search_fields = ['name', 'description']

    def get_queryset(self):
        # Если есть поиск, показываем плоский список результатов
        q = self.request.GET.get('q')
        if q:
            return super().get_queryset()
        # Иначе получаем только корневые подразделения для дерева
        self.queryset = Department.objects.filter(parent=None).prefetch_related('children')
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Структура подразделений'
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentCreateView(LoginRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'dashboard/department_form.html'
    success_url = reverse_lazy('dashboard:department_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:department_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentUpdateView(LoginRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'dashboard/department_form.html'
    success_url = reverse_lazy('dashboard:department_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:department_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentDeleteView(LoginRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = Department
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:department_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление подразделения'
        context['message'] = f'Вы уверены, что хотите удалить подразделение "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:department_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

# --- Employees ---

class EmployeeForm(forms.ModelForm):
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    
    class Meta:
        model = TenantUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'position', 'department', 'role', 'is_active']
        labels = {
            'username': 'Логин',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
            'phone': 'Телефон',
            'position': 'Должность',
            'department': 'Подразделение',
            'role': 'Роль',
            'is_active': 'Активен'
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (___) ___-__-__'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле username доступным только для чтения для обычных админов,
        # но доступным для редактирования для суперпользователей
        if self.instance and self.instance.pk:
            # Это редактирование существующего пользователя
            current_user = getattr(self, 'current_user', None)
            if current_user and not getattr(current_user, 'is_superuser', False):
                # Обычный админ не может изменять username
                self.fields['username'].widget.attrs['readonly'] = True

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class EmployeeListView(LoginRequiredMixin, SearchableListViewMixin, ListView):
    model = TenantUser
    template_name = 'dashboard/employee_list.html'
    context_object_name = 'employees'
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'position__name', 'department__name']
    
    def dispatch(self, request, *args, **kwargs):
        # Доступ только для админов
        user = request.user
        if hasattr(user, 'role') and user.role == 'ADMIN':
            return super().dispatch(request, *args, **kwargs)
        if getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

    def get_queryset(self):
        self.queryset = TenantUser.objects.all().order_by('-created_at')
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Список сотрудников'
        tenant = getattr(self.request, 'tenant', None)
        employees_count = TenantUser.objects.count()
        context['employees_count'] = employees_count
        
        if tenant and tenant.subscription_plan:
            plan = tenant.subscription_plan
            context['users_limit'] = plan.max_users
            if plan.max_users > 0:
                context['users_percent'] = min(int((employees_count / plan.max_users) * 100), 100)
        return context

class EmployeeCreateView(LoginRequiredMixin, PreserveQueryParamsMixin, CreateView):
    model = TenantUser
    form_class = EmployeeForm
    template_name = 'dashboard/employee_form.html'
    success_url = reverse_lazy('dashboard:employee_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:employee_list')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not ((hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False)):
            return redirect('dashboard:home')
            
        # Проверка лимита пользователей по тарифу
        tenant = getattr(request, 'tenant', None)
        if tenant and tenant.subscription_plan:
            current_user_count = TenantUser.objects.count()
            if current_user_count >= tenant.subscription_plan.max_users:
                messages.error(request, f"Превышен лимит пользователей для вашего тарифа ({tenant.subscription_plan.max_users}). Удалите существующих пользователей или обновите тариф.")
                return redirect('dashboard:employee_list')
                
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Повторная проверка при сохранении формы (на случай одновременных запросов)
        tenant = getattr(self.request, 'tenant', None)
        if tenant and tenant.subscription_plan:
            current_user_count = TenantUser.objects.count()
            if current_user_count >= tenant.subscription_plan.max_users:
                messages.error(self.request, f"Превышен лимит пользователей для вашего тарифа ({tenant.subscription_plan.max_users}).")
                return redirect('dashboard:employee_list')
        return super().form_valid(form)

class EmployeeUpdateView(LoginRequiredMixin, PreserveQueryParamsMixin, UpdateView):
    model = TenantUser
    form_class = EmployeeForm
    template_name = 'dashboard/employee_form.html'
    success_url = reverse_lazy('dashboard:employee_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['back_url'] = reverse_lazy('dashboard:employee_list')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class EmployeeDeleteView(LoginRequiredMixin, PreserveQueryParamsMixin, DeleteView):
    model = TenantUser
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:employee_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление сотрудника'
        context['message'] = f'Вы уверены, что хотите удалить сотрудника "{self.object.get_full_name() or self.object.username}"?'
        context['cancel_url'] = reverse_lazy('dashboard:employee_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

# --- AJAX Task Management ---

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class TaskStatusUpdateAjaxView(LoginRequiredMixin, UpdateView):
    model = Task
    fields = ['status']

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.status == 'CLOSE':
            self.object.is_completed = True
            if not self.object.closed_at:
                self.object.closed_at = timezone.now()
        else:
            self.object.is_completed = False
            self.object.closed_at = None
        self.object.save()
        return JsonResponse({
            'status': 'success',
            'task_status': self.object.status,
            'task_status_display': self.object.get_status_display()
        })

    def form_invalid(self, form):
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class TaskStageMediaUploadAjaxView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        stage_id = kwargs.get('pk')
        try:
            stage = TaskStage.objects.get(pk=stage_id)
            user = request.user
            
            # Проверка прав (админ или исполнитель)
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user or stage.assigned_executor == user))):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            file = request.FILES.get('file')
            if not file:
                return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
            
            # Создаем медиа-объект
            media = Media.objects.create(
                file=file,
                task=stage.task,
                stage=stage,
                uploaded_by=user if hasattr(user, 'role') else None
            )
            
            return JsonResponse({
                'status': 'success',
                'media_id': media.id,
                'media_title': media.title,
                'media_url': media.file.url
            })
            
        except TaskStage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Stage not found'}, status=404)

# --- Quick Login & QR Code Views ---

@login_required
def generate_qr_code(request, pk):
    """
    Генерация QR-кода для быстрого входа сотрудника.
    Доступно только администраторам.
    """
    user = request.user
    if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and user.role == 'ADMIN')):
        messages.error(request, "Доступ разрешен только администраторам.")
        return redirect('dashboard:home')
    
    target_user = get_object_or_404(TenantUser, pk=pk)
    
    # Генерируем токен
    token = generate_quick_login_token(target_user)
    
    # Формируем ссылку
    login_url = request.build_absolute_uri(reverse('dashboard:quick_login', args=[token]))
    
    # Определяем правильный домен для ссылки
    host = request.get_host()
    target_domain = None
    
    if hasattr(request, 'tenant'):
        # 1. Ищем основной домен
        primary = request.tenant.domains.filter(is_primary=True).first()
        if primary:
            target_domain = primary.domain
            
        # 2. Если мы на localhost/127.0.0.1 (разработка), пытаемся найти nip.io домен
        if 'localhost' in host or '127.0.0.1' in host:
            nip_domain = None
            for domain in request.tenant.domains.all():
                if 'nip.io' in domain.domain:
                    nip_domain = domain.domain
                    break
            
            if nip_domain:
                target_domain = nip_domain
                # Сохраняем порт, если он есть
                if ':' in host:
                    port = host.split(':')[1]
                    if ':' not in target_domain:
                        target_domain = f"{target_domain}:{port}"
    
    # Применяем целевой домен, если он отличается от текущего
    if target_domain and target_domain != host:
        login_url = login_url.replace(host, target_domain)
    
    # Генерируем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(login_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'target_user': target_user,
        'qr_image': img_str,
        'login_url': login_url,
    }
    return render(request, 'dashboard/qr_code.html', context)

def quick_login(request, token):
    """
    Вход по токе (QR-коду).
    Доступен анонимным пользователям.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
        
    user = validate_quick_login_token(token)
    if user:
        if not user.is_active:
             messages.error(request, "Аккаунт заблокирован.")
             return redirect('dashboard:login')
        
        # Указываем бэкенд аутентификации
        if isinstance(user, TenantUser):
            user.backend = 'users_app.backends.TenantUserBackend'
        else:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            
        login(request, user)
        return redirect('dashboard:home')
    else:
        messages.error(request, "Недействительная или устаревшая ссылка для входа.")
        return redirect('dashboard:login')

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class TaskStageCreateAjaxView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        task_id = kwargs.get('pk')
        try:
            task = Task.objects.get(pk=task_id)
            user = request.user
            
            # Проверка прав: либо админ, либо исполнитель задачи
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or task.assigned_to == user))):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            name = request.POST.get('name')
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Name is required'}, status=400)
            
            # Определяем порядок (последний + 1)
            last_order = task.stages.aggregate(models.Max('order'))['order__max'] or 0
            
            stage = TaskStage.objects.create(
                task=task,
                name=name,
                order=last_order + 1,
                is_worker_added=True
            )
            
            return JsonResponse({
                'status': 'success',
                'id': stage.id,
                'name': stage.name,
                'is_worker_added': stage.is_worker_added
            })
        except Task.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class TaskStageStatusUpdateAjaxView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        stage_id = kwargs.get('pk')
        try:
            stage = TaskStage.objects.get(pk=stage_id)
            user = request.user
            
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user or stage.assigned_executor == user))):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            status = request.POST.get('status')
            if status not in dict(TaskStage.STAGE_STATUS_CHOICES):
                return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
            
            stage.status = status
            stage.save()
            
            # Синхронизация статуса задачи
            all_completed = not stage.task.stages.filter(is_completed=False).exists()
            if all_completed and not stage.task.is_completed:
                stage.task.is_completed = True
                stage.task.status = 'CLOSE'
                stage.task.save()
            elif not all_completed and stage.task.is_completed:
                stage.task.is_completed = False
                stage.task.status = 'OPEN'
                stage.task.save()

            return JsonResponse({
                'status': 'success',
                'stage_status': stage.status,
                'stage_status_display': stage.get_status_display(),
                'is_completed': stage.is_completed,
                'task_is_completed': stage.task.is_completed,
                'task_status': stage.task.status,
                'actual_duration': stage.actual_duration
            })
        except TaskStage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Stage not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class TaskStageToggleAjaxView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        stage_id = kwargs.get('pk')
        try:
            stage = TaskStage.objects.get(pk=stage_id)
            # Проверяем права: либо админ, либо исполнитель задачи
            user = request.user
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user or stage.assigned_executor == user))):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            stage.is_completed = not stage.is_completed
            if stage.is_completed:
                stage.status = 'COMPLETED'
            else:
                stage.status = 'PENDING'
            stage.save()
            
            # Проверяем, все ли этапы завершены, чтобы обновить статус задачи
            all_completed = not stage.task.stages.filter(is_completed=False).exists()
            if all_completed and not stage.task.is_completed:
                stage.task.is_completed = True
                stage.task.status = 'CLOSE'
                stage.task.save()
            elif not all_completed and stage.task.is_completed:
                stage.task.is_completed = False
                stage.task.status = 'OPEN'
                stage.task.save()

            return JsonResponse({
                'status': 'success',
                'is_completed': stage.is_completed,
                'stage_status': stage.status,
                'stage_status_display': stage.get_status_display(),
                'task_is_completed': stage.task.is_completed,
                'task_status': stage.task.status,
                'actual_duration': stage.actual_duration
            })
        except TaskStage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Stage not found'}, status=404)

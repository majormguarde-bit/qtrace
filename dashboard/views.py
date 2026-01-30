from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django import forms
from django.forms import inlineformset_factory
from django.contrib import messages
from django.utils import timezone
from django.http import Http404

from django.db.models import Sum
from django.db import models as django_models
from tasks.models import Task, TaskStage
from media_app.models import Media
from users_app.models import TenantUser, Department, Position
from task_templates.models import (
    TaskTemplate, TaskTemplateStage, TemplateProposal, ActivityCategory, 
    StageMaterial, DurationUnit, Material
)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

def home(request):
    """
    ТИПОВАЯ ЛОГИКА МАРШРУТИЗАЦИИ - НЕ ИЗМЕНЯТЬ!
    
    Эта функция определяет, куда перенаправлять пользователя при обращении к корневому URL (/).
    
    Правила маршрутизации (ЗАФИКСИРОВАНЫ):
    1. Public schema (localhost:8000) → ВСЕГДА перенаправляем на /landing/
       - Лендинг доступен всем без авторизации
       - Авторизованные пользователи тоже видят лендинг
       - Из лендинга есть ссылки на /superuser/ и /login/
    
    2. Tenant schema (subdomain.localhost:8000) → требуется авторизация
       - Если не авторизован → перенаправляем на /login/
       - Если авторизован → показываем dashboard тенанта
    
    ВАЖНО: Проверка авторизации происходит ТОЛЬКО в панелях управления,
    НЕ на лендинге! Лендинг - публичная страница для всех.
    """
    user = request.user
    tenant = getattr(request, 'tenant', None)
    
    # Правило 1: Public schema → лендинг для всех
    if tenant and tenant.schema_name == 'public':
        return redirect('/landing/')
    
    # Правило 2: Tenant schema → требуется авторизация
    if not user.is_authenticated:
        return redirect('dashboard:login')
    
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
        # Worker sees only their own data
        tasks_qs = Task.objects.filter(assigned_to=user).prefetch_related('stages', 'assigned_to')

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
            delta = tenant.subscription_end_date - timezone.now().date()
            context['days_left'] = delta.days
    
    # Kanban data
    context['kanban_tasks'] = {
        'OPEN': tasks_qs.filter(status='OPEN'),
        'CONTINUE': tasks_qs.filter(status='CONTINUE'),
        'PAUSE': tasks_qs.filter(status='PAUSE'),
        'IMPORTANT': tasks_qs.filter(status='IMPORTANT'),
        'CLOSE': tasks_qs.filter(status='CLOSE'),
    }
    
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
    next_page = '/login/'

# --- Tasks ---

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'is_completed']
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'is_completed': 'Выполнено',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

TaskStageFormSet = inlineformset_factory(
    Task, TaskStage,
    fields=['name', 'duration_value', 'duration_unit', 'order', 'assigned_to', 'position_name', 'duration_text', 'materials_info'],
    extra=0,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название этапа'}),
        'duration_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Значение', 'step': '0.01', 'min': '0'}),
        'duration_unit': forms.Select(attrs={'class': 'form-select'}),
        'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '№'}),
        'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        'position_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Должность', 'readonly': 'readonly'}),
        'duration_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Длительность', 'readonly': 'readonly'}),
        'materials_info': forms.HiddenInput(),
    }
)

# Formset для этапов шаблонов
TemplateStageFormSet = inlineformset_factory(
    TaskTemplate, TaskTemplateStage,
    fields=['name', 'duration_from', 'duration_to', 'duration_unit', 'position', 'sequence_number'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название этапа'}),
        'duration_from': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Длительность от', 'step': '0.01', 'min': '0.01'}),
        'duration_to': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Длительность до', 'step': '0.01', 'min': '0.01'}),
        'duration_unit': forms.Select(attrs={'class': 'form-select'}),
        'position': forms.Select(attrs={'class': 'form-select'}),
        'sequence_number': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Порядок'}),
    }
)

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'dashboard/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if user.role == 'ADMIN':
                return Task.objects.all().prefetch_related('stages__media').order_by('-created_at')
            return Task.objects.filter(assigned_to=user).prefetch_related('stages__media').order_by('-created_at')
        elif getattr(user, 'is_superuser', False):
            return Task.objects.all().prefetch_related('stages__media').order_by('-created_at')
        return Task.objects.none()

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'dashboard/task_form.html'
    success_url = reverse_lazy('dashboard:task_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['stages'] = TaskStageFormSet(self.request.POST)
        else:
            data['stages'] = TaskStageFormSet()
        
        # Добавляем доступные шаблоны
        # В тенанте показываем только локальные шаблоны (template_type='local')
        data['templates'] = TaskTemplate.objects.filter(
            template_type='local'
        ).prefetch_related('activity_category').order_by('activity_category', 'name')
        
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
            return redirect(self.success_url)
        else:
            # Проверяем, есть ли ошибки в formset (кроме пустых форм)
            has_errors = any(form.errors for form in stages.forms if form.cleaned_data)
            if has_errors:
                return self.render_to_response(self.get_context_data(form=form))
            else:
                # Если ошибок нет, сохраняем задачу без этапов
                self.object = form.save()
                stages.instance = self.object
                stages.save()
                return redirect(self.success_url)

class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'dashboard/task_form.html'
    success_url = reverse_lazy('dashboard:task_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['stages'] = TaskStageFormSet(self.request.POST, instance=self.object)
        else:
            data['stages'] = TaskStageFormSet(instance=self.object)
        
        # Добавляем доступные шаблоны
        # В тенанте показываем только локальные шаблоны (template_type='local')
        data['templates'] = TaskTemplate.objects.filter(
            template_type='local'
        ).prefetch_related('activity_category').order_by('activity_category', 'name')
        
        return data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            return redirect(self.success_url)
        else:
            # Проверяем, есть ли ошибки в formset (кроме пустых форм)
            has_errors = any(form.errors for form in stages.forms if form.cleaned_data)
            if has_errors:
                return self.render_to_response(self.get_context_data(form=form))
            else:
                # Если ошибок нет, сохраняем задачу без этапов
                self.object = form.save()
                stages.instance = self.object
                stages.save()
                return redirect(self.success_url)

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if user.role == 'ADMIN':
                return Task.objects.all()
            return Task.objects.filter(assigned_to=user)
        elif getattr(user, 'is_superuser', False):
            return Task.objects.all()
        return Task.objects.none()

# --- Media ---

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

class PositionListView(LoginRequiredMixin, ListView):
    model = Position
    template_name = 'dashboard/position_list.html'
    context_object_name = 'positions'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class PositionUpdateView(LoginRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = 'dashboard/position_form.html'
    success_url = reverse_lazy('dashboard:position_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class PositionDeleteView(LoginRequiredMixin, DeleteView):
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

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'dashboard/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        # Получаем только корневые подразделения, остальные будут выведены рекурсивно в шаблоне
        return Department.objects.filter(parent=None).prefetch_related('children')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'dashboard/department_form.html'
    success_url = reverse_lazy('dashboard:department_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'dashboard/department_form.html'
    success_url = reverse_lazy('dashboard:department_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
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
        # Заполняем queryset для department
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        # Заполняем queryset для position
        self.fields['position'].queryset = Position.objects.all().order_by('name')

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class EmployeeListView(LoginRequiredMixin, ListView):
    model = TenantUser
    template_name = 'dashboard/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        # Доступ только для админов
        user = request.user
        if hasattr(user, 'role') and user.role == 'ADMIN':
            return super().dispatch(request, *args, **kwargs)
        if getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

    def get_queryset(self):
        return TenantUser.objects.all().order_by('-created_at')

class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = TenantUser
    form_class = EmployeeForm
    template_name = 'dashboard/employee_form.html'
    success_url = reverse_lazy('dashboard:employee_list')
    
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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Если это создание нового сотрудника, генерируем логин
        if not self.object or not self.object.pk:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                role = self.request.POST.get('role', 'WORKER') if self.request.method == 'POST' else 'WORKER'
                count = TenantUser.objects.filter(role=role).count() + 1
                tenant_name = tenant.name.replace(' ', '-').lower()
                role_name = role.lower()
                suggested_username = f"{tenant_name}-{role_name}-{count}".lower()
                form.fields['username'].initial = suggested_username
                form.fields['username'].widget.attrs['readonly'] = True
        return form

    def form_valid(self, form):
        # Повторная проверка при сохранении формы (на случай одновременных запросов)
        tenant = getattr(self.request, 'tenant', None)
        if tenant and tenant.subscription_plan:
            current_user_count = TenantUser.objects.count()
            if current_user_count >= tenant.subscription_plan.max_users:
                messages.error(self.request, f"Превышен лимит пользователей для вашего тарифа ({tenant.subscription_plan.max_users}).")
                return redirect('dashboard:employee_list')
        
        # Если логин не заполнен, генерируем его автоматически
        if not form.cleaned_data.get('username'):
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                role = form.cleaned_data.get('role', 'WORKER')
                count = TenantUser.objects.filter(role=role).count() + 1
                tenant_name = tenant.name.replace(' ', '-').lower()
                role_name = role.lower()
                form.instance.username = f"{tenant_name}-{role_name}-{count}".lower()
        
        return super().form_valid(form)

class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = TenantUser
    form_class = EmployeeForm
    template_name = 'dashboard/employee_form.html'
    success_url = reverse_lazy('dashboard:employee_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

class EmployeeDeleteView(LoginRequiredMixin, DeleteView):
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
        self.object = form.save()
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
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user))):
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
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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
            
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user))):
                return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
            
            status = request.POST.get('status')
            if status not in dict(TaskStage.STAGE_STATUS_CHOICES):
                return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
            
            stage.status = status
            if status == 'COMPLETED':
                stage.is_completed = True
            else:
                stage.is_completed = False
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
                'task_status': stage.task.status
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
            if not (getattr(user, 'is_superuser', False) or (hasattr(user, 'role') and (user.role == 'ADMIN' or stage.task.assigned_to == user))):
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
                'task_status': stage.task.status
            })
        except TaskStage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Stage not found'}, status=404)

# --- Task Templates (Global) ---

class TemplateListView(LoginRequiredMixin, ListView):
    """Список глобальных шаблонов (только для root-администратора)"""
    model = TaskTemplate
    template_name = 'dashboard/template_list.html'
    context_object_name = 'templates'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # Только root-администратор может видеть глобальные шаблоны
        if not getattr(user, 'is_superuser', False):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = TaskTemplate.objects.filter(template_type='global').prefetch_related('stages', 'activity_category')
        
        # Фильтрация по категории
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(activity_category_id=category_id)
        
        # Поиск по названию и описанию
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                django_models.Q(name__icontains=search) | 
                django_models.Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ActivityCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class TemplateCreateView(LoginRequiredMixin, CreateView):
    """Создание глобального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/template_form.html'
    fields = ['name', 'description', 'activity_category']
    success_url = reverse_lazy('dashboard:template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, 'is_superuser', False):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['stages'] = TemplateStageFormSet(self.request.POST)
        else:
            context['stages'] = TemplateStageFormSet()
        context['is_global'] = True
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        
        if stages.is_valid():
            form.instance.template_type = 'global'
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, 'Шаблон успешно создан.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class TemplateEditView(LoginRequiredMixin, UpdateView):
    """Редактирование глобального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/template_form.html'
    fields = ['name', 'description', 'activity_category']
    success_url = reverse_lazy('dashboard:template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, 'is_superuser', False):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        
        obj = self.get_object()
        if obj.template_type != 'global':
            messages.error(request, 'Вы не можете редактировать локальный шаблон.')
            return redirect('dashboard:template_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['stages'] = TemplateStageFormSet(self.request.POST, instance=self.object)
        else:
            context['stages'] = TemplateStageFormSet(instance=self.object)
        context['template_type'] = 'global'
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        stages = context['stages']
        
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, 'Шаблон успешно обновлен.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление глобального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, 'is_superuser', False):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        
        obj = self.get_object()
        if obj.template_type != 'global':
            messages.error(request, 'Вы не можете удалить локальный шаблон.')
            return redirect('dashboard:template_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление шаблона'
        context['message'] = f'Вы уверены, что хотите удалить шаблон "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:template_list')
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Шаблон успешно удален.')
        return super().delete(request, *args, **kwargs)


class TemplateDetailView(LoginRequiredMixin, TemplateView):
    """Просмотр деталей шаблона (AJAX)"""
    template_name = 'dashboard/template_detail_modal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template_id = self.kwargs.get('pk')
        try:
            template = TaskTemplate.objects.prefetch_related('stages').get(pk=template_id)
            context['template'] = template
            context['stages'] = template.stages.all().order_by('sequence_number')
        except TaskTemplate.DoesNotExist:
            context['error'] = 'Шаблон не найден'
        return context
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        template_id = self.kwargs.get('pk')
        try:
            template = TaskTemplate.objects.get(pk=template_id)
            # Глобальные шаблоны видны всем, локальные - только администратору тенанта
            if template.template_type != 'global':
                if not (hasattr(user, 'role') and user.role == 'ADMIN'):
                    return JsonResponse({'error': 'Permission denied'}, status=403)
        except TaskTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)
        
        return super().dispatch(request, *args, **kwargs)


# --- Task Templates (Local) ---

class LocalTemplateListView(LoginRequiredMixin, ListView):
    """Список локальных и глобальных шаблонов с переключателем"""
    model = TaskTemplate
    template_name = 'dashboard/local_template_list.html'
    context_object_name = 'templates'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # Только администратор тенанта может видеть шаблоны
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # Получаем фильтры
        category_id = self.request.GET.get('category')
        search = self.request.GET.get('search', '')
        template_type = self.request.GET.get('type', 'local')  # По умолчанию показываем мои шаблоны
        
        # Определяем, какие шаблоны показывать
        if template_type == 'local':
            queryset = TaskTemplate.objects.filter(template_type='local').prefetch_related('stages', 'activity_category')
        else:
            queryset = TaskTemplate.objects.filter(template_type='global').prefetch_related('stages', 'activity_category')
        
        # Применяем фильтры
        if category_id and category_id.strip():  # Проверяем, что category_id не пустой
            try:
                queryset = queryset.filter(activity_category_id=int(category_id))
            except (ValueError, TypeError):
                pass  # Если не число, игнорируем фильтр
        
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем фильтры
        category_id = self.request.GET.get('category')
        search = self.request.GET.get('search', '')
        template_type = self.request.GET.get('type', 'local')  # По умолчанию показываем мои шаблоны
        
        # Определяем заголовок
        if template_type == 'local':
            context['page_title'] = 'Мои шаблоны'
        else:
            context['page_title'] = 'Типовые шаблоны задач'
        
        context['categories'] = ActivityCategory.objects.all()
        context['selected_category'] = category_id
        context['search_query'] = search
        context['template_type'] = template_type
        
        return context


class LocalTemplateCreateView(LoginRequiredMixin, CreateView):
    """Создание локального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/local_template_form.html'
    fields = ['name', 'description', 'activity_category']
    success_url = reverse_lazy('dashboard:local_template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['stages'] = TemplateStageFormSet(self.request.POST)
        else:
            context['stages'] = TemplateStageFormSet()
        context['global_templates'] = TaskTemplate.objects.filter(template_type='global')
        context['template_type'] = 'local'
        return context
    
    def form_valid(self, form):
        import json
        from task_templates.models import DurationUnit, Material, StageMaterial
        
        form.instance.template_type = 'local'
        self.object = form.save()
        
        # Обработка этапов и материалов из JSON
        stages_data = self.request.POST.get('stages_data')
        if stages_data:
            try:
                stages = json.loads(stages_data)
                for stage_data in stages:
                    # Получаем duration_unit по ID или используем default (hour)
                    duration_unit_id = stage_data.get('duration_unit_id')
                    if not duration_unit_id:
                        # Используем час как default
                        duration_unit = DurationUnit.objects.filter(unit_type='hour').first()
                        if not duration_unit:
                            # Если нет, создаём
                            duration_unit, _ = DurationUnit.objects.get_or_create(
                                unit_type='hour',
                                defaults={'name': 'Час', 'abbreviation': 'ч'}
                            )
                    else:
                        duration_unit = DurationUnit.objects.get(id=duration_unit_id)
                    
                    stage = TaskTemplateStage.objects.create(
                        template=self.object,
                        name=stage_data.get('name', ''),
                        duration_from=float(stage_data.get('duration_from', 1)),
                        duration_to=float(stage_data.get('duration_to', 1)),
                        duration_unit=duration_unit,
                        position_id=stage_data.get('position_id') or None,
                        sequence_number=int(stage_data.get('sequence_number', 1))
                    )
                    
                    # Обработка материалов для этапа
                    materials = stage_data.get('materials', [])
                    for material_data in materials:
                        material_id = material_data.get('id')
                        if material_id:
                            try:
                                material = Material.objects.get(id=material_id)
                                # Создаём связь материала с этапом
                                StageMaterial.objects.create(
                                    stage=stage,
                                    material=material,
                                    quantity=float(material_data.get('quantity', 1))
                                )
                            except Material.DoesNotExist:
                                pass  # Пропускаем несуществующие материалы
            except (json.JSONDecodeError, ValueError) as e:
                messages.warning(self.request, f'Ошибка при сохранении этапов: {e}')
        
        messages.success(self.request, 'Мой шаблон успешно создан.')
        return redirect(self.success_url)


class LocalTemplateEditView(LoginRequiredMixin, UpdateView):
    """Редактирование локального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/local_template_form.html'
    fields = ['name', 'description', 'activity_category']
    success_url = reverse_lazy('dashboard:local_template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        
        obj = self.get_object()
        if obj.template_type == 'global':
            messages.error(request, 'Вы не можете редактировать типовой шаблон.')
            return redirect('dashboard:local_template_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['stages'] = TemplateStageFormSet(self.request.POST, instance=self.object)
        else:
            context['stages'] = TemplateStageFormSet(instance=self.object)
        context['global_templates'] = TaskTemplate.objects.filter(template_type='global')
        context['template_type'] = 'local'
        return context
    
    def form_valid(self, form):
        import json
        from task_templates.models import DurationUnit, Material, StageMaterial
        
        self.object = form.save()
        
        # Удаляем старые этапы
        self.object.stages.all().delete()
        
        # Обработка этапов и материалов из JSON
        stages_data = self.request.POST.get('stages_data')
        print(f"DEBUG: stages_data = {stages_data}")  # DEBUG
        if stages_data:
            try:
                stages = json.loads(stages_data)
                print(f"DEBUG: Parsed stages = {stages}")  # DEBUG
                for stage_data in stages:
                    # Получаем duration_unit по ID или используем default (hour)
                    duration_unit_id = stage_data.get('duration_unit_id')
                    if not duration_unit_id:
                        # Используем час как default
                        duration_unit = DurationUnit.objects.filter(unit_type='hour').first()
                        if not duration_unit:
                            # Если нет, создаём
                            duration_unit, _ = DurationUnit.objects.get_or_create(
                                unit_type='hour',
                                defaults={'name': 'Час', 'abbreviation': 'ч'}
                            )
                    else:
                        duration_unit = DurationUnit.objects.get(id=duration_unit_id)
                    
                    stage = TaskTemplateStage.objects.create(
                        template=self.object,
                        name=stage_data.get('name', ''),
                        duration_from=float(stage_data.get('duration_from', 1)),
                        duration_to=float(stage_data.get('duration_to', 1)),
                        duration_unit=duration_unit,
                        position_id=stage_data.get('position_id') or None,
                        sequence_number=int(stage_data.get('sequence_number', 1))
                    )
                    
                    # Обработка материалов для этапа
                    materials = stage_data.get('materials', [])
                    print(f"DEBUG: Stage '{stage.name}' materials = {materials}")  # DEBUG
                    for material_data in materials:
                        material_id = material_data.get('id')
                        quantity = material_data.get('quantity', 1)
                        print(f"DEBUG: Creating StageMaterial - material_id={material_id}, quantity={quantity}")  # DEBUG
                        if material_id:
                            try:
                                material = Material.objects.get(id=material_id)
                                # Создаём связь материала с этапом
                                stage_material = StageMaterial.objects.create(
                                    stage=stage,
                                    material=material,
                                    quantity=float(quantity)
                                )
                                print(f"DEBUG: Created StageMaterial id={stage_material.id}, quantity={stage_material.quantity}")  # DEBUG
                            except Material.DoesNotExist:
                                print(f"DEBUG: Material with id={material_id} not found")  # DEBUG
                                pass  # Пропускаем несуществующие материалы
            except (json.JSONDecodeError, ValueError) as e:
                print(f"DEBUG: Error parsing stages_data: {e}")  # DEBUG
                messages.warning(self.request, f'Ошибка при сохранении этапов: {e}')
        
        messages.success(self.request, 'Мой шаблон успешно обновлен.')
        return redirect(self.success_url)


class LocalTemplateDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление локального шаблона"""
    model = TaskTemplate
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:local_template_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        
        obj = self.get_object()
        if obj.template_type == 'global':
            messages.error(request, 'Вы не можете удалить типовой шаблон.')
            return redirect('dashboard:local_template_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление моего шаблона'
        context['message'] = f'Вы уверены, что хотите удалить шаблон "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:local_template_list')
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Мой шаблон успешно удален.')
        return super().delete(request, *args, **kwargs)


class LocalTemplateDiagramView(LoginRequiredMixin, TemplateView):
    """Редактор диаграммы для локального шаблона тенанта"""
    template_name = 'dashboard/local_template_diagram.html'
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template_id = self.kwargs.get('pk')
        template = get_object_or_404(TaskTemplate, id=template_id, template_type='local')
        
        # Проверяем, что это локальный шаблон
        if template.template_type != 'local':
            raise Http404("Это не локальный шаблон")
        
        context['template'] = template
        
        # Подготавливаем данные для Cytoscape
        import json
        stages_data = []
        for stage in template.stages.all().order_by('sequence_number'):
            stage_data = {
                'id': stage.id,
                'sequence_number': stage.sequence_number,
                'name': stage.name,
                'parent_stage_id': stage.parent_stage_id,
                'duration_from': stage.duration_from,
                'duration_to': stage.duration_to,
                'duration_unit': stage.duration_unit.name if stage.duration_unit else '',
                'position_id': stage.position_id,
                'position': stage.position.name if stage.position else '',
                'leads_to_stop': stage.leads_to_stop,
                'materials': [
                    {
                        'id': m.id,
                        'name': m.material.name,
                        'quantity': str(m.quantity),
                        'unit': m.material.unit.abbreviation
                    }
                    for m in stage.materials.all()
                ]
            }
            stages_data.append(stage_data)
        
        context['stages_json'] = json.dumps(stages_data)
        
        # Подготавливаем данные о должностях
        positions_data = []
        for position in Position.objects.all():
            positions_data.append({
                'id': position.id,
                'name': position.name
            })
        context['positions_json'] = json.dumps(positions_data)
        
        # Получаем все этапы для выпадающего списка
        context['all_stages'] = template.stages.all().order_by('sequence_number')
        context['positions'] = Position.objects.all()
        
        # Вычисляем общее время
        total_min = sum(s.duration_from for s in template.stages.all()) if template.stages.exists() else 0
        total_max = sum(s.duration_to for s in template.stages.all()) if template.stages.exists() else 0
        context['total_duration_min'] = total_min
        context['total_duration_max'] = total_max
        
        # Уникальные должности
        unique_positions = set()
        for stage in template.stages.all():
            if stage.position:
                unique_positions.add(stage.position.name)
        context['unique_positions'] = sorted(list(unique_positions))
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class CopyGlobalTemplateView(LoginRequiredMixin, TemplateView):
    """Копирование глобального шаблона в локальный с импортом справочников"""
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            from task_templates.models import DurationUnit, Material
            
            global_template_id = request.POST.get('template_id')
            if not global_template_id:
                return JsonResponse({'status': 'error', 'message': 'Template ID required'})
            
            # Получаем глобальный шаблон
            global_template = get_object_or_404(TaskTemplate, id=global_template_id, template_type='global')
            
            # Импортируем справочники и получаем маппинг старых ID на новые
            reference_mapping = self._import_reference_data(global_template)
            
            # Создаём локальный шаблон на основе глобального
            local_template = TaskTemplate.objects.create(
                name=f"{global_template.name} (копия)",
                description=global_template.description,
                template_type='local',
                activity_category=global_template.activity_category,
                based_on_global=global_template,
                version=1
            )
            
            # Копируем все этапы
            for stage in global_template.stages.all():
                # Получаем новые ID справочников
                new_duration_unit = None
                if stage.duration_unit:
                    new_duration_unit = reference_mapping['duration_units'].get(stage.duration_unit.id)
                
                new_position = None
                if stage.position:
                    new_position = reference_mapping['positions'].get(stage.position.id)
                
                new_stage = TaskTemplateStage.objects.create(
                    template=local_template,
                    name=stage.name,
                    parent_stage=None,  # Пока не копируем иерархию
                    duration_from=stage.duration_from,
                    duration_to=stage.duration_to,
                    duration_unit=new_duration_unit,
                    position=new_position,
                    sequence_number=stage.sequence_number,
                    leads_to_stop=stage.leads_to_stop
                )
                
                # Копируем материалы для этапа
                for material in stage.materials.all():
                    new_material = reference_mapping['materials'].get(material.material.id)
                    if new_material:
                        StageMaterial.objects.create(
                            stage=new_stage,
                            material=new_material,
                            quantity=material.quantity
                        )
            
            # Копируем SVG диаграмму если есть
            if global_template.diagram_svg:
                local_template.diagram_svg = global_template.diagram_svg
                local_template.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Шаблон "{local_template.name}" успешно создан',
                'template_id': local_template.id,
                'template_name': local_template.name,
                'redirect_url': reverse('dashboard:local_template_edit', args=[local_template.id])
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    def _import_reference_data(self, global_template):
        """Импортирует справочники из глобального шаблона в рабочую область тенанта
        Возвращает маппинг старых ID на новые объекты"""
        from task_templates.models import DurationUnit, Material
        
        # Маппинг для отслеживания импортированных справочников
        reference_mapping = {
            'duration_units': {},  # global_id -> local_object
            'positions': {},       # global_id -> local_object
            'materials': {}        # global_id -> local_object
        }
        
        # Собираем все уникальные справочники из этапов шаблона
        duration_units_to_import = set()
        positions_to_import = set()
        materials_to_import = set()
        
        for stage in global_template.stages.all():
            if stage.duration_unit:
                duration_units_to_import.add(stage.duration_unit.id)
            if stage.position:
                positions_to_import.add(stage.position.id)
            
            for material in stage.materials.all():
                materials_to_import.add(material.material.id)
        
        # Импортируем единицы времени
        for duration_unit_id in duration_units_to_import:
            try:
                global_unit = DurationUnit.objects.get(id=duration_unit_id)
                # Проверяем, есть ли уже такая единица в тенанте
                local_unit, created = DurationUnit.objects.get_or_create(
                    unit_type=global_unit.unit_type,
                    defaults={
                        'name': global_unit.name,
                        'abbreviation': global_unit.abbreviation
                    }
                )
                reference_mapping['duration_units'][duration_unit_id] = local_unit
            except DurationUnit.DoesNotExist:
                pass
        
        # Импортируем должности
        for position_id in positions_to_import:
            try:
                global_position = Position.objects.get(id=position_id)
                # Проверяем, есть ли уже такая должность в тенанте
                local_position, created = Position.objects.get_or_create(
                    name=global_position.name,
                    defaults={
                        'description': global_position.description
                    }
                )
                reference_mapping['positions'][position_id] = local_position
            except Position.DoesNotExist:
                pass
        
        # Импортируем материалы
        for material_id in materials_to_import:
            try:
                global_material = Material.objects.get(id=material_id)
                # Проверяем, есть ли уже такой материал в тенанте
                local_material, created = Material.objects.get_or_create(
                    code=global_material.code,
                    defaults={
                        'name': global_material.name,
                        'description': global_material.description,
                        'unit': global_material.unit,
                        'unit_cost': global_material.unit_cost
                    }
                )
                reference_mapping['materials'][material_id] = local_material
            except Material.DoesNotExist:
                pass
        
        return reference_mapping


class TemplateDetailAjaxView(LoginRequiredMixin, TemplateView):
    """AJAX представление для деталей шаблона"""
    template_name = 'dashboard/template_detail_ajax.html'
    
    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        template_id = self.kwargs.get('pk')
        
        try:
            template = TaskTemplate.objects.prefetch_related('stages', 'activity_category').get(pk=template_id)
            context['template'] = template
            stages = template.stages.all().order_by('sequence_number')
            context['stages'] = stages
            
            # Подготавливаем JSON данные для диаграммы
            stages_data = []
            for stage in stages:
                stage_data = {
                    'id': stage.id,
                    'sequence_number': stage.sequence_number,
                    'name': stage.name,
                    'position': stage.position.name if stage.position else None,
                    'duration_from': stage.duration_from,
                    'duration_to': stage.duration_to,
                    'duration_unit': stage.duration_unit.name if stage.duration_unit else None,
                    'parent_stage_id': stage.parent_stage_id,
                    'leads_to_stop': stage.leads_to_stop
                }
                stages_data.append(stage_data)
            
            context['stages_json'] = json.dumps(stages_data)
        except TaskTemplate.DoesNotExist:
            context['error'] = 'Шаблон не найден'
            context['stages_json'] = '[]'
        
        return context


# --- Template Proposals ---

class MyProposalsView(LoginRequiredMixin, ListView):
    """Мои предложения (администратор тенанта)"""
    model = TemplateProposal
    template_name = 'dashboard/my_proposals.html'
    context_object_name = 'proposals'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        queryset = TemplateProposal.objects.filter(proposed_by_id=user.id).prefetch_related('local_template', 'approved_global_template')
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = TemplateProposal.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status')
        return context


class AllProposalsView(LoginRequiredMixin, ListView):
    """Все предложения (root-администратор)"""
    model = TemplateProposal
    template_name = 'dashboard/all_proposals.html'
    context_object_name = 'proposals'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, 'is_superuser', False):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = TemplateProposal.objects.all().prefetch_related('template', 'proposed_by')
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = TemplateProposal.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status')
        return context


@login_required
def approve_proposal(request, pk):
    """Одобрение предложения"""
    user = request.user
    if not getattr(user, 'is_superuser', False):
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('dashboard:home')
    
    try:
        proposal = TemplateProposal.objects.get(pk=pk)
        proposal.approve()
        messages.success(request, 'Предложение успешно одобрено.')
    except TemplateProposal.DoesNotExist:
        messages.error(request, 'Предложение не найдено.')
    
    return redirect('dashboard:all_proposals')


@login_required
def reject_proposal(request, pk):
    """Отклонение предложения"""
    user = request.user
    if not getattr(user, 'is_superuser', False):
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        try:
            proposal = TemplateProposal.objects.get(pk=pk)
            proposal.reject(reason)
            messages.success(request, 'Предложение успешно отклонено.')
        except TemplateProposal.DoesNotExist:
            messages.error(request, 'Предложение не найдено.')
        
        return redirect('dashboard:all_proposals')
    
    try:
        proposal = TemplateProposal.objects.get(pk=pk)
        return render(request, 'dashboard/reject_proposal_modal.html', {'proposal': proposal})
    except TemplateProposal.DoesNotExist:
        messages.error(request, 'Предложение не найдено.')
        return redirect('dashboard:all_proposals')


@login_required
def withdraw_proposal(request, pk):
    """Отзыв предложения (администратор тенанта)"""
    user = request.user
    if not (hasattr(user, 'role') and user.role == 'ADMIN'):
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('dashboard:home')
    
    try:
        proposal = TemplateProposal.objects.get(pk=pk, proposed_by_id=user.id)
        proposal.withdraw()
        messages.success(request, 'Предложение успешно отозвано.')
    except TemplateProposal.DoesNotExist:
        messages.error(request, 'Предложение не найдено.')
    
    return redirect('dashboard:my_proposals')


@login_required
def get_template_stages(request, pk):
    """Получить этапы шаблона (AJAX)"""
    try:
        template = TaskTemplate.objects.prefetch_related(
            'stages__duration_unit',
            'stages__position',
            'stages__materials__material__unit'
        ).get(pk=pk)
        
        stages = []
        for stage in template.stages.all().order_by('sequence_number'):
            # Конвертируем длительность в минуты (берем среднее между duration_from и duration_to)
            duration_minutes = 0
            duration_text = ''
            if stage.duration_from and stage.duration_to and stage.duration_unit:
                avg_duration = (stage.duration_from + stage.duration_to) / 2
                
                # Конвертируем в минуты в зависимости от единицы времени
                if stage.duration_unit.unit_type == 'minute':
                    duration_minutes = int(avg_duration)
                elif stage.duration_unit.unit_type == 'hour':
                    duration_minutes = int(avg_duration * 60)
                elif stage.duration_unit.unit_type == 'day':
                    duration_minutes = int(avg_duration * 60 * 8)  # 8-часовой рабочий день
                elif stage.duration_unit.unit_type == 'second':
                    duration_minutes = int(avg_duration / 60)
                else:
                    duration_minutes = int(avg_duration)
                
                # Формируем текстовое описание длительности
                duration_text = f"{stage.duration_from}-{stage.duration_to} {stage.duration_unit.abbreviation}"
            
            # Собираем информацию о материалах
            materials = []
            for stage_material in stage.materials.all():
                materials.append({
                    'id': stage_material.material.id,
                    'name': stage_material.material.name,
                    'quantity': float(stage_material.quantity),
                    'unit': stage_material.material.unit.abbreviation
                })
            
            stage_data = {
                'name': stage.name,
                'duration_minutes': duration_minutes,
                'duration_text': duration_text,
                'order': stage.sequence_number,
                'position_id': stage.position.id if stage.position else None,
                'position': stage.position.name if stage.position else None,
                'materials': materials,
                'has_materials': len(materials) > 0
            }
            
            stages.append(stage_data)
        
        return JsonResponse({'status': 'success', 'stages': stages})
    except TaskTemplate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Template not found'}, status=404)


# ============================================================================
# СПРАВОЧНИКИ (DICTIONARIES) - CRUD операции для администраторов тенанта
# ============================================================================

# --- Единицы времени (Duration Units) ---

class DurationUnitForm(forms.ModelForm):
    class Meta:
        model = DurationUnit
        fields = ['unit_type', 'name', 'abbreviation']
        labels = {
            'unit_type': 'Тип единицы',
            'name': 'Название',
            'abbreviation': 'Сокращение'
        }
        widgets = {
            'unit_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5'}),
        }


class DurationUnitListView(LoginRequiredMixin, ListView):
    """Список единиц времени"""
    model = DurationUnit
    template_name = 'dashboard/duration_unit_list.html'
    context_object_name = 'duration_units'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

    def get_queryset(self):
        return DurationUnit.objects.all().order_by('id')


class DurationUnitCreateView(LoginRequiredMixin, CreateView):
    """Создание единицы времени"""
    model = DurationUnit
    form_class = DurationUnitForm
    template_name = 'dashboard/duration_unit_form.html'
    success_url = reverse_lazy('dashboard:duration_unit_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


class DurationUnitUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование единицы времени"""
    model = DurationUnit
    form_class = DurationUnitForm
    template_name = 'dashboard/duration_unit_form.html'
    success_url = reverse_lazy('dashboard:duration_unit_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


class DurationUnitDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление единицы времени"""
    model = DurationUnit
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:duration_unit_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление единицы времени'
        context['message'] = f'Вы уверены, что хотите удалить единицу времени "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:duration_unit_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


# --- Должности исполнителей (Positions) - дополнительные представления ---

class PositionCreateView(LoginRequiredMixin, CreateView):
    """Создание должности"""
    model = Position
    form_class = PositionForm
    template_name = 'dashboard/position_form.html'
    success_url = reverse_lazy('dashboard:position_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


# --- Материалы (Materials) ---

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['name', 'description', 'code', 'unit', 'unit_cost', 'is_active']
        labels = {
            'name': 'Название',
            'description': 'Описание',
            'code': 'Код материала',
            'unit': 'Единица измерения',
            'unit_cost': 'Стоимость за единицу',
            'is_active': 'Активен'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MaterialListView(LoginRequiredMixin, ListView):
    """Список материалов"""
    model = Material
    template_name = 'dashboard/material_list.html'
    context_object_name = 'materials'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')

    def get_queryset(self):
        return Material.objects.select_related('unit').all().order_by('name')


class MaterialCreateView(LoginRequiredMixin, CreateView):
    """Создание материала"""
    model = Material
    form_class = MaterialForm
    template_name = 'dashboard/material_form.html'
    success_url = reverse_lazy('dashboard:material_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование материала"""
    model = Material
    form_class = MaterialForm
    template_name = 'dashboard/material_form.html'
    success_url = reverse_lazy('dashboard:material_list')

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


class MaterialDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление материала"""
    model = Material
    template_name = 'dashboard/confirm_delete.html'
    success_url = reverse_lazy('dashboard:material_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление материала'
        context['message'] = f'Вы уверены, что хотите удалить материал "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:material_list')
        return context

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (hasattr(user, 'role') and user.role == 'ADMIN') or getattr(user, 'is_superuser', False):
            return super().dispatch(request, *args, **kwargs)
        return redirect('dashboard:home')


# --- Template Export/Import ---

from django.http import HttpResponse, JsonResponse
from task_templates.export_import import TemplateExporter, TemplateImporter

@login_required
def api_get_positions(request):
    """API для получения списка должностей из task_templates"""
    from task_templates.models import Position as TaskPosition
    positions = TaskPosition.objects.all().values('id', 'name', 'description')
    return JsonResponse(list(positions), safe=False)

@login_required
def api_get_duration_units(request):
    """API для получения списка единиц времени"""
    from task_templates.models import DurationUnit
    units = DurationUnit.objects.all().values('id', 'name', 'unit_type')
    return JsonResponse(list(units), safe=False)

@login_required
def api_get_materials(request):
    """API для получения списка материалов"""
    from task_templates.models import Material
    
    materials = Material.objects.filter(is_active=True).select_related('unit')
    data = [{
        'id': m.id,
        'name': m.name,
        'code': m.code,
        'unit_id': m.unit.id,
        'unit_name': m.unit.name,
        'unit_abbreviation': m.unit.abbreviation,
    } for m in materials]
    
    return JsonResponse(data, safe=False)


@login_required
def api_get_units(request):
    """API для получения списка единиц измерения"""
    from task_templates.models import UnitOfMeasure
    
    units = UnitOfMeasure.objects.filter(is_active=True)
    data = [{
        'id': u.id,
        'name': u.name,
        'abbreviation': u.abbreviation,
    } for u in units]
    
    return JsonResponse(data, safe=False)

@login_required
def api_get_employees(request):
    """API для получения списка сотрудников тенанта"""
    employees = TenantUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    data = [{
        'id': e.id,
        'name': e.get_full_name() or e.username,
        'username': e.username,
        'position': e.position.name if e.position else '',
    } for e in employees]
    
    return JsonResponse(data, safe=False)

@login_required
def api_create_position(request):
    """API для создания новой должности"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    import json
    from task_templates.models import Position as TaskPosition
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Название должности обязательно'}, status=400)
        
        # Проверяем, не существует ли уже такая должность
        if TaskPosition.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Должность с таким названием уже существует'}, status=400)
        
        # Создаем новую должность
        position = TaskPosition.objects.create(
            name=name,
            description=description
        )
        
        return JsonResponse({
            'id': position.id,
            'name': position.name,
            'description': position.description
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def export_template(request, pk):
    """Экспорт одного шаблона в JSON"""
    from urllib.parse import quote
    
    template = get_object_or_404(TaskTemplate, pk=pk)
    
    # Проверка прав доступа
    user = request.user
    if template.template_type == 'local':
        # Локальные шаблоны может экспортировать только админ тенанта
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет прав для экспорта этого шаблона.')
            return redirect('dashboard:local_template_list')
    
    # Экспортируем шаблон
    json_data = TemplateExporter.export_to_json(template)
    
    # Формируем имя файла: категория_имя_шаблона.tpl
    category_name = template.activity_category.name if template.activity_category else 'General'
    # Очищаем имена от спецсимволов
    category_clean = category_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    template_clean = template.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"{category_clean}_{template_clean}.tpl"
    
    # Создаем HTTP ответ с файлом
    response = HttpResponse(json_data, content_type='application/octet-stream')
    # Используем quote для правильного кодирования имени файла
    encoded_filename = quote(filename.encode('utf-8'))
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
    
    return response

@login_required
def import_template(request):
    """Импорт шаблона из JSON файла"""
    if request.method != 'POST':
        return redirect('dashboard:local_template_list')
    
    user = request.user
    
    # Проверка прав доступа
    if not (hasattr(user, 'role') and user.role == 'ADMIN'):
        messages.error(request, 'У вас нет прав для импорта шаблонов.')
        return redirect('dashboard:local_template_list')
    
    # Получаем файл
    uploaded_file = request.FILES.get('template_file')
    if not uploaded_file:
        messages.error(request, 'Файл не выбран.')
        return redirect('dashboard:local_template_list')
    
    # Проверяем расширение файла
    if not (uploaded_file.name.endswith('.tpl') or uploaded_file.name.endswith('.json')):
        messages.error(request, 'Неверный формат файла. Ожидается .tpl или .json')
        return redirect('dashboard:local_template_list')
    
    # Читаем содержимое файла
    try:
        json_string = uploaded_file.read().decode('utf-8')
    except Exception as e:
        messages.error(request, f'Ошибка чтения файла: {str(e)}')
        return redirect('dashboard:local_template_list')
    
    # Получаем параметры импорта
    template_type = request.POST.get('template_type', 'local')
    conflict_strategy = request.POST.get('conflict_strategy', 'rename')
    
    # Импортируем
    importer = TemplateImporter(user=user, tenant=getattr(request, 'tenant', None))
    result = importer.import_from_json(json_string, template_type, conflict_strategy)
    
    # Показываем результат
    if result['success']:
        created_count = len(result['created']['templates'])
        messages.success(request, f'Успешно импортировано шаблонов: {created_count}')
        
        if result['warnings']:
            for warning in result['warnings']:
                messages.warning(request, warning)
    else:
        messages.error(request, 'Ошибка импорта:')
        for error in result['errors']:
            messages.error(request, error)
    
    return redirect('dashboard:local_template_list')

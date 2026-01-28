from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django import forms
from django.forms import inlineformset_factory
from django.contrib import messages
from django.utils import timezone

from django.db.models import Sum
from django.db import models as django_models
from tasks.models import Task, TaskStage
from media_app.models import Media
from users_app.models import TenantUser, Department, Position
from task_templates.models import TaskTemplate, TaskTemplateStage, TemplateProposal, ActivityCategory
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

@login_required
def home(request):
    user = request.user
    tenant = getattr(request, 'tenant', None)
    
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
        fields = ['title', 'description', 'is_completed', 'assigned_to']
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'is_completed': 'Выполнено',
            'assigned_to': 'Исполнитель'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
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
    fields=['name', 'duration_minutes', 'order'],
    extra=1,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название этапа'}),
        'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Мин'}),
        'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '№'}),
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
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'ADMIN':
            # Администратор видит глобальные и локальные шаблоны
            data['templates'] = TaskTemplate.objects.all().prefetch_related('activity_category').order_by('activity_category', 'name')
        else:
            # Обычный пользователь видит только глобальные шаблоны
            data['templates'] = TaskTemplate.objects.filter(template_type='global').prefetch_related('activity_category').order_by('activity_category', 'name')
        
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
            return self.render_to_response(self.get_context_data(form=form))

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
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'ADMIN':
            data['templates'] = TaskTemplate.objects.all().prefetch_related('activity_category').order_by('activity_category', 'name')
        else:
            data['templates'] = TaskTemplate.objects.filter(template_type='global').prefetch_related('activity_category').order_by('activity_category', 'name')
        
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
            return self.render_to_response(self.get_context_data(form=form))

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

    def form_valid(self, form):
        # Повторная проверка при сохранении формы (на случай одновременных запросов)
        tenant = getattr(self.request, 'tenant', None)
        if tenant and tenant.subscription_plan:
            current_user_count = TenantUser.objects.count()
            if current_user_count >= tenant.subscription_plan.max_users:
                messages.error(self.request, f"Превышен лимит пользователей для вашего тарифа ({tenant.subscription_plan.max_users}).")
                return redirect('dashboard:employee_list')
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
            context['stages'] = template.stages.all().order_by('order')
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
    """Список локальных шаблонов тенанта"""
    model = TaskTemplate
    template_name = 'dashboard/local_template_list.html'
    context_object_name = 'templates'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # Только администратор тенанта может видеть локальные шаблоны
        if not (hasattr(user, 'role') and user.role == 'ADMIN'):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = TaskTemplate.objects.filter(template_type='local').prefetch_related('stages', 'activity_category')
        
        # Фильтрация по категории
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(activity_category_id=category_id)
        
        # Поиск по названию
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ActivityCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('search', '')
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
        context = self.get_context_data()
        stages = context['stages']
        
        if stages.is_valid():
            form.instance.template_type = 'local'
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, 'Локальный шаблон успешно создан.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


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
            messages.error(request, 'Вы не можете редактировать глобальный шаблон.')
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
        context = self.get_context_data()
        stages = context['stages']
        
        if stages.is_valid():
            self.object = form.save()
            stages.instance = self.object
            stages.save()
            messages.success(self.request, 'Локальный шаблон успешно обновлен.')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


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
            messages.error(request, 'Вы не можете удалить глобальный шаблон.')
            return redirect('dashboard:local_template_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление локального шаблона'
        context['message'] = f'Вы уверены, что хотите удалить шаблон "{self.object.name}"?'
        context['cancel_url'] = reverse_lazy('dashboard:local_template_list')
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Локальный шаблон успешно удален.')
        return super().delete(request, *args, **kwargs)


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
        queryset = TemplateProposal.objects.filter(proposed_by=user).prefetch_related('template')
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = TemplateProposal.PROPOSAL_STATUS_CHOICES
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
        context['statuses'] = TemplateProposal.PROPOSAL_STATUS_CHOICES
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
        proposal = TemplateProposal.objects.get(pk=pk, proposed_by=user)
        proposal.withdraw()
        messages.success(request, 'Предложение успешно отозвано.')
    except TemplateProposal.DoesNotExist:
        messages.error(request, 'Предложение не найдено.')
    
    return redirect('dashboard:my_proposals')


@login_required
def get_template_stages(request, pk):
    """Получить этапы шаблона (AJAX)"""
    try:
        template = TaskTemplate.objects.prefetch_related('stages').get(pk=pk)
        stages = [
            {
                'id': stage.id,
                'name': stage.name,
                'description': stage.description,
                'estimated_duration_hours': stage.estimated_duration_hours,
                'sequence_number': stage.sequence_number
            }
            for stage in template.stages.all().order_by('sequence_number')
        ]
        return JsonResponse({'status': 'success', 'stages': stages})
    except TaskTemplate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Template not found'}, status=404)

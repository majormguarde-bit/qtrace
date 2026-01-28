from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django_tenants.utils import tenant_context
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import subprocess
import os
from datetime import datetime
from django.db import connection
from django.conf import settings
from django.http import HttpResponse

from django.core.mail import get_connection, send_mail
from django.contrib.auth.hashers import make_password
from .models import Client, Domain, Payment, SubscriptionPlan, MailSettings, ContactMessage, UserProfile
from users_app.models import TenantUser
from .serializers import TenantRegistrationSerializer
from django.db.models import Sum, Max


def superuser_required(user):
    # Проверяем, что это активный пользователь, он является суперпользователем 
    # И это именно системный пользователь (User), а не пользователь тенанта (TenantUser)
    return user.is_active and user.is_superuser and isinstance(user, User)


def get_paginated_data(request, queryset, default_order='-id'):
    # Сортировка
    sort_by = request.GET.get('sort', default_order)
    try:
        queryset = queryset.order_by(sort_by)
    except:
        queryset = queryset.order_by(default_order)

    # Количество строк на странице
    per_page = request.GET.get('per_page', '10')
    if per_page == 'all':
        per_page = queryset.count() or 10
    else:
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return page_obj, sort_by, per_page


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_finance(request):
    """Страница финансов: сводная таблица платежей по клиентам"""
    search_query = request.GET.get('search', '')
    
    # Аннотируем клиентов общей суммой платежей и датой последнего платежа
    queryset = Client.objects.exclude(schema_name='public').annotate(
        total_paid=Sum('payments__amount'),
        last_payment_date=Max('payments__date')
    ).select_related('subscription_plan')
    
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(schema_name__icontains=search_query)
        )
    
    page_obj, sort_by, per_page = get_paginated_data(request, queryset, '-last_payment_date')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'per_page': per_page,
        'today': timezone.now().date(),
    }
    return render(request, 'customers/superuser_finance.html', context)


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_client_payments(request, tenant_id):
    """Управление платежами конкретного клиента"""
    tenant = get_object_or_404(Client, id=tenant_id)
    payments = tenant.payments.all().order_by('-date')
    
    context = {
        'tenant': tenant,
        'payments': payments,
        'total_paid': payments.aggregate(Sum('amount'))['amount__sum'] or 0
    }
    return render(request, 'customers/superuser_client_payments.html', context)


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_payment_add(request, tenant_id):
    """Добавление платежа"""
    tenant = get_object_or_404(Client, id=tenant_id)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_date = request.POST.get('payment_date')
        comment = request.POST.get('comment')
        
        Payment.objects.create(
            tenant=tenant,
            amount=amount,
            date=payment_date,
            description=comment
        )
        messages.success(request, f'Платеж для {tenant.name} успешно добавлен.')
        return redirect('superuser_client_payments', tenant_id=tenant.id)
    
    return render(request, 'customers/superuser_payment_form.html', {
        'tenant': tenant,
        'is_create': True,
        'today': timezone.now().date()
    })


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_payment_edit(request, payment_id):
    """Редактирование платежа"""
    payment = get_object_or_404(Payment, id=payment_id)
    tenant = payment.tenant
    if request.method == 'POST':
        payment.amount = request.POST.get('amount')
        payment.date = request.POST.get('payment_date')
        payment.description = request.POST.get('comment')
        payment.save()
        
        messages.success(request, 'Платеж успешно обновлен.')
        return redirect('superuser_client_payments', tenant_id=tenant.id)
    
    return render(request, 'customers/superuser_payment_form.html', {
        'payment': payment,
        'tenant': tenant,
        'is_create': False
    })


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_payment_delete(request, payment_id):
    """Удаление платежа"""
    payment = get_object_or_404(Payment, id=payment_id)
    tenant_id = payment.tenant.id
    payment.delete()
    messages.success(request, 'Платеж успешно удален.')
    return redirect('superuser_client_payments', tenant_id=tenant_id)

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_admin_create(request):
    """Создание нового администратора платформы"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        tenant_id = request.POST.get('tenant')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Пользователь с именем {username} уже существует.')
            return render(request, 'customers/superuser_admin_form.html', {
                'is_create': True,
                'tenants': Client.objects.exclude(schema_name='public')
            })
            
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', '')
        )
        
        user.is_superuser = 'is_superuser' in request.POST
        user.is_staff = 'is_staff' in request.POST or user.is_superuser
        user.is_active = 'is_active' in request.POST
        user.save()
 
        # Создаем профиль и привязываем тенант
        profile, created = UserProfile.objects.get_or_create(user=user)
        if tenant_id:
            profile.tenant_id = tenant_id
            
        # Если это не персонал платформы, но привязан к тенанту, это ADMIN тенанта
        if not (user.is_staff or user.is_superuser) and tenant_id:
            profile.role = 'ADMIN'
        elif user.is_staff or user.is_superuser:
            profile.role = 'ADMIN'
            
        profile.can_delete_media = 'can_delete_media' in request.POST
        profile.save()

        # Синхронизация с тенантом (если выбран)
        if tenant_id:
            try:
                tenant = Client.objects.get(id=tenant_id)
                with tenant_context(tenant):
                    # Проверка лимита пользователей по тарифу перед созданием в тенанте
                    if tenant.subscription_plan:
                        current_user_count = TenantUser.objects.count()
                        if current_user_count >= tenant.subscription_plan.max_users:
                            # Если пользователь уже существует (синхронизация существующего), разрешаем
                            if not TenantUser.objects.filter(username=user.username).exists():
                                messages.error(request, f'Не удалось добавить администратора в организацию "{tenant.name}": достигнут лимит пользователей по тарифу ({tenant.subscription_plan.max_users}).')
                                # Удаляем созданного системного пользователя, так как синхронизация невозможна
                                user.delete()
                                return render(request, 'customers/superuser_admin_form.html', {
                                    'is_create': True,
                                    'tenants': Client.objects.exclude(schema_name='public')
                                })

                    t_user, created = TenantUser.objects.get_or_create(username=user.username)
                    t_user.email = user.email
                    t_user.first_name = user.first_name
                    t_user.last_name = user.last_name
                    t_user.role = 'ADMIN' # Принудительно ставим роль админа
                    t_user.password_hash = user.password # Копируем хеш пароля
                    t_user.is_active = user.is_active
                    t_user.save()
            except Exception as e:
                messages.warning(request, f'Пользователь создан, но не удалось синхронизировать с тенантом: {e}')
        
        messages.success(request, f'Администратор {username} успешно создан.')
        return redirect('superuser_admins')
        
    return render(request, 'customers/superuser_admin_form.html', {
        'is_create': True,
        'tenants': Client.objects.exclude(schema_name='public')
    })

from django.contrib.auth import views as auth_views

class SuperuserLoginView(auth_views.LoginView):
    template_name = 'dashboard/login.html' # Используем существующий шаблон
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Для суперпользователя на главной странице всегда должен быть основной домен
        host = self.request.get_host().split(':')[0]
        if '.localhost' in self.request.get_host() or host == 'localhost' or host == '127.0.0.1':
            context['base_url'] = f"http://localhost:{self.request.get_port()}"
        else:
            # Пытаемся выделить основной домен (например, qtrace.ru)
            parts = self.request.get_host().split('.')
            if len(parts) > 2:
                context['base_url'] = f"https://{'.'.join(parts[-2:])}"
            else:
                context['base_url'] = f"https://{self.request.get_host()}"
        return context

    def get_success_url(self):
        return '/superuser/'

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_dashboard(request):
    """Панель управления для администратора платформы (Public Schema)"""
    tenants = Client.objects.exclude(schema_name='public')
    context = {
        'tenants_count': tenants.count(),
        'active_tenants': tenants.filter(is_active=True).count(),
        'blocked_tenants': tenants.filter(is_active=False).count(),
        'total_revenue': Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'recent_tenants': tenants.order_by('-created_on')[:5],
    }
    return render(request, 'customers/superuser_dashboard.html', context)


def public_tariffs(request):
    """Публичная страница с тарифами"""
    # Получаем все активные планы, сортируем по цене, но 0 (Договорной) должен быть в конце
    all_plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by('price_month'))
    
    # Перемещаем "Договорной" в конец, если он есть
    plans = [p for p in all_plans if p.name != 'Договорной']
    negotiated = [p for p in all_plans if p.name == 'Договорной']
    plans.extend(negotiated)
    
    return render(request, 'customers/public_tariffs.html', {'plans': plans})

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenants(request):
    """Список всех организаций"""
    
    queryset = Client.objects.all().exclude(schema_name='public').select_related('subscription_plan')
    today = timezone.now().date()
    
    # Статистика для графического представления
    tenants_all = Client.objects.exclude(schema_name='public')
    stats = {
        'total': tenants_all.count(),
        'active': tenants_all.filter(
            Q(subscription_end_date__gte=today) | Q(subscription_end_date__isnull=True),
            subscription_plan__isnull=False
        ).count(),
        'expiring_7': tenants_all.filter(
            subscription_end_date__gte=today,
            subscription_end_date__lte=today + timedelta(days=7)
        ).count(),
        'expiring_30': tenants_all.filter(
            subscription_end_date__gte=today,
            subscription_end_date__lte=today + timedelta(days=30)
        ).count(),
        'expired': tenants_all.filter(
            subscription_end_date__lt=today
        ).count(),
        'no_plan': tenants_all.filter(subscription_plan__isnull=True).count(),
    }
    
    # Расчет процентов для прогресс-баров
    if stats['total'] > 0:
        stats['active_pct'] = (stats['active'] / stats['total']) * 100
        stats['expired_pct'] = (stats['expired'] / stats['total']) * 100
        stats['no_plan_pct'] = (stats['no_plan'] / stats['total']) * 100
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(schema_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    page_obj, sort_by, per_page = get_paginated_data(request, queryset, '-created_on')
    
    # Добавляем количество пользователей для каждой организации на текущей странице
    for tenant in page_obj:
        try:
            with tenant_context(tenant):
                tenant.user_count = TenantUser.objects.count()
                if tenant.subscription_plan:
                    tenant.user_limit = tenant.subscription_plan.max_users
                    tenant.user_percent = min(int((tenant.user_count / tenant.user_limit) * 100), 100) if tenant.user_limit > 0 else 0
                else:
                    tenant.user_limit = 0
                    tenant.user_percent = 0
        except Exception as e:
            print(f"Error counting users for tenant {tenant.schema_name}: {e}")
            tenant.user_count = 0
            tenant.user_limit = 0
            tenant.user_percent = 0
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'per_page': per_page,
        'search_query': search_query,
        'today': timezone.now().date(),
        'stats': stats,
    }
    return render(request, 'customers/superuser_tenants.html', context)


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenant_edit(request, tenant_id):
    """Редактирование параметров организации"""
    tenant = get_object_or_404(Client, id=tenant_id)
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    if request.method == 'POST':
        tenant.name = request.POST.get('name')
        tenant.phone = request.POST.get('phone')
        tenant.email = request.POST.get('email')
        tenant.telegram = request.POST.get('telegram')
        tenant.contact_person = request.POST.get('contact_person')
        tenant.can_admin_delete_media = 'can_admin_delete_media' in request.POST
        
        plan_id = request.POST.get('subscription_plan')
        months = int(request.POST.get('subscription_months', 1))
        
        if plan_id:
            plan = get_object_or_404(SubscriptionPlan, id=plan_id)
            tenant.subscription_plan = plan
            
            # Автоматический расчет даты окончания: сегодня + (дни_тарифа * месяцев)
            total_days = plan.work_days_limit * months
            tenant.subscription_end_date = timezone.now().date() + timedelta(days=total_days)
        else:
            tenant.subscription_plan = None
            # Если тариф не выбран, сохраняем вручную введенную дату или оставляем пустой
            sub_end = request.POST.get('subscription_end_date')
            if sub_end:
                tenant.subscription_end_date = sub_end
            else:
                tenant.subscription_end_date = None
            
        tenant.save()
        messages.success(request, f'Параметры организации "{tenant.name}" успешно обновлены.')
        return redirect('superuser_tenants')
        
    context = {
        'tenant': tenant,
        'plans': plans,
        'payments': tenant.payments.all().order_by('-date')[:5],
        'total_paid': tenant.payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'today': timezone.now().date(),
    }
    return render(request, 'customers/superuser_tenant_form.html', context)


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenant_toggle_status(request, tenant_id):
    """Заблокировать / Разблокировать организацию и всех её пользователей"""
    tenant = get_object_or_404(Client, id=tenant_id)
    if tenant.schema_name == 'public':
        messages.error(request, 'Нельзя изменить статус публичной схемы.')
        return redirect('superuser_tenants')
        
    tenant.is_active = not tenant.is_active
    tenant.save()
    
    # Синхронно обновляем статус всех пользователей внутри тенанта
    try:
        with tenant_context(tenant):
            TenantUser.objects.all().update(is_active=tenant.is_active)
    except Exception as e:
        messages.warning(request, f'Статус организации изменен, но возникла ошибка при обновлении пользователей: {e}')
    
    status_text = "разблокирована" if tenant.is_active else "заблокирована"
    messages.success(request, f'Организация "{tenant.name}" и все её пользователи успешно {status_text}.')
    
    # Редирект обратно на ту же страницу, откуда пришли, или в список
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    
    referer = request.META.get('HTTP_REFERER')
    if referer and 'edit' in referer:
        return redirect('superuser_tenant_edit', tenant_id=tenant.id)
        
    return redirect('superuser_tenants')


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenant_delete(request, tenant_id):
    """Удаление организации"""
    tenant = get_object_or_404(Client, id=tenant_id)
    if tenant.schema_name == 'public':
        messages.error(request, 'Нельзя удалить публичную схему.')
        return redirect('superuser_tenants')
        
    if request.method == 'POST':
        name = tenant.name
        tenant.delete() # django-tenants автоматически удалит схему, если auto_drop_schema=True
        messages.success(request, f'Организация "{name}" и все её данные успешно удалены.')
        return redirect('superuser_tenants')
        
    return render(request, 'customers/superuser_tenant_confirm_delete.html', {'tenant': tenant})

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_domains(request):
    """Список всех доменов"""
    queryset = Domain.objects.all()
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(domain__icontains=search_query) | 
            Q(tenant__name__icontains=search_query)
        )

    page_obj, sort_by, per_page = get_paginated_data(request, queryset, 'domain')
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'per_page': per_page,
        'search_query': search_query,
    }
    return render(request, 'customers/superuser_domains.html', context)

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_admins(request):
    """Список администраторов (Платформы и Тенантов)"""
    # 1. Администраторы платформы (из public схемы)
    platform_admins = User.objects.filter(
        Q(is_superuser=True) | Q(is_staff=True)
    ).select_related('profile', 'profile__tenant').order_by('username')
    
    # 2. Администраторы тенантов (собираем из всех схем)
    tenant_admins = []
    tenants = Client.objects.exclude(schema_name='public')
    
    search_query = request.GET.get('search', '')
    
    for tenant in tenants:
        try:
            with tenant_context(tenant):
                # Ищем пользователей с ролью ADMIN в схеме тенанта
                admins = TenantUser.objects.filter(role='ADMIN')
                
                if search_query:
                    admins = admins.filter(
                        Q(username__icontains=search_query) | 
                        Q(email__icontains=search_query) |
                        Q(first_name__icontains=search_query) |
                        Q(last_name__icontains=search_query)
                    )
                
                for admin in admins:
                    # Добавляем информацию о тенанте для отображения в шаблоне
                    admin.tenant_obj = tenant 
                    tenant_admins.append(admin)
        except Exception as e:
            print(f"Error fetching admins for tenant {tenant.schema_name}: {e}")

    # Поиск для администраторов платформы
    if search_query:
        platform_admins = platform_admins.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Для администраторов платформы оставим пагинацию
    page_obj, sort_by, per_page = get_paginated_data(request, platform_admins, 'username')
    
    context = {
        'page_obj': page_obj,
        'tenant_admins': tenant_admins,
        'sort_by': sort_by,
        'per_page': per_page,
        'search_query': search_query,
    }
    return render(request, 'customers/superuser_admins.html', context)

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_admin_edit(request, user_id):
    """Редактирование администратора платформы"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        tenant_id = request.POST.get('tenant')
        
        # Смена пароля, если заполнен
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)
            if user == request.user:
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
            messages.info(request, f'Пароль для пользователя {user.username} успешно обновлен.')
            
        # Защита: нельзя снять флаг суперпользователя с 'admin' через форму
        if user.username != 'admin':
            user.is_superuser = 'is_superuser' in request.POST
            user.is_staff = 'is_staff' in request.POST or user.is_superuser
            user.is_active = 'is_active' in request.POST
            
        try:
            user.save()
        except Exception as e:
            messages.error(request, f'Критическая ошибка при сохранении: {e}')
            return redirect('superuser_admin_edit', user_id=user.id)

        # Обновляем профиль
        profile, created = UserProfile.objects.get_or_create(user=user)
        if tenant_id:
            profile.tenant_id = tenant_id
        else:
            profile.tenant = None
        
        # Если это не персонал платформы, но привязан к тенанту, это ADMIN тенанта
        if not (user.is_staff or user.is_superuser) and tenant_id:
            profile.role = 'ADMIN'
        elif user.is_staff or user.is_superuser:
            profile.role = 'ADMIN'
        
        profile.can_delete_media = 'can_delete_media' in request.POST
        profile.save()

        # Синхронизация с тенантом
        if tenant_id:
            try:
                tenant = Client.objects.get(id=tenant_id)
                with tenant_context(tenant):
                    t_user, created = TenantUser.objects.get_or_create(username=user.username)
                    t_user.email = user.email
                    t_user.first_name = user.first_name
                    t_user.last_name = user.last_name
                    t_user.role = 'ADMIN'
                    t_user.password_hash = user.password # Синхронизируем хеш
                    t_user.is_active = user.is_active
                    t_user.save()
                messages.info(request, f'Данные синхронизированы с предприятием "{tenant.name}".')
            except Exception as e:
                messages.warning(request, f'Внимание: Данные сохранены локально, но не синхронизированы с предприятием: {e}')
        
        messages.success(request, f'Администратор {user.username} успешно обновлен.')
        return redirect('superuser_admins')
        
    return render(request, 'customers/superuser_admin_form.html', {
        'edit_user': user,
        'tenants': Client.objects.exclude(schema_name='public')
    })


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenant_admin_edit(request, tenant_id, user_id):
    """Редактирование администратора внутри тенанта"""
    tenant = get_object_or_404(Client, id=tenant_id)
    
    with tenant_context(tenant):
        user = get_object_or_404(TenantUser, id=user_id)
        
        if request.method == 'POST':
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.phone = request.POST.get('phone', '')
            user.role = request.POST.get('role', 'ADMIN')
            user.is_active = 'is_active' in request.POST
            
            new_password = request.POST.get('password')
            if new_password:
                user.password_hash = make_password(new_password)
                messages.info(request, f'Пароль для {user.username} успешно изменен.')
            
            # Явно сохраняем пользователя
            user.save()
            
            status_text = "активирован" if user.is_active else "деактивирован"
            messages.success(request, f'Администратор {user.username} (предприятие "{tenant.name}") успешно {status_text}.')
            return redirect('superuser_admins')
        
        # При GET запросе просто отображаем форму
        return render(request, 'customers/superuser_admin_form.html', {
            'edit_user': user,
            'is_tenant_user': True,
            'tenant': tenant
        })

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_tenant_admin_delete(request, tenant_id, user_id):
    """Удаление администратора внутри тенанта"""
    tenant = get_object_or_404(Client, id=tenant_id)
    
    with tenant_context(tenant):
        user = get_object_or_404(TenantUser, id=user_id)
        username = user.username
        
        if request.method == 'POST':
            user.delete()
            messages.success(request, f'Администратор {username} удален из предприятия "{tenant.name}".')
            return redirect('superuser_admins')
            
        return render(request, 'customers/superuser_admin_confirm_delete.html', {
            'object': user,
            'tenant': tenant
        })

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_admin_delete(request, user_id):
    """Удаление администратора"""
    user = get_object_or_404(User, id=user_id)
    if user.username == 'admin':
        messages.error(request, 'Нельзя удалить главного суперпользователя.')
        return redirect('superuser_admins')
        
    if request.method == 'POST':
        try:
            # Пробуем удалить из тенанта, если привязан
            if hasattr(user, 'profile') and user.profile.tenant:
                tenant = user.profile.tenant
                with tenant_context(tenant):
                    TenantUser.objects.filter(username=user.username).delete()
        except Exception as e:
            # Логируем или игнорируем ошибку, если не удалось удалить из тенанта
            print(f"Failed to delete tenant user: {e}")
            
        username = user.username
        user.delete()
        messages.success(request, f'Администратор {username} успешно удален.')
        return redirect('superuser_admins')
        
    return render(request, 'customers/superuser_admin_confirm_delete.html', {'object': user})


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_plans(request):
    """Список тарифных планов"""
    plans = SubscriptionPlan.objects.all().order_by('-created_at')
    return render(request, 'customers/superuser_plans.html', {'plans': plans})


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_plan_create(request):
    """Создание нового тарифного плана"""
    if request.method == 'POST':
        SubscriptionPlan.objects.create(
            name=request.POST.get('name'),
            price_month=request.POST.get('price_month'),
            price_year=request.POST.get('price_year'),
            max_users=request.POST.get('max_users'),
            storage_gb=request.POST.get('storage_gb'),
            work_days_limit=request.POST.get('work_days_limit'),
            has_mobile_app='has_mobile_app' in request.POST
        )
        messages.success(request, 'Тарифный план успешно создан.')
        return redirect('superuser_plans')
        
    return render(request, 'customers/superuser_plan_form.html', {'is_create': True})


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_plan_edit(request, plan_id):
    """Редактирование тарифного плана"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    if request.method == 'POST':
        plan.name = request.POST.get('name')
        plan.price_month = request.POST.get('price_month')
        plan.price_year = request.POST.get('price_year')
        plan.max_users = request.POST.get('max_users')
        plan.storage_gb = request.POST.get('storage_gb')
        plan.work_days_limit = request.POST.get('work_days_limit')
        plan.has_mobile_app = 'has_mobile_app' in request.POST
        plan.save()
        
        messages.success(request, f'Тариф "{plan.name}" успешно обновлен.')
        return redirect('superuser_plans')
        
    return render(request, 'customers/superuser_plan_form.html', {
        'plan': plan,
        'is_create': False
    })


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_plan_delete(request, plan_id):
    """Удаление тарифного плана"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    name = plan.name
    plan.delete()
    messages.success(request, f'Тариф "{name}" удален.')
    return redirect('superuser_plans')


@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_mail_settings(request):
    """Настройки почтового сервера"""
    settings = MailSettings.get_settings()
    
    if request.method == 'POST':
        settings.email_host = request.POST.get('email_host')
        settings.email_port = request.POST.get('email_port')
        settings.email_host_user = request.POST.get('email_host_user')
        settings.email_host_password = request.POST.get('email_host_password')
        settings.email_use_tls = 'email_use_tls' in request.POST
        settings.email_use_ssl = 'email_use_ssl' in request.POST
        settings.default_from_email = request.POST.get('default_from_email')
        settings.save()
        messages.success(request, 'Настройки почты успешно обновлены.')
        return redirect('superuser_mail_settings')
    
    return render(request, 'customers/superuser_mail_settings.html', {'settings': settings})


def get_captcha(request):
    """Генерация простой математической капчи"""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    request.session['captcha_result'] = num1 + num2
    return JsonResponse({'question': f"{num1} + {num2} = ?"})

@csrf_exempt
def contact_form_submit(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)
    
    # 1. Защита от спама: Honeypot
    if request.POST.get('website_url'):
        return JsonResponse({'success': True})
    
    # 2. Проверка капчи
    captcha_answer = request.POST.get('captcha_answer', '')
    expected_result = request.session.get('captcha_result')
    
    if not captcha_answer or str(captcha_answer) != str(expected_result):
        return JsonResponse({'success': False, 'error': 'Неверный ответ на проверочный вопрос'})
    
    # Очищаем капчу после проверки
    if 'captcha_result' in request.session:
        del request.session['captcha_result']

    # 3. Получение данных и базовая очистка
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    message = request.POST.get('message', '').strip()
    
    # 4. Валидация данных
    if not name or not email or not message:
        return JsonResponse({'success': False, 'error': 'Поля Имя, Email и Сообщение обязательны'})
    
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'success': False, 'error': 'Некорректный email адрес'})
    
    # 5. Ограничение длины
    name = name[:100]
    email = email[:100]
    phone = phone[:20]
    message = message[:2000]
    
    # 6. Rate Limiting
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    time_threshold = timezone.now() - timedelta(minutes=10)
    recent_messages_count = ContactMessage.objects.filter(ip_address=ip, created_at__gt=time_threshold).count()
    
    if recent_messages_count >= 5: # Увеличим лимит до 5
        return JsonResponse({'success': False, 'error': 'Слишком много сообщений. Пожалуйста, подождите.'})
    
    # 7. Создание записи в логе
    log_entry = ContactMessage.objects.create(
        name=name,
        email=email,
        phone=phone,
        message=message,
        ip_address=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # 8. Отправка почты
    try:
        mail_settings = MailSettings.get_settings()
        if mail_settings and mail_settings.email_host:
            connection = get_connection(
                host=mail_settings.email_host,
                port=mail_settings.email_port,
                username=mail_settings.email_host_user,
                password=mail_settings.email_host_password,
                use_tls=mail_settings.email_use_tls,
                use_ssl=mail_settings.email_use_ssl,
                timeout=10
            )
            
            subject = f"Новое сообщение от {name} (Q-TRACE)"
            body = f"Имя: {name}\nEmail: {email}\nТелефон: {phone}\n\nСообщение:\n{message}\n\n---\nIP: {ip}\nДата: {timezone.now()}"
            
            send_mail(
                subject,
                body,
                mail_settings.default_from_email,
                [mail_settings.default_from_email],
                connection=connection,
                fail_silently=False
            )
            
            log_entry.is_sent = True
            log_entry.save()
            return JsonResponse({'success': True})
        else:
            log_entry.error_log = "Настройки почты не сконфигурированы"
            log_entry.save()
            return JsonResponse({'success': False, 'error': 'Служба отправки временно недоступна'})
            
    except Exception as e:
        log_entry.error_log = str(e)
        log_entry.save()
        return JsonResponse({'success': False, 'error': 'Ошибка при отправке сообщения'})

@user_passes_test(lambda u: u.is_superuser)
def superuser_mail_logs(request):
    messages = ContactMessage.objects.all().order_by('-created_at')
    paginator = Paginator(messages, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'customers/superuser_mail_logs.html', {'page_obj': page_obj})

@user_passes_test(lambda u: u.is_superuser)
def superuser_mail_log_delete(request, message_id):
    if request.method == 'POST':
        message = get_object_or_404(ContactMessage, id=message_id)
        message.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)

@user_passes_test(lambda u: u.is_superuser)
def superuser_mail_log_edit(request, message_id):
    message_obj = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        message_obj.name = request.POST.get('name', '').strip()[:100]
        message_obj.email = request.POST.get('email', '').strip()[:100]
        message_obj.phone = request.POST.get('phone', '').strip()[:20]
        message_obj.message = request.POST.get('message', '').strip()[:2000]
        message_obj.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_ai_settings(request):
    """Настройки AI ассистента"""
    from ai_app.models import AISettings, AIModelConfig
    settings = AISettings.get_settings()
    
    if request.method == 'POST':
        # Обновляем только те поля, которые пришли в запросе
        active_model = request.POST.get('active_model')
        if active_model:
            settings.active_model = active_model
            
            # Сохраняем настройки именно для ЭТОЙ модели в таблицу AIModelConfig
            if active_model != 'mock':
                api_key = request.POST.get('provider_api_key')
                api_url = request.POST.get('api_base_url')
                
                config, created = AIModelConfig.objects.get_or_create(model_code=active_model)
                config.api_key = api_key
                config.api_url = api_url
                config.save()
            
        settings.is_enabled = request.POST.get('is_enabled') == 'on'
        
        if 'temperature' in request.POST:
            try:
                temp_val = request.POST.get('temperature', '').strip()
                settings.temperature = float(temp_val) if temp_val else 0.7
            except (ValueError, TypeError):
                settings.temperature = 0.7
            
        if 'max_tokens' in request.POST:
            try:
                tokens_val = request.POST.get('max_tokens', '').strip()
                settings.max_tokens = int(tokens_val) if tokens_val else 1000
            except (ValueError, TypeError):
                settings.max_tokens = 1000
            
        settings.save()
        messages.success(request, 'Настройки AI успешно сохранены.')
        return redirect('superuser_ai_settings')
    
    # Получаем все сохраненные конфигурации для передачи в JS
    model_configs = {c.model_code: {'key': c.api_key, 'url': c.api_url} for c in AIModelConfig.objects.all()}
        
    context = {
        'settings': settings,
        'model_choices': AISettings.MODEL_CHOICES,
        'model_configs': model_configs,
    }
    return render(request, 'customers/superuser_ai_settings.html', context)


def landing_page(request):
    """Отображение главной страницы (только для публичной схемы)"""
    # Безопасно проверяем наличие тенанта
    tenant = getattr(request, 'tenant', None)
    
    # Если мы в тенанте и это не публичная схема - мы не должны быть здесь, 
    # но на всякий случай перенаправим в дашборд
    if tenant and tenant.schema_name != 'public':
        return redirect('dashboard:home')
    
    # Получаем базовый домен из текущего запроса
    host = request.get_host().split(':')[0]
    if host == '127.0.0.1' or host == 'localhost':
        base_domain = 'localhost'
    elif '.nip.io' in host:
        # Для отладки через nip.io
        base_domain = host
    else:
        # В проде, например qtrace.ru
        base_domain = host

    # Логика для формы входа (редирект по параметру)
    login_subdomain = request.GET.get('login_subdomain')
    
    if login_subdomain:
        subdomain = login_subdomain.strip().lower()
        if subdomain:
            port = request.get_port()
            port_str = f":{port}" if port not in (80, 443) else ""
            target_url = f"http://{subdomain}.{base_domain}{port_str}/"
            return redirect(target_url)
            
    # Получаем тарифы для формы регистрации
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_month')
            
    return render(request, 'customers/index.html', {
        'plans': plans,
        'base_domain': base_domain
    })

@method_decorator(csrf_exempt, name='dispatch')
class TenantRegistrationViewSet(viewsets.ViewSet):
    """
    ViewSet для регистрации новых предприятий.
    Доступен публично (в shared schema).
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Отключаем аутентификацию для избежания CSRF проверок SessionAuth
    serializer_class = TenantRegistrationSerializer
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = TenantRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                with transaction.atomic():
                    # 1. Создаем клиента (тенанта)
                    client = Client.objects.create(
                        name=data['company_name'],
                        schema_name=data['subdomain'],
                        phone=data['phone'],
                        telegram=data.get('telegram', ''),
                        email=data.get('email', ''),
                        contact_person=data.get('contact_person', ''),
                        subscription_plan_id=data['subscription_plan']
                    )
                    
                    # 2. Создаем домен
                    host = request.get_host().split(':')[0]
                    if host == '127.0.0.1' or host == 'localhost':
                        base_domain = 'localhost'
                    else:
                        # Если мы на qtrace.ru, то base_domain будет qtrace.ru
                        # Если мы на 192.168.1.220.nip.io, то base_domain будет 192.168.1.220.nip.io
                        base_domain = host

                    domain = Domain.objects.create(
                        domain=f"{data['subdomain']}.{base_domain}",
                        tenant=client,
                        is_primary=True
                    )
                    
                    # 3. Создаем администратора внутри схемы тенанта
                    with tenant_context(client):
                        admin_user = TenantUser.objects.create(
                            username=data['admin_username'],
                            email=data['admin_email'],
                            first_name=data.get('admin_first_name', ''),
                            last_name=data.get('admin_last_name', ''),
                            role='ADMIN',
                            is_active=True
                        )
                        admin_user.set_password(data['admin_password'])
                        admin_user.save()
                        
                    # Определяем протокол и порт для ссылки
                    protocol = 'https' if request.is_secure() else 'http'
                    port = request.get_port()
                    
                    # Не добавляем порт, если это стандартный порт для протокола
                    if (protocol == 'https' and port == 443) or (protocol == 'http' and port == 80):
                        port_str = ""
                    else:
                        port_str = f":{port}"
                    
                    return Response({
                        'message': 'Заявка на регистрацию принята. Организация будет активирована после проверки администратором.',
                        'tenant_url': f"{protocol}://{domain.domain}{port_str}/"
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_db_management(request):
    """Страница управления базой данных"""
    print(f"DEBUG: superuser_db_management called, method={request.method}")
    with connection.cursor() as cursor:
        # Размер базы данных
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cursor.fetchone()[0]
        
        # Список всех схем в PostgreSQL
        cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'")
        db_schemas = [row[0] for row in cursor.fetchall()]
        
        # Список схем, зарегистрированных в Django
        registered_schemas = set(Client.objects.values_list('schema_name', flat=True))
        
        # "Мертвые" схемы (есть в PG, но нет в Django)
        dead_schemas = [s for s in db_schemas if s not in registered_schemas and s != 'public']
        
        # Статистика по таблицам
        cursor.execute("""
            SELECT relname, n_live_tup 
            FROM pg_stat_user_tables 
            ORDER BY n_live_tup DESC 
            LIMIT 10
        """)
        top_tables = cursor.fetchall()

    # Список бэкапов
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith('.sql'):
                path = os.path.join(backup_dir, f)
                backups.append({
                    'name': f,
                    'size': f"{os.path.getsize(path) / 1024 / 1024:.2f} MB",
                    'date': datetime.fromtimestamp(os.path.getmtime(path))
                })
    backups.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'customers/superuser_db_management.html', {
        'db_size': db_size,
        'dead_schemas': dead_schemas,
        'top_tables': top_tables,
        'backups': backups
    })

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_db_cleanup_tenants(request):
    """Очистка "мертвых" схем"""
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'")
            db_schemas = [row[0] for row in cursor.fetchall()]
            registered_schemas = set(Client.objects.values_list('schema_name', flat=True))
            dead_schemas = [s for s in db_schemas if s not in registered_schemas and s != 'public']
            
            count = 0
            for schema in dead_schemas:
                cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
                count += 1
            
            messages.success(request, f'Успешно удалено "мертвых" схем: {count}')
    return redirect('superuser_db_management')

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_db_vacuum(request):
    """Выполнение VACUUM ANALYZE"""
    if request.method == 'POST':
        # VACUUM нельзя выполнять внутри транзакции
        with connection.cursor() as cursor:
            # PostgreSQL требует, чтобы VACUUM запускался вне транзакционных блоков
            cursor.execute("COMMIT") 
            cursor.execute("VACUUM ANALYZE")
        messages.success(request, 'Оптимизация базы данных (VACUUM ANALYZE) успешно завершена.')
    return redirect('superuser_db_management')

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_db_backup(request):
    """Создание бэкапа"""
    if request.method == 'POST':
        import shutil
        print("DEBUG: superuser_db_backup POST received")
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        filepath = os.path.join(backup_dir, filename)
        
        db_settings = settings.DATABASES['default']
        os.environ['PGPASSWORD'] = db_settings['PASSWORD']
        
        # Попытка найти pg_dump
        pg_dump_path = shutil.which('pg_dump')
        if not pg_dump_path and os.name == 'nt':
            possible_paths = [
                r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\15\bin\pg_dump.exe',
                r'C:\Program Files\PostgreSQL\14\bin\pg_dump.exe',
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    pg_dump_path = p
                    break
        
        if not pg_dump_path:
            msg = "Утилита pg_dump не найдена в системе. Пожалуйста, установите PostgreSQL или добавьте путь к bin в PATH."
            print(f"DEBUG: {msg}")
            messages.error(request, msg)
            return redirect('superuser_db_management')

        cmd = [
            pg_dump_path,
            '-h', db_settings.get('HOST', 'localhost') or 'localhost',
            '-U', db_settings['USER'],
            '-p', str(db_settings.get('PORT', 5432) or 5432),
            '-f', filepath,
            db_settings['NAME']
        ]
        
        print(f"DEBUG: Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"DEBUG: pg_dump success: {result.stdout}")
            messages.success(request, f'Резервная копия {filename} успешно создана.')
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            print(f"DEBUG: pg_dump failed: {error_msg}")
            messages.error(request, f'Ошибка pg_dump: {error_msg}')
        except Exception as e:
            print(f"DEBUG: backup error: {e}")
            messages.error(request, f'Ошибка при создании бэкапа: {e}')
            
    return redirect('superuser_db_management')

@user_passes_test(superuser_required, login_url='/admin/login/')
def superuser_db_restore(request, filename):
    """Восстановление из бэкапа"""
    if request.method == 'POST':
        import shutil
        print(f"DEBUG: superuser_db_restore POST received for {filename}")
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            messages.error(request, 'Файл бэкапа не найден.')
            return redirect('superuser_db_management')
            
        db_settings = settings.DATABASES['default']
        os.environ['PGPASSWORD'] = db_settings['PASSWORD']
        
        # Попытка найти psql
        psql_path = shutil.which('psql')
        if not psql_path and os.name == 'nt':
            possible_paths = [
                r'C:\Program Files\PostgreSQL\17\bin\psql.exe',
                r'C:\Program Files\PostgreSQL\16\bin\psql.exe',
                r'C:\Program Files\PostgreSQL\15\bin\psql.exe',
                r'C:\Program Files\PostgreSQL\14\bin\psql.exe',
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    psql_path = p
                    break
        
        if not psql_path:
            msg = "Утилита psql не найдена в системе. Пожалуйста, установите PostgreSQL или добавьте путь к bin в PATH."
            print(f"DEBUG: {msg}")
            messages.error(request, msg)
            return redirect('superuser_db_management')

        # Для восстановления psql
        cmd = [
            psql_path,
            '-h', db_settings.get('HOST', 'localhost') or 'localhost',
            '-U', db_settings['USER'],
            '-p', str(db_settings.get('PORT', 5432) or 5432),
            '-d', db_settings['NAME'],
            '-f', filepath
        ]
        
        print(f"DEBUG: Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"DEBUG: psql success: {result.stdout}")
            messages.success(request, f'База данных успешно восстановлена из {filename}.')
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            print(f"DEBUG: psql failed: {error_msg}")
            messages.error(request, f'Ошибка psql: {error_msg}')
        except Exception as e:
            print(f"DEBUG: restore error: {e}")
            messages.error(request, f'Ошибка при восстановлении: {e}')
            
    return redirect('superuser_db_management')

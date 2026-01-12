from django import template

register = template.Library()

@register.filter(name='dict_item')
def dict_item(dictionary, key):
    """
    Позволяет получать значение из словаря по ключу в шаблоне.
    Использование: {{ my_dict|dict_item:my_key }}
    """
    return dictionary.get(key)

@register.filter
def filter_stages(task, user):
    """
    Возвращает этапы задачи в зависимости от роли пользователя.
    Если пользователь - админ или ответственный за задачу, возвращает все этапы.
    Иначе возвращает только этапы, назначенные пользователю.
    """
    if (hasattr(user, 'role') and user.role == 'ADMIN') or \
       getattr(user, 'is_superuser', False):
        return task.stages.all()
    
    return task.stages.filter(assigned_executor=user)

@register.filter(name='get_attr')
def get_attr(obj, attr_name):
    """
    Позволяет получать значение атрибута объекта по имени в шаблоне.
    Использование: {{ my_obj|get_attr:attr_name }}
    """
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None

from django import template

register = template.Library()


@register.filter
def user_stages_count(task, user_id):
    """
    Подсчитывает количество этапов задачи, назначенных на конкретного пользователя.
    Если user_id None, возвращает общее количество этапов.
    """
    if not user_id:
        return task.stages.count()
    
    return task.stages.filter(assigned_to_id=user_id).count()


@register.filter
def user_stages(task, user_id):
    """
    Возвращает этапы задачи, назначенные на конкретного пользователя.
    Если user_id None, возвращает все этапы.
    """
    if not user_id:
        return task.stages.all()
    
    return task.stages.filter(assigned_to_id=user_id)

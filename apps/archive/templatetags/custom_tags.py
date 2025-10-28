from django import template

register = template.Library()


@register.filter
def get_category_badge_color(category_slug):
    """
    Get badge color based on category slug
    
    Usage: {{ document.category.slug|get_category_badge_color }}
    """
    if category_slug == 'spd':
        return 'warning'
    return 'success'


@register.filter
def get_activity_color(action_type):
    """
    Get color based on activity type
    
    Usage: {{ activity.action_type|get_activity_color }}
    """
    colors = {
        'create': 'success',
        'delete': 'danger',
        'download': 'warning',
        'view': 'info',
        'update': 'info',
    }
    return colors.get(action_type, 'info')


@register.filter
def get_activity_icon(action_type):
    """
    Get FontAwesome icon based on activity type
    
    Usage: {{ activity.action_type|get_activity_icon }}
    """
    icons = {
        'create': 'fa-plus',
        'delete': 'fa-trash',
        'download': 'fa-download',
        'view': 'fa-eye',
        'update': 'fa-pen',
    }
    return icons.get(action_type, 'fa-circle-info')


@register.filter
def split(value, delimiter='/'):
    """
    Split string by delimiter
    
    Usage: {{ document.file.name|split:'/'|last }}
    """
    if value:
        return value.split(delimiter)
    return []


@register.simple_tag
def get_badge_class(category_slug, badge_type='pill'):
    """
    Get full badge class string
    
    Usage: {% get_badge_class document.category.slug 'pill' %}
    """
    color = 'warning' if category_slug == 'spd' else 'success'
    
    if badge_type == 'pill':
        return f'badge badge-pill badge-{color}'
    elif badge_type == 'dot':
        return f'badge badge-dot bg-{color}'
    else:
        return f'badge badge-{color}'


@register.simple_tag
def get_icon_class(category_slug):
    """
    Get icon shape class with color
    
    Usage: {% get_icon_class document.category.slug %}
    """
    color = 'warning' if category_slug == 'spd' else 'success'
    return f'icon icon-shape bg-{color} text-white rounded-circle shadow'
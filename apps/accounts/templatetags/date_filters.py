from django import template
from django.utils import timezone
import locale

register = template.Library()

# Try to set Indonesian locale
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')  # Windows
    except:
        pass  # Fallback to default if Indonesian locale not available

# Indonesian month names (fallback if locale not available)
INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

INDONESIAN_MONTHS_SHORT = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'Mei', 6: 'Jun', 7: 'Jul', 8: 'Agu',
    9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'
}

INDONESIAN_DAYS = {
    0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis',
    4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'
}


@register.filter
def indo_date(value, format_string='long'):
    """
    Format date to Indonesian format
    
    Usage:
        {{ document.document_date|indo_date }}  -> 15 Januari 2024
        {{ document.document_date|indo_date:'short' }}  -> 15/01/2024
        {{ document.created_at|indo_date:'datetime' }}  -> 15 Jan 2024 14:30
        {{ document.document_date|indo_date:'full' }}  -> Senin, 15 Januari 2024
    """
    if not value:
        return ''
    
    # Ensure timezone aware
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    
    if format_string == 'long':
        # Format: 15 Januari 2024
        month_name = INDONESIAN_MONTHS.get(value.month, value.strftime('%B'))
        return f"{value.day} {month_name} {value.year}"
    
    elif format_string == 'short':
        # Format: 15/01/2024
        return value.strftime('%d/%m/%Y')
    
    elif format_string == 'medium':
        # Format: 15 Jan 2024
        month_name = INDONESIAN_MONTHS_SHORT.get(value.month, value.strftime('%b'))
        return f"{value.day} {month_name} {value.year}"
    
    elif format_string == 'datetime':
        # Format: 15 Jan 2024 14:30
        month_name = INDONESIAN_MONTHS_SHORT.get(value.month, value.strftime('%b'))
        return f"{value.day} {month_name} {value.year} {value.strftime('%H:%M')}"
    
    elif format_string == 'full':
        # Format: Senin, 15 Januari 2024
        day_name = INDONESIAN_DAYS.get(value.weekday(), value.strftime('%A'))
        month_name = INDONESIAN_MONTHS.get(value.month, value.strftime('%B'))
        return f"{day_name}, {value.day} {month_name} {value.year}"
    
    elif format_string == 'time':
        # Format: 14:30
        return value.strftime('%H:%M')
    
    else:
        # Default to long format
        month_name = INDONESIAN_MONTHS.get(value.month, value.strftime('%B'))
        return f"{value.day} {month_name} {value.year}"


@register.filter
def time_since(value):
    """
    Human readable time difference
    
    Usage:
        {{ document.created_at|time_since }}  -> 2 jam yang lalu
    """
    if not value:
        return ''
    
    now = timezone.now()
    
    # Ensure timezone aware
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    
    diff = now - value
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'Baru saja'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} menit yang lalu'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} jam yang lalu'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} hari yang lalu'
    elif seconds < 2592000:  # ~30 days
        weeks = int(seconds / 604800)
        return f'{weeks} minggu yang lalu'
    elif seconds < 31536000:  # ~365 days
        months = int(seconds / 2592000)
        return f'{months} bulan yang lalu'
    else:
        years = int(seconds / 31536000)
        return f'{years} tahun yang lalu'


@register.filter
def file_size(value):
    """
    Format file size to human readable format
    
    Usage:
        {{ document.file_size|file_size }}  -> 1.5 MB
    """
    if not value:
        return '0 B'
    
    size = float(value)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    
    return f"{size:.2f} PB"


@register.filter
def duration_days(start_date, end_date):
    """
    Calculate duration between two dates in days
    
    Usage:
        {{ spd.start_date|duration_days:spd.end_date }}  -> 3 hari
    """
    if not start_date or not end_date:
        return ''
    
    days = (end_date - start_date).days + 1
    return f'{days} hari'


@register.filter
def month_year(value):
    """
    Format date to month and year only
    
    Usage:
        {{ document.document_date|month_year }}  -> Januari 2024
    """
    if not value:
        return ''
    
    month_name = INDONESIAN_MONTHS.get(value.month, value.strftime('%B'))
    return f"{month_name} {value.year}"


@register.filter
def truncate_chars(value, length):
    """
    Truncate string to specified length with ellipsis
    
    Usage:
        {{ document.title|truncate_chars:50 }}
    """
    if not value:
        return ''
    
    if len(value) <= length:
        return value
    
    return f"{value[:length]}..."


@register.simple_tag
def query_transform(request, **kwargs):
    """
    Transform query parameters for pagination with filters
    
    Usage:
        <a href="?{% query_transform page=page_obj.next_page_number %}">Next</a>
    """
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        else:
            updated.pop(key, None)
    
    return updated.urlencode()
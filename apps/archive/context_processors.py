from .models import DocumentCategory, Employee


def global_context(request):
    """
    Add global context data to all templates
    """
    context = {
        'categories': DocumentCategory.objects.filter(
            parent__isnull=True
        ).prefetch_related('children', 'documents'),
        'employees': Employee.objects.filter(is_active=True).order_by('name'),
    }
    
    return context
"""
Context processors untuk data global yang dibutuhkan di semua template
"""

from .models import DocumentCategory, Document, Employee


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

def sidebar_context(request):
    """
    Provide sidebar data untuk semua template
    
    Returns:
        dict: Context data dengan categories dan counts
    """
    # Get parent categories (categories tanpa parent)
    categories = DocumentCategory.objects.filter(
        parent__isnull=True
    ).prefetch_related(
        'children',  # Prefetch subcategories
        'documents'  # Prefetch documents untuk count
    ).order_by('name')
    
    # Total documents count (exclude soft deleted)
    total_documents = Document.objects.filter(is_deleted=False).count()
    
    return {
        'categories': categories,
        'total_documents': total_documents,
    }
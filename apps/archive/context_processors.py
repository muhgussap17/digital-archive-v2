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
    Menyediakan data kategori untuk sidebar dengan optimasi query
    
    Fungsi ini mengoptimalkan query database dengan menggunakan annotate
    untuk menghitung jumlah dokumen di level database, menghindari
    multiple queries saat template di-render.
    
    Args:
        request: HttpRequest object dari Django
    
    Returns:
        dict: Dictionary berisi:
            - categories: QuerySet kategori dengan annotasi total_docs
            - total_documents: Total semua dokumen aktif
    
    Optimasi:
        - Menggunakan annotate untuk pre-calculate counts
        - Mengurangi query dari N+1 menjadi 1 query
        - Prefetch children untuk menghindari additional queries
    
    Contoh Return:
        {
            'categories': <QuerySet [<DocumentCategory: SPD>, ...]>,
            'total_documents': 150
        }
    
    Implementasi Standar:
        Mengikuti best practice Django untuk optimasi query database
        sesuai dokumentasi Django ORM Performance

    Cara Penggunaan di Template:
        - Parent Categories:
            {% for category in categories %}
                {{ category.name }} - {{ category.parent_docs|add:category.children_docs }}
            {% endfor %}
        - Total Dokumen:
            {{ total_documents }}
        - Child Categories:
            {% for category in categories %}
                {% for child in category.children.all %}
                    {{ child.name }} - {{ child.children_docs }}
                {% endfor %}
            {% endfor %}
    """
    from django.db.models import Prefetch, Q, Count
    
    # Query parent categories dengan annotasi jumlah dokumen
    # Annotate akan menghitung di database, bukan di Python
    # Annotate untuk setiap kategori anak (child)
    children_qs = DocumentCategory.objects.annotate(
        children_docs=Count(
            'documents',
            filter=Q(documents__is_deleted=False),
            distinct=True
        )
    ).order_by('name')

    # Annotate untuk parent + gabungan dokumen anak
    categories = DocumentCategory.objects.filter(
        parent__isnull=True
    ).prefetch_related(
        Prefetch('children', queryset=children_qs)
        # 'children'  # Prefetch children untuk menghindari query tambahan
    ).annotate(
        # Hitung dokumen dari kategori ini
        parent_docs=Count(
            'documents',
            filter=Q(documents__is_deleted=False),
            distinct=True
        ),
        # Hitung dokumen dari semua kategori anak
        children_docs=Count(
            'children__documents',
            filter=Q(children__documents__is_deleted=False),
            distinct=True
        )
    ).order_by('name')
    
    # Hitung total dokumen aktif di sistem
    total_documents = Document.objects.filter(is_deleted=False).count()
    
    return {
        'categories': categories,
        'total_documents': total_documents,
    }
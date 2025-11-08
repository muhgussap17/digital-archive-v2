<!-- Jalankan di Django Shell -->
from apps.archive.models import DocumentCategory, Document

# Test 1: Manual count vs method
category = DocumentCategory.objects.get(slug='belanjaan')

# Hitung manual
manual_count = Document.objects.filter(
    category=category,
    is_deleted=False
).count()

# Hitung dengan method baru
method_count = category.get_total_documents()

print(f"Manual count: {manual_count}")
print(f"Method count: {method_count}")
print(f"Match: {manual_count == method_count}")

# Test 2: Cek annotated values dari context processor
from apps.archive.context_processors import sidebar_context
from django.test import RequestFactory

request = RequestFactory().get('/')
context = sidebar_context(request)

for cat in context['categories']:
    print(f"\nKategori: {cat.name}")
    print(f"  Parent docs: {cat.parent_docs}")
    print(f"  Children docs: {cat.children_docs}")
    print(f"  Total (method): {cat.get_total_documents()}")
    print(f"  Total (annotate): {cat.parent_docs + cat.children_docs}")
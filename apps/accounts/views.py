from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from apps.archive.models import Document, DocumentActivity
from .forms import ProfileEditForm


@login_required
def profile(request):
    """User profile view"""
    user = request.user
    
    # Get user statistics
    total_uploads = Document.objects.filter(
        created_by=user,
        is_deleted=False
    ).count()
    
    total_activities = DocumentActivity.objects.filter(
        user=user
    ).count()
    
    # Recent uploads
    recent_uploads = Document.objects.filter(
        created_by=user,
        is_deleted=False
    ).select_related('category').order_by('-created_at')[:5]
    
    # Recent activities
    recent_activities = DocumentActivity.objects.filter(
        user=user
    ).select_related('document').order_by('-created_at')[:10]
    
    # Monthly upload stats
    from django.db.models.functions import TruncMonth
    from datetime import datetime, timedelta
    
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_uploads = Document.objects.filter(
        created_by=user,
        created_at__gte=six_months_ago,
        is_deleted=False
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'total_uploads': total_uploads,
        'total_activities': total_activities,
        'recent_uploads': recent_uploads,
        'recent_activities': recent_activities,
        'monthly_uploads': monthly_uploads,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Mengedit profil pengguna menggunakan ModelForm yang aman."""
    user = request.user
    
    if request.method == 'POST':
        # Isi form dengan data POST, dan jadikan 'instance' sebagai user saat ini
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Terjadi kesalahan. Mohon periksa data Anda.')
    else:
        # Untuk method GET, tampilkan form yang sudah terisi data user saat ini
        form = ProfileEditForm(instance=request.user)     

    context = {
        'form': form
    }
    # Render ke template yang berisi form Anda
    return render(request, 'accounts/profile_edit.html', context)
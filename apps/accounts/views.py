from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from apps.archive.models import Document, DocumentActivity


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
    """Edit user profile"""
    if request.method == 'POST':
        user = request.user
        
        # Update basic info
        user.full_name = request.POST.get('full_name', user.full_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        
        try:
            user.save()
            messages.success(request, 'Profil berhasil diperbarui!')
            return redirect('accounts:profile')
        except Exception as e:
            messages.error(request, f'Gagal memperbarui profil: {str(e)}')
    
    return render(request, 'accounts/profile_edit.html')
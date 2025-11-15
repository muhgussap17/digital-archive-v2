from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def is_staff_user(user):
    """
    Memeriksa apakah user adalah superuser ATAU anggota grup 'Staff'.
    """
    if user.is_authenticated:
        return user.is_superuser or user.groups.filter(name='Staff').exists()
    return False


def staff_required(function=None, redirect_url='/accounts/login/'):
    """
    Decorator untuk views yang hanya memperbolehkan Superuser atau 'Staff'.
    Jika tidak, akan memunculkan 'Permission Denied' (403 Forbidden).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Anda harus login terlebih dahulu.')
                return redirect(redirect_url)
            
            if not request.user.is_staff:
                messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
                return redirect('archive:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    
    if function:
        return decorator(function)

    return decorator
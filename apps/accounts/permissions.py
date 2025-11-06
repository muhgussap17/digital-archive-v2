from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStaffOrReadOnly(BasePermission):
    """
    Izin kustom:
    - Memperbolehkan akses 'read-only' (GET, HEAD, OPTIONS) untuk SEMUA user yang terautentikasi.
    - Hanya memperbolehkan akses 'write' (POST, PUT, PATCH, DELETE) untuk user di grup 'Staff' atau Superuser.
    """

    def has_permission(self, request, view): # type: ignore
        # Jika user tidak login, tolak semua
        if not request.user or not request.user.is_authenticated:
            return False

        # Jika method-nya 'aman' (GET, etc.), izinkan (ini untuk "Regular User")
        if request.method in SAFE_METHODS:
            return True

        # Jika method-nya 'tidak aman' (POST, PUT, DELETE),
        # periksa apakah dia 'Staff' atau 'Superuser'.
        return request.user.is_superuser or request.user.groups.filter(name='Staff').exists()
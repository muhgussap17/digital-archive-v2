"""
Modul: services/user_service.py
Fungsi: Business logic untuk User management operations

Berisi pure business logic untuk:
    - Create user (with password)
    - Update user (profile & permissions)
    - Delete user (soft delete via is_active)
    - Activate/Deactivate user
    - Change password
    - Assign groups/permissions

Implementasi Standar:
    - Separation of concerns: business logic terpisah dari HTTP handling
    - Transaction management di service layer
    - Pure functions yang mudah di-test
    - No HTTP dependencies (request, messages, redirect)
    - Consistent dengan DocumentService pattern

Catatan Pemeliharaan:
    - Service functions harus pure (no side effects di HTTP layer)
    - Password handling menggunakan Django's make_password
    - Activity logging opsional (bisa ditambahkan)
    - User permissions handled via Django Groups
    
Cara Penggunaan:
    from apps.accounts.services import UserService
    
    # Create
    user = UserService.create_user(
        username='johndoe',
        password='securepass123',
        full_name='John Doe',
        email='john@example.com',
        is_staff=False
    )
    
    # Update
    updated_user = UserService.update_user(
        user=user,
        form_data={'full_name': 'John Doe Updated', ...}
    )
    
    # Activate/Deactivate
    UserService.toggle_active_status(user, is_active=False)
"""

from typing import Dict, Any, Optional, List
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.utils import timezone

from ..models import User


class UserService:
    """
    Service class untuk User management business logic
    
    Menyediakan static methods untuk:
        - create_user: Create user baru dengan password
        - update_user: Update user profile & permissions
        - delete_user: Soft delete (set is_active=False)
        - toggle_active_status: Activate/Deactivate user
        - change_password: Update user password
        - assign_groups: Assign user ke groups
        - get_users_list: Query users dengan filters
    
    Semua methods menggunakan transaction.atomic untuk data integrity
    dan automatic rollback jika terjadi error.
    """
    
    @staticmethod
    def create_user(
        username: str,
        password: str,
        full_name: str = '',
        email: str = '',
        phone: str = '',
        is_staff: bool = False,
        is_superuser: bool = False,
        groups: Optional[List[str]] = None,
        created_by: Optional[User] = None
    ) -> User:
        """
        Create user baru dengan password
        
        Flow:
            1. Validate username uniqueness (handled by model)
            2. Hash password dengan Django's make_password
            3. Create User object
            4. Assign groups jika ada
            5. Optional: Log activity
        
        Args:
            username: Username untuk login (required, unique)
            password: Plain text password (akan di-hash)
            full_name: Nama lengkap user
            email: Email address
            phone: Nomor telepon
            is_staff: Staff status (can access admin)
            is_superuser: Superuser status (full permissions)
            groups: List of group names untuk assign
            created_by: User yang membuat (untuk audit)
            
        Returns:
            User: Created user instance
            
        Raises:
            Exception: Jika username sudah ada atau validation error
            
        Examples:
            >>> user = UserService.create_user(
            ...     username='johndoe',
            ...     password='securepass123',
            ...     full_name='John Doe',
            ...     email='john@example.com',
            ...     is_staff=True,
            ...     groups=['Staff']
            ... )
        
        Implementasi Standar:
            - Password di-hash sebelum disimpan
            - Transaction atomic untuk rollback safety
            - Group assignment via Django Groups
        """
        with transaction.atomic():
            # Create user dengan hashed password
            user = User.objects.create(
                username=username,
                password=make_password(password),  # Hash password
                full_name=full_name,
                email=email,
                phone=phone,
                is_staff=is_staff,
                is_superuser=is_superuser,
                is_active=True  # Active by default
            )
            
            # Assign groups jika ada
            if groups:
                for group_name in groups:
                    try:
                        group = Group.objects.get(name=group_name)
                        user.groups.add(group)
                    except Group.DoesNotExist:
                        pass  # Skip jika group tidak ada
            
            # Future: Log activity
            # log_user_activity(user, created_by, 'create')
            
            return user
    
    @staticmethod
    def update_user(
        user: User,
        form_data: Dict[str, Any],
        updated_by: Optional[User] = None
    ) -> User:
        """
        Update user profile dan permissions
        
        Flow:
            1. Update basic profile (full_name, email, phone)
            2. Update permissions (is_staff, is_superuser)
            3. Update groups assignment
            4. Save changes
            5. Optional: Log activity
        
        Args:
            user: User instance yang akan diupdate
            form_data: Cleaned data dari form
                Expected keys: full_name, email, phone, is_staff, 
                               is_superuser, groups
            updated_by: User yang melakukan update (untuk audit)
            
        Returns:
            User: Updated user instance
            
        Raises:
            Exception: Jika update gagal
            
        Examples:
            >>> updated_user = UserService.update_user(
            ...     user=user,
            ...     form_data={
            ...         'full_name': 'John Doe Updated',
            ...         'email': 'newemail@example.com',
            ...         'is_staff': True,
            ...         'groups': ['Staff']
            ...     }
            ... )
        
        Implementasi Standar:
            - Tidak update password di sini (gunakan change_password)
            - Groups di-sync (clear existing, add new)
            - Transaction atomic
        
        Catatan:
            - Password tidak bisa diubah via update_user
            - Gunakan change_password untuk ubah password
            - Username tidak bisa diubah (identifier)
        """
        with transaction.atomic():
            # Update basic profile
            user.full_name = form_data.get('full_name', user.full_name)
            user.email = form_data.get('email', user.email)
            user.phone = form_data.get('phone', user.phone)
            
            # Update permissions (hanya superuser yang bisa ubah ini)
            if 'is_staff' in form_data:
                user.is_staff = form_data['is_staff']
            
            if 'is_superuser' in form_data:
                user.is_superuser = form_data['is_superuser']
            
            user.save()
            
            # Update groups jika ada
            if 'groups' in form_data:
                groups = form_data['groups']
                # Clear existing groups
                user.groups.clear()
                # Add new groups
                if groups:
                    for group_name in groups:
                        try:
                            group = Group.objects.get(name=group_name)
                            user.groups.add(group)
                        except Group.DoesNotExist:
                            pass
            
            # Future: Log activity
            # log_user_activity(user, updated_by, 'update')
            
            return user
    
    @staticmethod
    def delete_user(
        user: User,
        deleted_by: Optional[User] = None
    ) -> User:
        """
        Soft delete user (set is_active=False)
        
        Menandai user sebagai tidak aktif tanpa menghapus dari database.
        Data documents dan activities terkait tetap tersimpan.
        
        Args:
            user: User instance yang akan dihapus
            deleted_by: User yang melakukan delete (untuk audit)
            
        Returns:
            User: Deleted user instance
            
        Raises:
            Exception: Jika delete gagal
            
        Examples:
            >>> UserService.delete_user(
            ...     user=user,
            ...     deleted_by=request.user
            ... )
        
        Implementasi Standar:
            - Soft delete dengan set is_active=False
            - Data relasi tetap tersimpan (documents, activities)
            - Bisa di-restore dengan toggle_active_status
        
        Catatan:
            - Tidak menghapus dari database (compliance)
            - User tidak bisa login setelah deleted
            - Untuk hard delete, gunakan management command
        """
        with transaction.atomic():
            user.is_active = False
            user.save()
            
            # Future: Log activity
            # log_user_activity(user, deleted_by, 'delete')
            
            return user
    
    @staticmethod
    def toggle_active_status(
        user: User,
        is_active: bool,
        toggled_by: Optional[User] = None
    ) -> User:
        """
        Toggle user active status (activate/deactivate)
        
        Berguna untuk:
            - Menonaktifkan user sementara
            - Mengaktifkan kembali user yang di-deactivate
            - Restore user yang di-soft delete
        
        Args:
            user: User instance
            is_active: Status aktif baru (True/False)
            toggled_by: User yang melakukan toggle
            
        Returns:
            User: Updated user instance
            
        Examples:
            >>> # Deactivate user
            >>> UserService.toggle_active_status(user, False)
            
            >>> # Reactivate user
            >>> UserService.toggle_active_status(user, True)
        """
        with transaction.atomic():
            user.is_active = is_active
            user.save()
            
            # Future: Log activity
            action = 'activate' if is_active else 'deactivate'
            # log_user_activity(user, toggled_by, action)
            
            return user
    
    @staticmethod
    def change_password(
        user: User,
        new_password: str,
        changed_by: Optional[User] = None
    ) -> User:
        """
        Change user password
        
        Flow:
            1. Hash new password
            2. Update user password
            3. Save changes
            4. Optional: Log activity
        
        Args:
            user: User instance
            new_password: Plain text password baru (akan di-hash)
            changed_by: User yang melakukan perubahan
            
        Returns:
            User: Updated user instance
            
        Examples:
            >>> UserService.change_password(
            ...     user=user,
            ...     new_password='newsecurepass123',
            ...     changed_by=admin_user
            ... )
        
        Implementasi Standar:
            - Password di-hash sebelum disimpan
            - Bisa dipanggil oleh admin atau user sendiri
        
        Catatan:
            - Untuk user change password sendiri, gunakan Django's
              PasswordChangeView (sudah handle old password validation)
            - Method ini untuk admin reset password user lain
        """
        with transaction.atomic():
            user.set_password(new_password)
            user.save()
            
            # Future: Log activity & send email notification
            # log_user_activity(user, changed_by, 'password_change')
            # send_password_changed_email(user)
            
            return user
    
    @staticmethod
    def assign_groups(
        user: User,
        group_names: List[str],
        assigned_by: Optional[User] = None
    ) -> User:
        """
        Assign user ke groups (replace existing)
        
        Args:
            user: User instance
            group_names: List of group names
            assigned_by: User yang melakukan assignment
            
        Returns:
            User: Updated user instance
            
        Examples:
            >>> UserService.assign_groups(
            ...     user=user,
            ...     group_names=['Staff', 'Editor'],
            ...     assigned_by=admin_user
            ... )
        """
        with transaction.atomic():
            # Clear existing groups
            user.groups.clear()
            
            # Add new groups
            for group_name in group_names:
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass  # Skip jika group tidak ada
            
            # Future: Log activity
            # log_user_activity(user, assigned_by, 'groups_changed')
            
            return user
    
    @staticmethod
    def get_users_list(
        filters: Optional[Dict[str, Any]] = None,
        include_inactive: bool = False
    ):
        """
        Get users list dengan optional filters
        
        Helper method untuk query users dengan optimization.
        Include document counts dan activity counts.
        
        Args:
            filters: Dictionary of filters (optional)
                Example: {
                    'search': 'john',
                    'is_staff': True,
                    'group': 'Staff'
                }
            include_inactive: Include inactive users (default: False)
                
        Returns:
            QuerySet: Users dengan annotations
            
        Examples:
            >>> users = UserService.get_users_list({
            ...     'search': 'john',
            ...     'is_staff': True
            ... })
        
        Implementasi Standar:
            - Annotate dengan document_count dan activity_count
            - Support search dan filter
            - Optimize dengan select_related dan prefetch_related
        """
        # Base query
        queryset = User.objects.all()
        
        # Filter active/inactive
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        # Annotate counts
        queryset = queryset.annotate(
            document_count=Count(
                'documents_created',
                filter=Q(documents_created__is_deleted=False),
                distinct=True
            ),
            activity_count=Count('document_activities', distinct=True)
        )
        
        # Prefetch groups untuk efisiensi
        queryset = queryset.prefetch_related('groups')
        
        # Apply filters jika provided
        if filters:
            # Search filter (username, full_name, email)
            if 'search' in filters and filters['search']:
                search = filters['search']
                queryset = queryset.filter(
                    Q(username__icontains=search) |
                    Q(full_name__icontains=search) |
                    Q(email__icontains=search)
                )
            
            # Staff filter
            if 'is_staff' in filters and filters['is_staff'] is not None:
                queryset = queryset.filter(is_staff=filters['is_staff'])
            
            # Superuser filter
            if 'is_superuser' in filters and filters['is_superuser'] is not None:
                queryset = queryset.filter(is_superuser=filters['is_superuser'])
            
            # Group filter
            if 'group' in filters and filters['group']:
                queryset = queryset.filter(groups__name=filters['group'])
        
        return queryset.order_by('-date_joined')
    
    @staticmethod
    def get_user_statistics():
        """
        Get user statistics untuk dashboard
        
        Returns:
            dict: Statistics dictionary
                - total_users: Total users aktif
                - total_staff: Total staff users
                - total_inactive: Total inactive users
                - by_group: Breakdown per group
        
        Examples:
            >>> stats = UserService.get_user_statistics()
            >>> print(stats['total_users'])
            45
        """
        # Total counts
        total_users = User.objects.filter(is_active=True).count()
        total_staff = User.objects.filter(is_active=True, is_staff=True).count()
        total_inactive = User.objects.filter(is_active=False).count()
        
        # Breakdown by group
        by_group = Group.objects.annotate(
            user_count=Count('user', filter=Q(user__is_active=True))
        ).values('name', 'user_count').order_by('-user_count')
        
        return {
            'total_users': total_users,
            'total_staff': total_staff,
            'total_inactive': total_inactive,
            'by_group': list(by_group)
        }
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength
        
        Checks:
            - Minimum length
            - Contains uppercase
            - Contains lowercase
            - Contains digit
            - Contains special character
        
        Args:
            password: Plain text password
            
        Returns:
            dict: {
                'is_valid': bool,
                'score': int (0-5),
                'messages': list of error messages
            }
        
        Examples:
            >>> result = UserService.validate_password_strength('Pass123!')
            >>> if result['is_valid']:
            ...     # Password valid
        """
        import re
        
        messages = []
        score = 0
        
        # Check length
        if len(password) < 8:
            messages.append('Password minimal 8 karakter')
        else:
            score += 1
            if len(password) >= 12:
                score += 1
        
        # Check uppercase
        if not re.search(r'[A-Z]', password):
            messages.append('Password harus mengandung huruf besar')
        else:
            score += 1
        
        # Check lowercase
        if not re.search(r'[a-z]', password):
            messages.append('Password harus mengandung huruf kecil')
        else:
            score += 1
        
        # Check digit
        if not re.search(r'\d', password):
            messages.append('Password harus mengandung angka')
        else:
            score += 1
        
        # Check special character
        if not re.search(r'[^A-Za-z0-9]', password):
            messages.append('Password harus mengandung karakter khusus')
        else:
            score += 1
        
        return {
            'is_valid': len(messages) == 0,
            'score': score,
            'messages': messages
        }
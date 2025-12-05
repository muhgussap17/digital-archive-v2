"""
Modul: services/employee_service.py
Fungsi: Business logic untuk Employee operations

Berisi pure business logic untuk:
    - Create employee
    - Update employee
    - Delete employee (soft delete)
    - Employee queries

Implementasi Standar:
    - Separation of concerns: business logic terpisah dari HTTP handling
    - Transaction management di service layer
    - Pure functions yang mudah di-test
    - No HTTP dependencies (request, messages, redirect)

Catatan Pemeliharaan:
    - Service functions harus pure (no side effects di HTTP layer)
    - Semua validasi di form layer
    - Activity logging opsional (belum diimplementasi untuk employee)
    
Cara Penggunaan:
    from ..services import EmployeeService
    
    # Create
    employee = EmployeeService.create_employee(
        form_data=form.cleaned_data,
        user=request.user
    )
    
    # Update
    updated_emp = EmployeeService.update_employee(
        employee=employee,
        form_data=form.cleaned_data,
        user=request.user
    )
    
    # Delete
    EmployeeService.delete_employee(
        employee=employee,
        user=request.user
    )
"""

from typing import Dict, Any, Optional
from django.db import transaction
from django.db.models import Count, Q

from ..models import Employee


class EmployeeService:
    """
    Service class untuk Employee business logic
    
    Menyediakan static methods untuk:
        - create_employee: Create pegawai baru
        - update_employee: Update data pegawai
        - delete_employee: Soft delete pegawai
        - get_active_employees: Query pegawai aktif
    
    Semua methods menggunakan transaction.atomic untuk data integrity
    dan automatic rollback jika terjadi error.
    """
    
    @staticmethod
    def create_employee(
        form_data: Dict[str, Any],
        user=None
    ) -> Employee:
        """
        Create pegawai baru
        
        Flow:
            1. Create Employee object
            2. Save to database
            3. Optional: Log activity (future)
        
        Args:
            form_data: Cleaned data dari EmployeeForm
                Required keys: nip, name, position, department, is_active
            user: User yang melakukan create (optional, untuk audit)
            
        Returns:
            Employee: Created employee instance
            
        Raises:
            Exception: Jika save gagal (akan di-rollback)
            
        Examples:
            >>> employee = EmployeeService.create_employee(
            ...     form_data={
            ...         'nip': '198501012010011001',
            ...         'name': 'John Doe',
            ...         'position': 'Staf Administrasi',
            ...         'department': 'Bagian Umum',
            ...         'is_active': True
            ...     },
            ...     user=request.user
            ... )
        
        Implementasi Standar:
            - Menggunakan transaction.atomic untuk rollback safety
            - NIP validation sudah dilakukan di form layer
        """
        with transaction.atomic():
            # Create employee instance
            employee = Employee.objects.create(
                nip=form_data['nip'],
                name=form_data['name'],
                position=form_data['position'],
                department=form_data['department'],
                is_active=form_data.get('is_active', True)
            )
            
            # Future: Log activity untuk audit trail
            # log_employee_activity(employee, user, 'create')
            
            return employee
    
    @staticmethod
    def update_employee(
        employee: Employee,
        form_data: Dict[str, Any],
        user=None
    ) -> Employee:
        """
        Update data pegawai
        
        Flow:
            1. Update employee fields
            2. Save to database
            3. Optional: Log activity (future)
        
        Args:
            employee: Employee instance yang akan diupdate
            form_data: Cleaned data dari EmployeeForm
                Required keys: nip, name, position, department, is_active
            user: User yang melakukan update (optional, untuk audit)
            
        Returns:
            Employee: Updated employee instance
            
        Raises:
            Exception: Jika update gagal (akan di-rollback)
            
        Examples:
            >>> updated_emp = EmployeeService.update_employee(
            ...     employee=emp,
            ...     form_data={
            ...         'nip': '198501012010011001',
            ...         'name': 'John Doe Updated',
            ...         'position': 'Kepala Bagian',
            ...         'department': 'Bagian Umum',
            ...         'is_active': True
            ...     },
            ...     user=request.user
            ... )
        
        Implementasi Standar:
            - Update semua fields yang disubmit
            - Auto update timestamp (updated_at)
        """
        with transaction.atomic():
            # Update fields
            employee.nip = form_data['nip']
            employee.name = form_data['name']
            employee.position = form_data['position']
            employee.department = form_data['department']
            employee.is_active = form_data.get('is_active', True)
            employee.save()
            
            # Future: Log activity
            # log_employee_activity(employee, user, 'update')
            
            return employee
    
    @staticmethod
    def delete_employee(
        employee: Employee,
        user=None
    ) -> Employee:
        """
        Soft delete pegawai
        
        Menandai pegawai sebagai tidak aktif tanpa menghapus dari database.
        Data SPD yang terkait tetap tersimpan untuk compliance.
        
        Args:
            employee: Employee instance yang akan dihapus
            user: User yang melakukan delete (optional, untuk audit)
            
        Returns:
            Employee: Deleted employee instance
            
        Raises:
            Exception: Jika delete gagal (akan di-rollback)
            
        Examples:
            >>> EmployeeService.delete_employee(
            ...     employee=emp,
            ...     user=request.user
            ... )
        
        Implementasi Standar:
            - Soft delete dengan set is_active=False
            - Data SPD terkait tetap tersimpan
            - Bisa di-restore dengan set is_active=True
        
        Catatan:
            - Tidak menghapus data dari database
            - Employee bisa di-restore jika diperlukan
            - SPD documents tetap valid
        """
        with transaction.atomic():
            # Soft delete
            employee.is_active = False
            employee.save()
            
            # Future: Log activity
            # log_employee_activity(employee, user, 'delete')
            
            return employee
    
    @staticmethod
    def get_active_employees(filters: Optional[Dict[str, Any]] = None):
        """
        Get active employees dengan optional filters
        
        Helper method untuk query employees dengan optimization.
        Includes SPD count annotation.
        
        Args:
            filters: Dictionary of filters (optional)
                Example: {'search': 'john', 'department': 'Bagian Umum'}
                
        Returns:
            QuerySet: Active employees dengan spd_count
            
        Examples:
            >>> emps = EmployeeService.get_active_employees({
            ...     'search': 'john',
            ...     'department': 'Bagian Umum'
            ... })
        
        Implementasi Standar:
            - Annotate dengan spd_count untuk efisiensi
            - Support search dan filter
        """
        # Base query: active employees only
        queryset = Employee.objects.filter(
            is_active=True
        ).annotate(
            spd_count=Count('spd_documents', filter=Q(spd_documents__document__is_deleted=False))
        )
        
        # Apply filters jika provided
        if filters:
            # Search filter (nama atau NIP)
            if 'search' in filters:
                search = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(nip__icontains=search)
                )
            
            # Department filter
            if 'department' in filters:
                queryset = queryset.filter(
                    department__icontains=filters['department']
                )
            
            # Position filter
            if 'position' in filters:
                queryset = queryset.filter(
                    position__icontains=filters['position']
                )
        
        return queryset.order_by('name')
    
    @staticmethod
    def get_employee_statistics():
        """
        Get employee statistics untuk dashboard
        
        Returns:
            dict: Statistics dictionary
                - total_active: Jumlah pegawai aktif
                - total_inactive: Jumlah pegawai tidak aktif
                - by_department: Breakdown per department
        
        Examples:
            >>> stats = EmployeeService.get_employee_statistics()
            >>> print(stats['total_active'])
            45
        """
        from django.db.models import Count
        
        # Total counts
        total_active = Employee.objects.filter(is_active=True).count()
        total_inactive = Employee.objects.filter(is_active=False).count()
        
        # Breakdown by department
        by_department = Employee.objects.filter(
            is_active=True
        ).values('department').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_active': total_active,
            'total_inactive': total_inactive,
            'by_department': by_department
        }
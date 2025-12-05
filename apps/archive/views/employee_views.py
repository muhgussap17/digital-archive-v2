"""
Modul: views/employee_views.py
Fungsi: Views untuk Employee CRUD operations

Views:
    - employee_list: List pegawai aktif dengan search & pagination
    - employee_create: Tambah pegawai baru
    - employee_update: Edit data pegawai
    - employee_delete: Hapus pegawai (soft delete)

Improvement:
    - Business logic extracted ke EmployeeService
    - AJAX handling extracted ke AjaxHandler
    - Views menjadi thin controllers (15-30 lines each)
    - Easier to test dan maintain

Contoh Penggunaan:
>>> # Di urls.py
>>> path('employees/', employee_views.employee_list, name='employee_list'),
>>> path('employees/create/', employee_views.employee_create, name='employee_create'),
>>> path('employees/<int:pk>/update/', employee_views.employee_update, name='employee_update'),
>>> path('employees/<int:pk>/delete/', employee_views.employee_delete, name='employee_delete'),
"""

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

from apps.accounts.decorators import staff_required
from ..models import Employee
from ..forms import EmployeeForm
from ..services import AjaxHandler, EmployeeService


@login_required
@require_http_methods(["GET"])
def employee_list(request):
    """
    View: List Pegawai Aktif dengan DataTables
    
    Fitur:
        - DataTables client-side processing
        - Live search (no page reload)
        - Sortable columns
        - Show SPD count per employee
    
    Permission:
        @login_required - Semua user bisa view
    
    Query Optimization:
        - Annotate spd_count untuk avoid N+1
        - Filter only active employees
        - Load ALL data (DataTables handle pagination client-side)
    
    Catatan:
        - Tidak pakai pagination di backend (Django Paginator)
        - DataTables handle search, sort, pagination di client-side
        - Cocok untuk data < 10,000 rows
    """
    # Get ALL active employees (no pagination)
    # DataTables akan handle pagination di client-side
    employees = EmployeeService.get_active_employees()
    
    context = {
        'employees': employees,
        'total_results': employees.count(),
    }
    
    return render(request, 'archive/employee_list.html', context)

@staff_required
@require_http_methods(["GET", "POST"])
def employee_create(request):
    """
    View: Tambah Pegawai Baru
    
    Fitur:
        - Form validasi NIP (18 digit)
        - Check NIP uniqueness
        - Support AJAX modal
    
    Flow:
        GET  -> Return empty form
        POST -> Validate -> Service create -> Redirect
    
    Permission:
        @staff_required - Hanya staff
    
    Catatan:
        - Business logic di EmployeeService.create_employee()
        - AJAX handling di AjaxHandler
        - View hanya orchestrate HTTP layer
    """
    # Initialize form
    form = EmployeeForm(request.POST or None)
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer (pure business logic)
            employee = EmployeeService.create_employee(
                form_data=form.cleaned_data,
                user=request.user
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'Pegawai "{employee.name}" berhasil ditambahkan!',
                redirect_url='archive:employee_list'
            )
            
        except Exception as e:
            # Handle errors
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal menambahkan pegawai: {str(e)}',
                redirect_url='archive:employee_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/employee_form_content.html',
            context={'is_update': False},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback for non-AJAX
    return render(request, 'archive/modals/employee_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def employee_update(request, pk):
    """
    View: Edit Data Pegawai
    
    Fitur:
        - Edit semua fields
        - NIP uniqueness check (exclude self)
        - Support AJAX modal
    
    Permission:
        @staff_required - Hanya staff
    
    Catatan:
        - Business logic di EmployeeService.update_employee()
        - Form validation handle NIP uniqueness
    """
    # Get employee atau 404
    employee = get_object_or_404(Employee, pk=pk, is_active=True)
    
    # Initialize form
    form = EmployeeForm(
        request.POST or None,
        instance=employee
    )
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer
            updated_employee = EmployeeService.update_employee(
                employee=employee,
                form_data=form.cleaned_data,
                user=request.user
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'Data pegawai "{updated_employee.name}" berhasil diperbarui!',
                redirect_url='archive:employee_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal memperbarui data pegawai: {str(e)}',
                redirect_url='archive:employee_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/employee_form_content.html',
            context={'employee': employee, 'is_update': True},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback
    return render(request, 'archive/modals/employee_form.html', {
        'form': form,
        'employee': employee,
        'is_update': True
    })


@staff_required
@require_http_methods(["POST"])
def employee_delete(request, pk):
    """
    View: Hapus Pegawai (Soft Delete)
    
    Fitur:
        - Soft delete (is_active=False)
        - Data SPD terkait tetap tersimpan
        - Support AJAX
    
    Permission:
        @staff_required - Hanya staff
        POST only untuk keamanan
    
    Catatan:
        - Business logic di EmployeeService.delete_employee()
        - Tidak menghapus dari database
        - Bisa di-restore dengan set is_active=True
    """
    # Get employee atau 404
    employee = get_object_or_404(Employee, pk=pk, is_active=True)
    
    try:
        # Call service layer
        EmployeeService.delete_employee(
            employee=employee,
            user=request.user
        )
        
        # Return success
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message=f'Pegawai "{employee.name}" berhasil dihapus!',
            redirect_url='archive:employee_list'
        )
        
    except Exception as e:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message=f'Gagal menghapus pegawai: {str(e)}',
            redirect_url='archive:employee_list'
        )
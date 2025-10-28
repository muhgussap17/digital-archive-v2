from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
import os
from datetime import datetime


class User(AbstractUser):
    """Extended User model"""
    full_name = models.CharField(max_length=255, verbose_name="Nama Lengkap")
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.full_name} ({self.username})"


class DocumentCategory(models.Model):
    """Document category with hierarchical structure"""
    name = models.CharField(max_length=100, verbose_name="Nama Kategori")
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='children'
    )
    icon = models.CharField(max_length=50, default='fa-folder')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    
    class Meta:
        db_table = 'document_categories'
        verbose_name = 'Kategori Dokumen'
        verbose_name_plural = 'Kategori Dokumen'
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_full_path(self):
        """Get full category path for folder structure"""
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.slug}"
        return self.slug


class Employee(models.Model):
    """Master data pegawai untuk SPD"""
    nip = models.CharField(max_length=50, unique=True, verbose_name="NIP")
    name = models.CharField(max_length=255, verbose_name="Nama Lengkap")
    position = models.CharField(max_length=100, verbose_name="Jabatan")
    department = models.CharField(max_length=100, verbose_name="Unit Kerja")
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        verbose_name = 'Pegawai'
        verbose_name_plural = 'Pegawai'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.nip})"


def document_upload_path(instance, filename):
    """Generate upload path based on category and date"""
    category_path = instance.category.get_full_path()
    date = instance.document_date or datetime.now()
    year = date.strftime('%Y')
    month = date.strftime('%m-%B')
    
    # Clean filename
    name, ext = os.path.splitext(filename)
    clean_name = slugify(name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return f"uploads/{category_path}/{year}/{month}/{clean_name}_{timestamp}{ext}"


class Document(models.Model):
    """Main document model"""
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="File PDF"
    )
    file_size = models.BigIntegerField(default=0, verbose_name="Ukuran File (bytes)")
    document_date = models.DateField(verbose_name="Tanggal Dokumen")
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='documents_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    # title = models.CharField(max_length=255, verbose_name="Judul Dokumen")
    # description = models.TextField(blank=True, null=True, verbose_name="Deskripsi")
    
    class Meta:
        db_table = 'documents'
        verbose_name = 'Dokumen'
        verbose_name_plural = 'Dokumen'
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['document_date']),
            models.Index(fields=['category', 'document_date']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.category} - {self.document_date}" # type: ignore
    
    def get_display_name(self):
        """Generate display name from metadata"""
        try:
            if hasattr(self, 'spd_info'):
                spd = self.spd_info # type: ignore
                from django.template.defaultfilters import date as date_filter
                date_str = date_filter(self.document_date, 'd F Y')
                return f"SPD - {spd.employee.name} → {spd.get_destination_display_full()} ({date_str})"
        except:
            pass

        # Fallback to category + date
        from django.template.defaultfilters import date as date_filter
        date_str = date_filter(self.document_date, 'd F Y')
        return f"{self.category.name} - {date_str}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def get_file_size_display(self):
        """Human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class SPDDocument(models.Model):
    """Additional metadata for SPD (Surat Perjalanan Dinas) documents"""
    
    DESTINATION_CHOICES = [
        # Dalam Provinsi Kalimantan Timur
        ('balikpapan', 'Balikpapan'),
        ('samarinda', 'Samarinda'),
        ('bontang', 'Bontang'),
        ('kutai_kartanegara', 'Kutai Kartanegara'),
        ('paser', 'Paser'),
        ('berau', 'Berau'),
        ('kutai_barat', 'Kutai Barat'),
        ('kutai_timur', 'Kutai Timur'),
        ('penajam_paser_utara', 'Penajam Paser Utara'),
        ('mahakam_ulu', 'Mahakam Ulu'),
        
        # Luar Provinsi (Frequent destinations)
        ('jakarta', 'Jakarta'),
        ('surabaya', 'Surabaya'),
        ('makassar', 'Makassar'),
        ('banjarmasin', 'Banjarmasin'),
        ('yogyakarta', 'Yogyakarta'),
        ('bandung', 'Bandung'),
        ('semarang', 'Semarang'),
        ('denpasar', 'Denpasar'),
        
        # Other
        ('other', 'Lainnya'),
    ]
    
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='spd_info',
        primary_key=True
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Pegawai",
        related_name='spd_documents'
    )
    destination = models.CharField(
        max_length=100,
        choices=DESTINATION_CHOICES,
        verbose_name="Tujuan"
    )
    destination_other = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Tujuan Lainnya",
        help_text="Isi jika memilih 'Lainnya'"
    )
    start_date = models.DateField(verbose_name="Tanggal Mulai")
    end_date = models.DateField(verbose_name="Tanggal Selesai")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'spd_documents'
        verbose_name = 'Dokumen SPD'
        verbose_name_plural = 'Dokumen SPD'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"SPD - {self.employee.name} ke {self.get_destination_display_full()}"
    
    def get_destination_display_full(self):
        """Return destination with custom value if 'other'"""
        if self.destination == 'other':
            return self.destination_other or 'Lainnya'
        return self.get_destination_display() # type: ignore
    
    def clean(self):
        """Validation"""
        from django.core.exceptions import ValidationError
        
        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'Tanggal selesai harus setelah atau sama dengan tanggal mulai'
            })
        
        if self.destination == 'other' and not self.destination_other:
            raise ValidationError({
                'destination_other': 'Harap isi tujuan lainnya'
            })
    
    def get_duration_days(self):
        """Calculate trip duration in days"""
        return (self.end_date - self.start_date).days + 1


class DocumentActivity(models.Model):
    """Audit trail for document activities"""
    ACTION_CHOICES = [
        ('create', 'Dibuat'),
        ('view', 'Dilihat'),
        ('download', 'Diunduh'),
        ('update', 'Diperbarui'),
        ('delete', 'Dihapus'),
    ]
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_activities'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_activities'
        verbose_name = 'Aktivitas Dokumen'
        verbose_name_plural = 'Aktivitas Dokumen'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.document.title}" # type: ignore


class SystemSetting(models.Model):
    """System-wide settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = 'Pengaturan Sistem'
        verbose_name_plural = 'Pengaturan Sistem'
    
    def __str__(self):
        return self.key
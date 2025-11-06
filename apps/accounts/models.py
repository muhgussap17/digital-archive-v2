from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Model User Kustom.
    Menggantikan model User default Django untuk menambahkan field kustom.
    """
    # Field 'username', 'email', 'first_name', 'last_name' sudah ada di AbstractUser
    
    full_name = models.CharField(max_length=255, verbose_name="Nama Lengkap", blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nomor Telepon")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        # Gunakan full_name jika ada, jika tidak, gunakan username
        return self.full_name or self.username

    def get_full_name(self):
        # Override fungsi default untuk memastikan 'full_name' yang dipakai
        return self.full_name

    def get_short_name(self):
        # Anda bisa atur ini untuk menampilkan first_name atau inisial
        return self.first_name or self.username
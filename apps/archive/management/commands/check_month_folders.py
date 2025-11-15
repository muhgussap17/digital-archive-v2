"""
Management command untuk check folder bulan yang inconsistent

Usage:
    python manage.py check_month_folders
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re


class Command(BaseCommand):
    help = 'Check untuk folder bulan yang menggunakan English naming'
    
    # English month names yang perlu diganti
    ENGLISH_MONTHS = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    INDONESIAN_MONTHS = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    
    def handle(self, *args, **options):
        """Execute command"""
        self.stdout.write(self.style.WARNING('Checking for inconsistent month folders...'))
        self.stdout.write('')
        
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        
        if not os.path.exists(uploads_dir):
            self.stdout.write(self.style.ERROR(f'Uploads directory not found: {uploads_dir}'))
            return
        
        issues = []
        
        # Walk through directory tree
        for root, dirs, files in os.walk(uploads_dir):
            for dirname in dirs:
                # Check if folder matches pattern: XX-MonthName
                match = re.match(r'(\d{2})-(\w+)', dirname)
                if match:
                    month_num = match.group(1)
                    month_name = match.group(2)
                    
                    # Check if using English month
                    if month_name in self.ENGLISH_MONTHS:
                        # Get Indonesian equivalent
                        idx = self.ENGLISH_MONTHS.index(month_name)
                        indo_name = self.INDONESIAN_MONTHS[idx]
                        
                        old_path = os.path.join(root, dirname)
                        new_name = f"{month_num}-{indo_name}"
                        new_path = os.path.join(root, new_name)
                        
                        issues.append({
                            'old_path': old_path,
                            'new_path': new_path,
                            'old_name': dirname,
                            'new_name': new_name,
                            'file_count': len(os.listdir(old_path))
                        })
        
        # Display results
        if not issues:
            self.stdout.write(self.style.SUCCESS('✓ No inconsistent folders found!'))
            self.stdout.write(self.style.SUCCESS('All month folders already use Indonesian naming.'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {len(issues)} folder(s) to rename:'))
        self.stdout.write('')
        
        for i, issue in enumerate(issues, 1):
            self.stdout.write(f"{i}. {issue['old_name']} → {issue['new_name']}")
            self.stdout.write(f"   Path: {issue['old_path']}")
            self.stdout.write(f"   Files: {issue['file_count']}")
            self.stdout.write('')
        
        self.stdout.write(self.style.WARNING('To rename these folders, run:'))
        self.stdout.write(self.style.SUCCESS('python manage.py fix_month_folders'))
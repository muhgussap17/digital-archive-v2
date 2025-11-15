"""
Management command untuk rename folder bulan ke Bahasa Indonesia

Usage:
    python manage.py fix_month_folders
    python manage.py fix_month_folders --dry-run  # Test tanpa execute
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from apps.archive.models import Document
import os
import re


class Command(BaseCommand):
    help = 'Rename English month folders to Indonesian'
    
    ENGLISH_MONTHS = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    INDONESIAN_MONTHS = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate changes without actually renaming',
        )
    
    def handle(self, *args, **options):
        """Execute command"""
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            self.stdout.write('')
        else:
            self.stdout.write(self.style.WARNING('LIVE MODE - Folders will be renamed'))
            self.stdout.write('')
        
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        
        if not os.path.exists(uploads_dir):
            self.stdout.write(self.style.ERROR(f'Uploads directory not found: {uploads_dir}'))
            return
        
        rename_map = []
        
        # Collect folders to rename
        for root, dirs, files in os.walk(uploads_dir):
            for dirname in dirs:
                match = re.match(r'(\d{2})-(\w+)', dirname)
                if match:
                    month_num = match.group(1)
                    month_name = match.group(2)
                    
                    if month_name in self.ENGLISH_MONTHS:
                        idx = self.ENGLISH_MONTHS.index(month_name)
                        indo_name = self.INDONESIAN_MONTHS[idx]
                        
                        old_path = os.path.join(root, dirname)
                        new_name = f"{month_num}-{indo_name}"
                        new_path = os.path.join(root, new_name)
                        
                        rename_map.append((old_path, new_path, dirname, new_name))
        
        if not rename_map:
            self.stdout.write(self.style.SUCCESS('✓ No folders to rename!'))
            return
        
        self.stdout.write(f'Found {len(rename_map)} folder(s) to rename:')
        self.stdout.write('')
        
        success_count = 0
        error_count = 0
        
        for old_path, new_path, old_name, new_name in rename_map:
            try:
                self.stdout.write(f'Renaming: {old_name} → {new_name}')
                
                if not dry_run:
                    # Check if target already exists
                    if os.path.exists(new_path):
                        self.stdout.write(self.style.ERROR(f'  ✗ Target already exists: {new_path}'))
                        error_count += 1
                        continue
                    
                    # Rename folder
                    os.rename(old_path, new_path)
                    
                    # Update database records
                    old_prefix = old_path.replace(settings.MEDIA_ROOT + '/', '')
                    new_prefix = new_path.replace(settings.MEDIA_ROOT + '/', '')
                    
                    documents = Document.objects.filter(file__startswith=old_prefix)
                    updated = 0
                    
                    for doc in documents:
                        doc.file.name = doc.file.name.replace(old_prefix, new_prefix)
                        doc.save(update_fields=['file'])
                        updated += 1
                    
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Renamed! Updated {updated} document(s)'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING('  → Would rename (dry run)'))
                    success_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                error_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Success: {success_count}'))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('This was a dry run. To actually rename folders, run:'))
            self.stdout.write(self.style.SUCCESS('python manage.py fix_month_folders'))
import os
import shutil
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Backup database and uploaded files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to keep backups (default: 30)'
        )
    
    def handle(self, *args, **options):
        retention_days = options['retention_days']
        backup_dir = settings.BACKUP_DIR
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backup directories
        db_backup_dir = os.path.join(backup_dir, 'db')
        files_backup_dir = os.path.join(backup_dir, 'files')
        os.makedirs(db_backup_dir, exist_ok=True)
        os.makedirs(files_backup_dir, exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS(f'Starting backup at {timestamp}...'))
        
        # Backup database
        self.stdout.write('Backing up database...')
        db_backup_file = os.path.join(db_backup_dir, f'db_backup_{timestamp}.json')
        
        try:
            with open(db_backup_file, 'w') as f:
                call_command('dumpdata', '--natural-foreign', '--natural-primary', 
                           '--exclude=contenttypes', '--exclude=auth.permission',
                           stdout=f)
            self.stdout.write(self.style.SUCCESS(f'✓ Database backed up to {db_backup_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database backup failed: {str(e)}'))
            return
        
        # Backup uploaded files
        self.stdout.write('Backing up uploaded files...')
        media_root = settings.MEDIA_ROOT
        files_backup_path = os.path.join(files_backup_dir, f'files_backup_{timestamp}')
        
        try:
            shutil.copytree(
                os.path.join(media_root, 'uploads'),
                files_backup_path,
                dirs_exist_ok=True
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Files backed up to {files_backup_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Files backup failed: {str(e)}'))
            return
        
        # Cleanup old backups
        self.stdout.write(f'Cleaning up backups older than {retention_days} days...')
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for backup_type_dir in [db_backup_dir, files_backup_dir]:
            for item in os.listdir(backup_type_dir):
                item_path = os.path.join(backup_type_dir, item)
                item_time = datetime.fromtimestamp(os.path.getctime(item_path))
                
                if item_time < cutoff_date:
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        self.stdout.write(f'  Deleted old backup: {item}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Failed to delete {item}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Backup completed successfully!'))
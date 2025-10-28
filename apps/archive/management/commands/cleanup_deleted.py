from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.archive.models import Document
import os


class Command(BaseCommand):
    help = 'Permanently delete soft-deleted documents older than specified days'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete documents soft-deleted more than X days ago (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find deleted documents
        documents = Document.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        count = documents.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No documents to delete.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would delete {count} documents:'))
            for doc in documents:
                self.stdout.write(f'  - {doc.file} (deleted: {doc.deleted_at})')
            return
        
        # Confirm deletion
        self.stdout.write(self.style.WARNING(
            f'About to permanently delete {count} documents deleted before {cutoff_date.date()}'
        ))
        confirm = input('Are you sure? Type "yes" to confirm: ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Cancelled.'))
            return
        
        # Delete documents and files
        deleted_count = 0
        for doc in documents:
            try:
                # Delete physical file
                if doc.file and os.path.exists(doc.file.path):
                    os.remove(doc.file.path)
                    self.stdout.write(f'  Deleted file: {doc.file.path}')
                
                # Delete from database
                doc_title = doc.file
                doc.delete()
                deleted_count += 1
                self.stdout.write(f'  Deleted document: {doc_title}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed to delete {doc.file}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully deleted {deleted_count} documents'))
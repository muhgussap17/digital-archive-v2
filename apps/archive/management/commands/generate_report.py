from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.archive.models import Document, DocumentCategory, SPDDocument
import csv
import os


class Command(BaseCommand):
    help = 'Generate document statistics report'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Month in YYYY-MM format (default: current month)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='report.csv',
            help='Output file path (default: report.csv)'
        )
    
    def handle(self, *args, **options):
        # Parse month
        month_str = options['month']
        if month_str:
            try:
                year, month = map(int, month_str.split('-'))
                start_date = datetime(year, month, 1)
            except:
                self.stdout.write(self.style.ERROR('Invalid month format. Use YYYY-MM'))
                return
        else:
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1)
        
        # Calculate date range
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)
        
        self.stdout.write(f'Generating report for {start_date.strftime("%B %Y")}...')
        
        # Get statistics
        documents = Document.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            is_deleted=False
        )
        
        total_count = documents.count()
        
        # Category breakdown
        category_stats = documents.values(
            'category__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # SPD statistics
        spd_count = documents.filter(category__slug='spd').count()
        
        # Generate CSV
        output_file = options['output']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Laporan Dokumen Arsip Digital'])
            writer.writerow(['Periode', start_date.strftime('%B %Y')])
            writer.writerow(['Tanggal Generate', datetime.now().strftime('%d %B %Y %H:%M')])
            writer.writerow([])
            
            # Summary
            writer.writerow(['RINGKASAN'])
            writer.writerow(['Total Dokumen', total_count])
            writer.writerow(['Total SPD', spd_count])
            writer.writerow([])
            
            # Category breakdown
            writer.writerow(['RINCIAN PER KATEGORI'])
            writer.writerow(['Kategori', 'Jumlah'])
            for stat in category_stats:
                writer.writerow([stat['category__name'], stat['count']])
        
        self.stdout.write(self.style.SUCCESS(f'✓ Report generated: {output_file}'))
        self.stdout.write(f'  Total documents: {total_count}')
        self.stdout.write(f'  SPD documents: {spd_count}')
from rest_framework import serializers
from .models import Document, DocumentCategory, SPDDocument, Employee, DocumentActivity


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee model"""
    
    class Meta:
        model = Employee
        fields = ['id', 'nip', 'name', 'position', 'department', 'is_active']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for DocumentCategory model"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'slug', 'parent', 'parent_name', 'icon', 
                  'full_path', 'document_count']
    
    def get_full_path(self, obj):
        """Get full category path"""
        return obj.get_full_path()
    
    def get_document_count(self, obj):
        """Get active document count"""
        return obj.documents.filter(is_deleted=False).count()


class SPDSerializer(serializers.ModelSerializer):
    """Serializer for SPD Document"""
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_nip = serializers.CharField(source='employee.nip', read_only=True)
    destination_display = serializers.CharField(
        source='get_destination_display_full', 
        read_only=True
    )
    duration_days = serializers.IntegerField(
        source='get_duration_days', 
        read_only=True
    )
    
    class Meta:
        model = SPDDocument
        fields = ['document', 'employee', 'employee_name', 'employee_nip',
                  'destination', 'destination_display', 'destination_other',
                  'start_date', 'end_date', 'duration_days', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    file_size_display = serializers.CharField(
        source='get_file_size_display', 
        read_only=True
    )
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    
    # Date formatting
    document_date_formatted = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    
    # SPD info (if exists)
    spd_info = SPDSerializer(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'display_name', 'file', 'file_url', 'download_url', 'preview_url',
            'file_size', 'file_size_display', 'document_date', 
            'document_date_formatted', 'category', 'category_name', 
            'category_icon', 'created_by', 'created_by_name', 
            'created_at', 'created_at_formatted', 'updated_at', 
            'version', 'spd_info'
        ]
        read_only_fields = ['id', 'file_size', 'created_by', 'created_at', 'updated_at', 'version']
    
    def get_file_url(self, obj):
        """Get file URL"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_download_url(self, obj):
        """Get download URL"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/documents/{obj.id}/download/')
        return None
    
    def get_preview_url(self, obj):
        """Get preview URL"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/archive/documents/{obj.id}/preview/')
        return None
    
    def get_document_date_formatted(self, obj):
        """Format document date"""
        return obj.document_date.strftime('%d %B %Y')
    
    def get_created_at_formatted(self, obj):
        """Format created timestamp"""
        return obj.created_at.strftime('%d %B %Y %H:%M')


class DocumentActivitySerializer(serializers.ModelSerializer):
    """Serializer for Document Activity"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    action_display = serializers.CharField(
        source='get_action_type_display', 
        read_only=True
    )
    created_at_formatted = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentActivity
        fields = ['id', 'document', 'user', 'user_name', 'action_type',
                  'action_display', 'description', 'ip_address', 
                  'created_at', 'created_at_formatted', 'time_ago']
        read_only_fields = ['id', 'created_at']
    
    def get_created_at_formatted(self, obj):
        """Format timestamp"""
        return obj.created_at.strftime('%d %B %Y %H:%M')
    
    def get_time_ago(self, obj):
        """Get human readable time difference"""
        from django.utils import timezone
        
        now = timezone.now()
        diff = now - obj.created_at
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Baru saja'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} menit yang lalu'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} jam yang lalu'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} hari yang lalu'
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f'{weeks} minggu yang lalu'
        else:
            return obj.created_at.strftime('%d %B %Y')
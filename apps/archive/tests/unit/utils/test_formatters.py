"""
Modul: tests/unit/utils/test_formatters.py
Fungsi: Unit tests untuk formatters utilities

Test Coverage:
    - format_file_size() - File size formatting

Run Tests:
    pytest apps/archive/tests/unit/utils/test_formatters.py -v
"""

import pytest
from apps.archive.utils import format_file_size


@pytest.mark.unit
@pytest.mark.utils
class TestFormatFileSize:
    """
    Test format_file_size()
    
    Scenarios:
        - ✅ Format bytes
        - ✅ Format kilobytes
        - ✅ Format megabytes
        - ✅ Format gigabytes
        - ✅ Zero size
    """
    
    def test_format_bytes(self):
        """Test: Format size < 1KB"""
        assert format_file_size(512) == "512.00 B"
        assert format_file_size(1023) == "1023.00 B"
    
    def test_format_kilobytes(self):
        """Test: Format size in KB range"""
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
    
    def test_format_megabytes(self):
        """Test: Format size in MB range"""
        assert format_file_size(1048576) == "1.00 MB"  # 1 MB
        assert format_file_size(5242880) == "5.00 MB"  # 5 MB
    
    def test_format_gigabytes(self):
        """Test: Format size in GB range"""
        size_1gb = 1024 * 1024 * 1024
        assert format_file_size(size_1gb) == "1.00 GB"
    
    def test_format_zero_size(self):
        """Test: Handle zero size"""
        assert format_file_size(0) == "0.00 B"
    
    def test_format_precision(self):
        """Test: Decimal precision"""
        result = format_file_size(1536)  # 1.5 KB
        assert ".50" in result or ".5" in result
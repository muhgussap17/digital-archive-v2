# ==================== DATE & TIME CONSTANTS ====================

class IndonesianMonth:
    """
    Mapping bulan dalam Bahasa Indonesia
    
    Digunakan untuk konsistensi penamaan folder dan display
    sesuai dengan standar pemerintah Indonesia
    """
    
    MONTHS = {
        1: 'Januari',
        2: 'Februari',
        3: 'Maret',
        4: 'April',
        5: 'Mei',
        6: 'Juni',
        7: 'Juli',
        8: 'Agustus',
        9: 'September',
        10: 'Oktober',
        11: 'November',
        12: 'Desember'
    }
    
    MONTHS_SHORT = {
        1: 'Jan',
        2: 'Feb',
        3: 'Mar',
        4: 'Apr',
        5: 'Mei',
        6: 'Jun',
        7: 'Jul',
        8: 'Agu',
        9: 'Sep',
        10: 'Okt',
        11: 'Nov',
        12: 'Des'
    }
    
    @classmethod
    def get_month_name(cls, month_number):
        """
        Dapatkan nama bulan dalam Bahasa Indonesia
        
        Args:
            month_number (int): Nomor bulan (1-12)
            
        Returns:
            str: Nama bulan (e.g., "Januari")
            
        Raises:
            ValueError: Jika month_number tidak valid
        """
        if month_number not in range(1, 13):
            raise ValueError(f"Invalid month number: {month_number}")
        return cls.MONTHS[month_number]
    
    @classmethod
    def get_month_folder(cls, month_number):
        """
        Format folder bulan dengan prefix angka
        
        Args:
            month_number (int): Nomor bulan (1-12)
            
        Returns:
            str: Format folder (e.g., "01-Januari")
            
        Example:
            >>> IndonesianMonth.get_month_folder(1)
            '01-Januari'
            >>> IndonesianMonth.get_month_folder(12)
            '12-Desember'
        """
        month_name = cls.get_month_name(month_number)
        return f"{month_number:02d}-{month_name}"


class DateFormat:
    """
    Format tanggal standar untuk sistem
    
    Mengikuti standar pemerintah Indonesia dan best practice Django
    """
    
    # Display formats (untuk template)
    DISPLAY_LONG = 'd F Y'  # 15 Januari 2024 (menggunakan Indonesian locale)
    DISPLAY_SHORT = 'd/m/Y'  # 15/01/2024
    DISPLAY_MEDIUM = 'd M Y'  # 15 Jan 2024
    
    # File naming formats
    FILE_NAME = '%Y-%m-%d'  # 2024-01-15
    
    # Folder naming formats
    FOLDER_YEAR = '%Y'  # 2024
    # FOLDER_MONTH tidak pakai strftime, gunakan IndonesianMonth.get_month_folder()
    
    @staticmethod
    def get_folder_path(date_obj):
        """
        Generate path folder dari date object
        
        Args:
            date_obj (datetime.date): Tanggal dokumen
            
        Returns:
            tuple: (year, month_folder)
            
        Example:
            >>> from datetime import date
            >>> d = date(2024, 1, 15)
            >>> DateFormat.get_folder_path(d)
            ('2024', '01-Januari')
        """
        year = date_obj.strftime(DateFormat.FOLDER_YEAR)
        month_folder = IndonesianMonth.get_month_folder(date_obj.month)
        return year, month_folder
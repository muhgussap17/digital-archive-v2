from django.shortcuts import render

def test(request):
    """
    View: Halaman Testing
    Fungsi: Untuk keperluan development dan testing fitur baru
    
    Catatan: Hapus atau comment pada production!
    """
    return render(request, 'archive/test.html')
## 1. Struktur Projek Django
digital-archive/
│
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── templates/accounts/
│   │        ├── login.html
│   │        ├── password_change_done.html
│   │        ├── password_change.html
│   │        ├── profile_edit.html
│   │        └── profile.html
│   │        
│   └── archive/
│       ├── admin.py
│       ├── api_urls.py
│       ├── context_processors.py
│       ├── forms.py
│       ├── middleware.py
│       ├── models.py
│       ├── serializers.py
│       ├── signals.py
│       ├── urls.py
│       ├── utils.py
│       ├── views.py
│       ├── templatetags/
│       │   ├── custom_tags.py
│       │   └── date_filters.py
│       └── templates/archive/
│           ├── components/
│           │   └── detail_panel.html
│           ├── modals/
│           │   ├── edit_document.html
│           │   ├── edit_document.html
│           │   ├── filter.html
│           │   ├── upload_documents.html
│           │   └── upload_spd.html
│           ├── dashboard.html
│           └── documents_list.html
│
├── config/
│   ├── settings.py
│   └── urls.py
│
├── media/uploads/
│   ├── spd/
│   │   └── 2024/
│   │       ├── 01-January/
│   │       │   └── SPD_JohnDoe_Jakarta_2024-01-15.pdf
│   │       └── 02-February/
│   │           └── SPD_JaneSmith_Surabaya_2024-02-05.pdf
│   └── belanjaan/
│       ├── atk/
│       │   └── 2024/
│       │       └── 01-January/
│       │           └── ATK_2024-01-10.pdf
│       ├── konsumsi/
│       └── bbm/
│
├── static/
│   └── css/, fonts/, js/, vendor/
│
├── templates/
│   ├── errors/, partials/
│   └── base.html
│
├── venv/
│
└── manage.py

## 2. Nama Model dan Form yang ingin ditampilkan dalam modal
- Model: Document, DocumentCategory, SPDDocuments, Employee
- Form: DocumentUploadForm, SPDDocumentForm, DocumentFilterForm, DocumentUpdateForm
- View list saat ini: document_list

## 3. Tujuan Modal Form-nya
- Menambah data baru (Upload Dokumen & Upload SPD)
- Mengedit data yang sudah ada
- Memfilter list dokumen

## 4. Apakah projectmu sudah menggunakan jQuery / Bootstrap?
Pada `base.html` hanya memasukkan script js dari tema Bootstrap Argon berikut:

```html
<!-- Core JS -->
<script src="{% static 'vendor/jquery/dist/jquery.min.js' %}"></script>
<script src="{% static 'vendor/bootstrap/dist/js/bootstrap.bundle.min.js' %}"></script>
<script src="{% static 'vendor/js-cookie/js.cookie.js' %}"></script>
<script src="{% static 'vendor/jquery.scrollbar/jquery.scrollbar.min.js' %}"></script>
<script src="{% static 'vendor/jquery-scroll-lock/dist/jquery-scrollLock.min.js' %}"></script>

<!-- Argon JS -->
<script src="{% static 'js/argon.js' %}"></script>


<!-- Optional JS -->

<!-- Chart.js -->
<script src="{% static 'vendor/chart.js/dist/Chart.min.js' %}"></script>
<script src="{% static 'vendor/chart.js/dist/Chart.extension.js' %}"></script>

<!-- DataTables -->
<script src="{% static 'vendor/datatables.net/js/jquery.dataTables.min.js' %}"></script>
<script src="{% static 'vendor/datatables.net-bs4/js/dataTables.bootstrap4.min.js' %}"></script>

<!-- Select2 -->
<script src="{% static 'vendor/select2/dist/js/select2.min.js' %}"></script>

<!-- Bootstrap Datepicker -->
<script src="{% static 'vendor/bootstrap-datepicker/dist/js/bootstrap-datepicker.min.js' %}"></script>

<!-- Bootstrap Notify -->
<script src="{% static 'vendor/bootstrap-notify/bootstrap-notify.min.js' %}"></script>
```
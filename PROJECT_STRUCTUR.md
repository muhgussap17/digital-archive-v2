arsip_digital/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── config/                      # Project configuration
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── archive/                 # Main archive app
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── signals.py
│   │   ├── utils.py
│   │   ├── middleware.py
│   │   ├── context_processors.py
│   │   ├── api_urls.py
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── backup_documents.py
│   │   │       └── cleanup_deleted.py
│   │   ├── templatetags/
│   │   │   ├── custom_tags.py
│   │   │   └── date_filters.py
│   │   └── templates/
│   │       └── archive/
│   │           ├── dashboard.html
│   │           ├── document_list.html
│   │           ├── spd_list.html
│   │           ├── forms/
│   │           ├── include/
│   │           └── modals/
│   └── accounts/                # User management
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── forms.py
│       ├── urls.py
│       └── templates/
│           └── accounts/
├── static/                      # Argon theme assets
│   ├── css/
│   │   ├── argon.min.css
│   │   ├── select2-argon-fix.css
│   │   └── custom.css
│   ├── js/
│   │   ├── argon.min.js
│   │   ├── modal_handler.js
│   │   └── custom.js
│   ├── img/
│   └── vendor/
├── media/
│   └── uploads/                 # Document storage
│       ├── spd/
│       └── belanjaan/
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   └── footer.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
└── backups/                     # Backup directory
    ├── db/
    └── files/
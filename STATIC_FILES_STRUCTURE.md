# Static Files Structure Guide

## Directory Structure

```
static/
├── argon/                          # Bootstrap Argon Theme v1.2.1
│   ├── css/
│   │   ├── argon.min.css          # Main theme CSS
│   │   └── argon.css              # Unminified version
│   ├── js/
│   │   ├── argon.min.js           # Main theme JS
│   │   └── argon.js               # Unminified version
│   ├── img/
│   │   └── brand/
│   │       ├── favicon.png
│   │       ├── blue.png           # Logo
│   │       └── white.png
│   └── scss/                      # Source SCSS files (optional)
│
├── vendor/                        # Third-party libraries (self-hosted)
│   ├── jquery/
│   │   └── jquery.min.js         # jQuery 3.7.1
│   │
│   ├── bootstrap/
│   │   └── js/
│   │       └── bootstrap.bundle.min.js
│   │
│   ├── fontawesome-7/            # FontAwesome 7 (self-hosted)
│   │   ├── css/
│   │   │   ├── all.min.css
│   │   │   └── fontawesome.min.css
│   │   └── webfonts/
│   │       ├── fa-solid-900.woff2
│   │       ├── fa-regular-400.woff2
│   │       └── fa-brands-400.woff2
│   │
│   ├── bootstrap-datepicker/
│   │   ├── css/
│   │   │   └── bootstrap-datepicker.min.css
│   │   ├── js/
│   │   │   └── bootstrap-datepicker.min.js
│   │   └── locales/
│   │       └── bootstrap-datepicker.id.min.js
│   │
│   ├── datatables/
│   │   ├── jquery.dataTables.min.js
│   │   └── dataTables.bootstrap4.min.js
│   │   └── dataTables.bootstrap4.min.css
│   │
│   ├── select2/
│   │   ├── css/
│   │   │   ├── select2.min.css
│   │   │   └── select2-bootstrap4.min.css
│   │   └── js/
│   │       └── select2.min.js
│   │
│   ├── chart.js/
│   │   └── chart.min.js
│   │
│   ├── bootstrap-notify/
│   │   └── bootstrap-notify.min.js
│   │
│   └── animate/
│       └── animate.min.css
│
├── fonts/                         # Self-hosted fonts
│   ├── plus-jakarta-sans.css      # Font face declarations
│   └── plus-jakarta-sans/
│       ├── PlusJakartaSans-Regular.woff2
│       ├── PlusJakartaSans-Medium.woff2
│       ├── PlusJakartaSans-SemiBold.woff2
│       └── PlusJakartaSans-Bold.woff2
│
├── css/
│   └── custom.css                 # Custom application styles
│
├── js/
│   └── custom.js                  # Custom application scripts
│
└── img/
    └── (custom application images)
```

## Download Instructions

### 1. **Bootstrap Argon Dashboard v1.2.1**
- Download dari: https://www.creative-tim.com/product/argon-dashboard
- Extract dan copy folder `argon/` ke `static/argon/`

### 2. **FontAwesome 7 (Free)**
- Download dari: https://fontawesome.com/download (versi Free Web)
- Extract dan rename folder menjadi `fontawesome-7`
- Copy ke `static/vendor/fontawesome-7/`
- Struktur: `fontawesome-7/css/all.min.css` dan `fontawesome-7/webfonts/`

### 3. **jQuery 3.7.1**
- Download dari: https://jquery.com/download/
- Save as `static/vendor/jquery/jquery.min.js`

### 4. **Bootstrap 4.6.2**
- Already included in Argon theme
- Or download from: https://getbootstrap.com/docs/4.6/getting-started/download/
- Save `bootstrap.bundle.min.js` to `static/vendor/bootstrap/js/`

### 5. **Bootstrap Datepicker**
- Download dari: https://github.com/uxsolutions/bootstrap-datepicker/releases
- Copy files ke `static/vendor/bootstrap-datepicker/`
- Include Indonesian locale file

### 6. **DataTables Bootstrap 4**
- Download dari: https://datatables.net/download/
- Select: DataTables + Bootstrap 4 styling
- Copy files ke `static/vendor/datatables/`

### 7. **Select2**
- Download dari: https://github.com/select2/select2/releases
- Copy CSS ke `static/vendor/select2/css/`
- Copy JS ke `static/vendor/select2/js/`
- Download Bootstrap 4 theme dari: https://github.com/ttskch/select2-bootstrap4-theme

### 8. **Chart.js**
- Download dari: https://www.chartjs.org/
- Save as `static/vendor/chart.js/chart.min.js`

### 9. **Bootstrap Notify**
- Download dari: https://github.com/mouse0270/bootstrap-notify
- Save as `static/vendor/bootstrap-notify/bootstrap-notify.min.js`

### 10. **Animate.css**
- Download dari: https://animate.style/
- Save as `static/vendor/animate/animate.min.css`

### 11. **Plus Jakarta Sans Font (Self-hosted)**

Create `static/fonts/plus-jakarta-sans.css`:

```css
/* Plus Jakarta Sans Font - Self Hosted */

@font-face {
  font-family: 'Plus Jakarta Sans';
  font-style: normal;
  font-weight: 300;
  src: url('plus-jakarta-sans/PlusJakartaSans-Light.woff2') format('woff2');
}

@font-face {
  font-family: 'Plus Jakarta Sans';
  font-style: normal;
  font-weight: 400;
  src: url('plus-jakarta-sans/PlusJakartaSans-Regular.woff2') format('woff2');
}

@font-face {
  font-family: 'Plus Jakarta Sans';
  font-style: normal;
  font-weight: 500;
  src: url('plus-jakarta-sans/PlusJakartaSans-Medium.woff2') format('woff2');
}

@font-face {
  font-family: 'Plus Jakarta Sans';
  font-style: normal;
  font-weight: 600;
  src: url('plus-jakarta-sans/PlusJakartaSans-SemiBold.woff2') format('woff2');
}

@font-face {
  font-family: 'Plus Jakarta Sans';
  font-style: normal;
  font-weight: 700;
  src: url('plus-jakarta-sans/PlusJakartaSans-Bold.woff2') format('woff2');
}
```

Download font files dari: https://fonts.google.com/specimen/Plus+Jakarta+Sans
- Use "Download family" button
- Convert TTF to WOFF2 using: https://cloudconvert.com/ttf-to-woff2
- Place in `static/fonts/plus-jakarta-sans/`

## Verification Checklist

After setting up all files, verify:

```bash
# Check static files exist
ls -la static/argon/css/argon.min.css
ls -la static/vendor/fontawesome-7/css/all.min.css
ls -la static/vendor/jquery/jquery.min.js
ls -la static/fonts/plus-jakarta-sans.css

# Collect static files
python manage.py collectstatic --noinput

# Test in browser
# All CSS should load without 404 errors
# Check browser console for any missing files
```

## CDN Fallback (Optional)

If any self-hosted file fails, you can temporarily use CDN by updating base.html:

```html
<!-- Fallback to CDN if needed -->
<script>
if (typeof jQuery == 'undefined') {
    document.write('<script src="https://code.jquery.com/jquery-3.7.1.min.js"><\/script>');
}
</script>
```

## File Size Reference

Expected total size: ~15-20 MB

- Argon theme: ~5 MB
- FontAwesome 7: ~2 MB
- Other vendors: ~3 MB
- Fonts: ~500 KB

## Notes

1. **Always use minified versions** (.min.js, .min.css) in production
2. **Keep unminified versions** for debugging if needed
3. **Version control**: Add all static files to git (they're part of your app)
4. **Updates**: Check for updates quarterly, test thoroughly before upgrading
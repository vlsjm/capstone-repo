web: gunicorn ResourceHive.wsgi:application
release: python manage.py migrate && python manage.py init_permissions

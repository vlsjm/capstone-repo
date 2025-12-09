from django.core.management.base import BaseCommand
from app.models import AdminPermission


class Command(BaseCommand):
    help = 'Initialize admin permissions'

    def handle(self, *args, **options):
        self.stdout.write('Initializing admin permissions...')
        AdminPermission.initialize_permissions()
        
        # Display all permissions
        permissions = AdminPermission.objects.all().order_by('id')
        self.stdout.write(self.style.SUCCESS(f'\nTotal permissions: {permissions.count()}'))
        
        for perm in permissions:
            self.stdout.write(f'  - {perm.name} ({perm.codename})')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Permissions initialized successfully!'))

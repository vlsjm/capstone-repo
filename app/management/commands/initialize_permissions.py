from django.core.management.base import BaseCommand
from app.models import AdminPermission


class Command(BaseCommand):
    help = 'Initialize default admin permissions in the database'

    def handle(self, *args, **options):
        self.stdout.write('Initializing admin permissions...')
        
        AdminPermission.initialize_permissions()
        
        count = AdminPermission.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully initialized {count} admin permissions!'
            )
        )
        
        # Display all permissions
        self.stdout.write('\nAvailable permissions:')
        for perm in AdminPermission.objects.all().order_by('name'):
            self.stdout.write(f'  - {perm.name} ({perm.codename})')

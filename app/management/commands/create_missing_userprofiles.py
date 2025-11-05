"""
Management command to create missing UserProfile records for users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import UserProfile


class Command(BaseCommand):
    help = 'Create UserProfile for users that do not have one'

    def handle(self, *args, **options):
        users_without_profile = []
        
        for user in User.objects.all():
            try:
                # Try to access the user profile
                _ = user.userprofile
            except UserProfile.DoesNotExist:
                # Create a UserProfile for this user
                UserProfile.objects.create(
                    user=user,
                    role='USER'  # Default role
                )
                users_without_profile.append(user.username)
                self.stdout.write(
                    self.style.SUCCESS(f'Created UserProfile for user: {user.username}')
                )
        
        if not users_without_profile:
            self.stdout.write(
                self.style.SUCCESS('All users already have UserProfiles!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCreated UserProfiles for {len(users_without_profile)} user(s):\n' +
                    '\n'.join(f'  - {username}' for username in users_without_profile)
                )
            )

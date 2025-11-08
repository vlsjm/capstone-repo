from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import UserProfile, ActivityLog


class Command(BaseCommand):
    help = 'Automatically reactivate user accounts that have reached their auto_enable_at time'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find all profiles with auto_enable_at in the past and inactive users
        profiles_to_reactivate = UserProfile.objects.filter(
            auto_enable_at__lte=now,
            auto_enable_at__isnull=False,
            user__is_active=False
        )
        
        count = 0
        for profile in profiles_to_reactivate:
            # Reactivate the user
            profile.user.is_active = True
            profile.user.save()
            
            # Clear the auto_enable_at field
            profile.auto_enable_at = None
            profile.save()
            
            # Log the activity
            ActivityLog.log_activity(
                user=None,  # System action
                action='activate',
                model_name='User',
                object_repr=profile.user.username,
                description=f"Auto-reactivated user account for {profile.user.username}"
            )
            
            count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Reactivated user: {profile.user.username}')
            )
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No users to reactivate'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully reactivated {count} user(s)')
            )

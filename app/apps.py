from django.apps import AppConfig
import os


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        """Initialize scheduler when Django app is ready."""
        import logging
        import sys
        
        logger = logging.getLogger(__name__)
        
        # Check if we're in a migration
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            logger.debug("Skipping scheduler initialization during migrations")
            return
        
        # Only start scheduler if explicitly enabled via SCHEDULER_ENABLED environment variable
        # This prevents multiple scheduler instances in multi-worker environments
        # Worker 1 (scheduler): SCHEDULER_ENABLED=true
        # Worker 2+ (no scheduler): SCHEDULER_ENABLED=false (or not set)
        scheduler_enabled = os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true'
        
        if not scheduler_enabled:
            logger.debug("Scheduler is disabled (SCHEDULER_ENABLED is not 'true')")
            return
        
        # Start scheduler
        try:
            from app.scheduler import start_scheduler
            start_scheduler()
            logger.info("Scheduler initialized successfully in app.ready()")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {str(e)}", exc_info=True)

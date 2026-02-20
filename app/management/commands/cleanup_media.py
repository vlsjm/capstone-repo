"""
Management command: cleanup_media

Removes orphan media files from disk that no longer have a matching
database record. Run this once to clear the backlog of stale files that
accumulated before the post_delete / pre_save signals were in place.

Usage:
    python manage.py cleanup_media            # dry-run (safe preview)
    python manage.py cleanup_media --delete   # actually delete the files
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Delete orphan barcode images and PPMP files that have no DB record."

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            default=False,
            help='Actually delete the files (default is dry-run / preview only).',
        )

    def handle(self, *args, **options):
        dry_run = not options['delete']
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN — no files will be deleted. Pass --delete to remove them."
            ))

        total_removed = 0
        total_size = 0

        # ── Supply barcode images ─────────────────────────────────────────────
        from app.models import Supply
        known_supply_barcodes = set(
            Supply.objects.exclude(barcode_image='')
                          .exclude(barcode_image=None)
                          .values_list('barcode_image', flat=True)
        )
        supply_barcode_dir = os.path.join(settings.MEDIA_ROOT, 'barcodes', 'supplies')
        total_removed, total_size = self._clean_dir(
            supply_barcode_dir,
            known_supply_barcodes,
            prefix='barcodes/supplies/',
            label='Supply barcode',
            dry_run=dry_run,
            total_removed=total_removed,
            total_size=total_size,
        )

        # ── Property barcode images ───────────────────────────────────────────
        from app.models import Property
        known_property_barcodes = set(
            Property.objects.exclude(barcode_image='')
                            .exclude(barcode_image=None)
                            .values_list('barcode_image', flat=True)
        )
        property_barcode_dir = os.path.join(settings.MEDIA_ROOT, 'barcodes', 'properties')
        total_removed, total_size = self._clean_dir(
            property_barcode_dir,
            known_property_barcodes,
            prefix='barcodes/properties/',
            label='Property barcode',
            dry_run=dry_run,
            total_removed=total_removed,
            total_size=total_size,
        )

        # ── PPMP files ────────────────────────────────────────────────────────
        from app.models import PPMP
        known_ppmp_files = set(
            PPMP.objects.exclude(file='')
                        .exclude(file=None)
                        .values_list('file', flat=True)
        )
        ppmp_dir = os.path.join(settings.MEDIA_ROOT, 'ppmp_files')
        total_removed, total_size = self._clean_dir(
            ppmp_dir,
            known_ppmp_files,
            prefix='ppmp_files/',
            label='PPMP file',
            dry_run=dry_run,
            total_removed=total_removed,
            total_size=total_size,
        )

        verb = "Would remove" if dry_run else "Removed"
        self.stdout.write(self.style.SUCCESS(
            f"\n{verb} {total_removed} orphan file(s) "
            f"({total_size / 1024:.1f} KB freed)."
        ))
        if dry_run and total_removed:
            self.stdout.write("Run with --delete to actually delete them.")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clean_dir(self, directory, known_paths, prefix, label,
                   dry_run, total_removed, total_size):
        if not os.path.isdir(directory):
            return total_removed, total_size

        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue

            db_path = prefix + filename  # e.g. "barcodes/supplies/SUP-1.png"
            if db_path not in known_paths:
                size = os.path.getsize(filepath)
                if dry_run:
                    self.stdout.write(f"  [dry-run] Orphan {label}: {filepath}")
                else:
                    try:
                        os.remove(filepath)
                        self.stdout.write(f"  Deleted {label}: {filepath}")
                    except OSError as e:
                        self.stderr.write(f"  ERROR deleting {filepath}: {e}")
                        continue
                total_removed += 1
                total_size += size

        return total_removed, total_size

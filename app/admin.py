from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Supply, Property, SupplyRequest,
    Reservation, ReservationBatch, ReservationItem, DamageReport, LostItem, BorrowRequest,
    UserProfile, ActivityLog, Notification,
    SupplyQuantity, SupplyHistory, PropertyHistory,
    Department, PropertyCategory, SupplyCategory, SupplySubcategory, 
    SupplyRequestBatch, SupplyRequestItem, BorrowRequestBatch, BorrowRequestItem, BadStockReport,
    UserSession
)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'property_name', 'property_number', 'category', 'condition', 
        'quantity', 'reserved_quantity', 'overall_quantity', 'quantity_per_physical_count', 'accountable_person', 'year_acquired', 
        'availability', 'location'
    ]
    list_filter = ['category', 'condition', 'availability', 'year_acquired']
    search_fields = ['property_name', 'property_number', 'accountable_person', 'location']
    fieldsets = (
        ('Basic Information', {
            'fields': ('property_number', 'property_name', 'category', 'description')
        }),
        ('Specifications', {
            'fields': ('unit_of_measure', 'unit_value', 'overall_quantity', 'quantity', 'reserved_quantity', 'quantity_per_physical_count')
        }),
        ('Location and Responsibility', {
            'fields': ('location', 'accountable_person', 'year_acquired')
        }),
        ('Status', {
            'fields': ('condition', 'availability', 'is_archived')
        }),
        ('Technical', {
            'fields': ('barcode',),
            'classes': ('collapse',)
        }),
    )

@admin.register(PropertyCategory)
class PropertyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'uacs']
    search_fields = ['name', 'uacs']
    fields = ['name', 'uacs']

admin.site.register(Supply)
admin.site.register(SupplyRequest)
admin.site.register(Reservation)

@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'user', 'status', 'report_date', 'has_image', 'image_size_display', 'image_deleted']
    list_filter = ['status', 'report_date', 'deleted_at']
    search_fields = ['item__property_name', 'user__username', 'description', 'remarks']
    readonly_fields = ['report_date', 'image_size', 'deleted_at', 'deleted_by', 'image_preview']
    actions = ['delete_images_bulk']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('user', 'item', 'description', 'status', 'remarks', 'report_date')
        }),
        ('Image Information', {
            'fields': ('image_preview', 'image_name', 'image_type', 'image_size', 'deleted_at', 'deleted_by')
        }),
    )
    
    def has_image(self, obj):
        """Display whether report has an image"""
        if obj.has_image:
            return format_html('<span style="color: green;">✓</span>')
        elif obj.deleted_at:
            return format_html('<span style="color: red;">Deleted</span>')
        return format_html('<span style="color: gray;">✗</span>')
    has_image.short_description = 'Image'
    
    def image_size_display(self, obj):
        """Display image size in human-readable format"""
        if obj.image_size and not obj.deleted_at:
            size_kb = obj.image_size / 1024
            if size_kb < 1024:
                return f"{size_kb:.1f} KB"
            else:
                return f"{size_kb / 1024:.1f} MB"
        return "-"
    image_size_display.short_description = 'Size'
    
    def image_deleted(self, obj):
        """Display deletion status"""
        if obj.deleted_at:
            deleted_by = obj.deleted_by.username if obj.deleted_by else "Unknown"
            return format_html(
                '<span style="color: red;">Yes</span><br><small>By: {}<br>On: {}</small>',
                deleted_by,
                obj.deleted_at.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<span style="color: green;">No</span>')
    image_deleted.short_description = 'Deleted'
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.has_image:
            from django.urls import reverse
            image_url = reverse('damage_report_image', args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 300px; max-height: 300px; border: 1px solid #ddd; padding: 5px;"/></a>',
                image_url, image_url
            )
        elif obj.deleted_at:
            return format_html('<span style="color: red;">Image deleted on {}</span>', obj.deleted_at.strftime('%Y-%m-%d'))
        return format_html('<span style="color: gray;">No image</span>')
    image_preview.short_description = 'Image Preview'
    
    def delete_images_bulk(self, request, queryset):
        """Bulk action to delete images from resolved/reviewed reports"""
        # Filter only reports that have images and are resolved/reviewed
        eligible_reports = queryset.filter(
            status__in=['resolved', 'reviewed'],
            deleted_at__isnull=True
        ).exclude(image_data__isnull=True)
        
        count = eligible_reports.count()
        
        if count == 0:
            self.message_user(
                request,
                "No eligible images to delete. Only resolved/reviewed reports with images can be deleted.",
                level='warning'
            )
            return
        
        # Delete images and track deletion
        for report in eligible_reports:
            if report.image_data:
                # Clear the binary image data
                report.image_data = None
                # Mark as deleted with audit trail
                report.deleted_at = timezone.now()
                report.deleted_by = request.user
                report.save()
        
        self.message_user(
            request,
            f"Successfully deleted images from {count} damage report(s). Audit trail preserved.",
            level='success'
        )
    
    delete_images_bulk.short_description = "Delete images from resolved/reviewed reports"

@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'user', 'status', 'report_date', 'last_seen_location', 'last_seen_date']
    list_filter = ['status', 'report_date', 'last_seen_date']
    search_fields = ['item__property_name', 'user__username', 'description', 'remarks', 'last_seen_location']
    readonly_fields = ['report_date']
    actions = ['mark_as_acknowledged', 'mark_as_resolved']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('user', 'item', 'description', 'status', 'remarks', 'report_date')
        }),
        ('Location & Date Information', {
            'fields': ('last_seen_location', 'last_seen_date')
        }),
    )
    
    def mark_as_acknowledged(self, request, queryset):
        """Bulk action to mark reports as acknowledged"""
        updated = queryset.filter(status='pending').update(status='acknowledged')
        self.message_user(
            request,
            f"Successfully marked {updated} report(s) as acknowledged.",
            level='success'
        )
    mark_as_acknowledged.short_description = "Mark as acknowledged"
    
    def mark_as_resolved(self, request, queryset):
        """Bulk action to mark reports as resolved"""
        updated = queryset.update(status='resolved')
        self.message_user(
            request,
            f"Successfully marked {updated} report(s) as resolved.",
            level='success'
        )
    mark_as_resolved.short_description = "Mark as resolved"

admin.site.register(BorrowRequest)
admin.site.register(BorrowRequestBatch)
admin.site.register(BorrowRequestItem)
admin.site.register(UserProfile)
admin.site.register(ActivityLog)
admin.site.register(Notification)
admin.site.register(SupplyQuantity)
admin.site.register(SupplyHistory)
admin.site.register(PropertyHistory)
admin.site.register(Department)
admin.site.register(SupplyCategory)
admin.site.register(SupplySubcategory)
admin.site.register(SupplyRequestBatch)
admin.site.register(SupplyRequestItem)
admin.site.register(ReservationBatch)
admin.site.register(ReservationItem)

@admin.register(BadStockReport)
class BadStockReportAdmin(admin.ModelAdmin):
    list_display = ['supply', 'quantity_removed', 'reported_by', 'reported_at', 'get_short_remarks']
    list_filter = ['reported_at', 'supply__category', 'supply__subcategory']
    search_fields = ['supply__supply_name', 'remarks', 'reported_by__username', 'reported_by__first_name', 'reported_by__last_name']
    readonly_fields = ['reported_at']
    date_hierarchy = 'reported_at'
    
    fieldsets = (
        ('Bad Stock Information', {
            'fields': ('supply', 'quantity_removed', 'remarks')
        }),
        ('Reported By', {
            'fields': ('reported_by', 'reported_at')
        }),
    )
    
    def get_short_remarks(self, obj):
        """Display truncated remarks in list view"""
        if len(obj.remarks) > 50:
            return obj.remarks[:50] + '...'
        return obj.remarks
    get_short_remarks.short_description = 'Remarks'
    
    def has_add_permission(self, request):
        """Prevent adding bad stock reports through admin - should use the modal"""
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key_short', 'ip_address', 'created_at', 'last_activity']
    list_filter = ['created_at', 'last_activity']
    search_fields = ['user__username', 'session_key', 'ip_address']
    readonly_fields = ['session_key', 'created_at', 'last_activity', 'user_agent']
    fields = ['user', 'session_key', 'ip_address', 'user_agent', 'created_at', 'last_activity']
    
    def session_key_short(self, obj):
        """Display shortened session key"""
        return obj.session_key[:20] + '...'
    session_key_short.short_description = 'Session Key'
    
    def has_add_permission(self, request):
        """Prevent manual addition of session records"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion if user is superuser"""
        return request.user.is_superuser

from django.contrib import admin
from .models import (
    Supply, Property, SupplyRequest,
    Reservation, DamageReport, BorrowRequest,
    UserProfile, ActivityLog, Notification,
    SupplyQuantity, SupplyHistory, PropertyHistory,
    Department, PropertyCategory, SupplyCategory, SupplySubcategory, 
    SupplyRequestBatch, SupplyRequestItem, BadStockReport
)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'property_name', 'property_number', 'category', 'condition', 
        'quantity', 'overall_quantity', 'quantity_per_physical_count', 'accountable_person', 'year_acquired', 
        'availability', 'location'
    ]
    list_filter = ['category', 'condition', 'availability', 'year_acquired']
    search_fields = ['property_name', 'property_number', 'accountable_person', 'location']
    fieldsets = (
        ('Basic Information', {
            'fields': ('property_number', 'property_name', 'category', 'description')
        }),
        ('Specifications', {
            'fields': ('unit_of_measure', 'unit_value', 'overall_quantity', 'quantity', 'quantity_per_physical_count')
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
admin.site.register(DamageReport)
admin.site.register(BorrowRequest)
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

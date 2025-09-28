from django.contrib import admin
from .models import (
    Supply, Property, SupplyRequest,
    Reservation, DamageReport, BorrowRequest,
    UserProfile, ActivityLog, Notification,
    SupplyQuantity, SupplyHistory, PropertyHistory,
    Department, PropertyCategory, SupplyCategory, SupplySubcategory, 
    SupplyRequestBatch, SupplyRequestItem
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
admin.site.register(PropertyCategory)
admin.site.register(SupplyCategory)
admin.site.register(SupplySubcategory)
admin.site.register(SupplyRequestBatch)
admin.site.register(SupplyRequestItem)

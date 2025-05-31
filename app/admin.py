from django.contrib import admin
from .models import Supply, Property, SupplyRequest, Reservation, DamageReport, BorrowRequest, UserProfile, ActivityLog, Notification, SupplyQuantity, SupplyHistory, PropertyHistory, Department

admin.site.register(Supply)
admin.site.register(Property)
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


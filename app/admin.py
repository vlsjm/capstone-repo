from django.contrib import admin
from .models import Supply, Property, SupplyRequest, Reservation, DamageReport, BorrowRequest, UserProfile

admin.site.register(Supply)
admin.site.register(Property)
admin.site.register(SupplyRequest)
admin.site.register(Reservation)
admin.site.register(DamageReport)
admin.site.register(BorrowRequest)
admin.site.register(UserProfile)  

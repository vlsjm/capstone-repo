from django.contrib import admin
from .models import User, Supply, Property, SupplyRequest, Reservation, DamageReport, BorrowRequest

admin.site.register(User)
admin.site.register(Supply)
admin.site.register(Property)
admin.site.register(SupplyRequest)
admin.site.register(Reservation)
admin.site.register(DamageReport)
admin.site.register(BorrowRequest)


from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('faculty', 'Faculty'),
        ('csg_officer', 'CSG Officer'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

class Supply(models.Model):
    STATUS_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('available', 'Available'),
    ]

    supply_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    date_received = models.DateField()
    barcode = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    available_for_request = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Property(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('good', 'Good'),
        ('needs_repair', 'Needs Repair'),
        ('damaged', 'Damaged'),
    ]

    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('not_available', 'Not Available'),
    ]

    property_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    date_acquired = models.DateField()
    barcode = models.CharField(max_length=100, unique=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    available_for_request = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SupplyRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    request_date = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()
    approved_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Request by {self.user.username} for {self.supply.name}"


class Reservation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reservation_date = models.DateTimeField(auto_now_add=True)
    return_date = models.DateField()
    approved_date = models.DateTimeField(null=True, blank=True)
    purpose = models.TextField()

    def __str__(self):
        return f"Reservation by {self.user.username} for {self.item.name}"

class DamageReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Property, on_delete=models.CASCADE)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    report_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Damage Report for {self.item.name}"

class BorrowRequest(models.Model):
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('declined', 'Declined'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    borrow_date = models.DateTimeField(auto_now_add=True)
    return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    purpose = models.TextField()

    def __str__(self):
        return f"Borrow request by {self.user.username} for {self.property.name}"



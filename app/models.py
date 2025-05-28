from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} {self.get_action_display()} {self.model_name} - {self.object_repr}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('faculty', 'Faculty'),
        ('csg_officer', 'CSG Officer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.user.username

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
        return self.supply_name

class Property(models.Model):
    CATEGORY_CHOICES = [
        ('Office Equipment', 'Office Equipment'),
        ('ICT Equipment', 'ICT Equipment'),
        ('Communication Equipment', 'Communication Equipment'),
        ('Other Machinery and Equipment', 'Other Machinery and Equipment'),
        ('Furniture and Fixtures', 'Furniture and Fixtures'),
    ]

    CONDITION_CHOICES = [
        ('In good condition', 'In good condition'),
        ('Needing repair', 'Needing repair'),
        ('Unserviceable', 'Unserviceable'),
        ('Obsolete', 'Obsolete'),
        ('No longer needed', 'No longer needed'),
        ('Not used since purchased', 'Not used since purchased'),
    ]

    property_name = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    barcode = models.CharField(max_length=150, unique=True, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=50, null=True, blank=True)
    unit_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(max_length=100, choices=CONDITION_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.property_name} - {self.barcode}"


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
    remarks = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"Request by {self.user.username} for {self.supply.supply_name}"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey('Property', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reservation_date = models.DateTimeField(auto_now_add=True)  # when the reservation was made
    needed_date = models.DateField(null=True, blank=True)
    return_date = models.DateField()
    approved_date = models.DateTimeField(null=True, blank=True)
    purpose = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    remarks = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"Reservation by {self.user.username} for {self.item.property_name}"

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
    remarks = models.TextField(blank=True, null=True)
    report_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Damage Report for {self.item.property_name}"

class BorrowRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('declined', 'Declined'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    borrow_date = models.DateTimeField(auto_now_add=True)
    return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    purpose = models.TextField()

    def __str__(self):
        return f"Borrow request by {self.user.username} for {self.property.property_name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    remarks = models.TextField(blank=True, null=True) 
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"

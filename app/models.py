from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date, datetime, timedelta
from django.utils import timezone
import logging


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
        ('view', 'Viewed'),
        ('request', 'Requested'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('claim', 'Claimed'),
        ('complete', 'Completed'),
        ('borrow', 'Borrowed'),
        ('return', 'Returned'),
        ('report', 'Reported'),
        ('activate', 'Activated'),
        ('change_password', 'Changed Password'),
        ('bad_stock', 'Bad Stock Removal'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_repr = models.TextField()  # Changed to TextField for unlimited length
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} {self.get_action_display()} {self.model_name} - {self.object_repr}"

    @classmethod
    def log_activity(cls, user, action, model_name, object_repr, description=None):
        return cls.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_repr=object_repr,
            description=description
        )

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLE_CHOICES = [
        ('ADMIN', 'ADMIN'),
        ('USER', 'USER'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    auto_enable_at = models.DateTimeField(null=True, blank=True, help_text="If set, account will be automatically reactivated at this date/time")

    def __str__(self):
        return self.user.username
    

class SupplyQuantity(models.Model):
    supply = models.OneToOneField('Supply', on_delete=models.CASCADE, related_name='quantity_info')
    current_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)  # Track reserved stock for approved requests
    minimum_threshold = models.PositiveIntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def available_quantity(self):
        """Calculate available quantity (current - reserved)"""
        return max(0, self.current_quantity - self.reserved_quantity)

    def __str__(self):
        return f"Quantity for {self.supply.supply_name}: {self.current_quantity}"

    def save(self, *args, **kwargs):
        # Get the user from kwargs
        user = kwargs.pop('user', None)
        skip_history = kwargs.pop('skip_history', False)  # Add skip_history parameter
        
        # Check if this is a new quantity record
        is_new = self.pk is None

        if is_new:
            super().save(*args, **kwargs)  # Save first to get the ID
            
            # Only create history if not skipped
            if not skip_history:
                SupplyHistory.objects.create(
                    supply=self.supply,
                    user=user,
                    action='create',
                    field_name='initial_quantity',
                    old_value=None,
                    new_value=str(self.current_quantity),
                    remarks=f"Initial quantity set to {self.current_quantity}"
                )
        else:
            # For existing supplies, track quantity changes
            if not skip_history:
                old_obj = SupplyQuantity.objects.get(pk=self.pk)
                if old_obj.current_quantity != self.current_quantity:
                    change = self.current_quantity - old_obj.current_quantity
                    remarks = f"Quantity {'increased' if change > 0 else 'decreased'} by {abs(change)}"
                    
                    SupplyHistory.objects.create(
                        supply=self.supply,
                        user=user,
                        action='update',
                        field_name='quantity',
                        old_value=str(old_obj.current_quantity),
                        new_value=str(self.current_quantity),
                        remarks=remarks
                    )

            super().save(*args, **kwargs)

class SupplyCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Supply Categories"

class SupplySubcategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Supply Subcategories"

class Supply(models.Model):
    STATUS_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('available', 'Available'),
    ]

    supply_name = models.CharField(max_length=255)
    category = models.ForeignKey(SupplyCategory, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(SupplySubcategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Unique barcode text (e.g., "SUP-001")
    barcode_image = models.ImageField(upload_to='barcodes/supplies/', null=True, blank=True)  # Barcode image file
    available_for_request = models.BooleanField(default=True)
    date_received = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)



    def __str__(self):
        return self.supply_name

    @property
    def status(self):
        try:
            quantity_info = self.quantity_info
            if quantity_info.current_quantity == 0:
                return 'out_of_stock'
            elif quantity_info.current_quantity <= quantity_info.minimum_threshold:
                return 'low_stock'
            else:
                return 'available'
        except SupplyQuantity.DoesNotExist:
            return 'out_of_stock'

    @property
    def get_status_display(self):
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, 'Unknown')
    
    def save(self, *args, **kwargs):
        # Get the user from kwargs
        user = kwargs.pop('user', None)

        # Check if this is a new supply (being created)
        is_new = self.pk is None

        if is_new:
            # For new supplies, save first to get the ID
            super().save(*args, **kwargs)
        else:
            # For existing supplies, track changes
            old_obj = Supply.objects.get(pk=self.pk)
            fields_to_track = ['supply_name', 'category', 'subcategory', 'description', 'barcode', 'date_received', 'expiration_date']
            
            for field in fields_to_track:
                old_value = getattr(old_obj, field)
                new_value = getattr(self, field)
                
                # Convert values to strings for comparison, handling None and empty values
                old_str = str(old_value) if old_value not in [None, ''] else ''
                new_str = str(new_value) if new_value not in [None, ''] else ''
                
                # Only create history entry if the values are actually different
                if old_str != new_str:
                    SupplyHistory.objects.create(
                        supply=self,
                        user=user,
                        action='update',
                        field_name=field,
                        old_value=old_str if old_str else None,
                        new_value=new_str if new_str else None
                    )

        super().save(*args, **kwargs)
        
        # Generate barcode if not set (after initial save to have an ID)
        if not self.barcode:
            from .utils import generate_barcode_image
            self.barcode = f"SUP-{self.pk}"
            # Generate and save barcode image
            filename, content = generate_barcode_image(self.barcode)
            self.barcode_image.save(filename, content, save=False)
            super().save(update_fields=['barcode', 'barcode_image'])
    
    @property
    def is_expired(self):
        if self.expiration_date:
            return self.expiration_date < date.today()
        return False

    @property
    def is_nearly_expired(self):
        if self.expiration_date:
            days_until_expiration = (self.expiration_date - date.today()).days
            return 0 <= days_until_expiration <= 30
        return False

    @classmethod
    def check_expiring_supplies(cls):
        """
        Check and create notifications for supplies that are expiring soon or have expired.
        This should be run periodically (e.g., daily) using a scheduled task.
        """
        today = date.today()
        
        # Find supplies that will expire in 30 days
        expiring_soon = cls.objects.filter(
            expiration_date__isnull=False,
            expiration_date=today + timedelta(days=30)
        )
        
        # Find supplies that just expired today
        expired_today = cls.objects.filter(
            expiration_date__isnull=False,
            expiration_date=today
        )
        
        # Get all admin users
        admin_users = User.objects.filter(userprofile__role='ADMIN')
        
        # Create notifications for supplies expiring soon
        for supply in expiring_soon:
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"Supply '{supply.supply_name}' will expire in 30 days",
                    remarks=f"Expiration date: {supply.expiration_date}"
                )
        
        # Create notifications for supplies that expired today
        for supply in expired_today:
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"Supply '{supply.supply_name}' has expired today",
                    remarks=f"Please remove from inventory or take appropriate action."
                )

    class Meta:
        permissions = [
            ("view_admin_dashboard", "Can view  admin dashboard"),
            ("view_checkout_page", "Can view checkout page"),
            ("view_user_dashboard", "Can view user dashboard"), #user side permissions
            ("view_user_module", "Can view user module"),
            ("view_admin_module", "Can view admin module"),
        ]
class PropertyCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    uacs = models.BigIntegerField(null=True, blank=True, help_text="UACS (e.g., 13124324)")

    def __str__(self):
        return self.name

class Property(models.Model):
    CONDITION_CHOICES = [
        ('In good condition', 'In good condition'),
        ('Needing repair', 'Needing repair'),
        ('Unserviceable', 'Unserviceable'),
        ('Obsolete', 'Obsolete'),
        ('No longer needed', 'No longer needed'),
        ('Not used since purchased', 'Not used since purchased'),
    ]

    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('not_available', 'Not Available'),
    ]

    property_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    old_property_number = models.CharField(max_length=100, null=True, blank=True, help_text="Previous property number before change")
    property_name = models.CharField(max_length=100)
    category = models.ForeignKey(PropertyCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Unique barcode text (e.g., "PROP-001")
    barcode_image = models.ImageField(upload_to='barcodes/properties/', null=True, blank=True)  # Barcode image file
    unit_of_measure = models.CharField(max_length=50, null=True, blank=True)
    unit_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        validators=[MinValueValidator(0)]
    )
    overall_quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0)
    reserved_quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0, help_text="Quantity reserved by pending/approved requests")
    quantity_per_physical_count = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0, help_text="Quantity based on physical count/inventory")
    location = models.CharField(max_length=255, null=True, blank=True)
    accountable_person = models.CharField(max_length=255, null=True, blank=True)
    year_acquired = models.DateField(null=True, blank=True)
    condition = models.CharField(max_length=100, choices=CONDITION_CHOICES, default='In good condition')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        # Only show property name and property number (if available), not barcode
        if self.property_number:
            return f"{self.property_name} ({self.property_number})"
        return self.property_name

    @property
    def available_quantity(self):
        """
        Calculate available quantity for new requests.
        Returns quantity available after accounting for reserved/pending requests.
        """
        return max(0, (self.quantity or 0) - (self.reserved_quantity or 0))

    def update_availability(self):
        """Update availability based on condition and quantity"""
        unavailable_conditions = ['Needing repair', 'Unserviceable', 'Obsolete', 'No longer needed']
        
        # First check condition
        if self.condition in unavailable_conditions:
            if self.availability != 'not_available':
                self.availability = 'not_available'
                self.save(update_fields=['availability'])
        else:
            # Then check quantity (handle None as 0)
            current_quantity = self.quantity or 0
            if current_quantity == 0 and self.availability != 'not_available':
                self.availability = 'not_available'
                self.save(update_fields=['availability'])
            elif current_quantity > 0 and self.availability != 'available':
                self.availability = 'available'
                self.save(update_fields=['availability'])

    def save(self, *args, **kwargs):
        # Get the user from kwargs
        user = kwargs.pop('user', None)
        
        # Format property number to uppercase if it has characters
        if self.property_number:
            self.property_number = self.property_number.upper()
        
        # Format old property number to uppercase if it has characters
        if self.old_property_number:
            self.old_property_number = self.old_property_number.upper()
        
        # If this is a new property or overall_quantity has changed
        if not self.pk:
            # For new properties, set current quantity equal to overall_quantity
            self.quantity = self.overall_quantity
        elif self.pk:
            # For existing properties, only update quantity if overall_quantity actually changed
            old_obj = Property.objects.get(pk=self.pk)
            if old_obj.overall_quantity != self.overall_quantity:
                self.quantity = self.overall_quantity
        
        # Check if this is a new property
        is_new = self.pk is None

        if is_new:
            # Set initial availability based on condition and quantity
            unavailable_conditions = ['Needing repair', 'Unserviceable', 'Obsolete', 'No longer needed']
            if self.condition in unavailable_conditions:
                self.availability = 'not_available'
            else:
                self.availability = 'available' if self.quantity >= 1 else 'not_available'
            super().save(*args, **kwargs)
            
            # Create history entry for new property
            if user:
                PropertyHistory.objects.create(
                    property=self,
                    user=user,
                    action='create',
                    field_name='initial_creation',
                    new_value='Property created'
                )
        else:
            # For existing properties, track changes
            old_obj = Property.objects.get(pk=self.pk)
            
            # Handle property number change - store old value if property number is being changed
            if old_obj.property_number != self.property_number and old_obj.property_number:
                # Only update old_property_number if we don't already have one stored
                # or if the current old_property_number is the same as the old property_number
                if not self.old_property_number or self.old_property_number == old_obj.property_number:
                    self.old_property_number = old_obj.property_number
            
            fields_to_track = ['property_number', 'property_name', 'category', 'description', 'barcode', 
                             'unit_of_measure', 'unit_value', 'overall_quantity', 'quantity', 'quantity_per_physical_count',
                             'location', 'accountable_person', 'year_acquired', 'condition', 'availability']
            
            for field in fields_to_track:
                old_value = getattr(old_obj, field)
                new_value = getattr(self, field)
                
                # Handle special comparisons for different data types
                values_different = False
                if field == 'unit_value':
                    # Compare decimal values with proper precision
                    from decimal import Decimal
                    old_decimal = Decimal(str(old_value)) if old_value is not None else Decimal('0')
                    new_decimal = Decimal(str(new_value)) if new_value is not None else Decimal('0')
                    values_different = old_decimal != new_decimal
                elif field == 'category':
                    # Compare category objects properly
                    old_cat_id = old_value.id if old_value else None
                    new_cat_id = new_value.id if new_value else None
                    values_different = old_cat_id != new_cat_id
                else:
                    # Standard comparison for other fields
                    values_different = old_value != new_value
                
                if values_different:
                    # Add specific remarks for quantity changes
                    remarks = None
                    if field in ['quantity', 'overall_quantity', 'quantity_per_physical_count']:
                        change = (new_value or 0) - (old_value or 0)
                        if change > 0:
                            remarks = f"{field.replace('_', ' ').title()} increased by {abs(change)}"
                        else:
                            remarks = f"{field.replace('_', ' ').title()} decreased by {abs(change)}"

                    PropertyHistory.objects.create(
                        property=self,
                        user=user,
                        action='update',
                        field_name=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                        remarks=remarks
                    )
            
            super().save(*args, **kwargs)
            
            # Update availability based on condition and quantity changes
            if old_obj.condition != self.condition or old_obj.quantity != self.quantity:
                self.update_availability()

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure overall_quantity is not less than current quantity
        if self.overall_quantity is not None and self.quantity is not None:
            if self.overall_quantity < self.quantity:
                raise ValidationError({
                    'overall_quantity': 'Overall quantity cannot be less than current quantity.'
                })

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

    def save(self, *args, **kwargs):
        # Check if this is a new supply request
        is_new = self.pk is None
        
        # Get the old instance if it exists
        try:
            old_instance = SupplyRequest.objects.get(pk=self.pk)
            old_status = old_instance.status
        except SupplyRequest.DoesNotExist:
            old_status = None

        # Save the supply request
        super().save(*args, **kwargs)

        # If this is a new supply request, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New supply request #{self.id} submitted for {self.supply.supply_name} by {self.user.username}",
                    remarks=f"Quantity: {self.quantity}, Purpose: {self.purpose}"
                )

        # Update supply quantity when request is approved
        if old_status != self.status and self.status == 'approved':
            # Send approval email
            from .utils import send_supply_request_approval_email
            send_supply_request_approval_email(
                user=self.user,
                supply_name=self.supply.supply_name,
                requested_quantity=self.quantity,
                purpose=self.purpose,
                request_date=self.request_date,
                approved_date=self.approved_date or timezone.now(),
                request_id=self.id,
                remarks=self.remarks or ''
            )
            
            try:
                quantity_info = self.supply.quantity_info
                if quantity_info.current_quantity >= self.quantity:
                    quantity_info.current_quantity -= self.quantity
                    quantity_info.save()
                    
                    # Save the supply to update available_for_request
                    self.supply.save()
                    
                    # Create notification for low stock if needed
                    if quantity_info.current_quantity <= quantity_info.minimum_threshold:
                        # Get all admin users to notify about low stock
                        admin_users = User.objects.filter(userprofile__role='ADMIN')
                        
                        for admin_user in admin_users:
                            Notification.objects.create(
                                user=admin_user,
                                message=f"Supply '{self.supply.supply_name}' is running low on stock (Current: {quantity_info.current_quantity}, Minimum: {quantity_info.minimum_threshold})",
                                remarks="Please restock soon."
                            )
            except SupplyQuantity.DoesNotExist:
                pass

class SupplyRequestBatch(models.Model):
    """
    A batch supply request that can contain multiple supply items.
    This replaces single-item SupplyRequest for new multi-item functionality.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('partially_approved', 'Partially Approved'),
        ('for_claiming', 'For Claiming'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_date = models.DateTimeField(null=True, blank=True)
    claimed_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    claimed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='claimed_requests')
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"Batch Request #{self.id} by {self.user.username} ({self.request_date.date()})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    def save(self, *args, **kwargs):
        # Check if this is a new batch request
        is_new = self.pk is None
        
        # Get the old instance if it exists
        try:
            old_instance = SupplyRequestBatch.objects.get(pk=self.pk)
            old_status = old_instance.status
        except SupplyRequestBatch.DoesNotExist:
            old_status = None

        # Save the batch request
        super().save(*args, **kwargs)

        # If this is a new batch request, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            item_list = ", ".join([f"{item.supply.supply_name} (x{item.quantity})" 
                                 for item in self.items.all()[:3]])
            if self.items.count() > 3:
                item_list += f" and {self.items.count() - 3} more items"
            
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New batch supply request #{self.id} submitted by {self.user.username}",
                    remarks=f"Items: {item_list}. Purpose: {self.purpose[:100]}"
                )

        # NOTE: Quantity deduction is handled during the CLAIMING process, not during approval.
        # During approval, quantities are reserved (handled in views.py approve_batch_item).
        # During claiming, quantities are actually deducted from current_quantity (handled in views.py claim_batch_items).

class SupplyRequestItem(models.Model):
    """
    Individual supply items within a batch request.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    batch_request = models.ForeignKey(SupplyRequestBatch, on_delete=models.CASCADE, related_name='items')
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()  # Requested quantity
    approved_quantity = models.PositiveIntegerField(null=True, blank=True)  # Approved quantity
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved = models.BooleanField(default=False)  # Keep for backward compatibility
    claimed_date = models.DateTimeField(null=True, blank=True)  # When item was claimed
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['batch_request', 'supply']  # Prevent duplicate items in same batch

    def __str__(self):
        return f"{self.supply.supply_name} (x{self.quantity}) in Batch #{self.batch_request.id}"

    def save(self, *args, **kwargs):
        # Keep approved field in sync with status for backward compatibility
        self.approved = (self.status == 'approved')
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.quantity and self.supply:
            try:
                available_quantity = self.supply.quantity_info.current_quantity
                if self.quantity > available_quantity:
                    raise ValidationError({
                        'quantity': f'Only {available_quantity} units of {self.supply.supply_name} are available.'
                    })
            except SupplyQuantity.DoesNotExist:
                raise ValidationError({
                    'supply': f'Supply {self.supply.supply_name} has no quantity information.'
                })


class ReservationBatch(models.Model):
    """
    A batch reservation request that can contain multiple property items.
    Similar to BorrowRequestBatch and SupplyRequestBatch for consistency.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('partially_approved', 'Partially Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    
    # Link to the auto-generated borrow request batch
    generated_borrow_batch = models.ForeignKey('BorrowRequestBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_reservation_batch')

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"Reservation Batch #{self.id} by {self.user.username} ({self.request_date.date()})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def earliest_needed_date(self):
        """Get the earliest needed date among all items"""
        needed_dates = [item.needed_date for item in self.items.all() if item.needed_date]
        return min(needed_dates) if needed_dates else None

    @property
    def latest_return_date(self):
        """Get the latest return date among all items"""
        return_dates = [item.return_date for item in self.items.all() if item.return_date]
        return max(return_dates) if return_dates else None

    def save(self, *args, **kwargs):
        # Check if this is a new batch request
        is_new = self.pk is None
        
        # Get the old instance if it exists
        try:
            old_instance = ReservationBatch.objects.get(pk=self.pk)
            old_status = old_instance.status
        except ReservationBatch.DoesNotExist:
            old_status = None

        # Save the batch request
        super().save(*args, **kwargs)

        # If this is a new batch request, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            item_list = ", ".join([f"{item.property.property_name} (x{item.quantity})" 
                                 for item in self.items.all()[:3]])
            if self.items.count() > 3:
                item_list += f" and {self.items.count() - 3} more items"
            
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New batch reservation request #{self.id} submitted by {self.user.username}",
                    remarks=f"Items: {item_list}. Purpose: {self.purpose[:100]}"
                )

        # Handle status changes
        if old_status != self.status:
            if self.status == 'approved' and old_status == 'pending':
                # Notify user about approval
                Notification.objects.create(
                    user=self.user,
                    message=f"Your batch reservation request #{self.id} has been approved.",
                    remarks=self.remarks if self.remarks else None
                )
            elif self.status == 'rejected' and old_status == 'pending':
                # Notify user about rejection
                Notification.objects.create(
                    user=self.user,
                    message=f"Your batch reservation request #{self.id} has been rejected.",
                    remarks=self.remarks if self.remarks else None
                )

    @classmethod
    def check_and_update_batches(cls):
        """
        Check and update reservation batch statuses based on dates.
        Also handles auto-generation of borrow requests for approved reservations.
        This should be run periodically (e.g., daily) using a scheduled task.
        """
        from django.db import transaction
        
        # Get today's date in the configured timezone (not UTC)
        today = timezone.now().astimezone().date()
        
        # 0. Update individual items to expired when their needed_date OR return_date has passed
        # This applies to both pending and approved items that haven't been activated yet
        expired_items = ReservationItem.objects.filter(
            status__in=['pending', 'approved']
        ).filter(
            Q(needed_date__lt=today) | Q(return_date__lt=today)
        )
        for item in expired_items:
            item.status = 'expired'
            item.save()
        
        # 0b. Update pending/approved batches to expired when ALL their items are expired
        # This ensures batch status matches item status
        pending_batches = cls.objects.filter(status='pending')
        for batch in pending_batches:
            all_items = batch.items.all()
            if all_items and all(item.status == 'expired' for item in all_items):
                batch.status = 'expired'
                batch.save()
                # Notify the user about the expired reservation
                Notification.objects.create(
                    user=batch.user,
                    message=f"Your reservation batch #{batch.id} has expired.",
                    remarks=f"All items in the batch have expired before approval."
                )
        
        # 1. Update pending batches to expired when latest return_date has passed
        for batch in cls.objects.filter(status='pending'):
            if batch.latest_return_date and batch.latest_return_date < today:
                batch.status = 'expired'
                batch.save()
                
                # Notify the user about the expired reservation (only if not already notified)
                existing_notification = Notification.objects.filter(
                    user=batch.user,
                    message__contains=f"batch #{batch.id} has expired"
                ).exists()
                if not existing_notification:
                    Notification.objects.create(
                        user=batch.user,
                        message=f"Your reservation batch #{batch.id} has expired.",
                        remarks=f"The reservation period ended on {batch.latest_return_date} before approval."
                    )
        
        # 2a. Update approved batches to expired when ALL their items are expired
        approved_batches = cls.objects.filter(status='approved')
        for batch in approved_batches:
            all_items = batch.items.all()
            if all_items and all(item.status == 'expired' for item in all_items):
                batch.status = 'expired'
                batch.save()
                # Notify the user about the expired reservation
                existing_notification = Notification.objects.filter(
                    user=batch.user,
                    message__contains=f"batch #{batch.id} has expired"
                ).exists()
                if not existing_notification:
                    Notification.objects.create(
                        user=batch.user,
                        message=f"Your reservation batch #{batch.id} has expired.",
                        remarks=f"All items in the batch have expired."
                    )
        
        # 2b. Update approved batches to expired when latest return_date has passed without becoming active
        for batch in cls.objects.filter(status='approved'):
            if batch.latest_return_date and batch.latest_return_date < today and not batch.generated_borrow_batch:
                batch.status = 'expired'
                batch.save()
                
                # Notify the user about the expired reservation (only if not already notified)
                existing_notification = Notification.objects.filter(
                    user=batch.user,
                    message__contains=f"batch #{batch.id} has expired"
                ).exists()
                if not existing_notification:
                    Notification.objects.create(
                        user=batch.user,
                        message=f"Your reservation batch #{batch.id} has expired.",
                        remarks=f"The reservation period ended on {batch.latest_return_date} without activation."
                    )
        
        # 3. AUTO-GENERATE BORROW REQUESTS: Update approved batches to active when earliest needed_date is reached
        approved_batches = cls.objects.filter(
            status='approved',
            generated_borrow_batch__isnull=True  # Only if borrow request hasn't been created yet
        )
        
        for batch in approved_batches:
            earliest_date = batch.earliest_needed_date
            latest_date = batch.latest_return_date
            
            # Check if it's time to activate (needed_date reached and return_date hasn't passed)
            if earliest_date and earliest_date <= today and latest_date and latest_date >= today:
                with transaction.atomic():
                    # Create a single BorrowRequestBatch for the entire reservation batch
                    borrow_batch = BorrowRequestBatch.objects.create(
                        user=batch.user,
                        purpose=f"Auto-generated from Reservation Batch #{batch.id}: {batch.purpose}",
                        status='for_claiming',
                        approved_date=timezone.now(),
                        remarks=f"Automatically created from approved reservation batch #{batch.id}"
                    )
                    
                    # Create BorrowRequestItem for each approved item in the batch
                    approved_items = batch.items.filter(status='approved')
                    for item in approved_items:
                        BorrowRequestItem.objects.create(
                            batch_request=borrow_batch,
                            property=item.property,
                            quantity=item.quantity,
                            approved_quantity=item.quantity,
                            return_date=item.return_date,
                            status='approved',
                            approved=True,
                            remarks=f"Auto-generated from reservation batch #{batch.id}"
                        )
                        
                        # Mark item as active
                        item.status = 'active'
                        item.save()
                    
                    # Link the borrow batch to the reservation batch and mark as active
                    batch.generated_borrow_batch = borrow_batch
                    batch.status = 'active'
                    batch.save()
                    
                    # Notify admins about the auto-generated borrow request
                    admin_users = User.objects.filter(userprofile__role='ADMIN')
                    item_count = approved_items.count()
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"Borrow request #{borrow_batch.id} auto-generated from reservation batch #{batch.id}",
                            remarks=f"User: {batch.user.username}, {item_count} items, Status: For Claiming"
                        )
        
        # 4. Check active reservations to see if their linked borrow requests have been completed
        active_batches = cls.objects.filter(status='active', generated_borrow_batch__isnull=False)
        for batch in active_batches:
            borrow_batch = batch.generated_borrow_batch
            # Check if all items in the borrow batch have been returned
            if borrow_batch.status == 'returned':
                # Mark reservation items as completed
                batch.items.filter(status='active').update(status='completed')
                # Mark the reservation batch as completed
                batch.status = 'completed'
                batch.save()


class ReservationItem(models.Model):
    """
    Individual property items within a batch reservation request.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    
    batch_request = models.ForeignKey(ReservationBatch, on_delete=models.CASCADE, related_name='items')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    needed_date = models.DateField(null=True, blank=True)
    return_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved = models.BooleanField(default=False)  # For backward compatibility
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['batch_request', 'property']  # Prevent duplicate items in same batch

    def __str__(self):
        return f"{self.property.property_name} (x{self.quantity}) in Reservation Batch #{self.batch_request.id}"

    def save(self, *args, **kwargs):
        # Check if this is a new item or status is changing
        is_new = self.pk is None
        old_status = None
        old_quantity = None
        
        if not is_new:
            try:
                old_instance = ReservationItem.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_quantity = old_instance.quantity
            except ReservationItem.DoesNotExist:
                pass
        
        # Keep approved field in sync with status for backward compatibility
        self.approved = (self.status == 'approved')
        
        super().save(*args, **kwargs)
        
        # Handle reserved_quantity updates
        # NOTE: Reservations only reserve when APPROVED (not when pending)
        # Pending = waiting for admin review, Approved = reserved and waiting to be active
        if is_new and self.status == 'approved':
            # New approved reservation - reserve the quantity
            self.property.reserved_quantity += self.quantity
            self.property.save(update_fields=['reserved_quantity'])
        
        elif old_status and old_status != self.status:
            # Status changed
            if self.status == 'approved' and old_status == 'pending':
                # Pending -> Approved: NOW reserve the quantity
                self.property.reserved_quantity += self.quantity
                self.property.save(update_fields=['reserved_quantity'])
            
            elif self.status == 'rejected' and old_status == 'approved':
                # Rejected after approval: Release reserved quantity
                self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
                self.property.save(update_fields=['reserved_quantity'])
            
            elif self.status == 'rejected' and old_status == 'pending':
                # Rejected while pending: No reserved quantity to release
                pass
            
            elif self.status == 'active' and old_status == 'approved':
                # Approved -> Active (claimed): Deduct from both reserved and actual quantity
                self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
                self.property.quantity = max(0, self.property.quantity - self.quantity)
                self.property.save(update_fields=['reserved_quantity', 'quantity'])
                self.property.update_availability()
            
            elif self.status == 'completed' and old_status == 'active':
                # Active -> Completed (returned): Restore quantity
                self.property.quantity += self.quantity
                self.property.save(update_fields=['quantity'])
                self.property.update_availability()
            
            elif self.status == 'expired' and old_status == 'approved':
                # Expired after approval: Release reserved quantity
                self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
                self.property.save(update_fields=['reserved_quantity'])
                self.property.update_availability()
            
            elif self.status == 'expired' and old_status == 'pending':
                # Expired while pending: No reserved quantity to release
                pass
        
        elif old_quantity and old_quantity != self.quantity and self.status == 'approved':
            # Quantity changed while approved - update reserved amount
            quantity_diff = self.quantity - old_quantity
            self.property.reserved_quantity = max(0, self.property.reserved_quantity + quantity_diff)
            self.property.save(update_fields=['reserved_quantity'])
    
    def delete(self, *args, **kwargs):
        # Release reserved quantity if item is deleted while approved (not pending)
        if self.status == 'approved':
            self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
            self.property.save(update_fields=['reserved_quantity'])
        super().delete(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Allow users to submit any quantity - validation happens during approval
        # No need to check available_quantity at submission time
        pass


class Reservation(models.Model):
    """
    LEGACY MODEL - Kept for backward compatibility only.
    New reservations should use ReservationBatch and ReservationItem models.
    This model may be removed in future versions after data migration.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reservation_date = models.DateTimeField(auto_now_add=True)
    needed_date = models.DateField(null=True, blank=True)
    return_date = models.DateField()
    approved_date = models.DateTimeField(null=True, blank=True)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    
    # DEPRECATED: batch_id and batch_request_date (use ReservationBatch instead)
    batch_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    batch_request_date = models.DateTimeField(null=True, blank=True)
    
    # Link to the auto-generated borrow request
    generated_borrow_batch = models.ForeignKey('BorrowRequestBatch', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_reservation')

    class Meta:
        ordering = ['-reservation_date']

    def __str__(self):
        return f"[LEGACY] Reservation #{self.id} by {self.user.username} for {self.item.property_name}"

    def save(self, *args, **kwargs):
        # Check if this is a new reservation
        is_new = self.pk is None
        
        # Skip notification flag (used when creating batch to notify once)
        skip_notification = kwargs.pop('skip_notification', False)
        
        # Get the old instance if it exists
        try:
            old_instance = Reservation.objects.get(pk=self.pk)
            old_status = old_instance.status
        except Reservation.DoesNotExist:
            old_status = None

        # Save the reservation
        super().save(*args, **kwargs)
        
        # If this is a new reservation, notify admin users (unless skipped for batch)
        if is_new and not skip_notification:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            
            if self.batch_id:
                # For batch reservations, check if this is the first item
                batch_reservations = Reservation.objects.filter(batch_id=self.batch_id)
                if batch_reservations.count() == 1:  # This is the first item
                    # Notification will be sent after all items are created
                    pass
            else:
                # Single reservation (legacy or individual)
                for admin_user in admin_users:
                    Notification.objects.create(
                        user=admin_user,
                        message=f"New reservation #{self.id} submitted for {self.item.property_name} by {self.user.username}",
                        remarks=f"Quantity: {self.quantity}, Needed Date: {self.needed_date}, Return Date: {self.return_date}, Purpose: {self.purpose}"
                    )

        # Handle status changes
        if old_status != self.status:
            # When a reservation becomes active (auto-generated borrow request created)
            if self.status == 'active' and old_status == 'approved':
                # Don't decrease quantity here - it will be handled when borrow request becomes active
                
                # Notify the user that borrow request has been created
                borrow_batch_info = f"Borrow Request #{self.generated_borrow_batch.id} has been created for you." if self.generated_borrow_batch else "Please visit the office to claim your items."
                
                Notification.objects.create(
                    user=self.user,
                    message=f"Your reservation for {self.item.property_name} is ready for claiming!",
                    remarks=f"{borrow_batch_info} Return date: {self.return_date}"
                )
            
            # When a reservation is completed
            elif self.status == 'completed' and old_status == 'active':
                # Don't increase quantity here - it will be handled by the borrow request system
                
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your reservation for {self.item.property_name} has been completed.",
                    remarks="Thank you for returning the items on time."
                )
            
            # When a reservation is approved
            elif self.status == 'approved' and old_status in ['pending', None]:
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your reservation for {self.item.property_name} has been approved.",
                    remarks=self.remarks if self.remarks else None
                )
            
            # When a reservation is rejected
            elif self.status == 'rejected' and old_status in ['pending', None]:
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your reservation for {self.item.property_name} has been rejected.",
                    remarks=self.remarks if self.remarks else None
                )

    @classmethod
    def check_and_update_reservations(cls):
        """
        Check and update reservation statuses based on dates.
        This should be run periodically (e.g., daily) using a scheduled task.
        """
        today = timezone.now().date()
        
        # Update pending reservations to expired when return_date has passed
        pending_to_expired = cls.objects.filter(
            status='pending',
            return_date__lt=today
        )
        for reservation in pending_to_expired:
            reservation.status = 'expired'
            reservation.save()
            
            # Notify the user about the expired reservation
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation request for {reservation.item.property_name} has expired.",
                remarks=f"The reservation period ended on {reservation.return_date} before approval."
            )
        
        # Update approved reservations to expired when return_date has passed without becoming active
        approved_to_expired = cls.objects.filter(
            status='approved',
            return_date__lt=today
        )
        for reservation in approved_to_expired:
            reservation.status = 'expired'
            reservation.save()
            
            # Notify the user about the expired reservation
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation for {reservation.item.property_name} has expired.",
                remarks=f"The reservation period ended on {reservation.return_date} without activation."
            )
        
        # AUTO-GENERATE BORROW REQUESTS: Update approved reservations to active when needed_date is reached
        from django.db import transaction
        
        # Get unique batch_ids of approved reservations ready for activation
        approved_reservations = cls.objects.filter(
            status='approved',
            needed_date__lte=today,
            return_date__gte=today,
            generated_borrow_batch__isnull=True  # Only if borrow request hasn't been created yet
        )
        
        # Group by batch_id (None for non-batch reservations)
        processed_batches = set()
        
        for reservation in approved_reservations:
            # Skip if we've already processed this batch
            if reservation.batch_id and reservation.batch_id in processed_batches:
                continue
            
            with transaction.atomic():
                if reservation.batch_id:
                    # Handle batch reservation - get all items in the batch
                    batch_reservations = cls.objects.filter(
                        batch_id=reservation.batch_id,
                        status='approved',
                        generated_borrow_batch__isnull=True
                    )
                    
                    # Create a single BorrowRequestBatch for the entire reservation batch
                    borrow_batch = BorrowRequestBatch.objects.create(
                        user=reservation.user,
                        purpose=f"Auto-generated from Reservation Batch {reservation.batch_id[:8]}: {reservation.purpose}",
                        status='for_claiming',
                        approved_date=timezone.now(),
                        remarks=f"Automatically created from approved reservation batch {reservation.batch_id[:8]}"
                    )
                    
                    # Create BorrowRequestItem for each reservation in the batch
                    for res in batch_reservations:
                        BorrowRequestItem.objects.create(
                            batch_request=borrow_batch,
                            property=res.item,
                            quantity=res.quantity,
                            approved_quantity=res.quantity,
                            return_date=res.return_date,
                            status='approved',
                            approved=True,
                            remarks=f"Auto-generated from reservation #{res.id}"
                        )
                        
                        # Link the borrow batch to each reservation and mark as active
                        res.generated_borrow_batch = borrow_batch
                        res.status = 'active'
                        res.save()
                    
                    # Mark batch as processed
                    processed_batches.add(reservation.batch_id)
                    
                    # Notify admins about the auto-generated borrow request
                    admin_users = User.objects.filter(userprofile__role='ADMIN')
                    item_count = batch_reservations.count()
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"Borrow request #{borrow_batch.id} auto-generated from reservation batch",
                            remarks=f"User: {reservation.user.username}, {item_count} items, Status: For Claiming"
                        )
                else:
                    # Handle single (non-batch) reservation - legacy support
                    borrow_batch = BorrowRequestBatch.objects.create(
                        user=reservation.user,
                        purpose=f"Auto-generated from Reservation #{reservation.id}: {reservation.purpose}",
                        status='for_claiming',
                        approved_date=timezone.now(),
                        remarks=f"Automatically created from approved reservation #{reservation.id}"
                    )
                    
                    # Create the BorrowRequestItem for this reservation
                    BorrowRequestItem.objects.create(
                        batch_request=borrow_batch,
                        property=reservation.item,
                        quantity=reservation.quantity,
                        approved_quantity=reservation.quantity,
                        return_date=reservation.return_date,
                        status='approved',
                        approved=True,
                        remarks=f"Auto-generated from reservation #{reservation.id}"
                    )
                    
                    # Link the borrow batch to the reservation
                    reservation.generated_borrow_batch = borrow_batch
                    reservation.status = 'active'
                    reservation.save()
                    
                    # Notify admins about the auto-generated borrow request
                    admin_users = User.objects.filter(userprofile__role='ADMIN')
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"Borrow request #{borrow_batch.id} auto-generated from reservation #{reservation.id}",
                            remarks=f"User: {reservation.user.username}, Item: {reservation.item.property_name} (x{reservation.quantity}), Status: For Claiming"
                        )
                # Notify admins about the auto-generated borrow request
                admin_users = User.objects.filter(userprofile__role='ADMIN')
                for admin_user in admin_users:
                    Notification.objects.create(
                        user=admin_user,
                        message=f"Borrow request #{borrow_batch.id} auto-generated from reservation #{reservation.id}",
                        remarks=f"User: {reservation.user.username}, Item: {reservation.item.property_name} (x{reservation.quantity}), Status: For Claiming"
                    )
        
        # Update active reservations to completed when return_date is passed
        active_to_completed = cls.objects.filter(
            status='active',
            return_date__lt=today
        )
        for reservation in active_to_completed:
            reservation.status = 'completed'
            reservation.save()

    @classmethod
    def get_active_reservations(cls, item, date=None):
        """
        Get all active reservations for an item on a specific date.
        If no date is provided, uses the current date.
        """
        if date is None:
            date = timezone.now().date()
        
        return cls.objects.filter(
            item=item,
            status__in=['approved', 'active'],
            needed_date__lte=date,
            return_date__gte=date
        )

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
    
    # Store image as binary data in PostgreSQL database
    image_data = models.BinaryField(blank=True, null=True, help_text="Compressed image stored as binary data")
    image_name = models.CharField(max_length=255, blank=True, null=True, help_text="Original filename")
    image_type = models.CharField(max_length=50, default='image/jpeg', help_text="MIME type (e.g., image/jpeg)")
    image_size = models.PositiveIntegerField(null=True, blank=True, help_text="Image size in bytes")
    
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="When the image was deleted")
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_damage_reports', help_text="Admin who deleted the image")

    def __str__(self):
        return f"Damage Report for {self.item.property_name}"
    
    @property
    def has_image(self):
        """Check if report has an image that hasn't been deleted"""
        return bool(self.image_data and not self.deleted_at)
    
    def set_image_from_file(self, image_file):
        """
        Compress and store image file as binary data in database.
        This method should be called from forms/views when processing uploads.
        """
        from .image_compression import compress_and_convert_to_binary
        
        if image_file:
            try:
                # Compress image and convert to binary
                binary_data, size = compress_and_convert_to_binary(image_file)
                
                if binary_data:
                    self.image_data = binary_data
                    self.image_name = image_file.name
                    self.image_type = 'image/jpeg'  # Always JPEG after compression
                    self.image_size = size
                    return True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to process image for damage report: {str(e)}")
        return False

    def save(self, *args, **kwargs):
        # Check if this is a new damage report
        is_new = self.pk is None
        
        # Save the damage report
        super().save(*args, **kwargs)
        
        # If this is a new damage report, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New damage report #{self.id} submitted for {self.item.property_name} by {self.user.username}",
                    remarks=f"Description: {self.description}"
                )

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

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Check if quantity is available for new requests
        if not self.pk:
            if self.quantity is None:
                raise ValidationError({
                    'quantity': 'Quantity is required.'
                })
            
            if self.property is None:
                raise ValidationError({
                    'property': 'Property is required.'
                })

            available_quantity = self.property.quantity if self.property.quantity is not None else 0
            if available_quantity == 0:
                raise ValidationError({
                    'quantity': 'This item is currently not available for borrowing.'
                })
            if self.quantity > available_quantity:
                raise ValidationError({
                    'quantity': f'Cannot borrow more than available quantity. Available: {available_quantity}'
                })
        
        # For existing requests being updated
        if self.pk:
            old_request = BorrowRequest.objects.get(pk=self.pk)
            if self.status != old_request.status and self.status == 'approved':
                if self.quantity is None:
                    raise ValidationError({
                        'quantity': 'Quantity is required.'
                    })
                
                available_quantity = self.property.quantity if self.property.quantity is not None else 0
                if self.quantity > available_quantity:
                    raise ValidationError({
                        'quantity': f'Cannot approve request. Available quantity ({available_quantity}) is less than requested quantity ({self.quantity})'
                    })

    def save(self, *args, **kwargs):
        # Run validation
        self.clean()
        
        # Check if this is a new borrow request
        is_new = self.pk is None

        if is_new:
            super().save(*args, **kwargs)
            
            # Notify admin users about new request
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New borrow request for {self.property.property_name} by {self.user.username}",
                    remarks=f"Quantity: {self.quantity}, Return Date: {self.return_date}"
                )
        else:
            # Get the old instance
            old_instance = BorrowRequest.objects.get(pk=self.pk)
            old_status = old_instance.status
            super().save(*args, **kwargs)

            # Handle status changes
            if old_status != self.status:
                if self.status == 'approved':
                    # Decrease the property's quantity
                    self.property.quantity -= self.quantity
                    self.property.save()

                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} has been approved.",
                        remarks=self.remarks if self.remarks else None
                    )

                elif self.status == 'returned' and old_status in ['approved', 'overdue']:
                    # Increase the property's quantity
                    self.property.quantity += self.quantity
                    self.property.save()
                    
                    # Set actual return date
                    self.actual_return_date = timezone.now().date()

                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrowed {self.property.property_name} has been marked as returned.",
                        remarks=self.remarks if self.remarks else None
                    )

                elif self.status == 'declined' and old_status == 'pending':
                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} has been declined.",
                        remarks=self.remarks if self.remarks else None
                    )

                elif self.status == 'overdue' and old_status == 'approved':
                    # Notify the user and admin
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} is overdue.",
                        remarks=f"Please return the item(s) as soon as possible. Return date was: {self.return_date}"
                    )
                    
                    admin_users = User.objects.filter(userprofile__role='ADMIN')
                    for admin_user in admin_users:
                        Notification.objects.create(
                            user=admin_user,
                            message=f"Borrow request for {self.property.property_name} by {self.user.username} is overdue",
                            remarks=f"Return date was: {self.return_date}"
                        )

    @classmethod
    def check_overdue_items(cls):
        # Get today's date in the local timezone (not UTC)
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = timezone.now().astimezone(local_tz).date()
        
        overdue_requests = cls.objects.filter(
            status='approved',
            return_date__lt=today
        )
        for request in overdue_requests:
            request.status = 'overdue'
            request.save()

class BorrowRequestBatch(models.Model):
    """
    A batch borrow request that can contain multiple property items.
    This replaces single-item BorrowRequest for new multi-item functionality.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('partially_approved', 'Partially Approved'),
        ('for_claiming', 'For Claiming'),
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('expired', 'Expired'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_date = models.DateTimeField(null=True, blank=True)
    claimed_date = models.DateTimeField(null=True, blank=True)
    returned_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    claimed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='claimed_borrow_requests')
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"Borrow Batch #{self.id} by {self.user.username} ({self.request_date.date()})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def earliest_return_date(self):
        """Get the earliest return date among all items"""
        return_dates = [item.return_date for item in self.items.all() if item.return_date]
        return min(return_dates) if return_dates else None

    @property
    def latest_return_date(self):
        """Get the latest return date among all items"""
        return_dates = [item.return_date for item in self.items.all() if item.return_date]
        return max(return_dates) if return_dates else None

    def save(self, *args, **kwargs):
        # Check if this is a new batch request
        is_new = self.pk is None
        
        # Get the old instance if it exists
        try:
            old_instance = BorrowRequestBatch.objects.get(pk=self.pk)
            old_status = old_instance.status
        except BorrowRequestBatch.DoesNotExist:
            old_status = None

        # Save the batch request
        super().save(*args, **kwargs)

        # If this is a new batch request, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            item_list = ", ".join([f"{item.property.property_name} (x{item.quantity})" 
                                 for item in self.items.all()[:3]])
            if self.items.count() > 3:
                item_list += f" and {self.items.count() - 3} more items"
            
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New batch borrow request #{self.id} submitted by {self.user.username}",
                    remarks=f"Items: {item_list}. Purpose: {self.purpose[:100]}"
                )

        # Handle status changes
        if old_status != self.status:
            if self.status == 'active':
                # When items are claimed/borrowed
                for item in self.items.filter(status='approved'):
                    item.property.quantity -= item.quantity
                    item.property.save()
                    item.status = 'active'
                    item.save()
                
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your borrow request batch #{self.id} is now active.",
                    remarks=f"Items have been claimed. Please return by: {self.latest_return_date}"
                )

            elif self.status == 'returned':
                # When all items are returned
                for item in self.items.filter(status='active'):
                    item.property.quantity += item.quantity
                    item.property.save()
                    item.status = 'returned'
                    item.actual_return_date = timezone.now().date()
                    item.save()
                
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your borrow request batch #{self.id} has been marked as returned.",
                    remarks="Thank you for returning all items."
                )

    @classmethod
    def check_overdue_batches(cls):
        """
        Check and update batch statuses based on return dates and send SMS notifications.
        
        This method:
        1. Finds all active batches with items past their return_date
        2. Marks those batches and items as 'overdue'
        3. Sends SMS notifications to users (only once per item)
        4. Creates in-app notifications
        
        Called by:
        - Scheduler (every 2 hours) - for automatic detection
        - View (when page loads) - for immediate UI updates
        """
        from django.conf import settings
        from zoneinfo import ZoneInfo
        from app.utils import send_sms_alert
        
        logger = logging.getLogger(__name__)
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = timezone.now().astimezone(local_tz).date()
        
        logger.info(f"Checking for overdue batches (today: {today})...")
        
        # Find active OR overdue batches where any item is past the return date
        active_batches = cls.objects.filter(status__in=['active', 'overdue']).prefetch_related('items__property', 'user__userprofile')
        
        total_batches_checked = active_batches.count()
        batches_marked_overdue = 0
        sms_sent_count = 0
        sms_failed_count = 0
        
        logger.info(f"Found {total_batches_checked} active batch(es) to check")
        
        for batch in active_batches:
            # Find items in this batch that are overdue (return_date < today and not yet returned)
            overdue_items = batch.items.filter(
                return_date__lt=today,
                actual_return_date__isnull=True,  # Not yet returned
                status__in=['active', 'overdue']  # Check both active and already-overdue items
            )
            
            if not overdue_items.exists():
                continue  # This batch has no overdue items
            
            # Get the data BEFORE updating (query will be lost after update)
            overdue_items_list = list(overdue_items.select_related('property'))
            item_count = len(overdue_items_list)
            
            logger.info(f"Batch #{batch.id}: Found {item_count} overdue item(s)")
            
            # Mark batch as overdue
            batch.status = 'overdue'
            batch.save(update_fields=['status'])
            batches_marked_overdue += 1
            
            # Mark individual items as overdue
            overdue_items.update(status='overdue')
            
            # Check if we need to send SMS notification
            user = batch.user
            
            # Count how many items haven't been notified yet
            unnotified_items = [item for item in overdue_items_list if not item.overdue_notified]
            
            if not unnotified_items:
                logger.info(f"Batch #{batch.id}: All items already notified, skipping SMS")
                continue
            
            logger.info(f"Batch #{batch.id}: {len(unnotified_items)} item(s) need SMS notification")
            
            # Send SMS notification
            try:
                # Get user phone number
                phone_number = None
                try:
                    user_profile = user.userprofile
                    phone_number = user_profile.phone
                except Exception:
                    logger.warning(f"Batch #{batch.id}: User {user.username} has no UserProfile. Skipping SMS.")
                    continue
                
                if not phone_number:
                    logger.warning(f"Batch #{batch.id}: User {user.username} has no phone number. Skipping SMS.")
                    continue
                
                # Create SMS message
                user_name = user.first_name or user.username
                
                # Calculate days overdue for each item
                days_overdue_list = [(today - item.return_date).days for item in overdue_items_list]
                max_days_overdue = max(days_overdue_list) if days_overdue_list else 0
                
                # Create item summary - list all overdue items with details
                item_summary = ", ".join([
                    f"{item.property.property_name} - {item.property.property_number} (x{item.quantity})"
                    for item in overdue_items_list
                ])
                
                # Construct SMS message
                message = (
                    f"Hello {user_name},\n\n"
                    f"Borrow Request #{batch.id}\n"
                    f"You have {item_count} OVERDUE item(s):\n"
                    f"{item_summary}\n\n"
                    f"Most overdue: {max_days_overdue} days\n\n"
                    f"Please return these items ASAP.\n\n"
                    f"Thank you,\nResource Hive Team"
                )
                
                # Log the SMS for debugging
                logger.info(f"\n{'='*60}\nSMS TO {phone_number} (User: {user.username}):\n{'='*60}\n{message}\n{'='*60}")
                
                # Send SMS
                success, response = send_sms_alert(phone_number, message)
                
                if success:
                    # Mark all items in this batch as notified
                    for item in overdue_items_list:
                        item.overdue_notified = True
                        item.save(update_fields=['overdue_notified'])
                    
                    sms_sent_count += 1
                    logger.info(f"✅ Batch #{batch.id}: SMS sent successfully to {user.username} ({phone_number})")
                else:
                    sms_failed_count += 1
                    logger.error(f"❌ Batch #{batch.id}: Failed to send SMS to {user.username}: {response}")
                
                # Create in-app notification (regardless of SMS success)
                Notification.objects.create(
                    user=user,
                    message=f"Your borrow request batch #{batch.id} is now OVERDUE. Please return the items immediately.",
                    remarks=f"{item_count} item(s) overdue"
                )
                
            except Exception as e:
                sms_failed_count += 1
                logger.error(f"❌ Batch #{batch.id}: Error sending overdue notification: {str(e)}", exc_info=True)
        
        # Summary logging
        if batches_marked_overdue > 0 or sms_sent_count > 0 or sms_failed_count > 0:
            logger.info(
                f"Overdue check complete: "
                f"{batches_marked_overdue} batch(es) marked overdue, "
                f"{sms_sent_count} SMS sent, "
                f"{sms_failed_count} SMS failed"
            )
        else:
            logger.info("Overdue check complete: No overdue items found")

    @classmethod
    def check_near_overdue_items(cls):
        """Check and send email reminders for items approaching their return date"""
        from django.utils import timezone
        from app.utils import calculate_reminder_trigger_date, send_near_overdue_borrow_email
        
        logger = logging.getLogger(__name__)
        now = timezone.now()
        today = now.date()
        
        try:
            # Get all active borrow items that haven't been returned and haven't been notified yet
            active_items = BorrowRequestItem.objects.filter(
                status='active',
                actual_return_date__isnull=True,
                near_overdue_notified=False,
                batch_request__status__in=['active', 'overdue']
            ).select_related('batch_request', 'batch_request__user', 'property')
            
            if not active_items.exists():
                logger.debug("No active borrow items needing near-overdue notifications")
                return
            
            logger.info(f"Checking {active_items.count()} active borrow items for near-overdue status")
            
            success_count = 0
            failure_count = 0
            
            for item in active_items:
                try:
                    # Calculate when reminder should be sent (returns datetime)
                    reminder_trigger_datetime = calculate_reminder_trigger_date(
                        item.batch_request.request_date.date(),
                        item.return_date
                    )
                    
                    # Check if current time has passed the trigger datetime (but before return date)
                    if now >= reminder_trigger_datetime and today <= item.return_date:
                        user = item.batch_request.user
                        days_until_return = (item.return_date - today).days
                        
                        # Calculate hours for short-term borrows
                        from datetime import datetime, time
                        return_datetime = datetime.combine(item.return_date, time(23, 59))
                        hours_until_return = (return_datetime - now).total_seconds() / 3600
                        
                        logger.info(
                            f"Sending near-overdue reminder to {user.username} for "
                            f"{item.property.property_name} ({days_until_return} days / {hours_until_return:.1f} hours until return)"
                        )
                        
                        # Send email reminder
                        success = send_near_overdue_borrow_email(item)
                        
                        if success:
                            # Mark as notified
                            item.near_overdue_notified = True
                            item.save(update_fields=['near_overdue_notified'])
                            success_count += 1
                            logger.info(f"[OK] Near-overdue email sent to {user.email} for item #{item.id}")
                        else:
                            failure_count += 1
                            logger.error(f"[FAIL] Failed to send near-overdue email to {user.email}")
                
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Error sending near-overdue notification for item #{item.id}: {str(e)}")
            
            if success_count + failure_count > 0:
                logger.info(f"Near-overdue check complete: {success_count} sent, {failure_count} failed")

        except Exception as e:
            logger.error(f"Error in check_near_overdue_items: {str(e)}")

    @classmethod
    def check_expired_batches(cls):
        """
        Check and update batch statuses when items or batches expire.
        
        This method:
        1. Marks pending/approved items as expired when their return_date has passed
        2. Marks pending batches as expired when their latest return_date has passed
        3. Unreserves quantities for expired items, freeing them for other requests
        4. Called whenever a borrow batch page is loaded for immediate UI updates
        """
        logger = logging.getLogger(__name__)
        today = timezone.now().astimezone().date()
        
        # 1. Mark pending/approved items as expired when return_date has passed
        expired_items = BorrowRequestItem.objects.filter(
            status__in=['pending', 'approved']
        ).filter(
            return_date__lt=today
        )
        
        if expired_items.exists():
            count = expired_items.count()
            
            # Unreserve quantities for each expired item
            for item in expired_items:
                if item.property:
                    # Reduce the reserved quantity
                    item.property.reserved_quantity = max(0, item.property.reserved_quantity - item.quantity)
                    item.property.save(update_fields=['reserved_quantity'])
                    item.property.update_availability()
                    logger.info(f"Unreserved {item.quantity} units of {item.property.property_name} (batch #{item.batch_request.id}, item #{item.id})")
            
            expired_items.update(status='expired')
            logger.info(f"Marked {count} borrow item(s) as expired and unreserved quantities")
        
        # 2. Mark pending batches as expired when latest return_date has passed
        pending_batches = cls.objects.filter(status='pending')
        
        for batch in pending_batches:
            if batch.latest_return_date and batch.latest_return_date < today:
                # Unreserve all quantities for items in this batch before marking as expired
                for item in batch.items.filter(status__in=['pending', 'approved']):
                    if item.property:
                        item.property.reserved_quantity = max(0, item.property.reserved_quantity - item.quantity)
                        item.property.save(update_fields=['reserved_quantity'])
                        item.property.update_availability()
                        logger.info(f"Unreserved {item.quantity} units of {item.property.property_name} from expired batch #{batch.id}")
                
                batch.status = 'expired'
                batch.save()
                logger.info(f"Marked batch #{batch.id} as expired and unreserved all quantities")
        
        # 3. Mark for_claiming/active batches as expired when latest return_date has passed
        # and mark their items as expired accordingly
        active_batches = cls.objects.filter(status__in=['for_claiming', 'active'])
        
        for batch in active_batches:
            if batch.latest_return_date and batch.latest_return_date < today:
                # Unreserve quantities only for items that haven't been returned yet
                for item in batch.items.filter(status__in=['pending', 'approved', 'active']):
                    if item.property:
                        item.property.reserved_quantity = max(0, item.property.reserved_quantity - item.quantity)
                        item.property.save(update_fields=['reserved_quantity'])
                        item.property.update_availability()
                        logger.info(f"Unreserved {item.quantity} units of {item.property.property_name} from expired batch #{batch.id}")
                    
                    # Mark item as expired if not already returned
                    if item.status != 'returned':
                        item.status = 'expired'
                        item.save()
                
                batch.status = 'expired'
                batch.save()
                logger.info(f"Marked active/for_claiming batch #{batch.id} as expired and unreserved all quantities")

class BorrowRequestItem(models.Model):
    """
    Individual property items within a batch borrow request.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
    ]
    
    batch_request = models.ForeignKey(BorrowRequestBatch, on_delete=models.CASCADE, related_name='items')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()  # Requested quantity
    approved_quantity = models.PositiveIntegerField(null=True, blank=True)  # Approved quantity
    return_date = models.DateField()  # Expected return date for this item
    actual_return_date = models.DateField(null=True, blank=True)  # Actual return date
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved = models.BooleanField(default=False)  # Keep for backward compatibility
    claimed_date = models.DateTimeField(null=True, blank=True)  # When item was claimed
    remarks = models.TextField(blank=True, null=True)
    near_overdue_notified = models.BooleanField(default=False)  # Track if near-overdue reminder was sent
    overdue_notified = models.BooleanField(default=False)  # Track if overdue SMS was sent

    class Meta:
        unique_together = ['batch_request', 'property']  # Prevent duplicate items in same batch

    def __str__(self):
        return f"{self.property.property_name} (x{self.quantity}) in Borrow Batch #{self.batch_request.id}"

    def save(self, *args, **kwargs):
        # Check if this is a new item or status is changing
        is_new = self.pk is None
        old_status = None
        old_quantity = None
        
        if not is_new:
            try:
                old_instance = BorrowRequestItem.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_quantity = old_instance.quantity
            except BorrowRequestItem.DoesNotExist:
                pass
        
        # Keep approved field in sync with status for backward compatibility
        self.approved = (self.status == 'approved')
        
        super().save(*args, **kwargs)
        
        # Handle reserved_quantity updates
        # NOTE: Borrow requests only reserve when APPROVED (not when pending)
        # This differs from reservations which reserve immediately when pending
        if is_new and self.status == 'approved':
            # New approved borrow request - reserve the quantity
            self.property.reserved_quantity += self.quantity
            self.property.save(update_fields=['reserved_quantity'])
        
        elif old_status and old_status != self.status:
            # Status changed
            if self.status == 'approved' and old_status == 'pending':
                # Pending -> Approved: NOW reserve the quantity
                self.property.reserved_quantity += self.quantity
                self.property.save(update_fields=['reserved_quantity'])
            
            elif self.status == 'rejected' and old_status == 'approved':
                # Rejected after approval: Release reserved quantity
                self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
                self.property.save(update_fields=['reserved_quantity'])
            
            elif self.status == 'rejected' and old_status == 'pending':
                # Rejected while pending: No reserved quantity to release
                pass
            
            elif self.status == 'active' and old_status == 'approved':
                # Approved -> Active (claimed): Only release reserved quantity
                # NOTE: Actual quantity deduction is handled in the claim view to prevent double deduction
                self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
                self.property.save(update_fields=['reserved_quantity'])
                self.property.update_availability()
            
            elif self.status == 'returned' and old_status in ['active', 'overdue']:
                # Returned: Quantity restoration is handled in the return view
                # NOTE: Do not add quantity here to prevent double addition
                self.property.update_availability()
            
            elif self.status == 'completed' and old_status == 'returned':
                # Returned -> Completed: No quantity change needed
                pass
        
        elif old_quantity and old_quantity != self.quantity and self.status == 'approved':
            # Quantity changed while approved - update reserved amount
            quantity_diff = self.quantity - old_quantity
            self.property.reserved_quantity = max(0, self.property.reserved_quantity + quantity_diff)
            self.property.save(update_fields=['reserved_quantity'])
    
    def delete(self, *args, **kwargs):
        # Release reserved quantity if item is deleted while approved (not pending)
        if self.status == 'approved':
            self.property.reserved_quantity = max(0, self.property.reserved_quantity - self.quantity)
            self.property.save(update_fields=['reserved_quantity'])
        super().delete(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Allow users to submit any quantity - validation happens during approval
        # No need to check available_quantity at submission time
        
        # Validate return date
        if self.return_date and self.return_date <= timezone.now().date():
            raise ValidationError({
                'return_date': 'Return date must be in the future.'
            })

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    remarks = models.TextField(blank=True, null=True) 
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"

class SupplyHistory(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # e.g., "quantity_update", "status_change", etc.
    field_name = models.CharField(max_length=100)  # The field that was changed
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)  # For additional context about the change
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_display = self.user.username if self.user else "Unknown User"  
        return f"{self.supply.supply_name} - {self.action} by {user_display} at {self.timestamp}"

class PropertyHistory(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # e.g., "condition_update", "availability_change", etc.
    field_name = models.CharField(max_length=100)  # The field that was changed
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)  # For additional context about the change
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_display = self.user.username if self.user else "Unknown User"  
        return f"{self.property.property_name} - {self.action} by {user_display} at {self.timestamp}"


class BadStockReport(models.Model):
    supply = models.ForeignKey(Supply, on_delete=models.CASCADE, related_name='bad_stock_reports')
    quantity_removed = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    remarks = models.TextField()  # Required detailed explanation including the reason
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bad_stock_reports')
    reported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"Bad Stock: {self.supply.supply_name} - {self.quantity_removed} units"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # For new reports, deduct inventory immediately
        if is_new:
            self.deduct_from_inventory()
        
        super().save(*args, **kwargs)
    
    def deduct_from_inventory(self):
        """Deduct the bad stock quantity from inventory and log the activity"""
        try:
            quantity_info = self.supply.quantity_info
            old_quantity = quantity_info.current_quantity
            
            if old_quantity < self.quantity_removed:
                raise ValueError(f"Cannot deduct {self.quantity_removed} units. Only {old_quantity} units available.")
            
            # Deduct the quantity (skip_history=True to prevent duplicate logging)
            quantity_info.current_quantity -= self.quantity_removed
            quantity_info.save(user=self.reported_by, skip_history=True)
            
            # Update supply's available_for_request status
            self.supply.available_for_request = (quantity_info.current_quantity > 0)
            self.supply.save(user=self.reported_by)
            
            # Create supply history entry (this is the only history entry we want)
            SupplyHistory.objects.create(
                supply=self.supply,
                user=self.reported_by,
                action='bad_stock_removal',
                field_name='quantity',
                old_value=str(old_quantity),
                new_value=str(quantity_info.current_quantity),
                remarks=f"Bad stock removed. Quantity deducted: {self.quantity_removed}. Reason: {self.remarks}"
            )
            
            # Create activity log
            ActivityLog.log_activity(
                user=self.reported_by,
                action='bad_stock',
                model_name='Supply',
                object_repr=str(self.supply),
                description=f"Removed {self.quantity_removed} units of '{self.supply.supply_name}' as bad stock. Quantity changed from {old_quantity} to {quantity_info.current_quantity}. Reason: {self.remarks}"
            )
            
        except SupplyQuantity.DoesNotExist:
            raise ValueError("Supply quantity information not found.")

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import date, datetime, timedelta
from django.utils import timezone


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
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
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

    def __str__(self):
        return self.user.username
    

class SupplyQuantity(models.Model):
    supply = models.OneToOneField('Supply', on_delete=models.CASCADE, related_name='quantity_info')
    current_quantity = models.PositiveIntegerField(default=0)
    minimum_threshold = models.PositiveIntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)

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
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    available_for_request = models.BooleanField(default=True)
    date_received = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Generate barcode if not set
        if not self.barcode and self.pk:
            self.barcode = f"SUP-{self.pk}"
        super().save(*args, **kwargs)

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
        # Update available_for_request based on quantity
        try:
            quantity_info = self.quantity_info
            self.available_for_request = (quantity_info.current_quantity > 0)
        except SupplyQuantity.DoesNotExist:
            # For new supplies, we'll set this after creating SupplyQuantity
            pass

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
    property_name = models.CharField(max_length=100)
    category = models.ForeignKey(PropertyCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    barcode = models.CharField(max_length=150, unique=True, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=50, null=True, blank=True)
    unit_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        validators=[MinValueValidator(0)]
    )
    overall_quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=0)
    location = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(max_length=100, choices=CONDITION_CHOICES, default='In good condition')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        # Only show property name and property number (if available), not barcode
        if self.property_number:
            return f"{self.property_name} ({self.property_number})"
        return self.property_name

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
        
        # If this is a new property or overall_quantity has changed
        if not self.pk or (self.pk and Property.objects.get(pk=self.pk).overall_quantity != self.overall_quantity):
            # Set the current quantity equal to overall_quantity if it's a new property
            # or if overall_quantity has been updated
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
            fields_to_track = ['property_number', 'property_name', 'category', 'description', 'barcode', 
                             'unit_of_measure', 'unit_value', 'overall_quantity', 'quantity', 
                             'location', 'condition', 'availability']
            
            for field in fields_to_track:
                old_value = getattr(old_obj, field)
                new_value = getattr(self, field)
                
                if old_value != new_value:
                    # Add specific remarks for quantity changes
                    remarks = None
                    if field in ['quantity', 'overall_quantity']:
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
                    message=f"New supply request submitted for {self.supply.supply_name} by {self.user.username}",
                    remarks=f"Quantity: {self.quantity}, Purpose: {self.purpose}"
                )

        # Update supply quantity when request is approved
        if old_status != self.status and self.status == 'approved':
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
                    message=f"New batch supply request submitted by {self.user.username}",
                    remarks=f"Items: {item_list}. Purpose: {self.purpose[:100]}"
                )

        # Update supply quantities when request is approved
        if old_status != self.status and self.status in ['approved', 'partially_approved']:
            for item in self.items.filter(status='approved'):
                try:
                    quantity_info = item.supply.quantity_info
                    if quantity_info.current_quantity >= item.quantity:
                        quantity_info.current_quantity -= item.quantity
                        quantity_info.save()
                        
                        # Save the supply to update available_for_request
                        item.supply.save()
                        
                        # Create notification for low stock if needed
                        if quantity_info.current_quantity <= quantity_info.minimum_threshold:
                            admin_users = User.objects.filter(userprofile__role='ADMIN')
                            
                            for admin_user in admin_users:
                                Notification.objects.create(
                                    user=admin_user,
                                    message=f"Supply '{item.supply.supply_name}' is running low on stock (Current: {quantity_info.current_quantity}, Minimum: {quantity_info.minimum_threshold})",
                                    remarks="Please restock soon."
                                )
                except SupplyQuantity.DoesNotExist:
                    pass

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

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),  # When the reservation period has started
        ('completed', 'Completed'),  # When the reservation period has ended
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Property, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reservation_date = models.DateTimeField(auto_now_add=True)  # when the reservation was made
    needed_date = models.DateField(null=True, blank=True)
    return_date = models.DateField()
    approved_date = models.DateTimeField(null=True, blank=True)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Reservation by {self.user.username} for {self.item.property_name}"

    def save(self, *args, **kwargs):
        # Check if this is a new reservation
        is_new = self.pk is None
        
        # Get the old instance if it exists
        try:
            old_instance = Reservation.objects.get(pk=self.pk)
            old_status = old_instance.status
        except Reservation.DoesNotExist:
            old_status = None

        # Save the reservation
        super().save(*args, **kwargs)
        
        # If this is a new reservation, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='ADMIN')
            for admin_user in admin_users:
                Notification.objects.create(
                    user=admin_user,
                    message=f"New reservation submitted for {self.item.property_name} by {self.user.username}",
                    remarks=f"Quantity: {self.quantity}, Needed Date: {self.needed_date}, Return Date: {self.return_date}, Purpose: {self.purpose}"
                )

        # Handle status changes
        if old_status != self.status:
            # When a reservation becomes active
            if self.status == 'active' and old_status in ['approved', None]:
                # Decrease the item's quantity
                self.item.quantity -= self.quantity
                self.item.save()
                
                # Notify the user
                Notification.objects.create(
                    user=self.user,
                    message=f"Your reservation for {self.item.property_name} is now active.",
                    remarks=f"Please collect your items. Return date: {self.return_date}"
                )
            
            # When a reservation is completed
            elif self.status == 'completed' and old_status == 'active':
                # Increase the item's quantity
                self.item.quantity += self.quantity
                self.item.save()
                
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
        
        # Update approved reservations to active when needed_date is reached
        approved_to_active = cls.objects.filter(
            status='approved',
            needed_date__lte=today,
            return_date__gte=today
        )
        for reservation in approved_to_active:
            reservation.status = 'active'
            reservation.save()
        
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
    image = models.ImageField(upload_to='report_images/', blank=True, null=True)

    def __str__(self):
        return f"Damage Report for {self.item.property_name}"

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
                    message=f"New damage report submitted for {self.item.property_name} by {self.user.username}",
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
        today = timezone.now().date()
        overdue_requests = cls.objects.filter(
            status='approved',
            return_date__lt=today
        )
        for request in overdue_requests:
            request.status = 'overdue'
            request.save()

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
        return f"{self.supply.supply_name} - {self.action} by {self.user.username} at {self.timestamp}"

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
        return f"{self.property.property_name} - {self.action} by {self.user.username} at {self.timestamp}"

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

class SupplyQuantity(models.Model):
    supply = models.OneToOneField('Supply', on_delete=models.CASCADE, related_name='quantity_info')
    current_quantity = models.PositiveIntegerField(default=0)
    minimum_threshold = models.PositiveIntegerField(default=10)
    original_quantity = models.PositiveIntegerField(null=True, blank=True)
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
            # For new supplies, set the original quantity
            self.original_quantity = self.current_quantity
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

class Supply(models.Model):
    STATUS_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('available', 'Available'),
    ]

    CATEGORY_CHOICES = [
        ('office_supplies', 'Office Supplies Expenses'),
        ('textbooks', 'Textbooks and Instructional Materials Expenses'),
        ('other_supplies', 'Other Supplies & Materials Expenses'),
    ]

    SUBCATEGORY_CHOICES = [
        ('common_office', 'COMMON OFFICE SUPPLIES AND MATERIALS'),
        ('filing', 'FILING SUPPLIES AND MATERIALS'),
        ('ribbons', 'RIBBONS, INKS, TONERS AND CARTRIDGES'),
        ('paper', 'PAPER PRODUCTS'),
        ('university_activity', 'OTHER UNIVERSITY ACTIVITY 1 (CSG Activity)'),
        ('printed_journals', 'PRINTED JOURNALS'),
        ('common_cleaning', 'COMMON CLEANING SUPPLIES AND MATERIALS'),
        ('other_supplies', 'OTHER SUPPLIES AND MATERIALS'),
        ('electrical', 'ELECTRICAL, LIGHTING FIXTURES, TOOLS AND ACCESSORIES'),
        ('kitchen', 'KITCHEN SUPPLIES AND MATERIALS'),
        ('common_office_supplies', 'COMMON OFFICE SUPPLIES'),
        ('cleaning_supplies', 'CLEANING SUPPLIES AND MATERIALS'),
        ('covid_supplies', 'COVID RECOVERY SUPPLIES'),
        ('electrical_supplies', 'ELECTRICAL SUPPLIES AND MATERIALS'),
    ]

    supply_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, null=True, blank=True)
    subcategory = models.CharField(max_length=100, choices=SUBCATEGORY_CHOICES, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    barcode = models.CharField(max_length=100, unique=True)
    available_for_request = models.BooleanField(default=True)
    date_received = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

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
        admin_users = User.objects.filter(userprofile__role='admin')
        
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
        ]

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

    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('not_available', 'Not Available'),
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
    original_quantity = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(max_length=100, choices=CONDITION_CHOICES, blank=True, null=True)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')

    def __str__(self):
        return f"{self.property_name} - {self.barcode}"

    def update_availability(self):
        """Update availability based on quantity"""
        is_available = self.quantity > 0
        if is_available and self.availability == 'not_available':
            self.availability = 'available'
            self.save()
        elif not is_available and self.availability == 'available':
            self.availability = 'not_available'
            self.save()

    def save(self, *args, **kwargs):
        # Get the user from kwargs
        user = kwargs.pop('user', None)

        # Check if this is a new property (being created)
        is_new = self.pk is None

        if is_new:
            # For new properties, set the original quantity
            self.original_quantity = self.quantity
            # Set initial availability based on quantity
            self.availability = 'available' if self.quantity > 0 else 'not_available'
            # Save first to get the ID
            super().save(*args, **kwargs)
            # Create a history entry for the initial quantity
            if self.quantity is not None:
                PropertyHistory.objects.create(
                    property=self,
                    user=user,
                    action='create',
                    field_name='initial_quantity',
                    old_value=None,
                    new_value=str(self.quantity),
                    remarks=f"Initial quantity set to {self.quantity}"
                )
        else:
            # For existing properties, track changes
            old_obj = Property.objects.get(pk=self.pk)
            fields_to_track = ['property_name', 'category', 'description', 'barcode', 'unit_of_measure', 
                             'unit_value', 'quantity', 'location', 'condition', 'availability']
            
            for field in fields_to_track:
                old_value = getattr(old_obj, field)
                new_value = getattr(self, field)
                
                # Convert values to strings for comparison, handling None and empty values
                old_str = str(old_value) if old_value not in [None, ''] else ''
                new_str = str(new_value) if new_value not in [None, ''] else ''
                
                # Only create history entry if the values are actually different
                if old_str != new_str:
                    remarks = None
                    if field == 'quantity':
                        change = (new_value or 0) - (old_value or 0)
                        if change > 0:
                            remarks = f"Quantity increased by {abs(change)}"
                        else:
                            remarks = f"Quantity decreased by {abs(change)}"

                    PropertyHistory.objects.create(
                        property=self,
                        user=user,
                        action='update',
                        field_name=field,
                        old_value=old_str if old_str else None,
                        new_value=new_str if new_str else None,
                        remarks=remarks
                    )

            super().save(*args, **kwargs)
            
            # Update availability based on quantity after save
            if old_obj.quantity != self.quantity:
                self.update_availability()

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
            admin_users = User.objects.filter(userprofile__role='admin')
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
                        admin_users = User.objects.filter(userprofile__role='admin')
                        
                        for admin_user in admin_users:
                            Notification.objects.create(
                                user=admin_user,
                                message=f"Supply '{self.supply.supply_name}' is running low on stock (Current: {quantity_info.current_quantity}, Minimum: {quantity_info.minimum_threshold})",
                                remarks="Please restock soon."
                            )
            except SupplyQuantity.DoesNotExist:
                pass

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
            admin_users = User.objects.filter(userprofile__role='admin')
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

    def __str__(self):
        return f"Damage Report for {self.item.property_name}"

    def save(self, *args, **kwargs):
        # Check if this is a new damage report
        is_new = self.pk is None
        
        # Save the damage report
        super().save(*args, **kwargs)
        
        # If this is a new damage report, notify admin users
        if is_new:
            admin_users = User.objects.filter(userprofile__role='admin')
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

    def __str__(self):
        return f"Request by {self.user.username} for {self.property.property_name}"

    def save(self, *args, **kwargs):
        # Check if this is a new borrow request
        is_new = self.pk is None

        if is_new:
            super().save(*args, **kwargs)
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
                    
                    # Update property availability based on new quantity
                    self.property.update_availability()

                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} has been approved.",
                        remarks=self.remarks if self.remarks else None
                    )

                if self.status == 'returned' and old_status in ['approved', 'overdue']:
                    # Increase the property's quantity
                    self.property.quantity += self.quantity
                    self.property.save()
                    
                    # Update property availability based on new quantity
                    self.property.update_availability()

                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrowed {self.property.property_name} has been marked as returned.",
                        remarks=self.remarks if self.remarks else None
                    )

                if self.status == 'declined' and old_status == 'pending':
                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} has been declined.",
                        remarks=self.remarks if self.remarks else None
                    )

                if self.status == 'overdue' and old_status == 'approved':
                    # Notify the user
                    Notification.objects.create(
                        user=self.user,
                        message=f"Your borrow request for {self.property.property_name} is overdue.",
                        remarks=self.remarks if self.remarks else None
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
        return f"{self.property.property_name} - {self.action} by {self.user.username} at {self.timestamp}"

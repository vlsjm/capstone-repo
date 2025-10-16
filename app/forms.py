from django import forms
from django.core.exceptions import ValidationError
from .models import Property, Supply, SupplyQuantity, SupplyCategory, SupplySubcategory, BadStockReport
from django.contrib.auth.models import User
from .models import UserProfile, SupplyRequest, BorrowRequest, DamageReport, Reservation, Department,PropertyCategory, SupplyRequestBatch, SupplyRequestItem, Supply, SupplyQuantity
from datetime import date
import os

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department name',
                'maxlength': 100
            })
        }


class PropertyCategoryForm(forms.ModelForm):
    class Meta:
        model = PropertyCategory
        fields = ['name', 'uacs']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
                'maxlength': 100,
                'required': True
            }),
            'uacs': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter UACS code (e.g., 13124324)',
                'min': 0
            })
        }
        labels = {
            'name': 'Category Name',
            'uacs': 'UACS'
        }
        help_texts = {
            'uacs': 'Unified Account Code Structure (optional)'
        }


class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'department-select form-control'})
    )
    phone = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'department', 'phone']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'property_number',
            'property_name',
            'category',
            'description',
            'unit_of_measure',
            'unit_value',
            'overall_quantity',
            'quantity',
            'quantity_per_physical_count',
            'location',
            'accountable_person',
            'year_acquired',
            'condition',
            'availability',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'property_number': forms.TextInput(attrs={'placeholder': 'Enter unique property number'}),
            'unit_value': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'overall_quantity': forms.NumberInput(attrs={'min': 0}),
            'quantity': forms.NumberInput(attrs={'min': 0, 'readonly': True}),
            'quantity_per_physical_count': forms.NumberInput(attrs={'min': 0}),
            'category': forms.Select(attrs={'class': 'select2'}), 
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'availability': forms.Select(attrs={'class': 'form-select'}),
            'accountable_person': forms.TextInput(attrs={'placeholder': 'Enter accountable person name'}),
            'year_acquired': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set required fields
        for field in ['property_name', 'description', 'unit_of_measure', 
                      'unit_value', 'overall_quantity', 'location', 'condition', 'category']:
            self.fields[field].required = True

        self.fields['property_number'].required = False
        self.fields['accountable_person'].required = False
        self.fields['year_acquired'].required = False
        self.fields['quantity_per_physical_count'].required = False

        # Handle quantity logic
        if not self.instance.pk:
            self.fields['quantity'].required = False
            self.fields['quantity'].widget.attrs['disabled'] = True
        else:
            self.fields['quantity'].required = True
            self.fields['quantity'].widget.attrs['readonly'] = True

        # Optional: reorder categories or set placeholder
        self.fields['category'].queryset = PropertyCategory.objects.all().order_by('name')
        self.fields['category'].empty_label = "Select a category"

    def clean(self):
        cleaned_data = super().clean()
        overall_quantity = cleaned_data.get('overall_quantity')
        quantity = cleaned_data.get('quantity')

        if not self.instance.pk:
            cleaned_data['quantity'] = overall_quantity
        elif overall_quantity is not None and quantity is not None:
            if quantity > overall_quantity:
                self.add_error('overall_quantity', 'Overall quantity cannot be less than current quantity.')

        return cleaned_data
    
    def clean_property_number(self):
        property_number = self.cleaned_data.get('property_number')
        if property_number:
            return property_number.upper()
        return property_number

class PropertyNumberChangeForm(forms.ModelForm):
    new_property_number = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new property number'
        })
    )
    
    class Meta:
        model = Property
        fields = ['new_property_number']
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # Add current property number as readonly field for reference
        if self.instance and self.instance.property_number:
            self.fields['current_property_number'] = forms.CharField(
                initial=self.instance.property_number,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False,
                label='Current Property Number'
            )
    
    def clean_new_property_number(self):
        new_property_number = self.cleaned_data['new_property_number']
        
        # Convert to uppercase if it has characters
        if new_property_number:
            new_property_number = new_property_number.upper()
        
        # Check if the new property number already exists (excluding current property)
        existing = Property.objects.filter(property_number=new_property_number)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise ValidationError(f'Property number "{new_property_number}" already exists.')
        
        return new_property_number
    
    def save(self, commit=True, user=None):
        if commit:
            # Store old property number before changing
            old_number = self.instance.property_number
            self.instance.property_number = self.cleaned_data['new_property_number']
            
            # The model's save method will handle storing the old number in old_property_number
            if user:
                self.instance.save(user=user)
            else:
                self.instance.save()
                
        return self.instance

class SupplyForm(forms.ModelForm):
    current_quantity = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    minimum_threshold = forms.IntegerField(min_value=0, initial=10, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Supply
        fields = [
            'supply_name',
            'category',
            'subcategory',
            'description',
            'available_for_request',
            'date_received',
            'expiration_date'
        ]
        widgets = {
            'supply_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_received': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': False}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control custom-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-control custom-select'}),
            'available_for_request': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'expiration_date': 'Optional. Leave empty if the supply does not expire.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up category field
        self.fields['category'].queryset = SupplyCategory.objects.all().order_by('name')
        self.fields['category'].empty_label = "Select a category"
        
        # Set up subcategory field - now independent of category
        self.fields['subcategory'].queryset = SupplySubcategory.objects.all().order_by('name')
        self.fields['subcategory'].empty_label = "Select a subcategory"

        # Set required fields
        for field in self.fields.values():
            field.required = True
        # Make description and expiration_date optional
        self.fields['description'].required = False
        self.fields['expiration_date'].required = False
        
        # Set initial values for quantity fields if editing existing supply
        if self.instance.pk:
            try:
                quantity_info = self.instance.quantity_info
                self.fields['current_quantity'].initial = quantity_info.current_quantity
                self.fields['minimum_threshold'].initial = quantity_info.minimum_threshold
            except SupplyQuantity.DoesNotExist:
                pass

    def save(self, commit=True):
        supply = super().save(commit=False)  # Always use commit=False here
        
        if commit:
            supply.save()
            # Only create/update quantity info if we're committing
            quantity_info, created = SupplyQuantity.objects.get_or_create(
                supply=supply,
                defaults={
                    'current_quantity': self.cleaned_data['current_quantity'],
                    'minimum_threshold': self.cleaned_data['minimum_threshold']
                }
            )
            
            if not created:
                quantity_info.current_quantity = self.cleaned_data['current_quantity']
                quantity_info.minimum_threshold = self.cleaned_data['minimum_threshold']
                quantity_info.save()
        
        return supply

class SupplyRequestForm(forms.ModelForm):
    class Meta:
        model = SupplyRequest
        fields = ['supply', 'quantity', 'purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show supplies that are available for request and have stock
        self.fields['supply'].queryset = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        )
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        supply = self.cleaned_data.get('supply')
        
        if supply and quantity:
            available_quantity = supply.quantity_info.current_quantity
            if quantity > available_quantity:
                raise forms.ValidationError(f"Only {available_quantity} units available.")
        
        return quantity


class SupplyRequestBatchForm(forms.ModelForm):
    """Form for creating a batch supply request (cart functionality)"""
    class Meta:
        model = SupplyRequestBatch
        fields = ['purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Please describe the purpose of this request...'
            }),
        }

class SupplyRequestItemForm(forms.Form):
    """Form for adding individual items to the cart"""
    supply = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'supply-select',
            'data-placeholder': 'Select a supply item...'
        }),
        empty_label="Select a supply item..."
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'quantity-input',
            'placeholder': 'Enter quantity'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show supplies that are available for request and have stock
        self.fields['supply'].queryset = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        ).select_related('quantity_info')

    def clean(self):
        cleaned_data = super().clean()
        supply = cleaned_data.get('supply')
        quantity = cleaned_data.get('quantity')
        
        if supply and quantity:
            try:
                available_quantity = supply.quantity_info.current_quantity
                if quantity > available_quantity:
                    raise forms.ValidationError(
                        f"Only {available_quantity} units of {supply.supply_name} are available."
                    )
            except SupplyQuantity.DoesNotExist:
                raise forms.ValidationError(
                    f"Supply {supply.supply_name} has no quantity information."
                )
        
        return cleaned_data


class BorrowRequestForm(forms.ModelForm):
    class Meta:
        model = BorrowRequest
        fields = ['property', 'quantity', 'return_date', 'purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show properties that are available
        self.fields['property'].queryset = Property.objects.filter(availability='available')

    def clean_return_date(self):
        return_date = self.cleaned_data.get('return_date')
        if return_date and return_date < date.today():
            raise forms.ValidationError("Return date cannot be in the past.")
        return return_date

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        property_item = self.cleaned_data.get('property')
        
        if property_item and quantity:
            if quantity > property_item.quantity:
                raise forms.ValidationError(f"Only {property_item.quantity} units available.")
        
        return quantity


class DamageReportForm(forms.ModelForm):
    class Meta:
        model = DamageReport
        fields = ['item', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control-file'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (limit to 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large. Please keep it under 5MB.")
            
            # Check file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = os.path.splitext(image.name)[1].lower()
            if file_extension not in valid_extensions:
                raise ValidationError("Please upload a valid image file (JPG, PNG, GIF, BMP, WebP).")
        
        return image


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['item', 'purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }


class AdminProfileUpdateForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        }),
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    
    # Password change fields
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password'
        }),
        help_text="Required to change password"
    )
    
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Pre-populate fields with current user data
        if not kwargs.get('data'):
            self.initial['username'] = user.username
            self.initial['first_name'] = user.first_name
            self.initial['last_name'] = user.last_name
            self.initial['email'] = user.email
            
            # Get phone from UserProfile if exists
            user_profile = getattr(user, 'userprofile', None)
            if user_profile:
                self.initial['phone'] = user_profile.phone
    
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        
        # Check if username is already taken by another user
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        
        # Validate username format (Django's default validation)
        import re
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError("Username may only contain letters, numbers, and @/./+/-/_ characters.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name or not first_name.strip():
            raise forms.ValidationError("First name is required.")
        return first_name.strip()
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name or not last_name.strip():
            raise forms.ValidationError("Last name is required.")
        return last_name.strip()
    
    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # If any password field is filled, all password fields are required
        password_fields_filled = any([current_password, new_password, confirm_password])
        
        if password_fields_filled:
            if not current_password:
                self.add_error('current_password', 'Current password is required to change password.')
            elif not self.user.check_password(current_password):
                self.add_error('current_password', 'Current password is incorrect.')
            
            if not new_password:
                self.add_error('new_password', 'New password is required.')
            elif len(new_password) < 8:
                self.add_error('new_password', 'Password must be at least 8 characters long.')
            
            if not confirm_password:
                self.add_error('confirm_password', 'Please confirm your new password.')
            elif new_password != confirm_password:
                self.add_error('confirm_password', 'New passwords do not match.')
        
        return cleaned_data

class BadStockReportForm(forms.ModelForm):
    class Meta:
        model = BadStockReport
        fields = ['supply', 'quantity_removed', 'remarks']
        widgets = {
            'supply': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'quantity_removed': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quantity to remove',
                'min': 1,
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Provide detailed explanation including the reason (e.g., damaged, expired, defective, lost, etc.)',
                'rows': 4,
                'required': True
            })
        }
        labels = {
            'supply': 'Supply Item',
            'quantity_removed': 'Quantity to Remove',
            'remarks': 'Reason and Remarks'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter supplies to show only non-archived supplies with quantity > 0
        self.fields['supply'].queryset = Supply.objects.filter(
            is_archived=False
        ).select_related('quantity_info').order_by('supply_name')
    
    def clean(self):
        cleaned_data = super().clean()
        supply = cleaned_data.get('supply')
        quantity_removed = cleaned_data.get('quantity_removed')
        
        if supply and quantity_removed:
            try:
                available_quantity = supply.quantity_info.current_quantity
                if quantity_removed > available_quantity:
                    self.add_error('quantity_removed', 
                        f'Cannot remove {quantity_removed} units. Only {available_quantity} units available.')
            except SupplyQuantity.DoesNotExist:
                self.add_error('supply', 'This supply has no quantity information.')
        
        return cleaned_data

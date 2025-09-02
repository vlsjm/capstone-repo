from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from app.models import SupplyRequest, Reservation, DamageReport, BorrowRequest, Supply, Property, UserProfile
from datetime import date
import os

class BorrowForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'
    
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'id_return_date',
            'min': date.today().isoformat()  # Set minimum date to today
        }),
        label="Expected Return Date",
        error_messages={
            'required': 'Return date is required.',
        }
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Purpose / Reason"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show properties that are available
        self.fields['property'].queryset = Property.objects.filter(availability='available')
        self.fields['property'].widget.attrs.update({'class': 'select2'})
        # Update the min date attribute dynamically
        self.fields['return_date'].widget.attrs['min'] = date.today().isoformat()

    def clean_return_date(self):
        return_date = self.cleaned_data.get('return_date')
        today = date.today()
        if return_date and return_date < today:
            raise forms.ValidationError("Return date cannot be in the past.")
        return return_date

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        property_obj = self.cleaned_data.get('property')
        
        if not property_obj:
            raise forms.ValidationError("Please select a property to borrow.")
            
        if not quantity or quantity < 1:
            raise forms.ValidationError("Please enter a valid quantity (minimum 1).")
        
        available_quantity = property_obj.quantity if property_obj.quantity is not None else 0
        if available_quantity == 0:
            raise forms.ValidationError("This item is currently not available for borrowing.")
        if quantity > available_quantity:
            raise forms.ValidationError(f"Cannot borrow more than available quantity. Only {available_quantity} units available.")
        
        return quantity

    class Meta:
        model = BorrowRequest
        fields = ['property', 'quantity', 'return_date', 'purpose']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

class SupplyRequestForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'
    
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Purpose / Reason"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show supplies that are available for request and have stock
        self.fields['supply'].queryset = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        )
        self.fields['supply'].widget.attrs.update({'class': 'select2'})
        self.fields['supply'].widget.attrs.update({'class': 'select2'})
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        supply = self.cleaned_data.get('supply')
        
        if supply and quantity:
            available_quantity = supply.quantity_info.current_quantity
            if quantity > available_quantity:
                raise forms.ValidationError(f"Only {available_quantity} units available.")
        
        return quantity
    
    class Meta:
        model = SupplyRequest
        fields = ['supply', 'quantity', 'purpose']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

class ReservationForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'

    needed_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'id_needed_date',
            'min': date.today().isoformat()  # Set minimum date to today
        }),
        label="Needed date",
        error_messages={
            'required': 'Needed date is required.',
        }
    )
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'id_return_date',
            'min': date.today().isoformat()  # Set minimum date to today
        }),
        label="Return date",
        error_messages={
            'required': 'Return date is required.',
        }
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1}),
        error_messages={
            'required': 'Quantity is required.',
            'min_value': 'Quantity must be at least 1.',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update the min date attributes dynamically
        today = date.today().isoformat()
        self.fields['needed_date'].widget.attrs['min'] = today
        self.fields['return_date'].widget.attrs['min'] = today

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        quantity = cleaned_data.get('quantity')
        needed_date = cleaned_data.get('needed_date')
        return_date = cleaned_data.get('return_date')

        if all([item, quantity, needed_date, return_date]):
            # Check if the requested quantity is available for the item
            if quantity > item.quantity:
                raise forms.ValidationError(f"Only {item.quantity} units available for {item.property_name}")

            # Check for overlapping approved reservations
            overlapping_reservations = Reservation.objects.filter(
                item=item,
                status='approved',
                needed_date__lte=return_date,
                return_date__gte=needed_date
            ).exclude(pk=self.instance.pk if self.instance else None)

            # Calculate total quantity reserved for the overlapping period
            total_reserved = sum(r.quantity for r in overlapping_reservations)
            available_quantity = item.quantity - total_reserved

            if quantity > available_quantity:
                if available_quantity <= 0:
                    raise forms.ValidationError(
                        f"This item is fully booked during the requested period ({needed_date} to {return_date})"
                    )
                else:
                    raise forms.ValidationError(
                        f"Only {available_quantity} units available during the requested period ({needed_date} to {return_date})"
                    )

        return cleaned_data

    def clean_needed_date(self):
        needed_date = self.cleaned_data.get('needed_date')
        today = date.today()
        if needed_date and needed_date < today:
            raise forms.ValidationError("Needed date cannot be in the past.")
        return needed_date

    def clean_return_date(self):
        return_date = self.cleaned_data.get('return_date')
        needed_date = self.cleaned_data.get('needed_date')
        today = date.today()
        
        if return_date and return_date < today:
            raise forms.ValidationError("Return date cannot be in the past.")
        
        if needed_date and return_date and return_date < needed_date:
            raise forms.ValidationError("Return date must be after the needed date.")
            
        return return_date

    class Meta:
        model = Reservation
        fields = ['item', 'quantity', 'needed_date', 'return_date', 'purpose']
        widgets = {
            'item': forms.Select(attrs={'class': 'select2'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }

class DamageReportForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'

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
        labels = {
            'image': 'Attach Image (Optional)',
        }
        help_texts = {
            'image': 'Upload an image to support your damage report (JPG, PNG, etc.)',
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

class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        }),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        }),
        label='Last Name'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'yourname@gmail.com'
        }),
        label='Email account'
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Add number'
        }),
        label='Mobile number'
    )
    
    # Password change fields
    current_password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        }),
        label='Current Password',
        help_text='Leave blank if you don\'t want to change your password'
    )
    new_password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        label='New Password'
    )
    confirm_password = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )

    class Meta:
        model = UserProfile
        fields = ['phone']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.user:
            # Check if email is already taken by another user
            existing_user = User.objects.filter(email=email).exclude(pk=self.user.pk).first()
            if existing_user:
                raise ValidationError("This email address is already in use.")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise ValidationError("First name is required.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise ValidationError("Last name is required.")
        return last_name

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        # Password change validation
        if any([current_password, new_password, confirm_password]):
            if not current_password:
                raise ValidationError("Current password is required to change password.")
            
            if not self.user.check_password(current_password):
                raise ValidationError("Current password is incorrect.")
            
            if not new_password:
                raise ValidationError("New password is required.")
            
            if new_password != confirm_password:
                raise ValidationError("New passwords do not match.")
            
            if len(new_password) < 8:
                raise ValidationError("New password must be at least 8 characters long.")

        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            # Update User model fields
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            
            # Change password if provided
            new_password = self.cleaned_data.get('new_password')
            if new_password:
                self.user.set_password(new_password)
            
            if commit:
                self.user.save()
                profile.save()
        return profile
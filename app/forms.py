from django import forms
from .models import Property, Supply, SupplyQuantity, SupplyCategory, SupplySubcategory
from django.contrib.auth.models import User
from .models import UserProfile, SupplyRequest, BorrowRequest, DamageReport, Reservation, Department,PropertyCategory
from datetime import date

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
            'location',
            'condition',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'property_number': forms.TextInput(attrs={'placeholder': 'Enter unique property number'}),
            'unit_value': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'overall_quantity': forms.NumberInput(attrs={'min': 0}),
            'quantity': forms.NumberInput(attrs={'min': 0, 'readonly': True}),
            'category': forms.Select(attrs={'class': 'select2'}), 
            'condition': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set required fields
        for field in ['property_name', 'description', 'unit_of_measure', 
                      'unit_value', 'overall_quantity', 'location', 'condition', 'category']:
            self.fields[field].required = True

        self.fields['property_number'].required = False

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
        fields = ['item', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['item', 'purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }
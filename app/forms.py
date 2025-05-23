from django import forms
from .models import Property, Supply
from django.contrib.auth.models import User
from .models import UserProfile

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
            'property_name',
            'category',
            'description',
            'barcode',
            'unit_of_measure',
            'unit_value',
            'quantity',
            'location',
            'condition',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def init(self, args, **kwargs):
        super().init(args, kwargs)
        for field in self.fields.values():
            field.required = True

class SupplyForm(forms.ModelForm):
    class Meta:
        model = Supply
        fields = ['supply_name', 'quantity', 'date_received', 'barcode', 'category', 'status', 'available_for_request']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'available_for_request': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
        }

    def init(self, *args, kwargs):
        super().init(*args, **kwargs)
        for field in self.fields.values():
            field.required = True
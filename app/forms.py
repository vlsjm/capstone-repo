# app/forms.py

from django import forms
from .models import Property, Supply

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['property_name', 'quantity', 'date_acquired', 'barcode', 'condition', 'availability', 'assigned_to', 'available_for_request']
        widgets = {
            'date_acquired': forms.DateInput(attrs={'type': 'date'}),
            'available_for_request': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
        }

class SupplyForm(forms.ModelForm):
    class Meta:
        model = Supply
        fields = ['supply_name', 'quantity', 'date_received', 'barcode', 'category', 'status', 'available_for_request']
        widgets = {
            'date_received': forms.DateInput(attrs={'type': 'date'}),
            'available_for_request': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
        }

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'property_name', 'quantity', 'date_acquired', 'barcode',
            'condition', 'availability', 'assigned_to', 'available_for_request'
        ]
        widgets = {
            'date_acquired': forms.DateInput(attrs={'type': 'date'}),
        }

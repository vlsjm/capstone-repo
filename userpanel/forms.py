from django import forms
from django.utils import timezone
from app.models import SupplyRequest, Reservation, DamageReport, BorrowRequest, Supply, Property
from datetime import date

class BorrowForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'
    
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'id_return_date'
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
    
    def clean_return_date(self):
        return_date = self.cleaned_data.get('return_date')
        today = date.today()
        if return_date and return_date < today:
            raise forms.ValidationError("Return date cannot be in the past.")
        return return_date

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
            'id': 'id_needed_date'
        }),
        label="Needed date",
        error_messages={
            'required': 'Needed date is required.',
        }
    )
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'id_return_date'
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

    class Meta:
        model = Reservation
        fields = ['item', 'quantity', 'needed_date', 'return_date', 'purpose']
        widgets = {
            'item': forms.Select(attrs={'class': 'select2'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }

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

class DamageReportForm(forms.ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'

    class Meta:
        model = DamageReport
        fields = ['item', 'description']
from django import forms
from app.models import SupplyRequest, Reservation, DamageReport, BorrowRequest

class BorrowForm(forms.ModelForm):
    return_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expected Return Date"
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Purpose / Reason"
    )
    
    class Meta:
        model = BorrowRequest
        fields = ['property', 'quantity', 'return_date', 'purpose']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

class SupplyRequestForm(forms.ModelForm):
    class Meta:
        model = SupplyRequest
        fields = ['supply', 'quantity', 'purpose']

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['item', 'quantity', 'needed_date', 'return_date', 'purpose']
        widgets = {
            'needed_date': forms.DateInput(attrs={'type': 'date'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }


class DamageReportForm(forms.ModelForm):
    class Meta:
        model = DamageReport
        fields = ['item', 'description']

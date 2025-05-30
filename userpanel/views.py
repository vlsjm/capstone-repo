from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm, SupplyRequest, BorrowRequest, Reservation, DamageReport
from django.contrib.auth.views import LoginView
from app.models import UserProfile, Notification, Property, ActivityLog
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json



class UserBorrowView( PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_borrow.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = BorrowForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = BorrowForm(request.POST)
        if form.is_valid():
            borrow_request = form.save(commit=False)
            borrow_request.user = request.user
            borrow_request.status = 'pending'  # default status
            borrow_request.save()

            # Log the borrow request activity
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='BorrowRequest',
                object_repr=str(borrow_request.property.property_name),
                description=f"Requested to borrow {borrow_request.quantity} units of {borrow_request.property.property_name}"
            )

            messages.success(request, 'Borrow request submitted successfully.')
            return redirect('user_borrow')
        return render(request, self.template_name, {'form': form})


class UserRequestView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_request.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = SupplyRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SupplyRequestForm(request.POST)
        if form.is_valid():
            supply_request = form.save(commit=False)
            supply_request.user = request.user
            supply_request.save()

            # Log the supply request activity
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='SupplyRequest',
                object_repr=str(supply_request.supply.supply_name),
                description=f"Requested {supply_request.quantity} units of {supply_request.supply.supply_name}"
            )

            messages.success(request, 'Supply request submitted successfully.')
            return redirect('user_request')
        return render(request, self.template_name, {'form': form})


class UserReserveView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_reserve.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = ReservationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()

            # Log the reservation activity
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='Reservation',
                object_repr=str(reservation.item.property_name),
                description=f"Reserved {reservation.quantity} units of {reservation.item.property_name} from {reservation.needed_date} to {reservation.return_date}"
            )

            messages.success(request, 'Reservation submitted successfully.')
            return redirect('user_reserve')
        return render(request, self.template_name, {'form': form})


class UserReportView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_report.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = DamageReportForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = DamageReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()

            # Log the damage report activity
            ActivityLog.log_activity(
                user=request.user,
                action='report',
                model_name='DamageReport',
                object_repr=str(report.item.property_name),
                description=f"Reported damage for {report.item.property_name}: {report.description[:100]}..."
            )

            messages.success(request, 'Damage report submitted successfully.')
            return redirect('user_report')
        return render(request, self.template_name, {'form': form})


class UserLoginView(LoginView):
    template_name = 'registration/user_login.html'

    def get_success_url(self):
        return reverse_lazy('user_dashboard')  

    def form_valid(self, form):
        user = form.get_user()

        try:
            profile = UserProfile.objects.get(user=user)
            if profile.role == 'ADMIN':
                messages.error(self.request, 'Access denied. Please use the admin login.')
                return self.form_invalid(form)
            
            if profile.role not in ['ADMIN', 'USER']:
                messages.error(self.request, 'Access denied. Invalid user role.')
                return self.form_invalid(form)

            # Log successful login
            ActivityLog.log_activity(
                user=user,
                action='login',
                model_name='User',
                object_repr=user.username,
                description=f"User {user.username} logged in to user panel"
            )

        except UserProfile.DoesNotExist:
            messages.error(self.request, 'User profile not found.')
            return self.form_invalid(form)

        return super().form_valid(form)


class UserDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_dashboard.html'
    permission_required = 'app.view_user_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Notifications
        user_notifications = Notification.objects.filter(user=user).order_by('-timestamp')
        unread_notifications = user_notifications.filter(is_read=False)

        # Request History
        request_history = SupplyRequest.objects.filter(user=user).order_by('-request_date')
        request_history_data = [{
            'item': req.supply.supply_name,
            'quantity': req.quantity,
            'status': req.get_status_display(),
            'date': req.request_date,
            'purpose': req.purpose
        } for req in request_history]

        # Borrow History
        borrow_history = BorrowRequest.objects.filter(user=user).order_by('-borrow_date')
        borrow_history_data = [{
            'item': borrow.property.property_name,
            'quantity': borrow.quantity,
            'status': borrow.get_status_display(),
            'borrow_date': borrow.borrow_date,
            'return_date': borrow.return_date
        } for borrow in borrow_history]

        # Reservation History
        reservation_history = Reservation.objects.filter(user=user).order_by('-reservation_date')
        reservation_history_data = [{
            'item': res.item.property_name,
            'quantity': res.quantity,
            'status': res.get_status_display(),
            'needed_date': res.needed_date,
            'return_date': res.return_date,
            'purpose': res.purpose
        } for res in reservation_history]

        # Damage Report History
        damage_history = DamageReport.objects.filter(user=user).order_by('-report_date')
        damage_history_data = [{
            'item': report.item.property_name,
            'status': report.get_status_display(),
            'date': report.report_date,
            'description': report.description
        } for report in damage_history]

        # Add to context
        context.update({
            'notifications': user_notifications,
            'unread_count': unread_notifications.count(),
            'request_history': request_history_data,
            'borrow_history': borrow_history_data,
            'reservation_history': reservation_history_data,
            'damage_history': damage_history_data,
        })

        return context


def get_item_availability(request):
    """API endpoint to get item availability data for the calendar"""
    item_id = request.GET.get('item_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([item_id, start_date, end_date]):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        item = Property.objects.get(id=item_id)
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get all approved reservations for this item in the date range
        reservations = Reservation.objects.filter(
            item=item,
            status__in=['approved', 'active'],
            needed_date__lte=end_date,
            return_date__gte=start_date
        )
        
        # Create a day-by-day availability map
        availability_map = {}
        current_date = start_date
        while current_date <= end_date:
            # Get reservations active on this date
            date_reservations = reservations.filter(
                needed_date__lte=current_date,
                return_date__gte=current_date
            )
            
            # Calculate total quantity reserved for this date
            total_reserved = sum(r.quantity for r in date_reservations)
            available_quantity = item.quantity - total_reserved
            
            availability_map[current_date.isoformat()] = {
                'available': available_quantity > 0,
                'quantity': available_quantity,
                'total_quantity': item.quantity,
                'reserved_quantity': total_reserved
            }
            
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'item_name': item.property_name,
            'availability': availability_map
        })
        
    except Property.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

        
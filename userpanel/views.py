from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm, SupplyRequest, BorrowRequest, Reservation, DamageReport
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView
from app.models import UserProfile, Notification, Property, ActivityLog, Supply, SupplyRequestBatch, SupplyRequestItem
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST



class UserRequestView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_request.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        # Get cart items from session
        cart_items = request.session.get('supply_cart', [])
        
        # Get available supplies
        available_supplies = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        ).select_related('quantity_info')
        
        # Get recent batch requests (new system)
        recent_batch_requests = SupplyRequestBatch.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        # Get recent single requests (legacy system) 
        recent_single_requests = SupplyRequest.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        # Combine and format recent requests
        recent_requests_data = []
        
        # Add batch requests
        for req in recent_batch_requests:
            items_text = f"{req.total_items} items"
            if req.total_items <= 3:
                items_list = ", ".join([f"{item.supply.supply_name} (x{item.quantity})" for item in req.items.all()])
                items_text = items_list
            
            recent_requests_data.append({
                'id': req.id,
                'item': items_text,
                'quantity': req.total_quantity,
                'status': req.status,
                'date': req.request_date,
                'purpose': req.purpose,
                'type': 'batch'
            })
        
        # Add single requests (for backward compatibility)
        for req in recent_single_requests:
            recent_requests_data.append({
                'id': req.id,
                'item': req.supply.supply_name,
                'quantity': req.quantity,
                'status': req.status,
                'date': req.request_date,
                'purpose': req.purpose,
                'type': 'single'
            })
        
        # Sort by date
        recent_requests_data.sort(key=lambda x: x['date'], reverse=True)
        recent_requests_data = recent_requests_data[:5]  # Keep only 5 most recent
        
        return render(request, self.template_name, {
            'cart_items': cart_items,
            'available_supplies': available_supplies,
            'recent_requests': recent_requests_data
        })

    def post(self, request):
        # This method is now handled by the new cart-based views in app.views
        # Redirect to the main supply request page
        return redirect('create_supply_request')


class UserBorrowView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_borrow.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = BorrowForm()
        recent_requests = BorrowRequest.objects.filter(user=request.user).order_by('-borrow_date')[:5]
        
        # Convert requests to dict format for template
        recent_requests_data = [{
            'id': req.id,
            'item': req.property.property_name,
            'quantity': req.quantity,
            'status': req.status,
            'date': req.borrow_date,
            'return_date': req.return_date,
            'purpose': req.purpose
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })

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
            
        # If form is invalid, include recent requests in context
        recent_requests = BorrowRequest.objects.filter(user=request.user).order_by('-borrow_date')[:5]
        recent_requests_data = [{
            'id': req.id,
            'item': req.property.property_name,
            'quantity': req.quantity,
            'status': req.status,
            'date': req.borrow_date,
            'return_date': req.return_date,
            'purpose': req.purpose
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })


class UserRequestView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_request.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        # Get cart items from session
        cart_items = request.session.get('supply_cart', [])
        
        # Get available supplies
        available_supplies = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        ).select_related('quantity_info')
        
        # Get recent batch requests (new system)
        recent_batch_requests = SupplyRequestBatch.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        # Get recent single requests (legacy system) 
        recent_single_requests = SupplyRequest.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        # Combine and format recent requests
        recent_requests_data = []
        
        # Add batch requests
        for req in recent_batch_requests:
            items_text = f"{req.total_items} items"
            if req.total_items <= 3:
                items_list = ", ".join([f"{item.supply.supply_name} (x{item.quantity})" for item in req.items.all()])
                items_text = items_list
            
            recent_requests_data.append({
                'id': req.id,
                'item': items_text,
                'quantity': req.total_quantity,
                'status': req.status,
                'date': req.request_date,
                'purpose': req.purpose,
                'type': 'batch'
            })
        
        # Add single requests (for backward compatibility)
        for req in recent_single_requests:
            recent_requests_data.append({
                'id': req.id,
                'item': req.supply.supply_name,
                'quantity': req.quantity,
                'status': req.status,
                'date': req.request_date,
                'purpose': req.purpose,
                'type': 'single'
            })
        
        # Sort by date
        recent_requests_data.sort(key=lambda x: x['date'], reverse=True)
        recent_requests_data = recent_requests_data[:5]  # Keep only 5 most recent
        
        return render(request, self.template_name, {
            'cart_items': cart_items,
            'available_supplies': available_supplies,
            'recent_requests': recent_requests_data
        })

    def post(self, request):
        # This method is now handled by the new cart-based views in app.views
        # Redirect to the main supply request page
        return redirect('create_supply_request')


class UserReserveView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_reserve.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = ReservationForm()
        recent_requests = Reservation.objects.filter(user=request.user).order_by('-reservation_date')[:5]
        
        # Convert requests to dict format for template
        recent_requests_data = [{
            'id': req.id,
            'item': req.item.property_name,
            'quantity': req.quantity,
            'status': req.status,
            'date': req.reservation_date,
            'needed_date': req.needed_date,
            'return_date': req.return_date,
            'purpose': req.purpose
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })

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
            
        # If form is invalid, include recent requests in context
        recent_requests = Reservation.objects.filter(user=request.user).order_by('-reservation_date')[:5]
        recent_requests_data = [{
            'id': req.id,
            'item': req.item.property_name,
            'quantity': req.quantity,
            'status': req.status,
            'date': req.reservation_date,
            'needed_date': req.needed_date,
            'return_date': req.return_date,
            'purpose': req.purpose
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })


class UserReportView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_report.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        form = DamageReportForm()
        recent_requests = DamageReport.objects.filter(user=request.user).order_by('-report_date')[:5]
        
        # Convert requests to dict format for template
        recent_requests_data = [{
            'id': req.id,
            'item': req.item.property_name,
            'status': req.status,
            'date': req.report_date,
            'description': req.description
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })

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
            
        # If form is invalid, include recent requests in context
        recent_requests = DamageReport.objects.filter(user=request.user).order_by('-report_date')[:5]
        recent_requests_data = [{
            'id': req.id,
            'item': req.item.property_name,
            'status': req.status,
            'date': req.report_date,
            'description': req.description
        } for req in recent_requests]
        
        return render(request, self.template_name, {
            'form': form,
            'recent_requests': recent_requests_data
        })


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

        # Pagination size
        per_page = 5

        # Get page numbers from GET params (default 1)
        request_page = self.request.GET.get('request_page', 1)
        borrow_page = self.request.GET.get('borrow_page', 1)
        reservation_page = self.request.GET.get('reservation_page', 1)
        damage_page = self.request.GET.get('damage_page', 1)

        # Querysets ordered by date descending
        request_history_qs = SupplyRequest.objects.filter(user=user).order_by('-request_date')
        borrow_history_qs = BorrowRequest.objects.filter(user=user).order_by('-borrow_date')
        reservation_history_qs = Reservation.objects.filter(user=user).order_by('-reservation_date')
        damage_history_qs = DamageReport.objects.filter(user=user).order_by('-report_date')

        # Paginators
        request_paginator = Paginator(request_history_qs, per_page)
        borrow_paginator = Paginator(borrow_history_qs, per_page)
        reservation_paginator = Paginator(reservation_history_qs, per_page)
        damage_paginator = Paginator(damage_history_qs, per_page)

        # Get the page objects
        request_history_page = request_paginator.get_page(request_page)
        borrow_history_page = borrow_paginator.get_page(borrow_page)
        reservation_history_page = reservation_paginator.get_page(reservation_page)
        damage_history_page = damage_paginator.get_page(damage_page)

        # Convert page object items to dicts
        def request_to_dict(req):
            return {
                'item': req.supply.supply_name,
                'quantity': req.quantity,
                'status': req.status,
                'date': req.request_date,
                'purpose': req.purpose,
            }

        def borrow_to_dict(borrow):
            return {
                'item': borrow.property.property_name,
                'quantity': borrow.quantity,
                'status': borrow.status,
                'borrow_date': borrow.borrow_date,
                'return_date': borrow.return_date,
            }

        def reservation_to_dict(res):
            return {
                'item': res.item.property_name,
                'quantity': res.quantity,
                'status': res.status,
                'needed_date': res.needed_date,
                'return_date': res.return_date,
                'purpose': res.purpose,
            }

        def damage_to_dict(report):
            return {
                'item': report.item.property_name,
                'status': report.status,
                'date': report.report_date,
                'description': report.description,
            }

        context.update({
            'notifications': Notification.objects.filter(user=user).order_by('-timestamp'),
            'unread_count': Notification.objects.filter(user=user, is_read=False).count(),

            # Pass paginated page objects (converted to dict)
            'request_history': [request_to_dict(r) for r in request_history_page],
            'request_history_page': request_history_page,

            'borrow_history': [borrow_to_dict(b) for b in borrow_history_page],
            'borrow_history_page': borrow_history_page,

            'reservation_history': [reservation_to_dict(r) for r in reservation_history_page],
            'reservation_history_page': reservation_history_page,

            'damage_history': [damage_to_dict(d) for d in damage_history_page],
            'damage_history_page': damage_history_page,
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


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('user_password_change_done')

    def get_template_names(self):
        return ['userpanel/password_change_form.html']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password was successfully updated!')
        return response

class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'registration/password_change_done.html'

    def get_template_names(self):
        return ['userpanel/password_change_done.html']

@login_required
@require_POST
def cancel_supply_request(request, request_id):
    supply_request = get_object_or_404(SupplyRequest, id=request_id, user=request.user)
    
    # Only allow cancellation if request is pending
    if supply_request.status == 'pending':
        supply_request.status = 'cancelled'
        supply_request.save()
        
        # Log the cancellation
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='SupplyRequest',
            object_repr=str(supply_request.supply.supply_name),
            description=f"Cancelled supply request for {supply_request.quantity} units of {supply_request.supply.supply_name}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Request cancelled successfully'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Request cannot be cancelled'
    }, status=400)

@login_required
@require_POST
def cancel_borrow_request(request, request_id):
    borrow_request = get_object_or_404(BorrowRequest, id=request_id, user=request.user)
    
    if borrow_request.status == 'pending':
        borrow_request.status = 'cancelled'
        borrow_request.save()
        
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='BorrowRequest',
            object_repr=str(borrow_request.property.property_name),
            description=f"Cancelled borrow request for {borrow_request.quantity} units of {borrow_request.property.property_name}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Request cancelled successfully'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Request cannot be cancelled'
    }, status=400)

@login_required
@require_POST
def cancel_reservation(request, request_id):
    reservation = get_object_or_404(Reservation, id=request_id, user=request.user)
    
    if reservation.status == 'pending':
        reservation.status = 'cancelled'
        reservation.save()
        
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='Reservation',
            object_repr=str(reservation.item.property_name),
            description=f"Cancelled reservation for {reservation.quantity} units of {reservation.item.property_name}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reservation cancelled successfully'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Reservation cannot be cancelled'
    }, status=400)

@login_required
@require_POST
def cancel_damage_report(request, request_id):
    report = get_object_or_404(DamageReport, id=request_id, user=request.user)
    
    if report.status == 'pending':
        report.status = 'cancelled'
        report.save()
        
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='DamageReport',
            object_repr=str(report.item.property_name),
            description=f"Cancelled damage report for {report.item.property_name}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Report cancelled successfully'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Report cannot be cancelled'
    }, status=400)
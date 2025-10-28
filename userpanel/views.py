from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm, UserProfileUpdateForm
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView
from app.models import UserProfile, Notification, Property, ActivityLog, Supply, SupplyRequestBatch, SupplyRequestItem, SupplyRequest, BorrowRequest, BorrowRequestBatch, BorrowRequestItem, Reservation, DamageReport
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
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
    """
    DEPRECATED: This view is maintained only for backward compatibility.
    Redirects to UserUnifiedRequestView with supply tab active.
    The original user_request.html template has been removed.
    """
    permission_required = 'app.view_user_module'

    def get(self, request):
        request.session['active_request_tab'] = 'supply'
        request.session.modified = True
        return redirect('user_unified_request')

    def post(self, request):
        request.session['active_request_tab'] = 'supply'
        request.session.modified = True
        return redirect('user_unified_request')


class UserBorrowView(PermissionRequiredMixin, TemplateView):
    """
    DEPRECATED: This view is maintained only for backward compatibility.
    Redirects to UserUnifiedRequestView with borrow tab active.
    The original user_borrow.html template has been removed.
    """
    permission_required = 'app.view_user_module'

    def get(self, request):
        request.session['active_request_tab'] = 'borrow'
        request.session.modified = True
        return redirect('user_unified_request')

    def post(self, request):
        request.session['active_request_tab'] = 'borrow'
        request.session.modified = True
        return redirect('user_unified_request')


class UserReserveView(PermissionRequiredMixin, TemplateView):
    template_name = 'userpanel/user_reserve.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        # Get cart items from session
        cart_items = request.session.get('reservation_cart', [])
        
        # Convert cart items to objects with property details
        cart_items_data = []
        for item in cart_items:
            try:
                if 'property_id' not in item:
                    continue
                    
                property_obj = Property.objects.get(id=item['property_id'])
                enriched_item = {
                    'supply': property_obj,  # Using 'supply' for template consistency
                    'quantity': item['quantity'],
                    'needed_date': datetime.strptime(item['needed_date'], '%Y-%m-%d').date() if item.get('needed_date') else None,
                    'return_date': datetime.strptime(item['return_date'], '%Y-%m-%d').date() if item.get('return_date') else None,
                    'purpose': item.get('purpose', '')
                }
                cart_items_data.append(enriched_item)
            except (Property.DoesNotExist, KeyError, ValueError) as e:
                continue
        
        # Get available properties for the dropdown
        available_supplies = Property.objects.filter(
            is_archived=False, 
            quantity__gt=0,
            availability='available'
        )
        
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
            'cart_items': cart_items_data,
            'available_supplies': available_supplies,
            'recent_requests': recent_requests_data
        })

    def post(self, request):
        # This method is now handled by the new cart-based views
        # Redirect to the main reservation page
        return redirect('user_reserve')


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
        form = DamageReportForm(request.POST, request.FILES)
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


class UserUnifiedRequestView(PermissionRequiredMixin, TemplateView):
    """Unified view for both Supply Request and Borrow Request with toggle"""
    template_name = 'userpanel/user_unified_request.html'
    permission_required = 'app.view_user_module'

    def get(self, request):
        from app.models import SupplyCategory, PropertyCategory
        
        # Get supply cart items from session
        supply_cart_items = request.session.get('supply_cart', [])
        supply_cart_items_data = []
        for item in supply_cart_items:
            try:
                if 'supply_id' not in item:
                    continue
                    
                supply_obj = Supply.objects.select_related('quantity_info').get(id=item['supply_id'])
                enriched_item = {
                    'supply_id': supply_obj.id,
                    'supply_name': supply_obj.supply_name,
                    'quantity': item['quantity'],
                    'available_quantity': supply_obj.quantity_info.current_quantity if supply_obj.quantity_info else 0,
                    'supply': supply_obj
                }
                supply_cart_items_data.append(enriched_item)
            except (Supply.DoesNotExist, KeyError, ValueError) as e:
                continue
        
        # Get borrow cart items from session
        borrow_cart_items = request.session.get('borrow_cart', [])
        borrow_cart_items_data = []
        for item in borrow_cart_items:
            try:
                property_obj = Property.objects.get(id=item['property_id'])
                enriched_item = {
                    'supply': property_obj,
                    'quantity': item['quantity'],
                    'return_date': datetime.strptime(item['return_date'], '%Y-%m-%d').date() if item['return_date'] else None,
                    'purpose': item['purpose']
                }
                borrow_cart_items_data.append(enriched_item)
            except Property.DoesNotExist:
                continue
            except Exception as e:
                continue
        
        # Get available supplies
        available_supplies = Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        ).select_related('quantity_info', 'category')
        
        # Get available properties
        available_properties = Property.objects.filter(
            is_archived=False, 
            quantity__gt=0,
            availability='available'
        )
        
        # Get categories
        supply_categories = SupplyCategory.objects.all()
        borrow_categories = PropertyCategory.objects.all()
        
        # Get recent supply requests
        recent_supply_batch_requests = SupplyRequestBatch.objects.filter(user=request.user).order_by('-request_date')[:5]
        recent_supply_single_requests = SupplyRequest.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        supply_recent_requests_data = []
        for req in recent_supply_batch_requests:
            items_text = f"{req.total_items} items"
            if req.total_items <= 3:
                items_list = ", ".join([f"{item.supply.supply_name} (x{item.quantity})" for item in req.items.all()])
                items_text = items_list
            
            supply_recent_requests_data.append({
                'id': req.id,
                'item': items_text,
                'quantity': req.total_quantity,
                'status': req.status,
                'date': req.request_date.isoformat(),
                'purpose': req.purpose,
                'type': 'batch'
            })
        
        for req in recent_supply_single_requests:
            supply_recent_requests_data.append({
                'id': req.id,
                'item': req.supply.supply_name,
                'quantity': req.quantity,
                'status': req.status,
                'date': req.request_date.isoformat(),
                'purpose': req.purpose,
                'type': 'single'
            })
        
        supply_recent_requests_data.sort(key=lambda x: x['date'], reverse=True)
        supply_recent_requests_data = supply_recent_requests_data[:5]
        
        # Get recent borrow requests
        recent_borrow_batch_requests = BorrowRequestBatch.objects.filter(user=request.user).order_by('-request_date')[:5]
        recent_borrow_single_requests = BorrowRequest.objects.filter(user=request.user).order_by('-borrow_date')[:5]
        
        borrow_recent_requests_data = []
        for req in recent_borrow_batch_requests:
            items_text = f"{req.total_items} items"
            if req.total_items <= 3:
                items_list = ", ".join([f"{item.property.property_name} (x{item.quantity})" for item in req.items.all()])
                items_text = items_list
            
            borrow_recent_requests_data.append({
                'id': req.id,
                'item': items_text,
                'quantity': req.total_quantity,
                'status': req.status,
                'date': req.request_date.isoformat(),
                'return_date': req.latest_return_date.isoformat() if req.latest_return_date else None,
                'purpose': req.purpose,
                'type': 'batch'
            })
        
        for req in recent_borrow_single_requests:
            borrow_recent_requests_data.append({
                'id': req.id,
                'item': req.property.property_name,
                'quantity': req.quantity,
                'status': req.status,
                'date': req.borrow_date.isoformat(),
                'return_date': req.return_date.isoformat() if req.return_date else None,
                'purpose': req.purpose,
                'type': 'single'
            })
        
        borrow_recent_requests_data.sort(key=lambda x: x['date'], reverse=True)
        borrow_recent_requests_data = borrow_recent_requests_data[:5]
        
        # Get active tab from session (set by request_again) or default to supply
        active_tab = request.session.pop('active_request_tab', None)
        
        return render(request, self.template_name, {
            'supply_cart_items': supply_cart_items_data,
            'borrow_cart_items': borrow_cart_items_data,
            'available_supplies': available_supplies,
            'available_properties': available_properties,
            'supply_categories': supply_categories,
            'borrow_categories': borrow_categories,
            'supply_recent_requests': json.dumps(supply_recent_requests_data),
            'borrow_recent_requests': json.dumps(borrow_recent_requests_data),
            'active_tab': active_tab,  # Pass to template
        })


class UserLoginView(LoginView):
    template_name = 'registration/login.html'

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
        
        # Combine old BorrowRequest and new BorrowRequestBatch systems
        # Get old borrow requests
        old_borrow_requests = BorrowRequest.objects.filter(user=user).select_related('property')
        # Get new batch borrow items
        batch_borrow_items = BorrowRequestItem.objects.filter(
            batch_request__user=user
        ).select_related('property', 'batch_request')
        
        # Create a combined list with unified structure
        combined_borrows = []
        
        # Add old borrow requests
        for borrow in old_borrow_requests:
            combined_borrows.append({
                'property': borrow.property,
                'quantity': borrow.quantity,
                'status': borrow.status,
                'borrow_date': borrow.borrow_date,
                'return_date': borrow.return_date,
                'sort_date': borrow.borrow_date,
                'type': 'old'
            })
        
        # Add batch borrow items
        for item in batch_borrow_items:
            # Use approved_quantity if available, otherwise quantity
            qty = item.approved_quantity if item.approved_quantity else item.quantity
            combined_borrows.append({
                'property': item.property,
                'quantity': qty,
                'status': item.status,
                'borrow_date': item.claimed_date if item.claimed_date else item.batch_request.request_date,
                'return_date': item.return_date,
                'sort_date': item.claimed_date if item.claimed_date else item.batch_request.request_date,
                'type': 'batch'
            })
        
        # Sort combined list by date descending
        combined_borrows.sort(key=lambda x: x['sort_date'], reverse=True)
        
        # Convert to queryset-like list for pagination
        borrow_history_qs = combined_borrows
        
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
            # Handle both old BorrowRequest objects and new combined dict format
            if isinstance(borrow, dict):
                return {
                    'item': borrow['property'].property_name,
                    'quantity': borrow['quantity'],
                    'status': borrow['status'],
                    'borrow_date': borrow['borrow_date'],
                    'return_date': borrow['return_date'],
                }
            else:
                # Old BorrowRequest object
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

        # Calculate stats counts
        request_count = request_history_qs.count()
        borrow_count = len(borrow_history_qs)  # Now it's a list, not a queryset
        reservation_count = reservation_history_qs.count()
        damage_count = damage_history_qs.count()

        # Get recent activity (last 5 activities from all types)
        recent_activity = []
        
        # Add recent requests
        for req in request_history_qs[:3]:
            recent_activity.append({
                'message': f'Requested {req.supply.supply_name} (x{req.quantity})',
                'timestamp': req.request_date,
                'type': 'request'
            })
        
        # Add recent borrows (from combined list)
        for borrow in borrow_history_qs[:3]:
            if isinstance(borrow, dict):
                recent_activity.append({
                    'message': f'Borrowed {borrow["property"].property_name} (x{borrow["quantity"]})',
                    'timestamp': borrow['borrow_date'],
                    'type': 'borrow'
                })
            else:
                recent_activity.append({
                    'message': f'Borrowed {borrow.property.property_name} (x{borrow.quantity})',
                    'timestamp': borrow.borrow_date,
                    'type': 'borrow'
                })
        
        # Add recent reservations
        for res in reservation_history_qs[:3]:
            recent_activity.append({
                'message': f'Reserved {res.item.property_name} (x{res.quantity})',
                'timestamp': res.reservation_date,
                'type': 'reservation'
            })
        
        # Sort by timestamp and get the 5 most recent
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:5]

        context.update({
            'notifications': Notification.objects.filter(user=user).order_by('-timestamp'),
            'unread_count': Notification.objects.filter(user=user, is_read=False).count(),

            # Stats counts
            'request_count': request_count,
            'borrow_count': borrow_count,
            'reservation_count': reservation_count,
            'damage_count': damage_count,
            'recent_activity': recent_activity,

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
def cancel_batch_supply_request(request, request_id):
    batch_request = get_object_or_404(SupplyRequestBatch, id=request_id, user=request.user)
    
    # Only allow cancellation if request is pending
    if batch_request.status == 'pending':
        batch_request.status = 'cancelled'
        batch_request.save()
        
        # Log the cancellation
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='SupplyRequestBatch',
            object_repr=f"Batch Request #{batch_request.id}",
            description=f"Cancelled batch supply request with {batch_request.items.count()} items"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Batch request cancelled successfully'
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
def cancel_batch_borrow_request(request, request_id):
    batch_request = get_object_or_404(BorrowRequestBatch, id=request_id, user=request.user)
    
    if batch_request.status == 'pending':
        batch_request.status = 'cancelled'
        batch_request.save()
        
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='BorrowRequestBatch',
            object_repr=f"Batch Request #{batch_request.id}",
            description=f"Cancelled batch borrow request with {batch_request.items.count()} items"
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


# Borrow Cart Functionality
@login_required
def add_to_borrow_list(request):
    """Add item to borrow cart session"""
    if request.method == 'POST':
        property_id = request.POST.get('property_id')  # Changed from 'supply' to 'property_id'
        quantity = int(request.POST.get('quantity', 1))
        return_date = request.POST.get('return_date')
        purpose = request.POST.get('purpose', '')
        
        if not property_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Please select an item'
            })
        
        try:
            property_obj = Property.objects.get(id=property_id)
            
            # Check if property is available for request
            if property_obj.availability != 'available':
                return JsonResponse({
                    'status': 'error',
                    'message': 'This item is not available for request'
                })
            
            # Check if property is archived
            if property_obj.is_archived:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This item is archived and cannot be requested'
                })
            
            # Validate quantity
            if quantity > property_obj.quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {property_obj.quantity} units available'
                })
            
            # Validate return date
            if return_date:
                return_date_obj = datetime.strptime(return_date, '%Y-%m-%d').date()
                if return_date_obj <= datetime.now().date():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Return date must be in the future'
                    })
            
            # Get or create cart in session
            cart = request.session.get('borrow_cart', [])
            
            # Check if item already exists in cart
            item_exists = False
            for item in cart:
                if item['property_id'] == property_id:
                    item['quantity'] += quantity
                    item['return_date'] = return_date
                    item['purpose'] = purpose
                    item_exists = True
                    break
            
            if not item_exists:
                cart.append({
                    'property_id': property_id,
                    'quantity': quantity,
                    'return_date': return_date,
                    'purpose': purpose
                })
            
            request.session['borrow_cart'] = cart
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success',
                'message': f'{property_obj.property_name} added to borrow list',
                'list_count': len(cart)
            })
            
        except Property.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Item not found'
            })
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def remove_from_borrow_list(request):
    """Remove item from borrow cart session"""
    if request.method == 'POST':
        property_id = request.POST.get('supply_id')
        
        cart = request.session.get('borrow_cart', [])
        cart = [item for item in cart if item['property_id'] != property_id]
        
        request.session['borrow_cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Item removed from borrow list',
            'list_count': len(cart)
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def update_borrow_list_item(request):
    """Update item quantity and return date in borrow cart session"""
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        property_id = request.POST.get('supply_id')
        quantity = int(request.POST.get('quantity', 1))
        return_date = request.POST.get('return_date')
        
        logger.info(f"Updating borrow cart item: property_id={property_id}, quantity={quantity}, return_date={return_date}")
        
        try:
            property_obj = Property.objects.get(id=property_id)
            
            # Validate quantity
            if quantity > property_obj.quantity:
                logger.warning(f"Quantity {quantity} exceeds available {property_obj.quantity}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {property_obj.quantity} units available'
                })
            
            # Validate return date
            if return_date:
                return_date_obj = datetime.strptime(return_date, '%Y-%m-%d').date()
                if return_date_obj <= datetime.now().date():
                    logger.warning(f"Invalid return date: {return_date_obj}")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Return date must be in the future'
                    })
            
            cart = request.session.get('borrow_cart', [])
            logger.info(f"Current borrow cart before update: {cart}")
            
            # Find and update the item
            for item in cart:
                if item['property_id'] == int(property_id):
                    item['quantity'] = quantity
                    item['return_date'] = return_date
                    logger.info(f"Updated borrow item in cart: {item}")
                    break
            
            request.session['borrow_cart'] = cart
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            
            logger.info(f"Borrow cart after update: {request.session.get('borrow_cart', [])}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Item updated successfully'
            })
            
        except Property.DoesNotExist:
            logger.error(f"Property not found: {property_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Item not found'
            })
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid data provided'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def clear_borrow_list(request):
    """Clear all items from borrow cart session"""
    if request.method == 'POST':
        request.session['borrow_cart'] = []
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Borrow list cleared successfully'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def submit_borrow_list_request(request):
    """Submit all items in borrow cart as a batch borrow request"""
    if request.method == 'POST':
        cart = request.session.get('borrow_cart', [])
        
        if not cart:
            return JsonResponse({
                'status': 'error',
                'message': 'No items in borrow list'
            })
        
        general_purpose = request.POST.get('general_purpose', '')
        
        try:
            # Create the batch borrow request
            batch_request = BorrowRequestBatch.objects.create(
                user=request.user,
                purpose=general_purpose,
                status='pending'
            )
            
            # Create individual borrow request items
            for item in cart:
                try:
                    property_obj = Property.objects.get(id=item['property_id'])
                except Property.DoesNotExist:
                    # Delete the batch request if a property doesn't exist
                    batch_request.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Property with ID {item["property_id"]} not found'
                    })
                
                # Check if property is available for request
                if property_obj.availability != 'available':
                    batch_request.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'{property_obj.property_name} is not available for request'
                    })
                
                # Check if property is archived
                if property_obj.is_archived:
                    batch_request.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'{property_obj.property_name} is archived and cannot be requested'
                    })
                
                # Check quantity availability
                if item['quantity'] > property_obj.quantity:
                    batch_request.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Only {property_obj.quantity} units of {property_obj.property_name} are available'
                    })
                
                # Create the borrow request item
                try:
                    BorrowRequestItem.objects.create(
                        batch_request=batch_request,
                        property=property_obj,
                        quantity=item['quantity'],
                        return_date=datetime.strptime(item['return_date'], '%Y-%m-%d').date(),
                        status='pending'
                    )
                except Exception as create_error:
                    # Delete the batch request if creating an item fails
                    batch_request.delete()
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Error creating borrow request item: {str(create_error)}'
                    })
            
            # Log activity for the batch request
            # Build item list for logging by fetching property names
            logged_items = []
            for item in cart[:3]:
                try:
                    property_obj = Property.objects.get(id=item['property_id'])
                    logged_items.append(f"{property_obj.property_name} (x{item['quantity']})")
                except Property.DoesNotExist:
                    logged_items.append(f"Unknown Item (x{item['quantity']})")
            
            item_list = ", ".join(logged_items)
            if len(cart) > 3:
                item_list += f" and {len(cart) - 3} more items"
            
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='BorrowRequestBatch',
                object_repr=f"Batch #{batch_request.id}",
                description=f"Submitted batch borrow request with {len(cart)} items: {item_list}"
            )
            
            # Clear the cart
            request.session['borrow_cart'] = []
            request.session.modified = True
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': f'Borrow request submitted successfully! Your request ID is #{batch_request.id}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error submitting batch request: {str(e)}'
            })
    
    # For non-POST requests
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


# Reservation Cart Functionality
@login_required
def add_to_reservation_list(request):
    """Add item to reservation cart session"""
    if request.method == 'POST':
        property_id = request.POST.get('supply')
        quantity = int(request.POST.get('quantity', 1))
        needed_date = request.POST.get('needed_date')
        return_date = request.POST.get('return_date')
        purpose = request.POST.get('purpose', '')
        
        # Get property details
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Property not found'
            })
        
        # Check if property is available for request
        if property_obj.availability != 'available':
            return JsonResponse({
                'status': 'error',
                'message': 'This item is not available for request'
            })
        
        # Check if property is archived
        if property_obj.is_archived:
            return JsonResponse({
                'status': 'error',
                'message': 'This item is archived and cannot be requested'
            })
        
        # Check if enough quantity is available
        if quantity > property_obj.quantity:
            return JsonResponse({
                'status': 'error',
                'message': f'Only {property_obj.quantity} units available'
            })
        
        # Check if item already exists in cart
        cart = request.session.get('reservation_cart', [])
        
        existing_item = None
        for i, item in enumerate(cart):
            if item['property_id'] == property_id:
                existing_item = i
                break
        
        if existing_item is not None:
            # Update existing item
            cart[existing_item]['quantity'] += quantity
            cart[existing_item]['needed_date'] = needed_date
            cart[existing_item]['return_date'] = return_date
            cart[existing_item]['purpose'] = purpose
            
            # Check if total quantity exceeds available
            if cart[existing_item]['quantity'] > property_obj.quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Total quantity would exceed available stock ({property_obj.quantity} units)'
                })
        else:
            # Add new item
            cart.append({
                'property_id': property_id,
                'property_name': property_obj.property_name,
                'quantity': quantity,
                'needed_date': needed_date,
                'return_date': return_date,
                'purpose': purpose
            })
        
        # Save cart to session
        request.session['reservation_cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': f'{property_obj.property_name} added to reservation list',
            'cart_count': len(cart),
            'item': {
                'property_id': property_id,
                'property_name': property_obj.property_name,
                'quantity': quantity,
                'needed_date': needed_date,
                'return_date': return_date,
                'purpose': purpose,
                'available_quantity': property_obj.quantity
            }
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def update_reservation_list_item(request):
    """Update quantity, needed_date, and return_date of item in reservation cart"""
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        new_quantity = int(request.POST.get('quantity', 1))
        needed_date = request.POST.get('needed_date')
        return_date = request.POST.get('return_date')
        
        cart = request.session.get('reservation_cart', [])
        
        # Find and update the item
        for i, item in enumerate(cart):
            if item['property_id'] == property_id:
                try:
                    property_obj = Property.objects.get(id=property_id)
                    
                    # Check if new quantity is available
                    if new_quantity > property_obj.quantity:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Only {property_obj.quantity} units available'
                        })
                    
                    cart[i]['quantity'] = new_quantity
                    if needed_date:
                        cart[i]['needed_date'] = needed_date
                    if return_date:
                        cart[i]['return_date'] = return_date
                        
                    request.session['reservation_cart'] = cart
                    request.session.modified = True
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Item updated successfully'
                    })
                    
                except Property.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Property not found'
                    })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Item not found in reservation list'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def remove_from_reservation_list(request):
    """Remove item from reservation cart"""
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        
        cart = request.session.get('reservation_cart', [])
        
        # Remove the item
        cart = [item for item in cart if item['property_id'] != property_id]
        
        request.session['reservation_cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Item removed from reservation list successfully',
            'cart_count': len(cart)
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def clear_reservation_list(request):
    """Clear all items from reservation cart"""
    if request.method == 'POST':
        request.session['reservation_cart'] = []
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reservation list cleared successfully'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def submit_reservation_list_request(request):
    """Submit all items in reservation cart as individual reservation requests"""
    if request.method == 'POST':
        cart = request.session.get('reservation_cart', [])
        
        if not cart:
            return JsonResponse({
                'status': 'error',
                'message': 'No items in reservation list'
            })
        
        general_purpose = request.POST.get('general_purpose', '')
        
        try:
            created_requests = []
            
            for item in cart:
                property_obj = Property.objects.get(id=item['property_id'])
                
                # Check if property is available for request
                if property_obj.availability != 'available':
                    return JsonResponse({
                        'status': 'error',
                        'message': f'{property_obj.property_name} is not available for request'
                    })
                
                # Check if property is archived
                if property_obj.is_archived:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'{property_obj.property_name} is archived and cannot be requested'
                    })
                
                # Check quantity availability
                if item['quantity'] > property_obj.quantity:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Only {property_obj.quantity} units of {property_obj.property_name} are available'
                    })
                
                # Create the reservation request
                reservation = Reservation.objects.create(
                    user=request.user,
                    item=property_obj,
                    quantity=item['quantity'],
                    needed_date=datetime.strptime(item['needed_date'], '%Y-%m-%d').date(),
                    return_date=datetime.strptime(item['return_date'], '%Y-%m-%d').date(),
                    purpose=f"{item['purpose']}. {general_purpose}".strip('. '),
                    status='pending'
                )
                
                created_requests.append(reservation)
                
                # Log the activity
                ActivityLog.log_activity(
                    user=request.user,
                    action='request',
                    model_name='Reservation',
                    object_repr=str(property_obj.property_name),
                    description=f"Reserved {item['quantity']} units of {property_obj.property_name} from {item['needed_date']} to {item['return_date']}"
                )
            
            # Clear the cart
            request.session['reservation_cart'] = []
            request.session.modified = True
            
            messages.success(request, f'{len(created_requests)} reservation request(s) submitted successfully.')
            return redirect('user_reserve')
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error submitting requests: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


class UserProfileView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View for users to view and edit their profile information"""
    template_name = 'userpanel/user_profile.html'
    permission_required = 'app.view_user_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            user_profile = UserProfile.objects.get(user=self.request.user)
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            user_profile = UserProfile.objects.create(
                user=self.request.user,
                role='USER'
            )
        
        context['form'] = UserProfileUpdateForm(instance=user_profile, user=self.request.user)
        context['user_profile'] = user_profile
        return context

    def post(self, request, *args, **kwargs):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(
                user=request.user,
                role='USER'
            )

        form = UserProfileUpdateForm(request.POST, instance=user_profile, user=request.user)
        
        if form.is_valid():
            # Check if password was changed
            password_changed = bool(form.cleaned_data.get('new_password'))
            
            form.save()
            
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                model_name='UserProfile',
                object_repr=request.user.username,
                description=f"User {request.user.username} updated their profile information" + 
                           (" and changed password" if password_changed else "")
            )
            
            if password_changed:
                # Update session auth hash to prevent logout after password change
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Your profile and password have been updated successfully!')
            else:
                messages.success(request, 'Your profile has been updated successfully!')
                
            return redirect('user_profile')
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class UserAllRequestsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View for users to view all their requests with filtering capabilities"""
    template_name = 'userpanel/user_all_requests.html'
    permission_required = 'app.view_user_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters from request
        request_type = self.request.GET.get('type', 'all')
        status_filter = self.request.GET.get('status', 'all')
        search_query = self.request.GET.get('search', '')
        
        # Initialize combined requests list
        all_requests = []
        
        # Get Supply Requests (batch and single)
        if request_type in ['all', 'supply']:
            # Batch supply requests
            batch_supply_requests = SupplyRequestBatch.objects.filter(
                user=self.request.user
            ).select_related('user').prefetch_related('items__supply')
            
            for req in batch_supply_requests:
                # Create items summary
                items_summary = []
                for item in req.items.all()[:3]:  # Show first 3 items
                    items_summary.append(f"{item.supply.supply_name} (x{item.quantity})")
                
                if req.items.count() > 3:
                    items_summary.append(f"and {req.items.count() - 3} more items")
                
                request_data = {
                    'id': f"SB-{req.id}",
                    'type': 'Supply Request',
                    'item_name': ", ".join(items_summary),
                    'quantity': req.total_quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.request_date,
                    'purpose': req.purpose,
                    'can_cancel': req.status == 'pending',
                    'model_type': 'batch_supply',
                    'real_id': req.id
                }
                all_requests.append(request_data)
            
            # Single supply requests (legacy)
            single_supply_requests = SupplyRequest.objects.filter(
                user=self.request.user
            ).select_related('user', 'supply')
            
            for req in single_supply_requests:
                request_data = {
                    'id': f"S-{req.id}",
                    'type': 'Supply Request',
                    'item_name': req.supply.supply_name,
                    'quantity': req.quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.request_date,
                    'purpose': req.purpose,
                    'can_cancel': req.status == 'pending',
                    'model_type': 'supply',
                    'real_id': req.id
                }
                all_requests.append(request_data)
        
        # Get Borrow Requests (batch and single)
        if request_type in ['all', 'borrow']:
            # Batch borrow requests
            batch_borrow_requests = BorrowRequestBatch.objects.filter(
                user=self.request.user
            ).select_related('user').prefetch_related('items__property')
            
            for req in batch_borrow_requests:
                # Create items summary
                items_summary = []
                for item in req.items.all()[:3]:  # Show first 3 items
                    items_summary.append(f"{item.property.property_name} (x{item.quantity})")
                
                if req.items.count() > 3:
                    items_summary.append(f"and {req.items.count() - 3} more items")
                
                request_data = {
                    'id': f"BB-{req.id}",
                    'type': 'Borrow Request',
                    'item_name': ", ".join(items_summary),
                    'quantity': req.total_quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.request_date,
                    'purpose': req.purpose,
                    'return_date': req.latest_return_date,
                    'can_cancel': req.status == 'pending',
                    'model_type': 'batch_borrow',
                    'real_id': req.id
                }
                all_requests.append(request_data)
            
            # Single borrow requests (legacy)
            single_borrow_requests = BorrowRequest.objects.filter(
                user=self.request.user
            ).select_related('user', 'property')
            
            for req in single_borrow_requests:
                request_data = {
                    'id': f"B-{req.id}",
                    'type': 'Borrow Request',
                    'item_name': req.property.property_name,
                    'quantity': req.quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.borrow_date,
                    'purpose': req.purpose,
                    'return_date': req.return_date,
                    'can_cancel': req.status == 'pending',
                    'model_type': 'borrow',
                    'real_id': req.id
                }
                all_requests.append(request_data)
        
        # Get Reservations
        if request_type in ['all', 'reservation']:
            reservations = Reservation.objects.filter(
                user=self.request.user
            ).select_related('user', 'item')
            
            for req in reservations:
                request_data = {
                    'id': f"R-{req.id}",
                    'type': 'Reservation',
                    'item_name': req.item.property_name,
                    'quantity': req.quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.reservation_date,
                    'purpose': req.purpose,
                    'needed_date': req.needed_date,
                    'return_date': req.return_date,
                    'can_cancel': req.status == 'pending',
                    'model_type': 'reservation',
                    'real_id': req.id
                }
                all_requests.append(request_data)
        
        # Apply status filter
        if status_filter != 'all':
            all_requests = [req for req in all_requests if req['status_raw'] == status_filter]
        
        # Apply search filter
        if search_query:
            search_query = search_query.lower()
            all_requests = [
                req for req in all_requests
                if (search_query in req['item_name'].lower() or 
                    search_query in req['purpose'].lower() or
                    search_query in req['type'].lower())
            ]
        
        # Sort by date (most recent first)
        all_requests.sort(key=lambda x: x['date'], reverse=True)
        
        # Get unique statuses for filter dropdown
        unique_statuses = set()
        for req in all_requests:
            unique_statuses.add((req['status_raw'], req['status']))
        unique_statuses = sorted(list(unique_statuses))
        
        # Pagination
        paginator = Paginator(all_requests, 10)  # Show 10 requests per page
        page_number = self.request.GET.get('page', 1)
        
        try:
            page_obj = paginator.get_page(page_number)
        except:
            page_obj = paginator.get_page(1)
        
        context.update({
            'all_requests': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'is_paginated': paginator.num_pages > 1,
            'request_type': request_type,
            'status_filter': status_filter,
            'search_query': search_query,
            'unique_statuses': unique_statuses,
            'total_requests': len(all_requests)
        })
        
        return context


@login_required
def request_detail(request, type, request_id):
    """View to show detailed information about a specific request"""
    try:
        if type == 'supply':
            request_obj = get_object_or_404(SupplyRequest, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            context = {
                'request_obj': request_obj,
                'request_type': 'Supply Request',
                'items': [{'item': request_obj.supply, 'quantity': request_obj.quantity}],
                'is_batch': False
            }
        elif type == 'batch_supply':
            request_obj = get_object_or_404(SupplyRequestBatch, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            items = request_obj.items.select_related('supply').all()
            context = {
                'request_obj': request_obj,
                'request_type': 'Supply Request',
                'items': [{'item': item.supply, 'quantity': item.quantity} for item in items],
                'is_batch': True
            }
        elif type == 'borrow':
            request_obj = get_object_or_404(BorrowRequest, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            context = {
                'request_obj': request_obj,
                'request_type': 'Borrow Request',
                'items': [{'item': request_obj.property, 'quantity': request_obj.quantity}],
                'is_batch': False
            }
        elif type == 'batch_borrow':
            request_obj = get_object_or_404(BorrowRequestBatch, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            items = request_obj.items.select_related('property').all()
            context = {
                'request_obj': request_obj,
                'request_type': 'Borrow Request',
                'items': [{'item': item.property, 'quantity': item.quantity} for item in items],
                'is_batch': True
            }
        elif type == 'reservation':
            request_obj = get_object_or_404(Reservation, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            context = {
                'request_obj': request_obj,
                'request_type': 'Reservation',
                'items': [{'item': request_obj.item, 'quantity': request_obj.quantity}],
                'is_batch': False
            }
        else:
            messages.error(request, 'Invalid request type.')
            return redirect('user_all_requests')
            
        return render(request, template, context)
        
    except Exception as e:
        messages.error(request, f'Request not found or access denied.')
        return redirect('user_all_requests')


@login_required 
def request_again(request):
    """View to handle request again functionality"""
    request_type = request.GET.get('type')
    request_id = request.GET.get('id')
    
    if not request_type or not request_id:
        messages.error(request, 'Invalid request parameters.')
        return redirect('user_all_requests')
    
    try:
        if request_type == 'supply':
            original_request = get_object_or_404(SupplyRequest, id=request_id, user=request.user)
            # Clear existing cart and add this item
            cart_item = {
                'supply_id': original_request.supply.id,
                'quantity': original_request.quantity
            }
            request.session['supply_cart'] = [cart_item]
            request.session['active_request_tab'] = 'supply'
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            messages.success(request, f'Added {original_request.supply.supply_name} to your cart.')
            return redirect('user_unified_request')
            
        elif request_type == 'batch_supply':
            original_request = get_object_or_404(SupplyRequestBatch, id=request_id, user=request.user)
            # Clear existing cart and add all items from the batch
            cart_items = []
            for item in original_request.items.all():
                cart_items.append({
                    'supply_id': item.supply.id,
                    'quantity': item.quantity
                })
            request.session['supply_cart'] = cart_items
            request.session['active_request_tab'] = 'supply'
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            messages.success(request, f'Added {original_request.items.count()} items to your cart.')
            return redirect('user_unified_request')
            
        elif request_type == 'borrow':
            original_request = get_object_or_404(BorrowRequest, id=request_id, user=request.user)
            # Clear existing borrow cart and add this item
            cart_item = {
                'property_id': original_request.property.id,
                'quantity': original_request.quantity,
                'return_date': original_request.return_date.strftime('%Y-%m-%d') if original_request.return_date else None,
                'purpose': original_request.purpose if hasattr(original_request, 'purpose') else ''
            }
            request.session['borrow_cart'] = [cart_item]
            request.session['active_request_tab'] = 'borrow'
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            messages.success(request, f'Added {original_request.property.property_name} to your borrow list.')
            return redirect('user_unified_request')
            
        elif request_type == 'batch_borrow':
            original_request = get_object_or_404(BorrowRequestBatch, id=request_id, user=request.user)
            # Clear existing borrow cart and add all items from the batch
            borrow_items = []
            for item in original_request.items.all():
                borrow_items.append({
                    'property_id': item.property.id,
                    'quantity': item.quantity,
                    'return_date': item.return_date.strftime('%Y-%m-%d') if item.return_date else None,
                    'purpose': original_request.purpose if hasattr(original_request, 'purpose') else ''
                })
            request.session['borrow_cart'] = borrow_items
            request.session['active_request_tab'] = 'borrow'
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            messages.success(request, f'Added {original_request.items.count()} items to your borrow list.')
            return redirect('user_unified_request')
            
        elif request_type == 'reservation':
            original_request = get_object_or_404(Reservation, id=request_id, user=request.user)
            # Clear existing reservation cart and add this item
            cart_item = {
                'property_id': original_request.item.id,
                'quantity': original_request.quantity,
                'needed_date': original_request.needed_date.strftime('%Y-%m-%d') if original_request.needed_date else None,
                'return_date': original_request.return_date.strftime('%Y-%m-%d') if original_request.return_date else None,
                'purpose': original_request.purpose if hasattr(original_request, 'purpose') else ''
            }
            request.session['reservation_cart'] = [cart_item]
            request.session.modified = True
            messages.success(request, f'Added {original_request.item.property_name} to your reservation list.')
            return redirect('user_reserve')
            
        else:
            messages.error(request, 'Invalid request type.')
            return redirect('user_all_requests')
            
    except Exception as e:
        messages.error(request, 'Original request not found or access denied.')
        return redirect('user_all_requests')


@login_required
@require_POST
def add_to_list(request):
    """Add an item to the supply request list"""
    supply_id = request.POST.get('supply_id')
    quantity = int(request.POST.get('quantity', 0))
    
    try:
        supply = Supply.objects.get(id=supply_id)
        
        # Validate quantity
        available_quantity = supply.quantity_info.current_quantity
        if quantity > available_quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {available_quantity} units of {supply.supply_name} are available.'
            })
        
        # Get or create cart in session
        cart = request.session.get('supply_cart', [])
        
        # Check if item already exists in cart
        item_exists = False
        for item in cart:
            if item['supply_id'] == supply_id:
                # Update quantity (prevent duplicates)
                new_quantity = item['quantity'] + quantity
                if new_quantity > available_quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f'Cannot add {quantity} more. Total would exceed available quantity ({available_quantity}).'
                    })
                item['quantity'] = new_quantity
                item_exists = True
                break
        
        if not item_exists:
            cart.append({
                'supply_id': supply_id,
                'supply_name': supply.supply_name,
                'quantity': quantity,
                'available_quantity': available_quantity
            })
        
        request.session['supply_cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': f'Added {supply.supply_name} to list.',
            'list_count': len(cart)
        })
        
    except Supply.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Supply item not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error adding item to cart: {str(e)}'
        })


@login_required
@require_POST
def remove_from_list(request):
    """Remove an item from the supply request list"""
    supply_id = request.POST.get('supply_id')
    
    cart = request.session.get('supply_cart', [])
    cart = [item for item in cart if item['supply_id'] != supply_id]
    
    request.session['supply_cart'] = cart
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'message': 'Item removed from cart.',
        'cart_count': len(cart)
    })


@login_required
@require_POST
def clear_supply_list(request):
    """Clear all items from the supply request list"""
    request.session['supply_cart'] = []
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'message': 'List cleared successfully.',
        'cart_count': 0
    })


@login_required
@require_POST
def update_list_item(request):
    """Update quantity of an item in the list"""
    import logging
    logger = logging.getLogger(__name__)
    
    supply_id = request.POST.get('supply_id')
    new_quantity = int(request.POST.get('quantity', 0))
    
    logger.info(f"Updating cart item: supply_id={supply_id}, new_quantity={new_quantity}")
    
    try:
        supply = Supply.objects.get(id=supply_id)
        available_quantity = supply.quantity_info.current_quantity
        
        if new_quantity > available_quantity:
            logger.warning(f"Quantity {new_quantity} exceeds available {available_quantity}")
            return JsonResponse({
                'success': False,
                'message': f'Only {available_quantity} units available.'
            })
        
        # Get the cart and create a new list with updated quantity
        cart = request.session.get('supply_cart', [])
        logger.info(f"Current cart before update: {cart}")
        
        # Find and update the item
        for item in cart:
            if item['supply_id'] == int(supply_id):
                item['quantity'] = new_quantity
                logger.info(f"Updated item in cart: {item}")
                break
        
        # Set the session with the updated cart
        request.session['supply_cart'] = cart
        request.session.modified = True
        request.session.save()  # Explicitly save the session
        
        logger.info(f"Cart after update: {request.session.get('supply_cart', [])}")
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated.',
            'cart_count': len(cart)
        })
        
    except Supply.DoesNotExist:
        logger.error(f"Supply not found: {supply_id}")
        return JsonResponse({
            'success': False,
            'message': 'Supply item not found.'
        })


@login_required
def submit_list_request(request):
    """Submit the list as a batch supply request"""
    if request.method == 'POST':
        purpose = request.POST.get('purpose', '').strip()
        cart = request.session.get('supply_cart', [])
        
        if not cart:
            return JsonResponse({
                'success': False,
                'message': 'Your request list is empty. Please add items before submitting.'
            })
        
        if not purpose:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a purpose for your request.'
            })
        
        try:
            # Create the batch request
            batch_request = SupplyRequestBatch.objects.create(
                user=request.user,
                purpose=purpose,
                status='pending'
            )
            
            # Create individual items
            for cart_item in cart:
                supply = Supply.objects.get(id=cart_item['supply_id'])
                SupplyRequestItem.objects.create(
                    batch_request=batch_request,
                    supply=supply,
                    quantity=cart_item['quantity']
                )
            
            # Log activity
            supplies_for_logging = []
            for cart_item in cart[:3]:
                try:
                    supply = Supply.objects.get(id=cart_item['supply_id'])
                    supplies_for_logging.append(f"{supply.supply_name} (x{cart_item['quantity']})")
                except Supply.DoesNotExist:
                    supplies_for_logging.append(f"Unknown Item (x{cart_item['quantity']})")
            
            item_list = ", ".join(supplies_for_logging)
            if len(cart) > 3:
                item_list += f" and {len(cart) - 3} more items"
            
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='SupplyRequestBatch',
                object_repr=f"Batch #{batch_request.id}",
                description=f"Submitted batch supply request with {len(cart)} items: {item_list}"
            )
            
            # Clear the cart
            request.session['supply_cart'] = []
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': f'Supply request submitted successfully! Your request ID is #{batch_request.id}.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error submitting request: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


# Requisition and Issue Slip PDF Generation Views (User Side)
@login_required
def user_download_requisition_slip(request, batch_id):
    """
    Download the requisition and issue slip PDF for a supply request batch (user side).
    Users can only download their own requisition slips.
    """
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    
    # Check permissions: users can only download their own slips
    if batch_request.user != request.user:
        messages.error(request, 'You do not have permission to access this requisition slip.')
        return redirect('user_all_requests')
    
    # Only generate slip for approved, partially approved, for_claiming, or completed requests
    if batch_request.status not in ['approved', 'partially_approved', 'for_claiming', 'completed']:
        messages.error(request, 'Requisition slip is only available for approved requests.')
        return redirect('request_detail', type='batch_supply', request_id=batch_id)
    
    try:
        from app.pdf_utils import download_requisition_slip
        
        # Log the download activity
        ActivityLog.log_activity(
            user=request.user,
            action='view',
            model_name='SupplyRequestBatch',
            object_repr=f"Requisition Slip #{batch_id}",
            description=f"Downloaded requisition slip for batch request #{batch_id}"
        )
        
        return download_requisition_slip(batch_request)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error downloading requisition slip: {error_details}")  # Log to console
        messages.error(request, f'Error generating requisition slip: {str(e)}')
        return redirect('request_detail', type='batch_supply', request_id=batch_id)


@login_required
def user_view_requisition_slip(request, batch_id):
    """
    View the requisition and issue slip PDF in browser for a supply request batch (user side).
    Users can only view their own requisition slips.
    """
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    
    # Check permissions: users can only view their own slips
    if batch_request.user != request.user:
        messages.error(request, 'You do not have permission to access this requisition slip.')
        return redirect('user_all_requests')
    
    # Only generate slip for approved, partially approved, for_claiming, or completed requests
    if batch_request.status not in ['approved', 'partially_approved', 'for_claiming', 'completed']:
        messages.error(request, 'Requisition slip is only available for approved requests.')
        return redirect('request_detail', type='batch_supply', request_id=batch_id)
    
    try:
        from app.pdf_utils import view_requisition_slip
        
        # Log the view activity
        ActivityLog.log_activity(
            user=request.user,
            action='view',
            model_name='SupplyRequestBatch',
            object_repr=f"Requisition Slip #{batch_id}",
            description=f"Viewed requisition slip for batch request #{batch_id}"
        )
        
        return view_requisition_slip(batch_request)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error viewing requisition slip: {error_details}")  # Log to console
        messages.error(request, f'Error generating requisition slip: {str(e)}')
        return redirect('request_detail', type='batch_supply', request_id=batch_id)
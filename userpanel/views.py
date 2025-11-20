from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm, UserProfileUpdateForm
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordChangeDoneView
from app.models import UserProfile, Notification, Property, ActivityLog, Supply, SupplyRequestBatch, SupplyRequestItem, SupplyRequest, BorrowRequest, BorrowRequestBatch, BorrowRequestItem, Reservation, ReservationBatch, ReservationItem, DamageReport, PropertyCategory
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

# Import summary views
from .views_summary import UserRequestsSummaryView, export_requests_summary_pdf


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
        # Check and update reservation batch statuses (triggers active reservations)
        from app.models import ReservationBatch
        ReservationBatch.check_and_update_batches()
        
        # Get cart items from session
        cart_items = request.session.get('reservation_cart', [])
        
        # Get batch-level dates from session (set by request_again)
        batch_needed_date = request.session.get('reservation_needed_date')
        batch_return_date = request.session.get('reservation_return_date')
        
        # Convert cart items to objects with property details
        cart_items_data = []
        for item in cart_items:
            try:
                if 'property_id' not in item:
                    continue
                    
                property_obj = Property.objects.get(id=item['property_id'])
                
                # Try to get dates from item, fallback to batch-level dates
                needed_date_str = item.get('needed_date', batch_needed_date)
                return_date_str = item.get('return_date', batch_return_date)
                
                needed_date = None
                return_date = None
                
                if needed_date_str:
                    try:
                        needed_date = datetime.strptime(needed_date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass
                
                if return_date_str:
                    try:
                        return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass
                
                enriched_item = {
                    'supply': property_obj,  # Using 'supply' for template consistency
                    'quantity': item['quantity'],
                    'needed_date': needed_date,
                    'return_date': return_date,
                    'purpose': item.get('purpose', '')
                }
                cart_items_data.append(enriched_item)
            except (Property.DoesNotExist, KeyError, ValueError) as e:
                continue
        
        # Get available properties for the dropdown
        # Show all non-archived properties - users can request any quantity
        # Admin will validate availability during approval
        available_supplies = Property.objects.filter(
            is_archived=False,
            availability='available'
        )
        
        # Get property categories
        supply_categories = PropertyCategory.objects.all()
        
        # Get recent reservation batches
        from app.models import ReservationBatch
        recent_batches = ReservationBatch.objects.filter(user=request.user).order_by('-request_date')[:5]
        
        # Convert batches to dict format for template
        recent_requests_data = []
        for batch in recent_batches:
            first_item = batch.items.first()
            recent_requests_data.append({
                'id': batch.id,
                'item': first_item.property.property_name if first_item else 'No items',
                'quantity': batch.total_quantity,
                'status': batch.status,
                'date': batch.request_date,
                'needed_date': batch.earliest_needed_date,
                'return_date': batch.latest_return_date,
                'purpose': batch.purpose
            })
        
        # Get today's date for min date validation
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        
        return render(request, self.template_name, {
            'cart_items': cart_items_data,
            'available_supplies': available_supplies,
            'supply_categories': supply_categories,
            'recent_requests': recent_requests_data,
            'batch_needed_date': batch_needed_date,
            'batch_return_date': batch_return_date,
            'today': today
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
        
        # Get all properties that can be reported as damaged (not archived)
        available_supplies = Property.objects.filter(
            is_archived=False
        )
        
        # Get property categories for filter
        supply_categories = PropertyCategory.objects.all()
        
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
            'available_supplies': available_supplies,
            'supply_categories': supply_categories,
            'recent_requests': recent_requests_data
        })

    def post(self, request):
        form = DamageReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            
            # Handle image upload and compression
            if 'image' in request.FILES:
                report.set_image_from_file(request.FILES['image'])
            
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
        
        # Get all properties for the dropdown (not archived)
        available_supplies = Property.objects.filter(
            is_archived=False
        )
        
        # Get property categories for filter
        supply_categories = PropertyCategory.objects.all()
        
        return render(request, self.template_name, {
            'form': form,
            'available_supplies': available_supplies,
            'supply_categories': supply_categories,
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
        # Check if user must change password
        user = self.request.user
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.must_change_password:
                return reverse_lazy('user_password_change')
        except UserProfile.DoesNotExist:
            pass
        
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
            
            # Show message if password change is required
            if profile.must_change_password:
                messages.warning(self.request, 'You must change your password before continuing.')

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
        # Combine old SupplyRequest and new SupplyRequestBatch systems
        legacy_supply_requests = SupplyRequest.objects.filter(user=user).select_related('supply')
        batch_supply_requests = SupplyRequestBatch.objects.filter(user=user)
        
        # Create a combined list for supply requests with unified structure
        combined_supply_requests = []
        
        # Add legacy supply requests
        for req in legacy_supply_requests:
            combined_supply_requests.append({
                'id': req.id,
                'supply': req.supply,
                'quantity': req.quantity,
                'status': req.status,
                'request_date': req.request_date,
                'purpose': req.purpose,
                'sort_date': req.request_date,
                'type': 'legacy'
            })
        
        # Add batch supply requests
        for batch in batch_supply_requests:
            first_item = batch.items.first()
            combined_supply_requests.append({
                'id': batch.id,
                'supply': first_item.supply if first_item else None,
                'quantity': batch.total_quantity,
                'status': batch.status,
                'request_date': batch.request_date,
                'purpose': batch.purpose,
                'sort_date': batch.request_date,
                'type': 'batch',
                'batch_obj': batch
            })
        
        # Sort combined list by date descending
        combined_supply_requests.sort(key=lambda x: x['sort_date'], reverse=True)
        request_history_qs = combined_supply_requests
        
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
                'id': borrow.id,
                'property': borrow.property,
                'quantity': borrow.quantity,
                'status': borrow.status,
                'borrow_date': borrow.borrow_date,
                'return_date': borrow.return_date,
                'sort_date': borrow.borrow_date,
                'type': 'old'
            })
        
        # Add batch borrow items - deduplicate by batch_item_id
        seen_batch_items = set()
        for item in batch_borrow_items:
            if item.id not in seen_batch_items:
                seen_batch_items.add(item.id)
                # Use approved_quantity if available, otherwise quantity
                qty = item.approved_quantity if item.approved_quantity else item.quantity
                combined_borrows.append({
                    'id': item.batch_request.id,
                    'batch_item_id': item.id,  # Add unique item ID
                    'property': item.property,
                    'quantity': qty,
                    'status': item.status,
                    'borrow_date': item.claimed_date if item.claimed_date else item.batch_request.request_date,
                    'return_date': item.return_date,
                    'sort_date': item.claimed_date if item.claimed_date else item.batch_request.request_date,
                    'type': 'batch',
                    'item_id': item.id  # Store the actual item id
                })
        
        # Sort combined list by date descending
        combined_borrows.sort(key=lambda x: x['sort_date'], reverse=True)
        
        # Convert to queryset-like list for pagination
        borrow_history_qs = combined_borrows
        
        # Combine old Reservation and new ReservationBatch systems
        legacy_reservations = Reservation.objects.filter(user=user).select_related('item')
        batch_reservations = ReservationBatch.objects.filter(user=user)
        
        # Create a combined list for reservations with unified structure
        combined_reservations = []
        
        # Add legacy reservations
        for res in legacy_reservations:
            combined_reservations.append({
                'id': res.id,
                'item': res.item,
                'quantity': res.quantity,
                'status': res.status,
                'needed_date': res.needed_date,
                'return_date': res.return_date,
                'purpose': res.purpose,
                'reservation_date': res.reservation_date,
                'sort_date': res.reservation_date,
                'type': 'legacy'
            })
        
        # Add batch reservations
        for batch in batch_reservations:
            first_item = batch.items.first()
            combined_reservations.append({
                'id': batch.id,
                'item': first_item.property if first_item else None,
                'quantity': batch.total_quantity,
                'status': batch.status,
                'needed_date': batch.earliest_needed_date,
                'return_date': batch.latest_return_date,
                'purpose': batch.purpose,
                'reservation_date': batch.request_date,
                'sort_date': batch.request_date,
                'type': 'batch',
                'batch_obj': batch
            })
        
        # Sort combined list by date descending
        combined_reservations.sort(key=lambda x: x['sort_date'], reverse=True)
        reservation_history_qs = combined_reservations
        
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
            # Handle both legacy SupplyRequest and batch format
            if isinstance(req, dict):
                if req['type'] == 'legacy':
                    return {
                        'item': req['supply'].supply_name,
                        'quantity': req['quantity'],
                        'status': req['status'],
                        'date': req['request_date'],
                        'purpose': req['purpose'],
                    }
                else:  # batch
                    return {
                        'item': req['supply'].supply_name if req['supply'] else 'Batch Request',
                        'quantity': req['quantity'],
                        'status': req['status'],
                        'date': req['request_date'],
                        'purpose': req['purpose'],
                    }
            else:
                # Fallback for legacy SupplyRequest object
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
            # Handle both legacy Reservation and batch format
            if isinstance(res, dict):
                if res['type'] == 'legacy':
                    return {
                        'item': res['item'].property_name,
                        'quantity': res['quantity'],
                        'status': res['status'],
                        'needed_date': res['needed_date'],
                        'return_date': res['return_date'],
                        'purpose': res['purpose'],
                    }
                else:  # batch
                    return {
                        'item': res['item'].property_name if res['item'] else 'Batch Reservation',
                        'quantity': res['quantity'],
                        'status': res['status'],
                        'needed_date': res['needed_date'],
                        'return_date': res['return_date'],
                        'purpose': res['purpose'],
                    }
            else:
                # Fallback for legacy Reservation object
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
        request_count = len(combined_supply_requests)  # Now it's a list, not a queryset
        borrow_count = len(borrow_history_qs)  # Now it's a list, not a queryset
        reservation_count = len(combined_reservations)  # Now it's a list, not a queryset
        damage_count = damage_history_qs.count()

        # Get recent activity (last 5 activities from all types)
        recent_activity = []
        
        # Add recent requests (from combined list)
        for req in request_history_qs[:3]:
            if isinstance(req, dict):
                if req['type'] == 'legacy':
                    recent_activity.append({
                        'message': f'Requested {req["supply"].supply_name} (x{req["quantity"]})',
                        'timestamp': req['request_date'],
                        'type': 'request'
                    })
                else:  # batch
                    recent_activity.append({
                        'message': f'Submitted supply request batch (x{req["quantity"]} items)',
                        'timestamp': req['request_date'],
                        'type': 'request'
                    })
            else:
                # Fallback for legacy request
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
        
        # Add recent reservations (from combined list)
        for res in reservation_history_qs[:3]:
            if isinstance(res, dict):
                if res['type'] == 'legacy':
                    recent_activity.append({
                        'message': f'Reserved {res["item"].property_name} (x{res["quantity"]})',
                        'timestamp': res['reservation_date'],
                        'type': 'reservation'
                    })
                else:  # batch
                    recent_activity.append({
                        'message': f'Submitted reservation batch (x{res["quantity"]} items)',
                        'timestamp': res['reservation_date'],
                        'type': 'reservation'
                    })
            else:
                # Fallback for legacy reservation
                recent_activity.append({
                    'message': f'Reserved {res.item.property_name} (x{res.quantity})',
                    'timestamp': res.reservation_date,
                    'type': 'reservation'
                })
        
        # Sort by timestamp and get the 5 most recent
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:5]

        # Calculate 30-day activity trend for line chart
        activity_trend = self._calculate_30day_activity_trend(
            combined_supply_requests,
            combined_borrows,
            combined_reservations
        )

        # Calculate status distribution for pie chart
        status_distribution = self._calculate_status_distribution(
            combined_supply_requests, 
            combined_borrows, 
            combined_reservations
        )

        context.update({
            'notifications': Notification.objects.filter(user=user).order_by('-timestamp'),
            'unread_count': Notification.objects.filter(user=user, is_read=False).count(),

            # Stats counts
            'request_count': request_count,
            'borrow_count': borrow_count,
            'reservation_count': reservation_count,
            'damage_count': damage_count,
            
            # New dashboard metrics
            'pending_count': self._calculate_pending_count(combined_supply_requests, combined_borrows, combined_reservations),
            'approved_count': self._calculate_approved_count(combined_supply_requests, combined_borrows, combined_reservations),
            'overdue_count': self._calculate_overdue_count(combined_supply_requests, combined_borrows, combined_reservations),
            'active_count': self._calculate_active_count(combined_supply_requests, combined_borrows, combined_reservations),
            'approval_rate': self._calculate_approval_rate(combined_supply_requests, combined_borrows, combined_reservations),
            
            'recent_activity': recent_activity,
            
            # Items for action - with pagination
            'items_for_claiming': self._get_items_for_claiming(combined_supply_requests, combined_borrows),
            'items_for_claiming_page': Paginator(self._get_items_for_claiming(combined_supply_requests, combined_borrows), 5).get_page(self.request.GET.get('claiming_page', 1)),
            'active_reservations': self._get_active_reservations(combined_reservations),
            'active_reservations_page': Paginator(self._get_active_reservations(combined_reservations), 5).get_page(self.request.GET.get('reservations_page', 1)),
            'active_borrows': self._get_active_borrows(combined_borrows),
            'active_borrows_page': Paginator(self._get_active_borrows(combined_borrows), 5).get_page(self.request.GET.get('borrows_page', 1)),

            # Pass paginated page objects (converted to dict)
            'request_history': [request_to_dict(r) for r in request_history_page],
            'request_history_page': request_history_page,

            'borrow_history': [borrow_to_dict(b) for b in borrow_history_page],
            'borrow_history_page': borrow_history_page,

            'reservation_history': [reservation_to_dict(r) for r in reservation_history_page],
            'reservation_history_page': reservation_history_page,

            'damage_history': [damage_to_dict(d) for d in damage_history_page],
            'damage_history_page': damage_history_page,
            
            # Chart data
            'status_chart_data': json.dumps(status_distribution),
            'activity_trend_data': json.dumps(activity_trend),
        })

        return context

    def _calculate_pending_count(self, requests, borrows, reservations):
        """Count items with pending/pending_approval status - deduplicates batch items by batch ID, excludes items with return_date < tomorrow"""
        from django.utils import timezone
        from datetime import timedelta
        count = 0
        today = timezone.now().astimezone().date()
        tomorrow = today + timedelta(days=1)
        seen_batch_requests = set()
        for item in requests + borrows + reservations:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                return_date = item.get('return_date')
                if status in ['pending', 'pending_approval']:
                    # Exclude items with return_date < tomorrow (only count items with future return dates)
                    if return_date and return_date < tomorrow:
                        continue
                    # For batch items, group by batch ID to avoid counting each item in a batch
                    batch_id = item.get('id')
                    if batch_id not in seen_batch_requests:
                        seen_batch_requests.add(batch_id)
                        count += 1
        return count

    def _calculate_approved_count(self, requests, borrows, reservations):
        """Count items with approved/for_claiming status - deduplicates batch items by batch ID"""
        count = 0
        seen_batch_requests = set()
        for item in requests + borrows + reservations:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status in ['approved', 'for_claiming']:
                    # For batch items, group by batch ID to avoid counting each item in a batch
                    batch_id = item.get('id')
                    if batch_id not in seen_batch_requests:
                        seen_batch_requests.add(batch_id)
                        count += 1
        return count

    def _calculate_overdue_count(self, requests, borrows, reservations):
        """
        Count items that are overdue:
        1. Items with status='overdue' 
        2. Items with return_date < today and status in active/approved/for_claiming
        Deduplicates batch items by batch_item_id for accurate counting
        """
        from django.utils import timezone
        count = 0
        today = timezone.now().astimezone().date()
        seen_batch_items = set()  # Track individual batch items, not batches
        
        for item in borrows:  # Focus on borrows for overdue count
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                return_date = item.get('return_date')
                
                # Count items that are explicitly marked as overdue OR past their return date
                is_overdue = (status == 'overdue') or \
                            (status in ['active', 'approved', 'for_claiming'] and return_date and return_date < today)
                
                if is_overdue:
                    # For batch items, track by unique batch_item_id to count each item separately
                    batch_item_id = item.get('batch_item_id')
                    if batch_item_id:
                        if batch_item_id not in seen_batch_items:
                            seen_batch_items.add(batch_item_id)
                            count += 1
                    else:
                        # Old borrow system - count directly
                        count += 1
        
        return count

    def _calculate_active_count(self, requests, borrows, reservations):
        """Count items with active status that are currently active by date - grouped by batch"""
        count = 0
        today = timezone.now().astimezone().date()  # Use local timezone, not UTC
        seen_batch_requests = set()  # Track batch requests to avoid duplicates
        
        # Count active borrows that are within date range
        for item in borrows:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status == 'active':
                    borrow_date = item.get('borrow_date')
                    return_date = item.get('return_date')
                    if borrow_date and return_date:
                        borrow_date_only = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                        return_date_only = return_date.date() if hasattr(return_date, 'date') else return_date
                        if borrow_date_only <= today <= return_date_only:
                            # Group by batch ID for batch items
                            item_type = item.get('type', 'old')
                            if item_type == 'batch':
                                batch_id = item.get('id')
                                if batch_id not in seen_batch_requests:
                                    seen_batch_requests.add(batch_id)
                                    count += 1
                            else:
                                # Old borrow requests count individually
                                count += 1
        
        # Count active reservations that are within date range
        for item in reservations:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status == 'active':
                    needed_date = item.get('needed_date')
                    return_date = item.get('return_date')
                    if needed_date and return_date:
                        if needed_date <= today <= return_date:
                            count += 1
        
        return count

    def _calculate_approval_rate(self, requests, borrows, reservations):
        """Calculate the approval rate percentage"""
        all_items = requests + borrows + reservations
        total = len(all_items)
        
        if total == 0:
            return 0
        
        approved = 0
        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                # Count approved, for_claiming, partially_approved, completed, and returned as "approved"
                if status in ['approved', 'for_claiming', 'partially_approved', 'completed', 'returned', 'active']:
                    approved += 1
        
        rate = round((approved / total) * 100)
        return rate

    def _calculate_status_distribution(self, requests, borrows, reservations):
        """Calculate request status distribution for pie chart"""
        all_items = requests + borrows + reservations
        
        status_counts = {
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'completed': 0,
            'active': 0,
        }
        
        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                # Normalize status values to our categories
                if status in ['pending', 'pending_approval']:
                    status_counts['pending'] += 1
                elif status in ['approved', 'for_claiming', 'partially_approved']:
                    status_counts['approved'] += 1
                elif status == 'rejected':
                    status_counts['rejected'] += 1
                elif status == 'completed':
                    status_counts['completed'] += 1
                elif status == 'active':
                    status_counts['active'] += 1
                elif status == 'returned':
                    status_counts['completed'] += 1  # Count returned as completed
        
        return {
            'labels': ['Pending', 'Approved', 'Rejected', 'Completed', 'Active'],
            'data': [
                status_counts['pending'],
                status_counts['approved'],
                status_counts['rejected'],
                status_counts['completed'],
                status_counts['active'],
            ],
            'backgroundColor': ['#FFC107', '#4CAF50', '#F44336', '#2196F3', '#FF9800']
        }

    def _calculate_30day_activity_trend(self, requests, borrows, reservations):
        """Calculate activity trend for the last 30 days for line chart"""
        from datetime import timedelta, datetime
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = timezone.now().astimezone(local_tz).date()
        thirty_days_ago = today - timedelta(days=29)  # 30 days including today
        
        # Create a dictionary to track daily counts
        daily_counts = {}
        current_date = thirty_days_ago
        
        # Initialize all 30 days with 0 count
        while current_date <= today:
            daily_counts[current_date] = 0
            current_date += timedelta(days=1)
        
        # Count requests by date
        all_items = requests + borrows + reservations
        
        for item in all_items:
            if isinstance(item, dict):
                # Get the relevant date field
                date_field = None
                if 'sort_date' in item:
                    date_field = item['sort_date']
                elif 'request_date' in item:
                    date_field = item['request_date']
                elif 'borrow_date' in item:
                    date_field = item['borrow_date']
                elif 'reservation_date' in item:
                    date_field = item['reservation_date']
                
                # Convert to date if it's datetime
                if date_field:
                    if isinstance(date_field, datetime):
                        date_key = date_field.date()
                    else:
                        date_key = date_field
                    
                    # Only count items within the 30-day range
                    if thirty_days_ago <= date_key <= today:
                        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        # Create labels (day abbreviations) and data points
        labels = []
        data = []
        current_date = thirty_days_ago
        
        while current_date <= today:
            # Format: "Mon 5" (day abbreviation + date)
            label = current_date.strftime('%a %d')
            labels.append(label)
            data.append(daily_counts.get(current_date, 0))
            current_date += timedelta(days=1)
        
        return {
            'labels': labels,
            'data': data,
            'borderColor': '#2196F3',
            'backgroundColor': 'rgba(33, 150, 243, 0.1)',
            'tension': 0.4,
            'fill': True
        }

    def _get_items_for_claiming(self, requests, borrows):
        """Get supply requests and borrows that are approved and ready for claiming"""
        items_for_claiming = []
        seen_batch_requests = {}  # Track batch requests and sum quantities
        
        # Get supply requests ready for claiming
        for item in requests:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status in ['approved', 'for_claiming']:
                    item_name = item.get('item', '')
                    if not item_name:
                        request_id = item.get('id', '?')
                        request_date = item.get('request_date', '')
                        if request_date:
                            request_date = request_date.date() if hasattr(request_date, 'date') else request_date
                        item_name = f"Batch Request #{request_id} ({request_date})"
                    items_for_claiming.append({
                        'type': 'Supply Request',
                        'item_name': item_name,
                        'quantity': item.get('quantity', 0),
                        'date': item.get('request_date'),
                        'id': item.get('id'),
                        'icon': 'fa-box'
                    })
        
        # Get borrows ready for claiming - group by batch request to avoid duplicates
        for item in borrows:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status in ['approved', 'for_claiming']:
                    item_type = item.get('type', 'old')
                    batch_req_id = item.get('id')
                    
                    if item_type == 'batch':
                        # For batch items, group by batch request ID and sum quantities
                        if batch_req_id not in seen_batch_requests:
                            borrow_id = batch_req_id
                            borrow_date = item.get('borrow_date', '')
                            if borrow_date:
                                borrow_date = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                            item_name = f"Borrow Request #{borrow_id} ({borrow_date})"
                            
                            seen_batch_requests[batch_req_id] = {
                                'type': 'Borrow Request',
                                'item_name': item_name,
                                'quantity': item.get('quantity', 0),
                                'date': item.get('borrow_date'),
                                'id': batch_req_id,
                                'icon': 'fa-hand-holding'
                            }
                        else:
                            # Add to existing batch quantity
                            seen_batch_requests[batch_req_id]['quantity'] += item.get('quantity', 0)
                    else:
                        # For old borrow requests, add individually
                        item_name = item.get('item', '')
                        if not item_name:
                            borrow_id = item.get('id', '?')
                            borrow_date = item.get('borrow_date', '')
                            if borrow_date:
                                borrow_date = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                            item_name = f"Borrow Request #{borrow_id} ({borrow_date})"
                        items_for_claiming.append({
                            'type': 'Borrow Request',
                            'item_name': item_name,
                            'quantity': item.get('quantity', 0),
                            'date': item.get('borrow_date'),
                            'id': item.get('id'),
                            'icon': 'fa-hand-holding'
                        })
        
        # Add grouped batch requests
        items_for_claiming.extend(seen_batch_requests.values())
        
        return sorted(items_for_claiming, key=lambda x: x['date'] if x['date'] else '', reverse=True)

    def _get_active_reservations(self, reservations):
        """Get reservations that are approved and currently active"""
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        active_reservations = []
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = timezone.now().astimezone(local_tz).date()
        
        for item in reservations:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                if status in ['approved', 'active']:
                    needed_date = item.get('needed_date')
                    return_date = item.get('return_date')
                    
                    # Check if reservation is currently active (needed_date <= today <= return_date)
                    if needed_date and return_date:
                        if needed_date <= today <= return_date:
                            res_id = item.get('id', '?')
                            res_date = item.get('reservation_date', '')
                            if res_date:
                                res_date = res_date.date() if hasattr(res_date, 'date') else res_date
                            item_name = f"Reservation #{res_id} ({res_date})"
                            active_reservations.append({
                                'type': 'Reservation',
                                'item_name': item_name,
                                'quantity': item.get('quantity', 0),
                                'needed_date': needed_date,
                                'return_date': return_date,
                                'id': item.get('id'),
                                'icon': 'fa-calendar-check',
                                'days_remaining': (return_date - today).days
                            })
        
        return sorted(active_reservations, key=lambda x: x['days_remaining'])

    def _get_active_borrows(self, borrows):
        """Get borrows that are active or overdue and currently borrowed"""
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        active_borrows = []
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = timezone.now().astimezone(local_tz).date()
        seen_batch_requests = {}  # Track batch requests to avoid duplicates
        
        for item in borrows:
            if isinstance(item, dict):
                status = item.get('status', '').lower()
                # Include both active and overdue items
                if status in ['active', 'overdue']:
                    borrow_date = item.get('borrow_date')
                    return_date = item.get('return_date')
                    
                    # Check if borrow is currently active/overdue (borrow_date <= today)
                    if borrow_date and return_date:
                        # Convert datetime to date if necessary for comparison
                        borrow_date_only = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                        return_date_only = return_date.date() if hasattr(return_date, 'date') else return_date
                        
                        # Include if it's started (borrow_date <= today) and not yet returned
                        if borrow_date_only <= today:
                            item_type = item.get('type', 'old')
                            batch_req_id = item.get('id')
                            
                            # Calculate days remaining (negative if overdue)
                            days_remaining = (return_date_only - today).days
                            
                            if item_type == 'batch':
                                # For batch items, group by batch request ID to avoid duplicates
                                if batch_req_id not in seen_batch_requests:
                                    borrow_id = batch_req_id
                                    borrow_date_formatted = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                                    
                                    # Add status indicator for overdue items
                                    status_indicator = " [OVERDUE]" if status == 'overdue' or days_remaining < 0 else ""
                                    item_name = f"Borrow Request #{borrow_id} ({borrow_date_formatted}){status_indicator}"
                                    
                                    seen_batch_requests[batch_req_id] = {
                                        'type': 'Borrow Request',
                                        'item_name': item_name,
                                        'quantity': item.get('quantity', 0),
                                        'borrow_date': borrow_date,
                                        'return_date': return_date,
                                        'id': batch_req_id,
                                        'icon': 'fa-exclamation-triangle' if status == 'overdue' or days_remaining < 0 else 'fa-hand-holding-heart',
                                        'days_remaining': days_remaining,
                                        'is_overdue': status == 'overdue' or days_remaining < 0
                                    }
                                else:
                                    # Add to existing batch quantity
                                    seen_batch_requests[batch_req_id]['quantity'] += item.get('quantity', 0)
                            else:
                                # For old borrow requests, add individually
                                property_obj = item.get('property')
                                item_name = property_obj.property_name if property_obj else f"Item #{item.get('id', '?')}"
                                
                                # Add status indicator for overdue items
                                status_indicator = " [OVERDUE]" if status == 'overdue' or days_remaining < 0 else ""
                                
                                active_borrows.append({
                                    'type': 'Borrow Request',
                                    'item_name': f"{item_name}{status_indicator}",
                                    'quantity': item.get('quantity', 0),
                                    'borrow_date': borrow_date,
                                    'return_date': return_date,
                                    'id': item.get('id'),
                                    'icon': 'fa-exclamation-triangle' if status == 'overdue' or days_remaining < 0 else 'fa-hand-holding-heart',
                                    'days_remaining': days_remaining,
                                    'is_overdue': status == 'overdue' or days_remaining < 0
                                })
        
        # Add grouped batch requests
        active_borrows.extend(seen_batch_requests.values())
        
        # Sort by days_remaining (overdue items first - they have negative values)
        return sorted(active_borrows, key=lambda x: x['days_remaining'])


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
        
        # Clear the must_change_password flag after successful password change
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            if profile.must_change_password:
                profile.must_change_password = False
                profile.save()
                messages.success(self.request, 'Your password was successfully updated! You can now access the dashboard.')
            else:
                messages.success(self.request, 'Your password was successfully updated!')
        except UserProfile.DoesNotExist:
            messages.success(self.request, 'Your password was successfully updated!')
        
        return response

class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'registration/password_change_done.html'

    def get_template_names(self):
        return ['userpanel/password_change_done.html']
    
    def get(self, request, *args, **kwargs):
        # Redirect to dashboard instead of showing done page
        return redirect('user_dashboard')

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
    reservation_batch = get_object_or_404(ReservationBatch, id=request_id, user=request.user)
    
    if reservation_batch.status == 'pending':
        reservation_batch.status = 'cancelled'
        reservation_batch.save()
        
        # Update all items in the batch
        reservation_batch.items.update(status='cancelled')
        
        # Create items summary for log
        items_summary = []
        for item in reservation_batch.items.all()[:3]:
            items_summary.append(f"{item.property.property_name} (x{item.quantity})")
        if reservation_batch.items.count() > 3:
            items_summary.append(f"and {reservation_batch.items.count() - 3} more items")
        items_str = ", ".join(items_summary)
        
        ActivityLog.log_activity(
            user=request.user,
            action='cancel',
            model_name='ReservationBatch',
            object_repr=f"Reservation Batch #{reservation_batch.id}",
            description=f"Cancelled reservation batch with {reservation_batch.items.count()} items: {items_str}"
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
    """Add item to borrow cart session - uses batch return date"""
    if request.method == 'POST':
        property_id = request.POST.get('property_id')  # Changed from 'supply' to 'property_id'
        quantity = int(request.POST.get('quantity', 1))
        return_date = request.POST.get('return_date')  # Batch return date from form
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
            
            # No quantity validation here - let users request any amount
            # Validation will happen during admin approval
            
            # Validate return date
            if return_date:
                return_date_obj = datetime.strptime(return_date, '%Y-%m-%d').date()
                if return_date_obj < datetime.now().date():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Return date cannot be in the past'
                    })
            
            # Get or create cart in session
            cart = request.session.get('borrow_cart', [])
            
            # Check if item already exists in cart
            item_exists = False
            for item in cart:
                if item['property_id'] == property_id:
                    item['quantity'] += quantity
                    # Return date is now the same for all items (batch date)
                    item['return_date'] = return_date
                    item['purpose'] = purpose
                    item_exists = True
                    break
            
            if not item_exists:
                cart.append({
                    'property_id': property_id,
                    'quantity': quantity,
                    'return_date': return_date,  # All items use batch return date
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
    """Update item quantity in borrow cart session - return date is batch-wide and cannot be changed per-item"""
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        property_id = request.POST.get('supply_id')
        quantity = int(request.POST.get('quantity', 1))
        
        logger.info(f"Updating borrow cart item: property_id={property_id}, quantity={quantity}")
        
        try:
            property_obj = Property.objects.get(id=property_id)
            
            cart = request.session.get('borrow_cart', [])
            logger.info(f"Current borrow cart before update: {cart}")
            
            # Find and update the item - only quantity, return date is batch-wide
            for item in cart:
                if item['property_id'] == int(property_id):
                    item['quantity'] = quantity
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
    """Submit all items in borrow cart as a batch borrow request with single return date"""
    if request.method == 'POST':
        cart = request.session.get('borrow_cart', [])
        
        if not cart:
            return JsonResponse({
                'status': 'error',
                'message': 'No items in borrow list'
            })
        
        # Get batch return date from form
        batch_return_date = request.POST.get('batch_return_date')
        
        if not batch_return_date:
            return JsonResponse({
                'status': 'error',
                'message': 'Return date is required'
            })
        
        general_purpose = request.POST.get('general_purpose', '')
        
        try:
            # Parse batch return date
            batch_return_date_obj = datetime.strptime(batch_return_date, '%Y-%m-%d').date()
            
            # Validate return date
            if batch_return_date_obj < datetime.now().date():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Return date cannot be in the past'
                })
            
            # Create the batch borrow request
            batch_request = BorrowRequestBatch.objects.create(
                user=request.user,
                purpose=general_purpose,
                status='pending'
            )
            
            # Create individual borrow request items - all with same return date
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
                
                # Create the borrow request item using get_or_create to handle duplicates gracefully
                try:
                    item_obj, created = BorrowRequestItem.objects.get_or_create(
                        batch_request=batch_request,
                        property=property_obj,
                        defaults={
                            'quantity': item['quantity'],
                            'return_date': batch_return_date_obj,  # Use batch return date for all items
                            'status': 'pending'
                        }
                    )
                    # If item already existed, update it
                    if not created:
                        item_obj.quantity = item['quantity']
                        item_obj.return_date = batch_return_date_obj  # Use batch return date
                        item_obj.save()
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
                description=f"Submitted batch borrow request with {len(cart)} items (Return: {batch_return_date_obj}): {item_list}"
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
        
        # No quantity validation here - let users request any amount
        # Validation will happen during admin approval
        
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
                'available_quantity': property_obj.available_quantity
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
    """Submit all items in reservation cart as a batch reservation request"""
    if request.method == 'POST':
        cart = request.session.get('reservation_cart', [])
        
        if not cart:
            messages.error(request, 'No items in reservation list')
            return redirect('user_reserve')
        
        general_purpose = request.POST.get('general_purpose', '')
        
        try:
            # Validate all items before creating batch
            for item in cart:
                property_obj = Property.objects.get(id=item['property_id'])
                
                # Check if property is available for request
                if property_obj.availability != 'available':
                    messages.error(request, f'{property_obj.property_name} is not available for request')
                    return redirect('user_reserve')
                
                # Check if property is archived
                if property_obj.is_archived:
                    messages.error(request, f'{property_obj.property_name} is archived and cannot be requested')
                    return redirect('user_reserve')
            
            # Create the ReservationBatch
            reservation_batch = ReservationBatch.objects.create(
                user=request.user,
                purpose=general_purpose if general_purpose else "Batch reservation request",
                status='pending'
            )
            
            # Create ReservationItem for each cart item
            created_items = []
            for item in cart:
                property_obj = Property.objects.get(id=item['property_id'])
                
                reservation_item = ReservationItem.objects.create(
                    batch_request=reservation_batch,
                    property=property_obj,
                    quantity=item['quantity'],
                    needed_date=datetime.strptime(item['needed_date'], '%Y-%m-%d').date(),
                    return_date=datetime.strptime(item['return_date'], '%Y-%m-%d').date(),
                    status='pending',
                    remarks=item.get('purpose', '')
                )
                
                created_items.append(reservation_item)
            
            # Notification is handled automatically in ReservationBatch.save()
            # when the batch is created, so we don't need to send it manually here
            
            # Log activity for the batch request
            item_list = ", ".join([f"{Property.objects.get(id=item['property_id']).property_name} (x{item['quantity']})" 
                                 for item in cart[:3]])
            if len(cart) > 3:
                item_list += f" and {len(cart) - 3} more items"
            
            ActivityLog.log_activity(
                user=request.user,
                action='request',
                model_name='ReservationBatch',
                object_repr=f"Batch #{reservation_batch.id}",
                description=f"Submitted batch reservation request with {len(cart)} items: {item_list}"
            )
            
            # Clear the cart and batch dates
            request.session['reservation_cart'] = []
            request.session['reservation_needed_date'] = None
            request.session['reservation_return_date'] = None
            request.session['reservation_purpose'] = None
            request.session.modified = True
            
            # Show success message and redirect
            messages.success(request, f'Reservation request #{reservation_batch.id} submitted successfully! Your batch includes {len(created_items)} item(s).')
            return redirect('user_reserve')
            
        except Exception as e:
            messages.error(request, f'Error submitting requests: {str(e)}')
            return redirect('user_reserve')
    
    messages.error(request, 'Invalid request')
    return redirect('user_reserve')


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
        # Check and update reservation batch statuses (triggers active reservations)
        from app.models import ReservationBatch
        ReservationBatch.check_and_update_batches()
        
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
        
        # Get Reservations (batch)
        if request_type in ['all', 'reservation']:
            reservation_batches = ReservationBatch.objects.filter(
                user=self.request.user
            ).select_related('user').prefetch_related('items__property')
            
            for req in reservation_batches:
                # Create items summary
                items_summary = []
                for item in req.items.all()[:3]:  # Show first 3 items
                    items_summary.append(f"{item.property.property_name} (x{item.quantity})")
                
                if req.items.count() > 3:
                    items_summary.append(f"and {req.items.count() - 3} more items")
                
                request_data = {
                    'id': f"RB-{req.id}",
                    'type': 'Reservation',
                    'item_name': ", ".join(items_summary) if items_summary else "No items",
                    'quantity': req.total_quantity,
                    'status': req.get_status_display(),
                    'status_raw': req.status,
                    'date': req.request_date,
                    'purpose': req.purpose,
                    'needed_date': req.earliest_needed_date,
                    'return_date': req.latest_return_date,
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
                    search_query in req['type'].lower() or
                    search_query in req['id'].lower() or
                    search_query in req['status'].lower() or
                    search_query in str(req['quantity']).lower())
            ]
        
        # Sort by date (most recent first)
        all_requests.sort(key=lambda x: x['date'], reverse=True)
        
        # Get unique statuses for filter dropdown
        unique_statuses = set()
        for req in all_requests:
            unique_statuses.add((req['status_raw'], req['status']))
        unique_statuses = sorted(list(unique_statuses))
        
        # Pagination - use 6 items per page on mobile, 10 on desktop
        user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'windows phone'])
        
        items_per_page = 6 if is_mobile else 10
        paginator = Paginator(all_requests, items_per_page)
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
            'total_requests': len(all_requests),
            'is_mobile': is_mobile
        })
        
        return context


@login_required
def request_detail(request, type, request_id):
    """View to show detailed information about a specific request"""
    # Check and update reservation batch statuses (triggers active reservations)
    if type in ['reservation', 'batch_reservation']:
        from app.models import ReservationBatch
        ReservationBatch.check_and_update_batches()
    
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
            request_obj = get_object_or_404(ReservationBatch, id=request_id, user=request.user)
            template = 'userpanel/request_detail.html'
            items = request_obj.items.select_related('property').all()
            context = {
                'request_obj': request_obj,
                'request_type': 'Reservation',
                'items': [{'item': item.property, 'quantity': item.quantity} for item in items],
                'is_batch': True
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
            original_request = get_object_or_404(ReservationBatch, id=request_id, user=request.user)
            # Clear existing reservation cart and add all items from the batch
            reservation_items = []
            for item in original_request.items.all():
                reservation_items.append({
                    'property_id': item.property.id,
                    'property_name': item.property.property_name,
                    'quantity': item.quantity,
                    'needed_date': item.needed_date.strftime('%Y-%m-%d') if item.needed_date else None,
                    'return_date': item.return_date.strftime('%Y-%m-%d') if item.return_date else None,
                    'purpose': item.remarks if item.remarks else ''
                })
            request.session['reservation_cart'] = reservation_items
            # Store batch-level dates and purpose for display
            earliest_date = original_request.earliest_needed_date
            latest_date = original_request.latest_return_date
            request.session['reservation_needed_date'] = earliest_date.strftime('%Y-%m-%d') if earliest_date else None
            request.session['reservation_return_date'] = latest_date.strftime('%Y-%m-%d') if latest_date else None
            request.session['reservation_purpose'] = original_request.purpose if hasattr(original_request, 'purpose') else ''
            request.session.modified = True
            request.session.save()  # Explicitly save the session
            messages.success(request, f'Added {original_request.items.count()} items to your reservation list.')
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
        
        # No quantity validation here - let users request any amount
        # Validation will happen during admin approval
        available_quantity = supply.quantity_info.current_quantity
        
        # Get or create cart in session
        cart = request.session.get('supply_cart', [])
        
        # Check if item already exists in cart
        item_exists = False
        for item in cart:
            if item['supply_id'] == supply_id:
                # Update quantity
                item['quantity'] += quantity
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
            
            # Create individual items - use get_or_create to handle duplicates gracefully
            for cart_item in cart:
                supply = Supply.objects.get(id=cart_item['supply_id'])
                # Use get_or_create in case item already exists (though it shouldn't in a new batch)
                item, created = SupplyRequestItem.objects.get_or_create(
                    batch_request=batch_request,
                    supply=supply,
                    defaults={'quantity': cart_item['quantity']}
                )
                # If item already existed, update quantity
                if not created:
                    item.quantity = cart_item['quantity']
                    item.save()
            
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


@login_required
def get_pending_count(request):
    """API endpoint to get pending count filtered by type - counts items grouped by batch ID, excludes return_date < tomorrow"""
    from django.utils import timezone
    from datetime import timedelta
    user = request.user
    request_type = request.GET.get('type', 'all')
    today = timezone.now().astimezone().date()
    tomorrow = today + timedelta(days=1)
    
    # Get all requests for the user
    legacy_supply_requests = SupplyRequest.objects.filter(user=user)
    batch_supply_requests = SupplyRequestBatch.objects.filter(user=user)
    old_borrow_requests = BorrowRequest.objects.filter(user=user)
    batch_borrow_items = BorrowRequestItem.objects.filter(batch_request__user=user)
    legacy_reservations = Reservation.objects.filter(user=user)
    batch_reservations = ReservationBatch.objects.filter(user=user)
    
    count = 0
    seen_batch_requests = set()  # Track batch requests to avoid counting duplicates (group by batch ID)
    
    if request_type == 'all':
        # Count all pending items (legacy items counted directly, batch items grouped by batch ID)
        # For supply - exclude if return_date < tomorrow
        for item in legacy_supply_requests.filter(status__in=['pending', 'pending_approval']):
            if not item.return_date or item.return_date >= tomorrow:
                count += 1
        # Batch supply requests - count unique batches and exclude if return_date < tomorrow
        for item in batch_supply_requests.filter(status__in=['pending', 'pending_approval']):
            if (not item.earliest_return_date or item.earliest_return_date >= tomorrow) and item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
        # For borrow - exclude if return_date < tomorrow
        for item in old_borrow_requests.filter(status__in=['pending', 'pending_approval']):
            if not item.return_date or item.return_date >= tomorrow:
                count += 1
        # Batch borrow items - count unique batches (group by batch_request.id) and exclude if return_date < tomorrow
        for item in batch_borrow_items.filter(status__in=['pending', 'pending_approval']):
            if (not item.return_date or item.return_date >= tomorrow):
                batch_id = item.batch_request.id
                if batch_id not in seen_batch_requests:
                    seen_batch_requests.add(batch_id)
                    count += 1
        # For reservation - no return_date filter for pending reservations
        for item in legacy_reservations.filter(status__in=['pending', 'pending_approval']):
            count += 1
        # Batch reservations - count unique batches
        for item in batch_reservations.filter(status__in=['pending', 'pending_approval']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    elif request_type == 'supply':
        # Count only supply requests
        for item in legacy_supply_requests.filter(status__in=['pending', 'pending_approval']):
            if not item.return_date or item.return_date >= tomorrow:
                count += 1
        # Batch supply requests - count unique batches and exclude if return_date < tomorrow
        for item in batch_supply_requests.filter(status__in=['pending', 'pending_approval']):
            if (not item.earliest_return_date or item.earliest_return_date >= tomorrow) and item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    elif request_type == 'borrow':
        # Count only borrow requests
        for item in old_borrow_requests.filter(status__in=['pending', 'pending_approval']):
            if not item.return_date or item.return_date >= tomorrow:
                count += 1
        # Batch borrow items - count unique batches (group by batch_request.id) and exclude if return_date < tomorrow
        for item in batch_borrow_items.filter(status__in=['pending', 'pending_approval']):
            if (not item.return_date or item.return_date >= tomorrow):
                batch_id = item.batch_request.id
                if batch_id not in seen_batch_requests:
                    seen_batch_requests.add(batch_id)
                    count += 1
    elif request_type == 'reservation':
        # Count only reservations
        for item in legacy_reservations.filter(status__in=['pending', 'pending_approval']):
            count += 1
        # Batch reservations - count unique batches
        for item in batch_reservations.filter(status__in=['pending', 'pending_approval']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    
    return JsonResponse({'count': count})


@login_required
def get_active_count(request):
    """API endpoint to get active count filtered by type - counts items currently active by date"""
    user = request.user
    request_type = request.GET.get('type', 'all')
    today = timezone.now().astimezone().date()  # Use local timezone, not UTC
    
    count = 0
    seen_batch_requests = set()  # Track batch requests to avoid counting duplicates (group by batch ID)
    
    # Get batch borrow items that are active and within date range
    if request_type in ['all', 'borrow']:
        batch_borrow_items = BorrowRequestItem.objects.filter(batch_request__user=user, status='active')
        for item in batch_borrow_items:
            # Use borrow_date from claimed_date or request_date
            borrow_date = item.claimed_date if item.claimed_date else item.batch_request.request_date
            return_date = item.return_date
            
            if borrow_date and return_date:
                borrow_date_only = borrow_date.date() if hasattr(borrow_date, 'date') else borrow_date
                return_date_only = return_date.date() if hasattr(return_date, 'date') else return_date
                
                if borrow_date_only <= today <= return_date_only:
                    # Group by batch request ID to avoid counting duplicates (multiple items in same batch)
                    batch_id = item.batch_request.id
                    if batch_id not in seen_batch_requests:
                        seen_batch_requests.add(batch_id)
                        count += 1
    
    # Get batch reservations that are active and within date range
    if request_type in ['all', 'reservation']:
        batch_reservations = ReservationBatch.objects.filter(user=user, status='active')
        for batch in batch_reservations:
            needed_date = batch.earliest_needed_date
            return_date = batch.latest_return_date
            
            if needed_date and return_date:
                if needed_date <= today <= return_date:
                    count += 1
    
    return JsonResponse({'count': count})


@login_required
def get_approved_count(request):
    """API endpoint to get approved count filtered by type - counts items grouped by batch ID"""
    user = request.user
    request_type = request.GET.get('type', 'all')
    
    # Get all requests for the user
    legacy_supply_requests = SupplyRequest.objects.filter(user=user)
    batch_supply_requests = SupplyRequestBatch.objects.filter(user=user)
    old_borrow_requests = BorrowRequest.objects.filter(user=user)
    batch_borrow_items = BorrowRequestItem.objects.filter(batch_request__user=user)
    legacy_reservations = Reservation.objects.filter(user=user)
    batch_reservations = ReservationBatch.objects.filter(user=user)
    
    count = 0
    seen_batch_requests = set()  # Track batch requests to avoid counting duplicates (group by batch ID)
    
    if request_type == 'all':
        # Count all approved items (legacy items counted directly, batch items grouped by batch ID)
        count += legacy_supply_requests.filter(status__in=['approved', 'for_claiming']).count()
        # Batch supply requests - count unique batches
        for item in batch_supply_requests.filter(status__in=['approved', 'for_claiming', 'partially_approved']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
        count += old_borrow_requests.filter(status__in=['approved', 'for_claiming']).count()
        # Batch borrow items - count unique batches (group by batch_request.id)
        for item in batch_borrow_items.filter(status__in=['approved', 'for_claiming']):
            batch_id = item.batch_request.id
            if batch_id not in seen_batch_requests:
                seen_batch_requests.add(batch_id)
                count += 1
        count += legacy_reservations.filter(status__in=['approved', 'for_claiming']).count()
        # Batch reservations - count unique batches
        for item in batch_reservations.filter(status__in=['approved', 'for_claiming', 'partially_approved']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    elif request_type == 'supply':
        # Count only supply requests
        count += legacy_supply_requests.filter(status__in=['approved', 'for_claiming']).count()
        # Batch supply requests - count unique batches
        for item in batch_supply_requests.filter(status__in=['approved', 'for_claiming', 'partially_approved']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    elif request_type == 'borrow':
        # Count only borrow requests
        count += old_borrow_requests.filter(status__in=['approved', 'for_claiming']).count()
        # Batch borrow items - count unique batches (group by batch_request.id)
        for item in batch_borrow_items.filter(status__in=['approved', 'for_claiming']):
            batch_id = item.batch_request.id
            if batch_id not in seen_batch_requests:
                seen_batch_requests.add(batch_id)
                count += 1
    elif request_type == 'reservation':
        # Count only reservations
        count += legacy_reservations.filter(status__in=['approved', 'for_claiming']).count()
        # Batch reservations - count unique batches
        for item in batch_reservations.filter(status__in=['approved', 'for_claiming', 'partially_approved']):
            if item.id not in seen_batch_requests:
                seen_batch_requests.add(item.id)
                count += 1
    
    return JsonResponse({'count': count})
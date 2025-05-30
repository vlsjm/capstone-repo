from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView

from django.views import View
from django.contrib.auth import login, authenticate
from .models import Supply, Property, BorrowRequest, SupplyRequest, DamageReport, Reservation, ActivityLog, UserProfile, Notification, SupplyQuantity, SupplyHistory, PropertyHistory
from .forms import PropertyForm, SupplyForm, UserProfileForm, UserRegistrationForm
from django.contrib.auth.forms import AuthenticationForm

from datetime import timedelta, date
import json
from django.utils import timezone
from django.utils.timezone import now

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required

from django.db import models

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


@login_required
@require_POST
def mark_all_notifications_as_read(request):
    try:
        data = json.loads(request.body)
        ids = data.get('notification_ids', [])
        Notification.objects.filter(id__in=ids, user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def clear_all_notifications(request):
    try:
        Notification.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def mark_notification_as_read_ajax(request):
    notification_id = request.POST.get('notification_id')
    if not notification_id:
        return JsonResponse({'error': 'No notification ID provided'}, status=400)

    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Reservation, DamageReport, BorrowRequest, SupplyRequest, Notification

def reservation_detail(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks')
        reservation.remarks = remarks
        
        if action == 'approve':
            # Check for overlapping reservations
            overlapping_reservations = Reservation.objects.filter(
                item=reservation.item,
                status__in=['approved', 'active'],
                needed_date__lte=reservation.return_date,
                return_date__gte=reservation.needed_date
            ).exclude(pk=reservation.pk)
            
            # Calculate total quantity reserved for the overlapping period
            total_reserved = sum(r.quantity for r in overlapping_reservations)
            available_quantity = reservation.item.quantity - total_reserved
            
            if available_quantity >= reservation.quantity:
                reservation.status = 'approved'
                reservation.approved_date = timezone.now()
                Notification.objects.create(
                    user=reservation.user,
                    message=f"Your reservation for {reservation.item.property_name} has been approved.",
                    remarks=remarks
                )
                reservation.save()
                messages.success(request, 'Reservation approved successfully.')
            else:
                messages.error(request, f'Cannot approve reservation. Only {available_quantity} items available for the requested period.')
                return render(request, 'app/reservation_detail.html', {'reservation': reservation})
                
        elif action == 'reject':
            reservation.status = 'rejected'
            reservation.approved_date = timezone.now()
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation for {reservation.item.property_name} has been rejected.",
                remarks=remarks
            )
            reservation.save()
            messages.success(request, 'Reservation rejected successfully.')
            
        return redirect('user_reservations')
    return render(request, 'app/reservation_detail.html', {'reservation': reservation})


def damage_report_detail(request, pk):
    report_obj = get_object_or_404(DamageReport, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks')
        report_obj.remarks = remarks
        if action == 'reviewed':
            report_obj.status = 'reviewed'
            Notification.objects.create(
                user=report_obj.user,
                message=f"Your damage report for {report_obj.item.property_name} has been reviewed.",
                remarks=remarks
            )
        elif action == 'resolved':
            report_obj.status = 'resolved'
            Notification.objects.create(
                user=report_obj.user,
                message=f"Your damage report for {report_obj.item.property_name} has been resolved.",
                remarks=remarks
            )
        report_obj.save()
        return redirect('user_damage_reports')
    return render(request, 'app/report_details.html', {'report_obj': report_obj})


def borrow_request_details(request, pk):
    request_obj = get_object_or_404(BorrowRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks')
        request_obj.remarks = remarks

        if action == 'approve':
            request_obj.status = 'approved'
            request_obj.approved_date = timezone.now()
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your borrow request for {request_obj.property.property_name} has been approved.",
                remarks=remarks
            )
        elif action == 'decline':
            request_obj.status = 'declined'
            request_obj.approved_date = timezone.now()
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your borrow request for {request_obj.property.property_name} has been declined.",
                remarks=remarks
            )
        elif action == 'return':
            request_obj.status = 'returned'
            request_obj.actual_return_date = timezone.now().date()
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your borrow request for {request_obj.property.property_name} has been marked as returned.",
                remarks=remarks
            )
        elif action == 'overdue':
            request_obj.status = 'overdue'
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your borrow request for {request_obj.property.property_name} is overdue.",
                remarks=remarks
            )
        request_obj.save()
        return redirect('user_borrow_requests')
    return render(request, 'app/borrow_request_details.html', {'borrow_obj': request_obj})


def borrow_request_status_update(request, pk):
    request_obj = get_object_or_404(BorrowRequest, pk=pk)
    status = request.POST.get('status')
    remarks = request.POST.get('remarks')  # optional if you want to use it here

    if status == 'returned':
        request_obj.status = 'returned'
        request_obj.actual_return_date = timezone.now().date()
        Notification.objects.create(
            user=request_obj.user,
            message=f"Your borrow request for {request_obj.property.property_name} has been marked as returned.",
            remarks=remarks
        )
    elif status == 'overdue':
        request_obj.status = 'overdue'
        Notification.objects.create(
            user=request_obj.user,
            message=f"Your borrow request for {request_obj.property.property_name} is overdue.",
            remarks=remarks
        )
    request_obj.save()
    return redirect('user_borrow_requests')


def request_detail(request, pk):
    request_obj = get_object_or_404(SupplyRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks')
        request_obj.remarks = remarks
        if action == 'approve':
            request_obj.status = 'approved'
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your supply request for {request_obj.supply.supply_name} has been approved.",
                remarks=remarks
            )
        elif action == 'rejected':
            request_obj.status = 'rejected'
            Notification.objects.create(
                user=request_obj.user,
                message=f"Your supply request for {request_obj.supply.supply_name} has been rejected.",
                remarks=remarks
            )
        request_obj.approved_date = timezone.now()
        request_obj.save()
        return redirect('user_supply_requests')
    return render(request, 'app/request_details.html', {'request_obj': request_obj})

#user create user 
def create_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            role = form.cleaned_data['role']  

            try:
                group = Group.objects.get(name=role)
                user.groups.add(group)
            except Group.DoesNotExist:
                pass  

            UserProfile.objects.create(
                user=user,
                role=role,
                department=form.cleaned_data['department'],
                phone=form.cleaned_data['phone'],
            )
            return redirect('manage_users')
    else:
        form = UserRegistrationForm()
    users = UserProfile.objects.select_related('user').all()
    return render(request, 'app/manage_users.html', {'form': form, 'users': users})


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    template_name = 'app/manage_users.html'
    permission_required = 'app.view_user_profile'
    context_object_name = 'users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserRegistrationForm()  
        return context

class DashboardPageView(PermissionRequiredMixin,TemplateView):
    template_name = 'app/dashboard.html'
    permission_required = 'app.view_admin_dashboard'  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Notifications
        user_notifications = Notification.objects.filter(user=self.request.user).order_by('-timestamp')
        unread_notifications = user_notifications.filter(is_read=False)

        # Supply Status Counts
        supply_status_counts = [
            Supply.objects.filter(
                quantity_info__current_quantity__gt=models.F('quantity_info__minimum_threshold')
            ).count(),  # available
            Supply.objects.filter(
                quantity_info__current_quantity__gt=0,
                quantity_info__current_quantity__lte=models.F('quantity_info__minimum_threshold')
            ).count(),  # low_stock
            Supply.objects.filter(
                quantity_info__current_quantity=0
            ).count(),  # out_of_stock
        ]

        # Property Condition Counts
        property_condition_choices = [
            'In good condition',
            'Needing repair',
            'Unserviceable',
            'Obsolete',
            'No longer needed',
            'Not used since purchased',
        ]
        property_condition_counts = [
            Property.objects.filter(condition=condition).count()
            for condition in property_condition_choices
        ]

        # Request Status Counts (SupplyRequest)
        request_status_choices = ['pending', 'approved', 'rejected']
        request_status_counts = [
            SupplyRequest.objects.filter(status__iexact=status).count()
            for status in request_status_choices
        ]

        # Damage Report Status Counts
        damage_status_choices = ['pending', 'reviewed', 'resolved']
        damage_status_counts = [
            DamageReport.objects.filter(status__iexact=status).count()
            for status in damage_status_choices
        ]

        # Borrow Request Trends (last 6 months)
        now_date = now().date()
        borrow_trends_data = []

        for i in reversed(range(6)):
            start_date = now_date.replace(day=1) - timedelta(days=30*i)
            if i == 0:
                end_date = now_date
            else:
                end_date = now_date.replace(day=1) - timedelta(days=30*(i-1))

            count = BorrowRequest.objects.filter(
                borrow_date__date__gte=start_date,
                borrow_date__date__lt=end_date
            ).count()

            month_str = start_date.strftime('%b %Y')

            borrow_trends_data.append({
                'month': month_str,
                'count': count
            })

        # Property Categories Counts
        try:
            categories = [choice[0] for choice in Property.CATEGORY_CHOICES]
            property_categories_data = []
            for category in categories:
                count = Property.objects.filter(category=category).count()
                if count > 0:
                    property_categories_data.append({
                        'category': category,
                        'count': count
                    })
        except AttributeError:
            property_categories_data = []

        # User Activity by Role
        try:
            user_roles = [choice[0] for choice in UserProfile.ROLE_CHOICES]
            user_activity_data = []
            for role in user_roles:
                try:
                    count = ActivityLog.objects.filter(
                        user__userprofile__role=role
                    ).count()
                except:
                    count = UserProfile.objects.filter(role=role).count()

                if count > 0:
                    user_activity_data.append({
                        'role': role.replace('_', ' ').title(),
                        'count': count
                    })
        except (AttributeError, NameError):
            user_activity_data = []

        # Recent Requests for Preview Table
        recent_supply_requests = SupplyRequest.objects.select_related(
            'user', 'supply'
        ).order_by('-request_date')[:10]

        recent_borrow_requests = BorrowRequest.objects.select_related(
            'user', 'property'
        ).order_by('-borrow_date')[:10]

        recent_reservations = Reservation.objects.select_related(
            'user', 'item'
        ).order_by('-reservation_date')[:10]

        all_recent_requests = []
        
        for req in recent_supply_requests:
            all_recent_requests.append({
                'type': 'Supply Request',
                'user': req.user.username,
                'item': req.supply.supply_name,
                'quantity': req.quantity,
                'status': req.get_status_display(),
                'date': req.request_date,
                'purpose': req.purpose[:50] + '...' if len(req.purpose) > 50 else req.purpose
            })
        
        for req in recent_borrow_requests:
            all_recent_requests.append({
                'type': 'Borrow Request',
                'user': req.user.username,
                'item': req.property.property_name,
                'quantity': req.quantity,
                'status': req.get_status_display(),
                'date': req.borrow_date,
                'purpose': req.purpose[:50] + '...' if len(req.purpose) > 50 else req.purpose
            })
        
        for req in recent_reservations:
            all_recent_requests.append({
                'type': 'Reservation',
                'user': req.user.username,
                'item': req.item.property_name,
                'quantity': req.quantity,
                'status': req.get_status_display(),
                'date': req.reservation_date,
                'purpose': req.purpose[:50] + '...' if len(req.purpose) > 50 else req.purpose
            })
            
        all_recent_requests.sort(key=lambda x: x['date'], reverse=True)
        recent_requests_preview = all_recent_requests[:5]

        context.update({
            # Notifications
            'notifications': user_notifications,
            'unread_count': unread_notifications.count(),

            # supply status summary
            'supply_available': supply_status_counts[0],
            'supply_low_stock': supply_status_counts[1],
            'supply_out_of_stock': supply_status_counts[2],

            # property condition summary
            'property_in_good_condition': property_condition_counts[0],
            'property_needing_repair': property_condition_counts[1],
            'property_unserviceable': property_condition_counts[2],
            'property_obsolete': property_condition_counts[3],
            'property_no_longer_needed': property_condition_counts[4],
            'property_not_used_since_purchased': property_condition_counts[5],

            # request status summary
            'request_status_pending': request_status_counts[0],
            'request_status_approved': request_status_counts[1],
            'request_status_rejected': request_status_counts[2],

            # damage status summary
            'damage_status_pending': damage_status_counts[0],
            'damage_status_reviewed': damage_status_counts[1],
            'damage_status_resolved': damage_status_counts[2],

            # JSON serialized data for charts
            'borrow_trends_data': json.dumps(borrow_trends_data),
            'property_categories_counts': json.dumps(property_categories_data),
            'user_activity_by_role': json.dumps(user_activity_data),

            # total counts for cards
            'supply_count': Supply.objects.count(),
            'property_count': Property.objects.count(),
            'pending_requests': SupplyRequest.objects.filter(status__iexact='pending').count(),
            'damage_reports': DamageReport.objects.filter(status__iexact='pending').count(),
            
            # Recent requests for preview table
            'recent_requests_preview': recent_requests_preview,
        })

        return context


class ActivityPageView(PermissionRequiredMixin, ListView):
    model = ActivityLog
    template_name = 'app/activity.html'
    permission_required = 'app.view_activity_log'
    permission_denied_message = "You do not have permission to view the activity log."
    context_object_name = 'activitylog_list'
    paginate_by = 10

    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by('-timestamp')
        
        # Apply filters
        user_filter = self.request.GET.get('user')
        action_filter = self.request.GET.get('action')
        model_filter = self.request.GET.get('model')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if user_filter:
            queryset = queryset.filter(user_id=user_filter)
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        if model_filter:
            queryset = queryset.filter(model_name=model_filter)
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)

        # Filter by category if specified
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(model_name=category)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        context['actions'] = dict(ActivityLog.ACTION_CHOICES)
        
        # Get all unique models for filtering
        context['models'] = ActivityLog.objects.values_list('model_name', flat=True).distinct()
        
        # Get current category for highlighting in template
        context['current_category'] = self.request.GET.get('category', '')
        
        return context



class UserBorrowRequestListView(PermissionRequiredMixin, ListView):
    model = BorrowRequest
    template_name = 'app/borrow.html'
    permission_required = 'app.view_borrow_request'
    context_object_name = 'borrow_requests'
    paginate_by = 10

    def get_queryset(self):
        # Check for overdue items before getting the queryset
        BorrowRequest.check_overdue_items()
        return BorrowRequest.objects \
            .select_related('user', 'user__userprofile', 'property') \
            .order_by('-borrow_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = self.get_queryset()
        
        context['pending_requests'] = all_requests.filter(status='pending')
        context['approved_requests'] = all_requests.filter(status='approved')
        context['returned_requests'] = all_requests.filter(status='returned')
        context['overdue_requests'] = all_requests.filter(status='overdue')
        context['declined_requests'] = all_requests.filter(status='declined')
        return context

class UserSupplyRequestListView(PermissionRequiredMixin, ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    permission_required = 'app.view_supply_request'
    context_object_name = 'requests'
    paginate_by = 10
    
    def get_queryset(self):
        return SupplyRequest.objects.select_related('user', 'user__userprofile', 'supply').order_by('-request_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = self.get_queryset()
        
        context['pending_requests'] = all_requests.filter(status='pending')
        context['approved_requests'] = all_requests.filter(status='approved')
        context['rejected_requests'] = all_requests.filter(status='rejected')
        
        return context



class UserDamageReportListView(PermissionRequiredMixin, ListView):
    model = DamageReport
    template_name = 'app/reports.html'
    permission_required = 'app.view_damage_report'
    context_object_name = 'damage_reports'
    paginate_by = 10
    
    def get_queryset(self):
        return DamageReport.objects.select_related('user', 'user__userprofile', 'item').order_by('-report_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_reports = self.get_queryset()

        context['pending_reports'] = all_reports.filter(status='pending')
        context['reviewed_reports'] = all_reports.filter(status='reviewed')
        context['resolved_reports'] = all_reports.filter(status='resolved')

        return context


class UserReservationListView(PermissionRequiredMixin, ListView):
    model = Reservation
    template_name = 'app/reservation.html'
    permission_required = 'app.view_reservation'
    context_object_name = 'reservations'  # all reservations
    paginate_by = 10

    def get_queryset(self):
        return Reservation.objects.select_related(
            'user', 'user__userprofile', 'item'
        ).order_by('-reservation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_reservations = self.get_queryset()
        context['pending_reservations'] = all_reservations.filter(status='pending')
        context['approved_reservations'] = all_reservations.filter(status='approved')
        context['rejected_reservations'] = all_reservations.filter(status='rejected')
        return context



class SupplyListView(PermissionRequiredMixin, ListView):
    model = Supply
    template_name = 'app/supply.html'
    permission_required = 'app.view_supply'
    context_object_name = 'supplies'
    paginate_by = None  # Disable default pagination as we'll handle it per category

    def get_queryset(self):
        return Supply.objects.select_related('quantity_info').order_by('supply_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SupplyForm()
        context['today'] = date.today()
        
        # Get all supplies
        supplies = self.get_queryset()
        
        # Group supplies by category
        grouped = defaultdict(list)
        for supply in supplies:
            category = supply.get_category_display() or 'Uncategorized'
            grouped[category].append(supply)
            
            # Calculate days until expiration for debugging
            if supply.expiration_date:
                days_until = (supply.expiration_date - date.today()).days
                supply.days_until_expiration = days_until
        
        # Create paginated groups
        paginated_groups = {}
        for category, category_supplies in grouped.items():
            page_number = self.request.GET.get(f'page_{category}', 1)
            paginator = Paginator(category_supplies, 10)  # 10 items per category per page
            
            try:
                paginated_groups[category] = paginator.page(page_number)
            except PageNotAnInteger:
                paginated_groups[category] = paginator.page(1)
            except EmptyPage:
                paginated_groups[category] = paginator.page(paginator.num_pages)
        
        # Convert to regular dict and sort categories
        context['grouped_supplies'] = paginated_groups
        return context

@permission_required('app.view_supply')
def add_supply(request):
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            supply = form.save(commit=False)
            supply._logged_in_user = request.user
            supply.save()

            ActivityLog.objects.create(
                user=request.user,
                action='create',
                model_name='Supply',
                object_repr=str(supply),
                description=f"Supply '{supply.supply_name}' was added."
            )
            messages.success(request, 'Supply added successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')
    return redirect('supply_list')


@login_required
def edit_supply(request):
    if request.method == 'POST':
        supply_id = request.POST.get('id')
        supply = get_object_or_404(Supply, id=supply_id)
        
        # Store old values for activity log
        old_values = {
            'supply_name': supply.supply_name,
            'description': supply.description,
            'current_quantity': supply.quantity_info.current_quantity if supply.quantity_info else 0,
            'minimum_threshold': supply.quantity_info.minimum_threshold if supply.quantity_info else 0,
            'category': supply.category,
            'subcategory': supply.subcategory,
            'barcode': supply.barcode,
            'date_received': supply.date_received,
            'expiration_date': supply.expiration_date
        }

        # Update supply fields
        supply.supply_name = request.POST.get('supply_name')
        supply.description = request.POST.get('description')
        supply.category = request.POST.get('category')
        supply.subcategory = request.POST.get('subcategory')
        supply.barcode = request.POST.get('barcode')
        supply.date_received = request.POST.get('date_received')
        supply.expiration_date = request.POST.get('expiration_date') or None
        
        # Update quantity info
        current_quantity = int(request.POST.get('current_quantity', 0))
        minimum_threshold = int(request.POST.get('minimum_threshold', 0))
        
        if not supply.quantity_info:
            supply.quantity_info = SupplyQuantity.objects.create(
                current_quantity=current_quantity,
                minimum_threshold=minimum_threshold
            )
        else:
            supply.quantity_info.current_quantity = current_quantity
            supply.quantity_info.minimum_threshold = minimum_threshold
            supply.quantity_info.save()
        
        supply.save()

        # Create activity log for the update
        new_values = {
            'supply_name': supply.supply_name,
            'description': supply.description,
            'current_quantity': current_quantity,
            'minimum_threshold': minimum_threshold,
            'category': supply.category,
            'subcategory': supply.subcategory,
            'barcode': supply.barcode,
            'date_received': supply.date_received,
            'expiration_date': supply.expiration_date
        }

        # Log changes for each field that was modified
        for field, new_value in new_values.items():
            if str(new_value) != str(old_values[field]):
                ActivityLog.objects.create(
                    user=request.user,
                    action='UPDATE',
                    model_name='Supply',
                    description=f'Updated {field} from "{old_values[field]}" to "{new_value}" for supply: {supply.supply_name}'
                )

        messages.success(request, 'Supply updated successfully!')
        return redirect('supply_list')
    return JsonResponse({'error': 'Invalid request method'}, status=400)


def delete_supply(request, pk):
    supply = get_object_or_404(Supply, pk=pk)
    if request.method == 'POST':
        supply_name = supply.supply_name
        repr_str = str(supply)
        supply._logged_in_user = request.user
        supply.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Supply',
            object_repr=repr_str,
            description=f"Supply '{supply_name}' was deleted."
        )
        messages.success(request, 'Supply deleted successfully.')
    return redirect('supply_list')


class PropertyListView(PermissionRequiredMixin, ListView):
    model = Property
    template_name = 'app/property.html'
    context_object_name = 'properties'
    permission_required = 'app.view_property'
    paginate_by = None  # Disable default pagination as we'll handle it per category

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PropertyForm()

        # Get all properties
        properties = Property.objects.all()
        
        # Group properties by category
        grouped = defaultdict(list)
        for prop in properties:
            grouped[prop.get_category_display()].append(prop)

        # Create paginated groups
        paginated_groups = {}
        for category, category_properties in grouped.items():
            page_number = self.request.GET.get(f'page_{category}', 1)
            paginator = Paginator(category_properties, 10)  # 10 items per category per page
            
            try:
                paginated_groups[category] = paginator.page(page_number)
            except PageNotAnInteger:
                paginated_groups[category] = paginator.page(1)
            except EmptyPage:
                paginated_groups[category] = paginator.page(paginator.num_pages)

        context['grouped_properties'] = paginated_groups
        return context


def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop._logged_in_user = request.user
            prop.save()

            ActivityLog.objects.create(
                user=request.user,
                action='create',
                model_name='Property',
                object_repr=str(prop),
                description=f"Property '{prop.property_name}' was added."
            )

            messages.success(request, 'Property added successfully.')
        else:
            messages.error(request, f'Errors: {form.errors}')
    return redirect('property_list')


@login_required
def edit_property(request):
    if request.method == 'POST':
        property_id = request.POST.get('id')
        property_obj = get_object_or_404(Property, id=property_id)

        # Store old values for activity log
        old_values = {
            'property_name': property_obj.property_name,
            'description': property_obj.description,
            'barcode': property_obj.barcode,
            'unit_of_measure': property_obj.unit_of_measure,
            'unit_value': property_obj.unit_value,
            'quantity': property_obj.quantity,
            'location': property_obj.location,
            'condition': property_obj.condition,
            'category': property_obj.category,
            'availability': property_obj.availability
        }

        # Update property fields
        property_obj.property_name = request.POST.get('property_name')
        property_obj.description = request.POST.get('description')
        property_obj.barcode = request.POST.get('barcode')
        property_obj.unit_of_measure = request.POST.get('unit_of_measure')
        property_obj.unit_value = request.POST.get('unit_value')
        property_obj.quantity = request.POST.get('quantity')
        property_obj.location = request.POST.get('location')
        property_obj.condition = request.POST.get('condition')
        property_obj.category = request.POST.get('category')
        property_obj.availability = request.POST.get('availability')
        
        property_obj.save()

        # Create activity log for the update
        new_values = {
            'property_name': property_obj.property_name,
            'description': property_obj.description,
            'barcode': property_obj.barcode,
            'unit_of_measure': property_obj.unit_of_measure,
            'unit_value': property_obj.unit_value,
            'quantity': property_obj.quantity,
            'location': property_obj.location,
            'condition': property_obj.condition,
            'category': property_obj.category,
            'availability': property_obj.availability
        }

        # Log changes for each field that was modified
        for field, new_value in new_values.items():
            if str(new_value) != str(old_values[field]):
                ActivityLog.objects.create(
                    user=request.user,
                    action='UPDATE',
                    model_name='Property',
                    description=f'Updated {field} from "{old_values[field]}" to "{new_value}" for property: {property_obj.property_name}'
                )

        messages.success(request, 'Property updated successfully!')
        return redirect('property_list')
    return JsonResponse({'error': 'Invalid request method'}, status=400)


def delete_property(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        prop_name = prop.property_name
        repr_str = str(prop)
        prop._logged_in_user = request.user
        prop.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Property',
            object_repr=repr_str,
            description=f"Property '{prop_name}' was deleted."
        )

        messages.success(request, 'Property deleted successfully.')
    return redirect('property_list')


class CheckOutPageView(PermissionRequiredMixin, TemplateView):
    template_name = 'app/checkout.html'
    permission_required = 'app.view_checkout_page'  # Adjust permission as needed

class LandingPageView(TemplateView):
    """View for the landing page that provides login options for both admin and regular users."""
    template_name = "app/landing_page.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class AdminLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = AuthenticationForm
    next_page = reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.log_activity(
            user=self.request.user,
            action='login',
            model_name='User',
            object_repr=self.request.user.username,
            description=f"User {self.request.user.username} logged in"
        )
        return response

def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        ActivityLog.log_activity(
            user=request.user,
            action='logout',
            model_name='User',
            object_repr=username,
            description=f"User {username} logged out"
        )
    return LogoutView.as_view()(request)

@login_required
def create_supply_request(request):
    if request.method == 'POST':
        supply_id = request.POST.get('supply_id')
        quantity = request.POST.get('quantity')
        purpose = request.POST.get('purpose')
        
        supply = get_object_or_404(Supply, id=supply_id)
        supply_request = SupplyRequest.objects.create(
            user=request.user,
            supply=supply,
            quantity=quantity,
            purpose=purpose,
            status='pending'
        )

        ActivityLog.log_activity(
            user=request.user,
            action='request',
            model_name='Supply',
            object_repr=supply.supply_name,
            description=f"Requested {quantity} units of {supply.supply_name} for {purpose}"
        )

        messages.success(request, 'Supply request created successfully.')
        return redirect('user_supply_requests')

@login_required
def create_borrow_request(request):
    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        quantity = request.POST.get('quantity')
        borrow_date = request.POST.get('borrow_date')
        return_date = request.POST.get('return_date')
        purpose = request.POST.get('purpose')
        
        property_item = get_object_or_404(Property, id=property_id)
        borrow_request = BorrowRequest.objects.create(
            user=request.user,
            property=property_item,
            quantity=quantity,
            borrow_date=borrow_date,
            return_date=return_date,
            purpose=purpose,
            status='pending'
        )

        ActivityLog.log_activity(
            user=request.user,
            action='request',
            model_name='Property',
            object_repr=property_item.property_name,
            description=f"Requested to borrow {quantity} units of {property_item.property_name} from {borrow_date} to {return_date} for {purpose}"
        )

        messages.success(request, 'Borrow request created successfully.')
        return redirect('user_borrow_requests')

@login_required
def approve_supply_request(request, request_id):
    supply_request = get_object_or_404(SupplyRequest, id=request_id)
    supply_request.status = 'approved'
    supply_request.save()

    ActivityLog.log_activity(
        user=request.user,
        action='approve',
        model_name='SupplyRequest',
        object_repr=f"Request #{request_id}",
        description=f"Approved supply request for {supply_request.quantity} units of {supply_request.supply.supply_name}"
    )

    messages.success(request, 'Supply request approved successfully.')
    return redirect('supply_requests')

@login_required
def approve_borrow_request(request, request_id):
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    borrow_request.status = 'approved'
    borrow_request.save()

    ActivityLog.log_activity(
        user=request.user,
        action='approve',
        model_name='BorrowRequest',
        object_repr=f"Request #{request_id}",
        description=f"Approved borrow request for {borrow_request.quantity} units of {borrow_request.property.property_name}"
    )

    messages.success(request, 'Borrow request approved successfully.')
    return redirect('borrow_requests')

@login_required
def reject_supply_request(request, request_id):
    supply_request = get_object_or_404(SupplyRequest, id=request_id)
    supply_request.status = 'rejected'
    supply_request.save()

    ActivityLog.log_activity(
        user=request.user,
        action='reject',
        model_name='SupplyRequest',
        object_repr=f"Request #{request_id}",
        description=f"Rejected supply request for {supply_request.quantity} units of {supply_request.supply.supply_name}"
    )

    messages.success(request, 'Supply request rejected successfully.')
    return redirect('supply_requests')

@login_required
def reject_borrow_request(request, request_id):
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    borrow_request.status = 'rejected'
    borrow_request.save()

    ActivityLog.log_activity(
        user=request.user,
        action='reject',
        model_name='BorrowRequest',
        object_repr=f"Request #{request_id}",
        description=f"Rejected borrow request for {borrow_request.quantity} units of {borrow_request.property.property_name}"
    )

    messages.success(request, 'Borrow request rejected successfully.')
    return redirect('borrow_requests')

@login_required
def get_supply_history(request, supply_id):
    supply = get_object_or_404(Supply, id=supply_id)
    history = supply.history.all()
    
    history_data = []
    for entry in history:
        history_data.append({
            'date': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action': entry.action,
            'field': entry.field_name,
            'previous_value': entry.old_value or 'N/A',
            'new_value': entry.new_value or 'N/A',
            'changed_by': entry.user.username if entry.user else 'System'
        })
    
    return JsonResponse({'history': history_data})

@login_required
def get_property_history(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    history = property_obj.history.all()
    
    history_data = []
    for entry in history:
        history_data.append({
            'date': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action': entry.action,
            'field': entry.field_name,
            'previous_value': entry.old_value or 'N/A',
            'new_value': entry.new_value or 'N/A',
            'changed_by': entry.user.username if entry.user else 'System'
        })
    
    return JsonResponse({'history': history_data})

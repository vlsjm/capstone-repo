from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView

from django.views import View
from django.contrib.auth import login, authenticate
from .models import Supply, Property, BorrowRequest, SupplyRequest, DamageReport, Reservation, ActivityLog, UserProfile, Notification
from .forms import PropertyForm, SupplyForm, UserProfileForm, UserRegistrationForm
from django.contrib.auth.forms import AuthenticationForm

from datetime import timedelta
import json
from django.utils import timezone
from django.utils.timezone import now

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required


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
            reservation.status = 'approved'
            reservation.approved_date = timezone.now()
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation for {reservation.item.property_name} has been approved.",
                remarks=remarks
            )
        elif action == 'reject':
            reservation.status = 'rejected'
            reservation.approved_date = timezone.now()
            Notification.objects.create(
                user=reservation.user,
                message=f"Your reservation for {reservation.item.property_name} has been rejected.",
                remarks=remarks
            )
        reservation.save()
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

def create_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create the user
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )

            # Create user profile
            role = form.cleaned_data['role']
            UserProfile.objects.create(
                user=user,
                role=role,
                department=form.cleaned_data['department'],
                phone=form.cleaned_data['phone'],
            )

            # Assign to group based on role (e.g., ADMIN or USER)
            group_name = role.upper()  # Ensures case-insensitive match
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
            except Group.DoesNotExist:
                messages.warning(request, f"Group '{group_name}' does not exist. User created without group.")

            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, 'Please correct the errors in the form.')

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

        # Supply Status Counts
        supply_status_counts = [
            Supply.objects.filter(status__iexact='available').count(),
            Supply.objects.filter(status__iexact='low_stock').count(),
            Supply.objects.filter(status__iexact='out_of_stock').count(),
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
    ordering = ['-timestamp']



class UserBorrowRequestListView(PermissionRequiredMixin, ListView):
    model = BorrowRequest
    template_name = 'app/borrow.html'
    permission_required = 'app.view_borrow_request'
    context_object_name = 'borrow_requests'

    def get_queryset(self):
        return BorrowRequest.objects \
            .select_related('user', 'user__userprofile', 'property') \
            .order_by('-borrow_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_requests = self.get_queryset()

        context['pending_requests'] = all_requests.filter(status='pending')  # <-- added pending
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SupplyForm()
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


@csrf_exempt
def edit_supply(request):
    if request.method == 'POST':
        supply = get_object_or_404(Supply, pk=request.POST.get('id'))
        changes = []

        def check_change(label, old, new):
            if str(old) != str(new):
                changes.append(f"{label} changed from '{old}' to '{new}'")

        check_change('Supply Name', supply.supply_name, request.POST.get('supply_name'))
        check_change('Quantity', supply.quantity, request.POST.get('quantity'))
        check_change('Date Received', supply.date_received, request.POST.get('date_received'))
        check_change('Barcode', supply.barcode, request.POST.get('barcode'))
        check_change('Category', supply.category, request.POST.get('category'))
        check_change('Status', supply.status, request.POST.get('status'))

        new_available = request.POST.get('available_for_request') == 'on'
        if supply.available_for_request != new_available:
            changes.append(f"Available For Request changed from '{supply.available_for_request}' to '{new_available}'")

        supply.supply_name = request.POST.get('supply_name')
        supply.quantity = request.POST.get('quantity')
        supply.date_received = request.POST.get('date_received')
        supply.barcode = request.POST.get('barcode')
        supply.category = request.POST.get('category')
        supply.status = request.POST.get('status')
        supply.available_for_request = new_available
        supply._logged_in_user = request.user
        supply.save()

        description = f"Supply '{supply.supply_name}' updated: " + ", ".join(changes) if changes else f"Supply '{supply.supply_name}' was updated but no changes detected."

        ActivityLog.objects.create(
            user=request.user,
            action='update',
            model_name='Supply',
            object_repr=str(supply),
            description=description
        )

        messages.success(request, 'Supply updated successfully.')
    return redirect('supply_list')


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PropertyForm()

        grouped = defaultdict(list)
        for prop in context['properties']:
            grouped[prop.get_category_display()].append(prop)

        context['grouped_properties'] = dict(grouped)
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


@csrf_exempt
def edit_property(request):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=request.POST.get('id'))
        changes = []

        def check_change(label, old, new):
            if str(old) != str(new):
                changes.append(f"{label} changed from '{old}' to '{new}'")

        check_change('Property Name', prop.property_name, request.POST.get('property_name'))
        check_change('Description', prop.description, request.POST.get('description'))
        check_change('Barcode', prop.barcode, request.POST.get('barcode'))
        check_change('Unit of Measure', prop.unit_of_measure, request.POST.get('unit_of_measure'))
        check_change('Unit Value', prop.unit_value, request.POST.get('unit_value'))
        check_change('Quantity', prop.quantity, request.POST.get('quantity'))
        check_change('Location', prop.location, request.POST.get('location'))
        check_change('Condition', prop.condition, request.POST.get('condition'))
        check_change('Category', prop.category, request.POST.get('category'))

        prop.property_name = request.POST.get('property_name')
        prop.description = request.POST.get('description')
        prop.barcode = request.POST.get('barcode')
        prop.unit_of_measure = request.POST.get('unit_of_measure')
        prop.unit_value = request.POST.get('unit_value')
        prop.quantity = request.POST.get('quantity')
        prop.location = request.POST.get('location')
        prop.condition = request.POST.get('condition')
        prop.category = request.POST.get('category')
        prop._logged_in_user = request.user
        prop.save()

        description = f"Property '{prop.property_name}' updated: " + ", ".join(changes) if changes else f"Property '{prop.property_name}' was updated but no changes detected."

        ActivityLog.objects.create(
            user=request.user,
            action='update',
            model_name='Property',
            object_repr=str(prop),
            description=description
        )

        messages.success(request, 'Property updated successfully.')
    return redirect('property_list')


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
    template_name = "app/landing_page.html"

class AdminLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.get_user()
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.role != 'ADMIN':
                messages.error(self.request, 'Access denied. Admin credentials required.')
                return self.form_invalid(form)

        except UserProfile.DoesNotExist:
            messages.error(self.request, 'Access denied. Admin credentials required.')
            return self.form_invalid(form)

        return super().form_valid(form)

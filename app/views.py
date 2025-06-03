from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView
from django.core.exceptions import ValidationError

from django.db.models import Count



from django.views import View
from django.contrib.auth import login, authenticate, logout
from .models import(
    Supply, Property, BorrowRequest,
    SupplyRequest, DamageReport, Reservation,
    ActivityLog, UserProfile, Notification,
    SupplyQuantity, SupplyHistory, PropertyHistory,
    Department, PropertyCategory
)
from .forms import PropertyForm, SupplyForm, UserProfileForm, UserRegistrationForm, DepartmentForm
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
from django.utils import timezone
from datetime import timedelta

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import os
from .utils import generate_barcode

# Create a logger
logger = logging.getLogger(__name__)


def verify_email_settings():
    """Verify email settings are properly configured"""
    logger.info("Verifying email settings...")
    logger.info(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    logger.info(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    logger.info(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    logger.info(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    logger.info(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    logger.info(f"EMAIL_HOST_PASSWORD is set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
    
    # Check if .env file exists and is readable
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    logger.info(f".env file exists: {'Yes' if os.path.exists(env_path) else 'No'}")

#user create user 
def create_user(request):
    if request.method == 'POST':
        logger.info("Starting user creation process...")
        # Verify email settings before proceeding
        verify_email_settings()
        
        form = UserRegistrationForm(request.POST)
        logger.info("Checking form validity...")
        if form.is_valid():
            logger.info("Form is valid, proceeding with user creation...")
            try:
                # Create user
                initial_password = form.cleaned_data['password1']
                logger.info(f"Creating user with email: {form.cleaned_data['email']}")
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    password=initial_password,
        )
                user.is_staff = True

                user.save()

                role = form.cleaned_data['role']  
                logger.info(f"User created successfully with role: {role}")
            
                # Add user to group
                try:
                    group = Group.objects.get(name=role)
                    user.groups.add(group)
                    logger.info(f"Added user to group: {role}")
                except Group.DoesNotExist:
                    logger.warning(f"Group {role} does not exist")
                    messages.warning(request, f'Group {role} does not exist. User created without group assignment.')

                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    role=role,
                    department=form.cleaned_data['department'],
                    phone=form.cleaned_data['phone'],
                )
                logger.info("User profile created successfully")

                # Send welcome email
                try:
                    context = {
                        'user': user,
                        'user_profile': profile,
                        'initial_password': initial_password,
                    }
                    html_message = render_to_string('app/email/account_created.html', context)
                    plain_message = strip_tags(html_message)
                    
                    logger.info(f"Attempting to send welcome email to {user.email}...")
                    send_mail(
                        subject='Welcome to ResourceHive - Your Account Has Been Created',
                        message=plain_message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    logger.info("Welcome email sent successfully!")
                    messages.success(request, f'Account created successfully for {user.username} and welcome email sent.')
                except Exception as e:
                    logger.error(f"Failed to send welcome email: {str(e)}")
                    messages.warning(request, f'Account created successfully but failed to send welcome email. Error: {str(e)}')

                # Log the activity
                ActivityLog.log_activity(
                    user=request.user,
                    action='create',
                    model_name='User',
                    object_repr=user.username,
                    description=f"Created new user account for {user.username} with role {role}"
                )

                return redirect('manage_users')
                
            except Exception as e:
                logger.error(f"Error in user creation process: {str(e)}")
                messages.error(request, f'Error creating account: {str(e)}')
                return redirect('manage_users')
        else:
            logger.error(f"Form validation failed. Errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    users = UserProfile.objects.select_related('user').all()
    departments = Department.objects.all()
    return render(request, 'app/manage_users.html', {'form': form, 'users': users, 'departments': departments, })

def create_department(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Department.objects.create(name=name)
            messages.success(request, "Department added.")
    return redirect('manage_users')
def edit_department(request, dept_id):
    if request.method == 'POST':
        department = get_object_or_404(Department, id=dept_id)
        new_name = request.POST.get('name')
        if new_name:
            department.name = new_name
            department.save()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False})

def delete_department(request, dept_id):
    if request.method == 'POST':
        department = get_object_or_404(Department, id=dept_id)
        department.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})

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

        try:
            if action == 'approve':
                request_obj.status = 'approved'
                request_obj.approved_date = timezone.now()
                request_obj.save()  # This will trigger validation
                messages.success(request, 'Borrow request approved successfully.')
                Notification.objects.create(
                    user=request_obj.user,
                    message=f"Your borrow request for {request_obj.property.property_name} has been approved.",
                    remarks=remarks
                )
            elif action == 'decline':
                request_obj.status = 'declined'
                request_obj.approved_date = timezone.now()
                request_obj.save()
                messages.success(request, 'Borrow request declined successfully.')
                Notification.objects.create(
                    user=request_obj.user,
                    message=f"Your borrow request for {request_obj.property.property_name} has been declined.",
                    remarks=remarks
                )
            elif action == 'return':
                request_obj.status = 'returned'
                request_obj.actual_return_date = timezone.now().date()
                request_obj.save()
                messages.success(request, 'Borrow request marked as returned successfully.')
                Notification.objects.create(
                    user=request_obj.user,
                    message=f"Your borrow request for {request_obj.property.property_name} has been marked as returned.",
                    remarks=remarks
                )
            elif action == 'overdue':
                request_obj.status = 'overdue'
                request_obj.save()
                messages.warning(request, 'Borrow request marked as overdue.')
                Notification.objects.create(
                    user=request_obj.user,
                    message=f"Your borrow request for {request_obj.property.property_name} is overdue.",
                    remarks=remarks
                )
        except ValidationError as e:
            if 'quantity' in e.message_dict:
                messages.error(request, e.message_dict['quantity'][0])
            else:
                messages.error(request, "An error occurred while processing the request.")
            return render(request, 'app/borrow_request_details.html', {'borrow_obj': request_obj})
            
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


class UserProfileListView(PermissionRequiredMixin, ListView):
    model = UserProfile
    template_name = 'app/manage_users.html'
    permission_required = 'app.view_admin_module'
    context_object_name = 'users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserRegistrationForm()
        context['departments'] = Department.objects.all() 
        return context

class DashboardPageView(PermissionRequiredMixin,TemplateView):
    template_name = 'app/dashboard.html'
    permission_required = 'app.view_admin_module'  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        

        # Notifications
        user_notifications = Notification.objects.filter(user=self.request.user).order_by('-timestamp')
        unread_notifications = user_notifications.filter(is_read=False)


        #expiry count
        today = timezone.now().date()
        seven_days_later = today + timedelta(days=7) #7 days before the expiry date para ma trigger
        context['near_expiry_count'] = Supply.objects.filter(
            expiration_date__range=(today, seven_days_later),
            quantity_info__current_quantity__gt=0
        ).count()

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
    permission_required = 'app.view_admin_module'
    permission_denied_message = "You do not have permission to view the activity log."
    context_object_name = 'activitylog_list'
    paginate_by = 10

    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by('-timestamp')
        
        # Apply filters
        user_filter = self.request.GET.get('user')
        model_filter = self.request.GET.get('model')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if user_filter:
            queryset = queryset.filter(user_id=user_filter)
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
        
        # Get all unique models and sort them
        models = ActivityLog.objects.values_list('model_name', flat=True).distinct()
        context['models'] = sorted(set(models))  # Convert to set to ensure uniqueness and sort
        
        # Get current category for highlighting in template
        context['current_category'] = self.request.GET.get('category', '')
        
        return context



class UserBorrowRequestListView(PermissionRequiredMixin, ListView):
    model = BorrowRequest
    template_name = 'app/borrow.html'
    permission_required = 'app.view_admin_module'
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
    permission_required = 'app.view_admin_module'
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
    permission_required = 'app.view_admin_module'
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
    permission_required = 'app.view_admin_module'
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
    permission_required = 'app.view_admin_module'
    context_object_name = 'supplies'
    paginate_by = None  # Disable default pagination as we'll handle it per category

    def get_queryset(self):
        return Supply.objects.select_related('quantity_info').order_by('supply_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SupplyForm()
        context['today'] = date.today()
        context['supply_list'] = Supply.objects.select_related('quantity_info').all()
        
        # Get all supplies
        supplies = self.get_queryset()
        
         # Generate barcodes for each supply
        for supply in supplies:
            supply.barcode = generate_barcode(f"SUP-{supply.id}")

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

@permission_required('app.view_admin_module')
def add_supply(request):
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            try:
                # First save the supply
                supply = form.save(commit=False)
                supply._logged_in_user = request.user
                supply.save(user=request.user)

                # Create and save quantity info
                quantity_info = SupplyQuantity.objects.create(
                    supply=supply,
                    current_quantity=form.cleaned_data['current_quantity'],
                    minimum_threshold=form.cleaned_data['minimum_threshold']
                )

                # Update available_for_request based on quantity
                supply.available_for_request = (quantity_info.current_quantity > 0)
                supply.save(user=request.user)

                # Create activity log
                ActivityLog.log_activity(
                    user=request.user,
                    action='create',
                    model_name='Supply',
                    object_repr=str(supply),
                    description=f"Added new supply '{supply.supply_name}' with initial quantity {form.cleaned_data['current_quantity']}"
                )
                messages.success(request, 'Supply added successfully.')
            except Exception as e:
                if 'supply' in locals() and supply.pk:
                    supply.delete()
                messages.error(request, f'Error adding supply: {str(e)}')
        else:
            messages.error(request, f'Errors: {form.errors}')
    return redirect('supply_list')


@login_required
def edit_supply(request):
    if request.method == 'POST':
        supply_id = request.POST.get('id')
        supply = get_object_or_404(Supply, id=supply_id)
        
        try:
            # Store old values for activity log
            old_values = {
                'supply_name': supply.supply_name,
                'description': supply.description,
                'category': supply.category,
                'subcategory': supply.subcategory,
                'barcode': supply.barcode,
                'date_received': supply.date_received,
                'expiration_date': supply.expiration_date,
                'current_quantity': supply.quantity_info.current_quantity if supply.quantity_info else 0,
                'minimum_threshold': supply.quantity_info.minimum_threshold if supply.quantity_info else 0
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
                # Create new quantity info
                quantity_info = SupplyQuantity(
                    supply=supply,
                    current_quantity=current_quantity,
                    minimum_threshold=minimum_threshold
                )
                quantity_info.save(user=request.user)
            else:
                supply.quantity_info.current_quantity = current_quantity
                supply.quantity_info.minimum_threshold = minimum_threshold
                supply.quantity_info.save(user=request.user)
            
            # Save supply with user information
            supply.save(user=request.user)

            # Create activity log for the update
            changes = []
            for field, old_value in old_values.items():
                if field in ['current_quantity', 'minimum_threshold']:
                    new_value = current_quantity if field == 'current_quantity' else minimum_threshold
                else:
                    new_value = getattr(supply, field)
                if str(old_value) != str(new_value):
                    changes.append(f"{field}: {old_value} → {new_value}")

            if changes:
                ActivityLog.log_activity(
                    user=request.user,
                    action='update',
                    model_name='Supply',
                    object_repr=str(supply),
                    description=f"Updated supply '{supply.supply_name}'. Changes: {', '.join(changes)}"
                )

            messages.success(request, 'Supply updated successfully!')
            return redirect('supply_list')
        except Exception as e:
            messages.error(request, f'Error updating supply: {str(e)}')
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
    permission_required = 'app.view_admin_module'
    paginate_by = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        properties = Property.objects.all()
        
        # Generate barcodes for each property
        for prop in properties:
            # Use property_number for barcode if available, otherwise use ID
            barcode_number = prop.property_number if prop.property_number else f"PROP-{prop.id}"
            prop.barcode = generate_barcode(barcode_number)
            
        # Group properties by category
        properties_by_category = defaultdict(list)
        for prop in properties:
            properties_by_category[prop.category].append(prop)
        
        context['properties_by_category'] = dict(properties_by_category)
        context['categories'] = PropertyCategory.objects.all()
        context['form'] = PropertyForm()
        
        return context

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
    
@require_POST
def modify_property_quantity_generic(request):
    property_id = request.POST.get("property_id")
    action_type = request.POST.get("action_type")
    amount = int(request.POST.get("amount", 0))

    prop = get_object_or_404(Property, pk=property_id)
    old_quantity = prop.quantity

    if action_type == 'add':
        prop.quantity += amount
        prop.overall_quantity += amount
    elif action_type == 'remove':
        if amount > prop.quantity:
            messages.error(request, "Cannot remove more than current quantity.")
            return redirect('property_list')
        prop.quantity -= amount
        prop.overall_quantity -= amount

    prop.save()

    PropertyHistory.objects.create(
        property=prop,
        user=request.user,
        action='quantity_update',
        field_name='quantity',
        old_value=str(old_quantity),
        new_value=str(prop.quantity),
        remarks=f"{action_type} {amount}"
    )

    # Add activity log
    ActivityLog.log_activity(
        user=request.user,
        action='quantity_update',
        model_name='Property',
        object_repr=str(prop),
        description=f"{action_type.title()}ed {amount} units to/from property '{prop.property_name}'. Changed quantity from {old_quantity} to {prop.quantity}"
    )

    messages.success(request, f"Quantity successfully {action_type}ed.")
    return redirect('property_list')

def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            try:
                # First save the property
                prop = form.save(commit=False)
                
                # Set initial quantity equal to overall_quantity for new properties
                if not prop.pk:
                    prop.quantity = form.cleaned_data['overall_quantity']
                
                prop._logged_in_user = request.user
                prop.save(user=request.user)  # Pass the user to save method


            # Generate barcode based on property_number or ID
                barcode_number = prop.property_number if prop.property_number else f"PROP-{prop.id}"
                prop.barcode = generate_barcode(barcode_number)
                prop.save(user=request.user)
                # Create activity log using log_activity method
                ActivityLog.log_activity(
                    user=request.user,
                    action='create',
                    model_name='Property',
                    object_repr=str(prop),
                    description=f"Added new property '{prop.property_name}' with property number {prop.property_number}, overall quantity {prop.overall_quantity}, and initial quantity {prop.quantity}"
                )
                messages.success(request, 'Property added successfully.')
            except Exception as e:
                # If anything goes wrong, delete the property to maintain data consistency
                if 'prop' in locals() and prop.pk:
                    prop.delete()
                messages.error(request, f'Error adding property: {str(e)}')
                return redirect('property_list')
        else:
            # Add form errors to messages
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            messages.error(request, f'Please correct the following errors: {", ".join(error_messages)}')
    return redirect('property_list')


@login_required
def edit_property(request):
    if request.method == 'POST':
        property_id = request.POST.get('id')
        property_obj = get_object_or_404(Property, id=property_id)

        try:
            # Store old values for activity log
            old_values = {
                'property_number': property_obj.property_number,
                'property_name': property_obj.property_name,
                'description': property_obj.description,
                'barcode': property_obj.barcode,
                'unit_of_measure': property_obj.unit_of_measure,
                'unit_value': property_obj.unit_value,
                'overall_quantity': property_obj.overall_quantity,
                'quantity': property_obj.quantity,
                'location': property_obj.location,
                'condition': property_obj.condition,
                'category': property_obj.category,
                'availability': property_obj.availability
            }

            # Update property fields from POST data
            property_obj.property_number = request.POST.get('property_number')
            property_obj.property_name = request.POST.get('property_name')
            property_obj.description = request.POST.get('description')
            property_obj.barcode = request.POST.get('barcode')
            property_obj.unit_of_measure = request.POST.get('unit_of_measure')

            # Convert unit_value to float safely
            try:
                property_obj.unit_value = float(request.POST.get('unit_value', 0))
            except (TypeError, ValueError):
                property_obj.unit_value = 0

            # Convert overall_quantity to int safely
            try:
                property_obj.overall_quantity = int(request.POST.get('overall_quantity', 0))
            except (TypeError, ValueError):
                property_obj.overall_quantity = 0

            property_obj.location = request.POST.get('location')

            # Handle ForeignKey category assignment
            category_id = request.POST.get('category')
            if category_id:
                property_obj.category = get_object_or_404(PropertyCategory, id=category_id)
            else:
                property_obj.category = None  # or keep existing?

            # Handle condition and availability
            new_condition = request.POST.get('condition')
            property_obj.condition = new_condition

            unavailable_conditions = ['Needing repair', 'Unserviceable', 'No longer needed', 'Obsolete']
            if new_condition in unavailable_conditions:
                property_obj.availability = 'not_available'
            else:
                # Only use submitted availability if condition allows it
                property_obj.availability = request.POST.get('availability')

            # Save the updated property, assuming your model's save method accepts user param
            property_obj.save(user=request.user)

            # Create activity log for changes
            changes = []
            for field, old_value in old_values.items():
                new_value = getattr(property_obj, field)
                # For category FK, compare by id or name for clarity
                if field == 'category':
                    old_val_repr = old_value.name if old_value else 'None'
                    new_val_repr = new_value.name if new_value else 'None'
                    if old_val_repr != new_val_repr:
                        changes.append(f"category: {old_val_repr} → {new_val_repr}")
                else:
                    if str(old_value) != str(new_value):
                        if field == 'overall_quantity':
                            changes.append(f"overall quantity: {old_value} → {new_value} (current quantity updated accordingly)")
                        elif field == 'condition' and new_value in unavailable_conditions:
                            changes.append(f"condition: {old_value} → {new_value} (automatically set availability to Not Available)")
                        else:
                            changes.append(f"{field.replace('_', ' ')}: {old_value} → {new_value}")

            if changes:
                ActivityLog.log_activity(
                    user=request.user,
                    action='update',
                    model_name='Property',
                    object_repr=str(property_obj),
                    description=f"Updated property '{property_obj.property_name}'. Changes: {', '.join(changes)}"
                )

            messages.success(request, 'Property updated successfully!')

        except Exception as e:
            messages.error(request, f'Error updating property: {str(e)}')

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

def add_property_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            PropertyCategory.objects.create(name=name)
    return redirect('property_list') 

class CheckOutPageView(PermissionRequiredMixin, TemplateView):
    template_name = 'app/checkout.html'
    permission_required = 'app.view_admin_module'  # Adjust permission as needed

class LandingPageView(TemplateView):
    """View for the landing page that provides login options for both admin and regular users."""
    template_name = "app/landing_page.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

#meow   
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        user = self.request.user

        if user.groups.filter(name='ADMIN').exists():
            return reverse('dashboard')
        elif user.groups.filter(name='USER').exists():
            return reverse('user_dashboard')
        else:
            logout(self.request)
            messages.error(self.request, "You do not have permission to access the system. Contact the Admin.")
            return reverse('login')


    def dashboard(request):
        return render(request, 'app/dashboard.html')

    def user_dashboard(request):
        return render(request, 'userpanel/user_dashboard.html')



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
        
        # Create the supply request object
        supply_request = SupplyRequest(
            user=request.user,
            supply=supply,
            quantity=quantity,
            purpose=purpose,
            status='pending'
        )
        # Save to trigger the model's save method which handles notifications
        supply_request.save()

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
    history = supply.history.all().order_by('-timestamp')
    
    history_data = []
    for entry in history:
        history_data.append({
            'date': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action': entry.action,
            'field_name': entry.field_name,
            'old_value': entry.old_value if entry.old_value is not None else '-',
            'new_value': entry.new_value if entry.new_value is not None else '-',
            'user': entry.user.username if entry.user else 'System',
            'remarks': entry.remarks if entry.remarks else ''
        })
    
    return JsonResponse({
        'history': history_data
    })

@login_required
def get_property_history(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    history = property_obj.history.all().order_by('-timestamp')
    
    history_data = []
    for entry in history:
        history_data.append({
            'date': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'action': entry.action,
            'field_name': entry.field_name,
            'old_value': entry.old_value if entry.old_value is not None else '-',
            'new_value': entry.new_value if entry.new_value is not None else '-',
            'user': entry.user.username if entry.user else 'System',
            'remarks': entry.remarks if entry.remarks else ''
        })
    
    return JsonResponse({
        'history': history_data
    })

@require_POST
def modify_supply_quantity_generic(request):
    supply_id = request.POST.get("supply_id")
    action_type = request.POST.get("action_type")
    amount = int(request.POST.get("amount", 0))

    supply = get_object_or_404(Supply, pk=supply_id)

    try:
        quantity_info = supply.quantity_info
        old_quantity = quantity_info.current_quantity

        if action_type == 'add':
            quantity_info.current_quantity += amount
        elif action_type == 'remove':
            if amount > quantity_info.current_quantity:
                messages.error(request, "Cannot remove more than current quantity.")
                return redirect('supply_list')
            quantity_info.current_quantity -= amount

        quantity_info.save(user=request.user)

        # Update supply's available_for_request status
        supply.available_for_request = (quantity_info.current_quantity > 0)
        supply.save(user=request.user)

        SupplyHistory.objects.create(
            supply=supply,
            user=request.user,
            action='quantity_update',
            field_name='quantity',
            old_value=str(old_quantity),
            new_value=str(quantity_info.current_quantity),
            remarks=f"{action_type} {amount}"
        )

        # Add activity log
        ActivityLog.log_activity(
            user=request.user,
            action='quantity_update',
            model_name='Supply',
            object_repr=str(supply),
            description=f"{action_type.title()}ed {amount} units to/from supply '{supply.supply_name}'. Changed quantity from {old_quantity} to {quantity_info.current_quantity}"
        )

        messages.success(request, f"Quantity successfully {action_type}ed.")
    except SupplyQuantity.DoesNotExist:
        messages.error(request, "Supply quantity information not found.")

    return redirect('supply_list')

class AdminPasswordChangeView(PasswordChangeView):
    template_name = 'app/password_change.html'
    success_url = reverse_lazy('password_change_done')

    def get_template_names(self):
        return [self.template_name]

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password was successfully updated!')
        return response

class AdminPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'app/password_change_done.html'

    def get_template_names(self):
        return [self.template_name]
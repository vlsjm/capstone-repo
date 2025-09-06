from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.urls import reverse

@require_POST
def update_damage_status(request, pk):
    report = get_object_or_404(DamageReport, pk=pk)
    action = request.POST.get('update_action')
    remarks = report.remarks or ''
    if action == 'unserviceable':
        report.remarks = f"Classified as Unserviceable. {remarks}"
        report.save()
    elif action == 'needs_repair':
        report.remarks = f"Classified as Needs Repair. {remarks}"
        report.save()
    elif action == 'back_in_use':
        report.status = 'reviewed'
        report.remarks = f"Marked as Back in Use. {remarks}"
        report.save()
    return HttpResponseRedirect(reverse('damaged_items_management'))

@require_POST
def update_property_condition(request, property_number):
    property_obj = get_object_or_404(Property, property_number=property_number)
    new_condition = request.POST.get('condition')
    if new_condition in ['Unserviceable', 'Needing repair', 'Working', 'In good condition']:
        property_obj.condition = new_condition
        if new_condition in ['Unserviceable', 'Needing repair']:
            property_obj.availability = 'not_available'
        else:
            property_obj.availability = 'available'
        property_obj.save()
    return HttpResponseRedirect(reverse('damaged_items_management'))
# Damaged Items Management Page (Admin)
from django.views.generic import TemplateView

from django.contrib.auth.mixins import PermissionRequiredMixin

class DamagedItemsManagementView(PermissionRequiredMixin, TemplateView):
    permission_required = 'app.view_admin_module'
    template_name = 'app/damaged_items_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get properties with unserviceable condition
        unserviceable_properties = Property.objects.filter(condition__iexact='Unserviceable')
        
        # Get properties needing repair
        needs_repair_properties = Property.objects.filter(condition__iexact='Needing repair')
        
        # Also include damage reports that have been classified (for backward compatibility)
        unserviceable_reports = DamageReport.objects.filter(status='resolved', remarks__icontains='Unserviceable')
        needs_repair_reports = DamageReport.objects.filter(status='resolved', remarks__icontains='Needs Repair')
        
        context['unserviceable_items'] = unserviceable_properties
        context['needs_repair_items'] = needs_repair_properties
        context['unserviceable_reports'] = unserviceable_reports
        context['needs_repair_reports'] = needs_repair_reports
        
        return context
from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.views import View
from django.contrib.auth import login, authenticate, logout
from .models import(
    Supply, Property, BorrowRequest, BorrowRequestBatch, BorrowRequestItem,
    SupplyRequest, DamageReport, Reservation,
    ActivityLog, UserProfile, Notification,
    SupplyQuantity, SupplyHistory, PropertyHistory,
    Department, PropertyCategory, SupplyCategory, SupplySubcategory,
    SupplyRequestBatch, SupplyRequestItem
)
from .forms import PropertyForm, SupplyForm, UserProfileForm, UserRegistrationForm, DepartmentForm, SupplyRequestBatchForm, SupplyRequestItemForm, SupplyRequestBatchForm, SupplyRequestItemForm
from django.contrib.auth.forms import AuthenticationForm
from datetime import timedelta, date, datetime
import json
from django.utils import timezone
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
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
from openpyxl import Workbook
from django.http import HttpResponse
from datetime import datetime
from openpyxl.styles import PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import MergedCell
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
                initial_password = form.cleaned_data['password']
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

@permission_required('app.view_admin_module')
def edit_department(request, dept_id):
    if request.method == 'POST':
        department = get_object_or_404(Department, id=dept_id)
        new_name = request.POST.get('name')
        if new_name:
            department.name = new_name
            department.save()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False})

@permission_required('app.view_admin_module')
def delete_department(request, dept_id):
    if request.method == 'POST':
        department = get_object_or_404(Department, id=dept_id)
        # Check if there are any users in this department
        if UserProfile.objects.filter(department=department).exists():
            return JsonResponse({
                "success": False,
                "error": "Cannot delete department that has users assigned to it. Please reassign or remove users first."
            })
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
        if action == 'classify':
            classification = request.POST.get('classification')
            if classification == 'unserviceable':
                report_obj.status = 'resolved'
                report_obj.remarks = f"Classified as Unserviceable. {remarks}"
                # Update property condition
                report_obj.item.condition = 'Unserviceable'
                report_obj.item.availability = 'not_available'
                report_obj.item.save()
                report_obj.save()
                Notification.objects.create(
                    user=report_obj.user,
                    message=f"Your damage report for {report_obj.item.property_name} has been classified as Unserviceable.",
                    remarks=remarks
                )
            elif classification == 'needs_repair':
                report_obj.status = 'resolved'
                report_obj.remarks = f"Classified as Needs Repair. {remarks}"
                # Update property condition
                report_obj.item.condition = 'Needing repair'
                report_obj.item.availability = 'not_available'
                report_obj.item.save()
                report_obj.save()
                Notification.objects.create(
                    user=report_obj.user,
                    message=f"Your damage report for {report_obj.item.property_name} has been classified as Needs Repair.",
                    remarks=remarks
                )
            elif classification == 'good_condition':
                report_obj.status = 'reviewed'
                report_obj.remarks = f"Classified as Good Condition. {remarks}"
                # Update property condition
                report_obj.item.condition = 'In good condition'
                report_obj.item.availability = 'available'
                report_obj.item.save()
                report_obj.save()
                Notification.objects.create(
                    user=report_obj.user,
                    message=f"Your damage report for {report_obj.item.property_name} has been reviewed and marked as Good Condition.",
                    remarks=remarks
                )
            return redirect('user_damage_reports')
        elif action == 'reviewed':
            report_obj.status = 'reviewed'
            Notification.objects.create(
                user=report_obj.user,
                message=f"Your damage report for {report_obj.item.property_name} has been reviewed.",
                remarks=remarks
            )
            report_obj.save()
            return redirect('user_damage_reports')
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
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'department')
        
        # Get filter parameters from the URL
        search = self.request.GET.get('search', '')
        role = self.request.GET.get('role', '')
        department = self.request.GET.get('department', '')
        
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(department__name__icontains=search)
            )
        
        if role:
            queryset = queryset.filter(role=role)
            
        if department:
            queryset = queryset.filter(department__name=department)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserRegistrationForm()
        context['departments'] = Department.objects.all()
        # Add current filter values to context
        context['search'] = self.request.GET.get('search', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['selected_department'] = self.request.GET.get('department', '')
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
        seven_days_later = today + timedelta(days=30) #30 days before the expiry date para ma trigger
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

        # Request Status Counts (SupplyRequest + SupplyRequestBatch)
        request_status_choices = ['pending', 'approved', 'rejected', 'partially_approved', 'for_claiming']
        request_status_counts = []
        for status in request_status_choices:
            legacy_count = SupplyRequest.objects.filter(status__iexact=status).count()
            batch_count = SupplyRequestBatch.objects.filter(status__iexact=status).count()
            request_status_counts.append(legacy_count + batch_count)

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
            # Get all categories from PropertyCategory model
            categories = PropertyCategory.objects.all()
            property_categories_data = []
            for category in categories:
                count = Property.objects.filter(category=category).count()
                if count > 0:
                    property_categories_data.append({
                        'category': category.name,
                        'count': count
                    })
        except Exception as e:
            logger.error(f"Error getting property categories data: {str(e)}")
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

        # Department Request Analysis
        try:
            # Get requests by department for both SupplyRequest and BorrowRequest
            departments = Department.objects.all()
            department_request_data = []
            
            for department in departments:
                # Count supply requests from users in this department (legacy system)
                legacy_supply_request_count = SupplyRequest.objects.filter(
                    user__userprofile__department=department
                ).count()
                
                # Count batch supply requests from users in this department (new system)
                batch_supply_request_count = SupplyRequestBatch.objects.filter(
                    user__userprofile__department=department
                ).count()
                
                # Total supply requests (legacy + batch)
                total_supply_requests = legacy_supply_request_count + batch_supply_request_count
                
                # Count borrow requests from users in this department
                borrow_request_count = BorrowRequest.objects.filter(
                    user__userprofile__department=department
                ).count()
                
                # Count reservations from users in this department
                reservation_count = Reservation.objects.filter(
                    user__userprofile__department=department
                ).count()
                
                # Total requests from this department
                total_requests = total_supply_requests + borrow_request_count + reservation_count
                
                if total_requests > 0:
                    department_request_data.append({
                        'department': department.name,
                        'total_requests': total_requests,
                        'supply_requests': total_supply_requests,
                        'borrow_requests': borrow_request_count,
                        'reservations': reservation_count
                    })
            
            # Sort by total requests descending
            department_request_data.sort(key=lambda x: x['total_requests'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting department request data: {str(e)}")
            department_request_data = []

        # Recent Requests for Preview Table
        recent_supply_requests = SupplyRequest.objects.select_related(
            'user', 'supply'
        ).order_by('-request_date')[:5]

        recent_batch_requests = SupplyRequestBatch.objects.select_related(
            'user'
        ).order_by('-request_date')[:5]

        recent_borrow_requests = BorrowRequest.objects.select_related(
            'user', 'property'
        ).order_by('-borrow_date')[:5]

        recent_reservations = Reservation.objects.select_related(
            'user', 'item'
        ).order_by('-reservation_date')[:5]

        all_recent_requests = []
        
        # Add legacy supply requests
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
        
        # Add batch supply requests
        for req in recent_batch_requests:
            items_text = f"{req.total_items} items"
            if req.total_items <= 3:
                try:
                    items_list = ", ".join([f"{item.supply.supply_name} (x{item.quantity})" for item in req.items.all()])
                    items_text = items_list
                except:
                    items_text = f"{req.total_items} items"
            
            all_recent_requests.append({
                'type': 'Batch Supply Request',
                'user': req.user.username,
                'item': items_text,
                'quantity': req.total_quantity,
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
            'department_requests_data': json.dumps(department_request_data),

            # total counts for cards
            'supply_count': Supply.objects.count(),
            'property_count': Property.objects.count(),
            'pending_requests': SupplyRequest.objects.filter(status__iexact='pending').count() + SupplyRequestBatch.objects.filter(status__iexact='pending').count(),
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



class UserSupplyRequestListView(PermissionRequiredMixin, ListView):
    model = SupplyRequestBatch
    template_name = 'app/requests.html'
    permission_required = 'app.view_admin_module'
    context_object_name = 'batch_requests'
    paginate_by = 8  # Optimized for table layout - shows 8 requests per page for better UX
    
    def get_queryset(self):
        # Show batch requests ordered by oldest first
        return SupplyRequestBatch.objects.select_related('user', 'user__userprofile', 'user__userprofile__department').prefetch_related('items__supply').order_by('request_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current tab from request
        current_tab = self.request.GET.get('tab', 'pending')
        
        # Get search and filter parameters
        search_query = self.request.GET.get('search', '').strip()
        department_filter = self.request.GET.get('department', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        # Base queryset with related data
        base_queryset = SupplyRequestBatch.objects.select_related('user', 'user__userprofile', 'user__userprofile__department').prefetch_related('items__supply').order_by('request_date')
        
        # Apply search filter
        if search_query:
            # Search only by supply request ID/number
            try:
                # Try to extract just the number from the search query
                search_number = ''.join(filter(str.isdigit, search_query))
                if search_number:
                    base_queryset = base_queryset.filter(id=int(search_number))
                else:
                    # If no number found, return empty queryset
                    base_queryset = base_queryset.none()
            except (ValueError, TypeError):
                # If conversion fails, return empty queryset
                base_queryset = base_queryset.none()
        
        # Apply department filter
        if department_filter:
            base_queryset = base_queryset.filter(user__userprofile__department__id=department_filter)
        
        # Apply date range filters
        if date_from:
            try:
                from django.utils import timezone
                from datetime import datetime
                # Convert string to datetime and make it timezone aware
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                date_from_aware = timezone.make_aware(date_from_obj)
                base_queryset = base_queryset.filter(request_date__date__gte=date_from_aware.date())
            except ValueError:
                # Invalid date format, ignore filter
                pass
        if date_to:
            try:
                from django.utils import timezone
                from datetime import datetime
                # Convert string to datetime and make it timezone aware
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_aware = timezone.make_aware(date_to_obj)
                base_queryset = base_queryset.filter(request_date__date__lte=date_to_aware.date())
            except ValueError:
                # Invalid date format, ignore filter
                pass
        
        # Apply pagination to each status filter
        from django.core.paginator import Paginator
        
        pending_requests = base_queryset.filter(status='pending')
        approved_requests = base_queryset.filter(status='approved')
        rejected_requests = base_queryset.filter(status='rejected')
        partially_approved_requests = base_queryset.filter(status='partially_approved')
        for_claiming_requests = base_queryset.filter(status='for_claiming')
        # Completed requests ordered by completion date (most recent first)
        completed_requests = base_queryset.filter(status='completed').order_by('-completed_date')
        
        # Paginate each category
        pending_paginator = Paginator(pending_requests, self.paginate_by)
        approved_paginator = Paginator(approved_requests, self.paginate_by)
        rejected_paginator = Paginator(rejected_requests, self.paginate_by)
        partially_approved_paginator = Paginator(partially_approved_requests, self.paginate_by)
        for_claiming_paginator = Paginator(for_claiming_requests, self.paginate_by)
        completed_paginator = Paginator(completed_requests, self.paginate_by)
        
        # Get current page number for each tab
        pending_page = self.request.GET.get('pending_page', 1)
        approved_page = self.request.GET.get('approved_page', 1)
        rejected_page = self.request.GET.get('rejected_page', 1)
        partially_approved_page = self.request.GET.get('partially_approved_page', 1)
        for_claiming_page = self.request.GET.get('for_claiming_page', 1)
        completed_page = self.request.GET.get('completed_page', 1)
        
        # Get the page objects
        context['pending_batch_requests'] = pending_paginator.get_page(pending_page)
        context['approved_batch_requests'] = approved_paginator.get_page(approved_page)
        context['rejected_batch_requests'] = rejected_paginator.get_page(rejected_page)
        context['partially_approved_batch_requests'] = partially_approved_paginator.get_page(partially_approved_page)
        context['for_claiming_batch_requests'] = for_claiming_paginator.get_page(for_claiming_page)
        context['completed_batch_requests'] = completed_paginator.get_page(completed_page)
        
        # Add current tab to context
        context['current_tab'] = current_tab
        
        # Add search and filter parameters to context
        context['search_query'] = search_query
        context['department_filter'] = department_filter
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        # Build URL parameters string for pagination links
        url_params = []
        if search_query:
            url_params.append(f'search={search_query}')
        if department_filter:
            url_params.append(f'department={department_filter}')
        if date_from:
            url_params.append(f'date_from={date_from}')
        if date_to:
            url_params.append(f'date_to={date_to}')
        
        base_url_params = '&'.join(url_params)
        context['url_params'] = '&' + base_url_params if base_url_params else ''
        
        # Get all departments for the filter dropdown
        from .models import Department
        context['departments'] = Department.objects.all().order_by('name')
        
        return context



class UserDamageReportListView(PermissionRequiredMixin, ListView):
    model = DamageReport
    template_name = 'app/reports.html'
    permission_required = 'app.view_admin_module'
    context_object_name = 'damage_reports'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = DamageReport.objects.select_related('user', 'user__userprofile', 'item').order_by('report_date')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(item__property_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Department filter
        department = self.request.GET.get('department')
        if department:
            queryset = queryset.filter(user__userprofile__department_id=department)
        
        # Date range filters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(report_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(report_date__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_reports = self.get_queryset()

        context['pending_reports'] = all_reports.filter(status='pending')
        context['reviewed_reports'] = all_reports.filter(status='reviewed')
        context['resolved_reports'] = all_reports.filter(status='resolved')
        
        # Add departments for filter dropdown
        from .models import Department
        context['departments'] = Department.objects.all().order_by('name')
        
        # Add search parameters for form persistence
        context['search'] = self.request.GET.get('search', '')
        context['department_filter'] = self.request.GET.get('department', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        return context


class UserReservationListView(PermissionRequiredMixin, ListView):
    model = Reservation
    template_name = 'app/reservation.html'
    permission_required = 'app.view_admin_module'
    context_object_name = 'reservations'  # all reservations
    paginate_by = 10

    def get_queryset(self):
        queryset = Reservation.objects.select_related(
            'user', 'user__userprofile', 'item'
        ).order_by('reservation_date')
        
        # Apply search filter
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(item__property_name__icontains=search_query) |
                Q(purpose__icontains=search_query)
            )
        
        # Apply department filter
        department = self.request.GET.get('department')
        if department:
            queryset = queryset.filter(user__userprofile__department_id=department)
        
        # Apply date filters
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(reservation_date__date__gte=date_from_obj)
            except ValueError:
                pass
                
        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(reservation_date__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_reservations = self.get_queryset()
        
        # Group reservations by status
        context['pending_reservations'] = all_reservations.filter(status='pending')
        context['approved_reservations'] = all_reservations.filter(status='approved')
        context['active_reservations'] = all_reservations.filter(status='active')
        context['completed_reservations'] = all_reservations.filter(status='completed')
        context['rejected_reservations'] = all_reservations.filter(status='rejected')
        
        # Add departments for the filter dropdown
        context['departments'] = Department.objects.all()
        
        return context



class SupplyListView(PermissionRequiredMixin, ListView):
    model = Supply
    template_name = 'app/supply.html'
    permission_required = 'app.view_admin_module'
    context_object_name = 'supplies'
    paginate_by = 15  # Enable pagination with 15 items per page

    def get_queryset(self):
        return Supply.objects.filter(is_archived=False).select_related('quantity_info', 'category', 'subcategory').order_by('supply_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = SupplyForm()
        context['form'] = form
        context['today'] = date.today()
        
        # Get the paginated supplies from the parent context
        supplies = context['supplies']
        
        # Generate barcodes for each supply in the current page
        for supply in supplies:
            supply.barcode = generate_barcode(f"SUP-{supply.id}")
            
            # Calculate days until expiration
            if supply.expiration_date:
                days_until = (supply.expiration_date - date.today()).days
                supply.days_until_expiration = days_until
        
        # Get all categories and subcategories for the filter dropdowns
        context['categories'] = SupplyCategory.objects.prefetch_related('supply_set').all()
        context['subcategories'] = SupplySubcategory.objects.prefetch_related('supply_set').all()
        
        # Keep grouped_supplies for backward compatibility with modals (get all supplies, not just current page)
        all_supplies = Supply.objects.filter(is_archived=False).select_related('quantity_info', 'category', 'subcategory').order_by('supply_name')
        context['all_supplies'] = all_supplies
        
        # Group supplies by category for modals
        grouped = defaultdict(list)
        for supply in all_supplies:
            category_name = supply.category.name if supply.category else 'Uncategorized'
            grouped[category_name].append(supply)
        context['grouped_supplies'] = dict(sorted(grouped.items()))
        
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


@permission_required('app.view_admin_module')
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
                'category': supply.category.id if supply.category else None,
                'subcategory': supply.subcategory.id if supply.subcategory else None,
                'date_received': supply.date_received,
                'expiration_date': supply.expiration_date,
                'current_quantity': supply.quantity_info.current_quantity if supply.quantity_info else 0,
                'minimum_threshold': supply.quantity_info.minimum_threshold if supply.quantity_info else 0
            }

            # Update supply fields
            supply.supply_name = request.POST.get('supply_name')
            supply.description = request.POST.get('description')
            
            # Handle category and subcategory
            category_id = request.POST.get('category')
            subcategory_id = request.POST.get('subcategory')
            
            if category_id:
                supply.category = get_object_or_404(SupplyCategory, id=category_id)
            else:
                supply.category = None
                
            if subcategory_id:
                supply.subcategory = get_object_or_404(SupplySubcategory, id=subcategory_id)
            else:
                supply.subcategory = None
                
            supply.date_received = request.POST.get('date_received')
            supply.expiration_date = request.POST.get('expiration_date') or None
            
            # Only update minimum_threshold, NOT current_quantity
            minimum_threshold = int(request.POST.get('minimum_threshold', 0))
            
            if not supply.quantity_info:
                # Create new quantity info, set current_quantity to 0 by default
                quantity_info = SupplyQuantity(
                    supply=supply,
                    current_quantity=0,
                    minimum_threshold=minimum_threshold
                )
                quantity_info.save(user=request.user)
            else:
                # Only update minimum_threshold
                supply.quantity_info.minimum_threshold = minimum_threshold
                supply.quantity_info.save(user=request.user)
            
            # Save supply with user information
            supply.save(user=request.user)

            # Create activity log for the update
            changes = []
            for field, old_value in old_values.items():
                if field == 'minimum_threshold':
                    new_value = minimum_threshold
                elif field == 'current_quantity':
                    new_value = old_value  # current_quantity is not changed here
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

@permission_required('app.view_admin_module')
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
    paginate_by = 15

    def get_queryset(self):
        queryset = Property.objects.filter(is_archived=False).select_related('category').order_by('property_name')
        
        # Apply search filter
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(property_name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(property_number__icontains=search_query)
            )
        
        # Apply category filter
        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category__name=category_filter)
        
        # Apply availability filter
        availability_filter = self.request.GET.get('availability')
        if availability_filter == 'available':
            queryset = queryset.filter(availability='available')
        elif availability_filter == 'not_available':
            queryset = queryset.exclude(availability='available')
        
        # Apply condition filter
        condition_filter = self.request.GET.get('condition')
        if condition_filter:
            queryset = queryset.filter(condition=condition_filter)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the paginated properties from the parent context
        properties = context['properties']
        
        # Generate barcodes for each property in the current page
        for prop in properties:
            # Use property_number for barcode if available, otherwise use ID
            barcode_number = prop.property_number if prop.property_number else f"PROP-{prop.id}"
            prop.barcode = generate_barcode(barcode_number)
        
        # Get all categories for the filter dropdown
        context['categories'] = PropertyCategory.objects.all()
        context['form'] = PropertyForm()
        
        # Keep properties_by_category for backward compatibility with modals
        # Get all properties (not just current page) for modals
        all_properties = Property.objects.filter(is_archived=False).select_related('category').order_by('property_name')
        properties_by_category = defaultdict(list)
        for prop in all_properties:
            properties_by_category[prop.category].append(prop)
        context['properties_by_category'] = dict(properties_by_category)
        
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
def modify_supply_quantity_generic(request):
    try:
        supply_id = request.POST.get("supply_id")
        if not supply_id:
            return JsonResponse({
                'success': False,
                'error': 'Supply ID is required'
            })

        amount = int(request.POST.get("amount", 0))
        supply = get_object_or_404(Supply, pk=supply_id)

        quantity_info = supply.quantity_info
        old_quantity = quantity_info.current_quantity

        # Always add the quantity since we removed the action type selection
        quantity_info.current_quantity += amount
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
            remarks=f"add {amount}"
        )

        # Add activity log
        ActivityLog.log_activity(
            user=request.user,
            action='quantity_update',
            model_name='Supply',
            object_repr=str(supply),
            description=f"Added {amount} units to supply '{supply.supply_name}'. Changed quantity from {old_quantity} to {quantity_info.current_quantity}"
        )

        messages.success(request, f"Quantity successfully added.")
        
        # Check if request expects JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Quantity updated successfully',
                'new_quantity': quantity_info.current_quantity
            })
        return redirect('supply_list')

    except SupplyQuantity.DoesNotExist:
        error_msg = "Supply quantity information not found."
        messages.error(request, error_msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        return redirect('supply_list')
    except ValueError as e:
        error_msg = str(e)
        messages.error(request, error_msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        return redirect('supply_list')

@permission_required('app.view_admin_module')
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

@permission_required('app.view_admin_module')
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

@permission_required('app.view_admin_module')
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

@permission_required('app.view_admin_module')
def add_property_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            try:
                category = PropertyCategory.objects.create(name=name)
                
                # Log the activity
                ActivityLog.log_activity(
                    user=request.user,
                    action='create',
                    model_name='PropertyCategory',
                    object_repr=str(category),
                    description=f"Added new property category '{name}'"
                )
                
                messages.success(request, 'Category added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding category: {str(e)}')
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
    """
    New cart-based supply request system.
    Users can add multiple items to a cart before submitting.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_to_cart':
            # Handle adding item to list
            return add_to_list(request)
        elif action == 'remove_from_cart':
            # Handle removing item from list
            return remove_from_list(request)
        elif action == 'update_cart':
            # Handle updating item quantity in list
            return update_list_item(request)
        elif action == 'submit_request':
            # Handle final request submission
            return submit_list_request(request)
    
    # GET request - show the cart page
    cart_items = request.session.get('supply_cart', [])
    
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
    
    context = {
        'cart_items': cart_items,
        'item_form': SupplyRequestItemForm(),
        'batch_form': SupplyRequestBatchForm(),
        'available_supplies': Supply.objects.filter(
            available_for_request=True,
            quantity_info__current_quantity__gt=0
        ).select_related('quantity_info'),
        'recent_requests': recent_requests_data,
    }
    
    return render(request, 'userpanel/user_request.html', context)

@login_required
def add_to_list(request):
    """Add an item to the supply request list"""
    if request.method == 'POST':
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
def remove_from_list(request):
    """Remove an item from the supply request list"""
    if request.method == 'POST':
        supply_id = request.POST.get('supply_id')
        
        cart = request.session.get('supply_cart', [])
        cart = [item for item in cart if item['supply_id'] != supply_id]
        
        request.session['supply_cart'] = cart
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart.',
            'cart_count': len(cart)
        })

@login_required
def update_list_item(request):
    """Update quantity of an item in the list"""
    if request.method == 'POST':
        supply_id = request.POST.get('supply_id')
        new_quantity = int(request.POST.get('quantity', 0))
        
        try:
            supply = Supply.objects.get(id=supply_id)
            available_quantity = supply.quantity_info.current_quantity
            
            if new_quantity > available_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {available_quantity} units available.'
                })
            
            cart = request.session.get('supply_cart', [])
            
            for item in cart:
                if item['supply_id'] == supply_id:
                    item['quantity'] = new_quantity
                    break
            
            request.session['supply_cart'] = cart
            
            return JsonResponse({
                'success': True,
                'message': 'Cart updated.',
                'cart_count': len(cart)
            })
            
        except Supply.DoesNotExist:
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
            messages.error(request, 'Your request list is empty. Please add items before submitting.')
            return redirect('create_supply_request')
        
        if not purpose:
            messages.error(request, 'Please provide a purpose for your request.')
            return redirect('create_supply_request')
        
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
            item_list = ", ".join([f"{item['supply_name']} (x{item['quantity']})" for item in cart[:3]])
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
            
            messages.success(request, f'Supply request submitted successfully! Your request ID is #{batch_request.id}.')
            return redirect('create_supply_request')
            
        except Exception as e:
            messages.error(request, f'Error submitting request: {str(e)}')
            return redirect('create_supply_request')


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
        return redirect('create_borrow_request')


@permission_required('app.view_admin_module')
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


@permission_required('app.view_admin_module')
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
    try:
        supply_id = request.POST.get("supply_id")
        if not supply_id:
            return JsonResponse({
                'success': False,
                'error': 'Supply ID is required'
            })

        amount = int(request.POST.get("amount", 0))
        supply = get_object_or_404(Supply, pk=supply_id)

        quantity_info = supply.quantity_info
        old_quantity = quantity_info.current_quantity

        # Always add the quantity since we removed the action type selection
        quantity_info.current_quantity += amount
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
            remarks=f"add {amount}"
        )

        # Add activity log
        ActivityLog.log_activity(
            user=request.user,
            action='quantity_update',
            model_name='Supply',
            object_repr=str(supply),
            description=f"Added {amount} units to supply '{supply.supply_name}'. Changed quantity from {old_quantity} to {quantity_info.current_quantity}"
        )

        messages.success(request, f"Quantity successfully added.")
        
        # Check if request expects JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Quantity updated successfully',
                'new_quantity': quantity_info.current_quantity
            })
        return redirect('supply_list')

    except SupplyQuantity.DoesNotExist:
        error_msg = "Supply quantity information not found."
        messages.error(request, error_msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        return redirect('supply_list')
    except ValueError as e:
        error_msg = str(e)
        messages.error(request, error_msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
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

@permission_required('app.view_admin_module')
@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
        try:
            category = SupplyCategory.objects.create(name=name)
            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@permission_required('app.view_admin_module')
@login_required
def add_subcategory(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})
        
        try:
            subcategory = SupplySubcategory.objects.create(name=name)
            return JsonResponse({
                'success': True,
                'subcategory': {
                    'id': subcategory.id,
                    'name': subcategory.name
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_subcategories(request):
    category_id = request.GET.get('category_id')
    if category_id:
        subcategories = SupplySubcategory.objects.filter(category_id=category_id)
        return JsonResponse({
            'subcategories': [
                {'id': sub.id, 'name': sub.name}
                for sub in subcategories
            ]
        })
    return JsonResponse({'subcategories': []})
   #new
@permission_required('app.view_admin_module')
@login_required
def update_property_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('id')
        new_name = request.POST.get('name')
       
        try:
            category = PropertyCategory.objects.get(id=category_id)
            old_name = category.name
            category.name = new_name
            category.save()
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                model_name='PropertyCategory',
                object_repr=str(category),
                description=f"Updated category name from '{old_name}' to '{new_name}'"
            )
           
            return JsonResponse({'success': True})
        except PropertyCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
           
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@permission_required('app.view_admin_module')
@login_required
def delete_property_category(request, category_id):
    if request.method == 'POST':
        try:
            category = PropertyCategory.objects.get(id=category_id)
            category_name = category.name
            category.delete()
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='delete',
                model_name='PropertyCategory',
                object_repr=category_name,
                description=f"Deleted property category '{category_name}'"
            )
           
            messages.success(request, 'Category deleted successfully.')
        except PropertyCategory.DoesNotExist:
            messages.error(request, 'Category not found.')
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')
           
    return redirect('property_list')

@permission_required('app.view_admin_module')
def export_supply_to_excel(request):
    """Export supply data to Excel with filters"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Supply Inventory"

    # Title and Header Styling
    title_font = ws['A1'].font.copy(bold=True, size=16)
    header_font = ws['A1'].font.copy(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="152D64", end_color="152D64", fill_type="solid")
    thin_border = Side(border_style="thin", color="000000")
    category_font = ws['A1'].font.copy(bold=True, size=12)

    # Get selected fields from request
    selected_fields = request.POST.getlist('fields', [
        'supply_name', 'description', 'category', 'subcategory',
        'current_quantity', 'date_received', 'expiration_date'
    ])

    # Define all possible fields and their display names
    field_mapping = {
        'supply_name': 'Supply Name',
        'description': 'Description',
        'category': 'Category',
        'subcategory': 'Sub Category',
        'current_quantity': 'Current Quantity',
        'date_received': 'Date Received',
        'expiration_date': 'Expiration Date'
    }

    # Create header row with title and metadata
    num_columns = len(selected_fields)
    merge_range = f'A1:{chr(64 + num_columns)}1'
    ws.merge_cells(merge_range)
    ws['A1'] = 'INVENTORY REPORT FOR SUPPLY'
    ws['A1'].font = title_font
    ws['A1'].alignment = ws['A1'].alignment.copy(horizontal='center')

    # Add metadata
    ws['A3'] = 'Department:'
    ws['B3'] = request.user.userprofile.department.name if hasattr(request.user, 'userprofile') and request.user.userprofile.department else '_____________________'
    ws['G3'] = 'Date:'
    ws['H3'] = datetime.now().strftime("%B %d, %Y")
    
    ws['A4'] = 'Prepared by:'
    ws['B4'] = f'{request.user.first_name} {request.user.last_name}'
    ws['G4'] = 'Page:'
    ws['H4'] = '1 of 1'

    # Headers start at row 6
    ws['A6'] = 'SUPPLY INVENTORY'
    ws['A6'].font = ws['A6'].font.copy(bold=True)

    # Get all supplies with related data and group by category
    supplies = Supply.objects.select_related(
        'category', 'subcategory', 'quantity_info'
    ).order_by('category__name', 'supply_name').all()

    # Group supplies by category
    supplies_by_category = {}
    for supply in supplies:
        category_name = supply.category.name if supply.category else 'Uncategorized'
        if category_name not in supplies_by_category:
            supplies_by_category[category_name] = []
        supplies_by_category[category_name].append(supply)

    current_row = 8  # Start after the title and metadata

    # Process each category
    for category_name, category_supplies in supplies_by_category.items():
        # Add category header
        ws.cell(row=current_row, column=1, value=category_name)
        ws.cell(row=current_row, column=1).font = category_font
        current_row += 1

        # Add headers for this category
        headers = [field_mapping[field] for field in selected_fields]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)
        current_row += 1

        # Add data for this category
        for supply in category_supplies:
            row_data = []
            for field in selected_fields:
                if field == 'supply_name':
                    row_data.append(supply.supply_name)
                elif field == 'description':
                    row_data.append(supply.description or 'N/A')
                elif field == 'category':
                    row_data.append(supply.category.name if supply.category else 'N/A')
                elif field == 'subcategory':
                    row_data.append(supply.subcategory.name if supply.subcategory else 'N/A')
                elif field == 'current_quantity':
                    row_data.append(supply.quantity_info.current_quantity if supply.quantity_info else 0)
                elif field == 'date_received':
                    row_data.append(supply.date_received.strftime('%Y-%m-%d') if supply.date_received else 'N/A')
                elif field == 'expiration_date':
                    row_data.append(supply.expiration_date.strftime('%Y-%m-%d') if supply.expiration_date else 'N/A')

            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col)
                cell.value = value
                cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)
            current_row += 1

        current_row += 1  # Add space between categories

    # Add signature section
    signature_row = current_row + 2
    ws.cell(row=signature_row, column=1, value='Prepared by:')
    ws.cell(row=signature_row, column=4, value='Reviewed by:')
    ws.cell(row=signature_row, column=7, value='Approved by:')

    ws.cell(row=signature_row + 2, column=1, value='_____________________')
    ws.cell(row=signature_row + 2, column=4, value='_____________________')
    ws.cell(row=signature_row + 2, column=7, value='_____________________')

    ws.cell(row=signature_row + 3, column=1, value='Inventory Officer')
    ws.cell(row=signature_row + 3, column=4, value='Department Head')
    ws.cell(row=signature_row + 3, column=7, value='Property Custodian')

    # Add notes section
    notes_row = signature_row + 5
    ws.cell(row=notes_row, column=1, value='Notes:')
    ws.cell(row=notes_row + 1, column=1, value='1. This report shows the current inventory status of supplies.')
    ws.cell(row=notes_row + 2, column=1, value='2. Please verify physical count against this report.')
    ws.cell(row=notes_row + 3, column=1, value='3. Report any discrepancies to the inventory officer.')

    # Auto-adjust column widths
    for col_idx, column in enumerate(ws.columns, 1):
        max_length = 0
        column_letter = get_column_letter(col_idx)
        
        for cell in column[1:]:
            if isinstance(cell, MergedCell):
                continue
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=supply_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    wb.save(response)
    return response

@permission_required('app.view_admin_module')
def export_property_to_excel(request):
    """Export property data to Excel with filters"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Property Inventory"

    # Title and Header Styling
    title_font = ws['A1'].font.copy(bold=True, size=16)
    header_font = ws['A1'].font.copy(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="152D64", end_color="152D64", fill_type="solid")
    thin_border = Side(border_style="thin", color="000000")
    category_font = ws['A1'].font.copy(bold=True, size=12)

    # Get selected fields from request
    selected_fields = request.POST.getlist('fields', [
        'property_number', 'property_name', 'description', 'unit_of_measure',
        'unit_value', 'overall_quantity', 'current_quantity', 'location',
        'condition', 'category'
    ])

    # Define all possible fields and their display names
    field_mapping = {
        'property_number': 'Property Number',
        'property_name': 'Property Name',
        'description': 'Description',
        'unit_of_measure': 'Unit of Measure',
        'unit_value': 'Unit Value',
        'overall_quantity': 'Overall Quantity',
        'current_quantity': 'Current Quantity',
        'location': 'Location',
        'condition': 'Condition',
        'category': 'Category'
    }

    # Create header row with title and metadata
    num_columns = len(selected_fields)
    merge_range = f'A1:{chr(64 + num_columns)}1'
    ws.merge_cells(merge_range)
    ws['A1'] = 'INVENTORY REPORT FOR PROPERTY'
    ws['A1'].font = title_font
    ws['A1'].alignment = ws['A1'].alignment.copy(horizontal='center')

    # Add metadata
    ws['A3'] = 'Department:'
    ws['B3'] = request.user.userprofile.department.name if hasattr(request.user, 'userprofile') and request.user.userprofile.department else '_____________________'
    ws['G3'] = 'Date:'
    ws['H3'] = datetime.now().strftime("%B %d, %Y")
    
    ws['A4'] = 'Prepared by:'
    ws['B4'] = f'{request.user.first_name} {request.user.last_name}'
    ws['G4'] = 'Page:'
    ws['H4'] = '1 of 1'

    # Headers start at row 6
    ws['A6'] = 'PROPERTY INVENTORY'
    ws['A6'].font = ws['A6'].font.copy(bold=True)

    # Get all properties with related data and group by category
    properties = Property.objects.select_related('category').order_by('category__name', 'property_name').all()

    # Group properties by category
    properties_by_category = {}
    for prop in properties:
        category_name = prop.category.name if prop.category else 'Uncategorized'
        if category_name not in properties_by_category:
            properties_by_category[category_name] = []
        properties_by_category[category_name].append(prop)

    current_row = 8  # Start after the title and metadata

    # Process each category
    for category_name, category_properties in properties_by_category.items():
        # Add category header
        ws.cell(row=current_row, column=1, value=category_name)
        ws.cell(row=current_row, column=1).font = category_font
        current_row += 1

        # Add headers for this category
        headers = [field_mapping[field] for field in selected_fields]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)
        current_row += 1

        # Add data for this category
        for prop in category_properties:
            row_data = []
            for field in selected_fields:
                if field == 'property_number':
                    row_data.append(prop.property_number or 'N/A')
                elif field == 'property_name':
                    row_data.append(prop.property_name)
                elif field == 'description':
                    row_data.append(prop.description or 'N/A')
                elif field == 'unit_of_measure':
                    row_data.append(prop.unit_of_measure or 'N/A')
                elif field == 'unit_value':
                    row_data.append(prop.unit_value or 0)
                elif field == 'overall_quantity':
                    row_data.append(prop.overall_quantity or 0)
                elif field == 'current_quantity':
                    row_data.append(prop.quantity or 0)
                elif field == 'location':
                    row_data.append(prop.location or 'N/A')
                elif field == 'condition':
                    row_data.append(prop.get_condition_display() if prop.condition else 'N/A')
                elif field == 'category':
                    row_data.append(prop.category.name if prop.category else 'N/A')

            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col)
                cell.value = value
                cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)
            current_row += 1

        current_row += 1  # Add space between categories

    # Add signature section
    signature_row = current_row + 2
    ws.cell(row=signature_row, column=1, value='Prepared by:')
    ws.cell(row=signature_row, column=4, value='Reviewed by:')
    ws.cell(row=signature_row, column=7, value='Approved by:')

    ws.cell(row=signature_row + 2, column=1, value='_____________________')
    ws.cell(row=signature_row + 2, column=4, value='_____________________')
    ws.cell(row=signature_row + 2, column=7, value='_____________________')

    ws.cell(row=signature_row + 3, column=1, value='Inventory Officer')
    ws.cell(row=signature_row + 3, column=4, value='Department Head')
    ws.cell(row=signature_row + 3, column=7, value='Property Custodian')

    # Add notes section
    notes_row = signature_row + 5
    ws.cell(row=notes_row, column=1, value='Notes:')
    ws.cell(row=notes_row + 1, column=1, value='1. This report shows the current inventory status of properties.')
    ws.cell(row=notes_row + 2, column=1, value='2. Please verify physical count against this report.')
    ws.cell(row=notes_row + 3, column=1, value='3. Report any discrepancies to the inventory officer.')

    # Auto-adjust column widths
    for col_idx, column in enumerate(ws.columns, 1):
        max_length = 0
        column_letter = get_column_letter(col_idx)
        
        for cell in column[1:]:
            if isinstance(cell, MergedCell):
                continue
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=property_inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    wb.save(response)
    return response

# def generate_sample_inventory_report(request):
#     """Generate a sample inventory report template"""
#     wb = Workbook()
#     ws = wb.active
#     ws.title = "Sample Inventory Report"

#     # Title and Header Styling
#     title_font = ws['A1'].font.copy(bold=True, size=16)
#     header_font = ws['A1'].font.copy(bold=True, color="FFFFFF")
#     header_fill = PatternFill(start_color="152D64", end_color="152D64", fill_type="solid")
    
#     # Merge cells for title
#     ws.merge_cells('A1:J1')
#     ws['A1'] = 'SAMPLE INVENTORY REPORT TEMPLATE'
#     ws['A1'].font = title_font
#     ws['A1'].alignment = ws['A1'].alignment.copy(horizontal='center')

#     # Add metadata
#     ws['A3'] = 'Department:'
#     ws['B3'] = '_____________________'
#     ws['G3'] = 'Date:'
#     ws['H3'] = datetime.now().strftime("%B %d, %Y")
    
#     ws['A4'] = 'Prepared by:'
#     ws['B4'] = '_____________________'
#     ws['G4'] = 'Page:'
#     ws['H4'] = '1 of 1'

#     # Add section headers
#     ws['A6'] = 'SUPPLY INVENTORY'
#     ws['A6'].font = ws['A6'].font.copy(bold=True)
    
#     # Supply headers
#     supply_headers = ['Item Code', 'Supply Name', 'Category', 'Current Quantity', 'Unit', 'Status', 'Remarks']
#     for col, header in enumerate(supply_headers, 1):
#         cell = ws.cell(row=7, column=col)
#         cell.value = header
#         cell.font = header_font
#         cell.fill = header_fill

#     # Sample supply data
#     sample_supplies = [
#         ['SUP-001', 'Ballpen (Black)', 'Office Supplies', 100, 'Pieces', 'Available', ''],
#         ['SUP-002', 'A4 Paper', 'Office Supplies', 50, 'Reams', 'Low Stock', 'Need to reorder'],
#         ['SUP-003', 'Printer Ink', 'Supplies', 5, 'Cartridges', 'Low Stock', 'Order pending'],
#     ]

#     for row, data in enumerate(sample_supplies, 8):
#         for col, value in enumerate(data, 1):
#             cell = ws.cell(row=row, column=col)
#             cell.value = value

#     # Add property section
#     ws['A12'] = 'PROPERTY INVENTORY'
#     ws['A12'].font = ws['A12'].font.copy(bold=True)

#     # Property headers
#     property_headers = ['Property No.', 'Property Name', 'Description', 'Quantity', 'Location', 'Condition', 'Remarks']
#     for col, header in enumerate(property_headers, 1):
#         cell = ws.cell(row=13, column=col)
#         cell.value = header
#         cell.font = header_font
#         cell.fill = header_fill

#     # Sample property data
#     sample_properties = [
#         ['PROP-001', 'Desktop Computer', 'Dell OptiPlex', 5, 'IT Room', 'Good Condition', ''],
#         ['PROP-002', 'Office Chair', 'Ergonomic Chair', 10, 'Main Office', 'Good Condition', ''],
#         ['PROP-003', 'Printer', 'HP LaserJet', 2, 'Admin Office', 'Needs Repair', 'Under maintenance'],
#     ]

#     for row, data in enumerate(sample_properties, 14):
#         for col, value in enumerate(data, 1):
#             cell = ws.cell(row=row, column=col)
#             cell.value = value

#     # Add signature section
#     ws['A18'] = 'Prepared by:'
#     ws['D18'] = 'Reviewed by:'
#     ws['G18'] = 'Approved by:'

#     ws['A20'] = '_____________________'
#     ws['D20'] = '_____________________'
#     ws['G20'] = '_____________________'

#     ws['A21'] = 'Inventory Officer'
#     ws['D21'] = 'Department Head'
#     ws['G21'] = 'Property Custodian'

#     # Add notes section
#     ws['A23'] = 'Notes:'
#     ws['A24'] = '1. This is a sample template for inventory reporting.'
#     ws['A25'] = '2. Customize the sections and fields according to your needs.'
#     ws['A26'] = '3. Regular inventory count is recommended for accurate record keeping.'

#     # Adjust column widths
#     column_widths = [15, 20, 15, 15, 15, 15, 30]
#     for i, width in enumerate(column_widths, 1):
#         ws.column_dimensions[get_column_letter(i)].width = width

#     # Add borders to all cells with content
#     thin_border = Side(border_style="thin", color="000000")
#     max_row = ws.max_row
#     max_col = ws.max_column

#     for row in range(7, 11):  # Supply section
#         for col in range(1, 8):
#             cell = ws.cell(row=row, column=col)
#             cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)

#     for row in range(13, 17):  # Property section
#         for col in range(1, 8):
#             cell = ws.cell(row=row, column=col)
#             cell.border = Border(top=thin_border, left=thin_border, right=thin_border, bottom=thin_border)

#     # Create response
#     response = HttpResponse(
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = f'attachment; filename=inventory_report_template.xlsx'
    
#     wb.save(response)
#     return response

@login_required
def get_supply_by_barcode(request, barcode):
    try:
        # Try to find the supply by the exact barcode first
        supply = Supply.objects.get(barcode=barcode)
    except Supply.DoesNotExist:
        try:
            # If not found, try to find by ID (extract ID from SUP-{id} format)
            if barcode.startswith('SUP-'):
                supply_id = barcode.split('-')[1]
                supply = Supply.objects.get(id=supply_id)
            else:
                raise Supply.DoesNotExist
        except (Supply.DoesNotExist, IndexError):
            return JsonResponse({
                'success': False,
                'error': 'Supply not found'
            })
    
    return JsonResponse({
        'success': True,
        'supply': {
            'id': supply.id,
            'name': supply.supply_name,
            'current_quantity': supply.quantity_info.current_quantity if hasattr(supply, 'quantity_info') else 0,
            'description': supply.description or ''
        }
    })

@permission_required('app.view_admin_module')
@require_POST
def modify_property_quantity_generic(request):
    try:
        property_id = request.POST.get("property_id")
        amount = int(request.POST.get("amount", 0))

        prop = get_object_or_404(Property, pk=property_id)
        old_quantity = prop.quantity

        # Always add the quantity since we removed the action type selection
        prop.quantity += amount
        prop.overall_quantity += amount
        prop.save()

        PropertyHistory.objects.create(
            property=prop,
            user=request.user,
            action='quantity_update',
            field_name='quantity',
            old_value=str(old_quantity),
            new_value=str(prop.quantity),
            remarks=f"add {amount}"
        )

        # Add activity log
        ActivityLog.log_activity(
            user=request.user,
            action='quantity_update',
            model_name='Property',
            object_repr=str(prop),
            description=f"Added {amount} units to property '{prop.property_name}'. Changed quantity from {old_quantity} to {prop.quantity}"
        )

        messages.success(request, f"Quantity successfully added.")
        
        # Return JSON response for AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Quantity updated successfully',
                'new_quantity': prop.quantity
            })
        return redirect('property_list')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        messages.error(request, f"Error modifying quantity: {str(e)}")
        return redirect('property_list')

@login_required
def get_property_by_barcode(request, barcode):
    try:
        # Try to find the property by the exact barcode first
        property = Property.objects.get(barcode=barcode)
    except Property.DoesNotExist:
        try:
            # If not found, try to find by property number
            property = Property.objects.get(property_number=barcode)
        except Property.DoesNotExist:
            try:
                # If still not found, try to find by ID (extract ID from PROP-{id} format)
                if barcode.startswith('PROP-'):
                    property_id = barcode.split('-')[1]
                    property = Property.objects.get(id=property_id)
                else:
                    raise Property.DoesNotExist
            except (Property.DoesNotExist, IndexError):
                return JsonResponse({
                    'success': False,
                    'error': 'Property not found'
                })
    
    return JsonResponse({
        'success': True,
        'property': {
            'id': property.id,
            'name': property.property_name,
            'current_quantity': property.quantity
        }
    })

@permission_required('app.view_admin_module')
@login_required
def archive_supply(request, pk):
    supply = get_object_or_404(Supply, pk=pk)
    if request.method == 'POST':
        # Allow archive if expired, otherwise only if quantity is zero
        if not supply.is_expired and hasattr(supply, 'quantity_info') and supply.quantity_info.current_quantity > 0:
            messages.error(request, f"Cannot archive supply '{supply.supply_name}' because it still has {supply.quantity_info.current_quantity} units.")
            return redirect('supply_list')
        
        supply.is_archived = True
        supply.save(user=request.user)
        
        ActivityLog.log_activity(
            user=request.user,
            action='archive',
            model_name='Supply',
            object_repr=str(supply),
            description=f"Archived supply '{supply.supply_name}'"
        )
        messages.success(request, 'Supply archived successfully.')
    return redirect('supply_list')

@permission_required('app.view_admin_module')
@login_required
def unarchive_supply(request, pk):
    supply = get_object_or_404(Supply, pk=pk)
    if request.method == 'POST':
        supply.is_archived = False
        supply.save(user=request.user)
        
        ActivityLog.log_activity(
            user=request.user,
            action='unarchive',
            model_name='Supply',
            object_repr=str(supply),
            description=f"Unarchived supply '{supply.supply_name}'"
        )
        messages.success(request, 'Supply unarchived successfully.')
    return redirect('archived_items')

@permission_required('app.view_admin_module')
@login_required
def archive_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        # Check if property has zero quantity
        if property_obj.quantity > 0:
            messages.error(request, f"Cannot archive property '{property_obj.property_name}' because it still has {property_obj.quantity} units.")
            return redirect('property_list')
        
        property_obj.is_archived = True
        property_obj.save(user=request.user)
        
        ActivityLog.log_activity(
            user=request.user,
            action='archive',
            model_name='Property',
            object_repr=str(property_obj),
            description=f"Archived property '{property_obj.property_name}'"
        )
        messages.success(request, 'Property archived successfully.')
    return redirect('property_list')

@permission_required('app.view_admin_module')
@login_required
def unarchive_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        property_obj.is_archived = False
        property_obj.save(user=request.user)
        
        ActivityLog.log_activity(
            user=request.user,
            action='unarchive',
            model_name='Property',
            object_repr=str(property_obj),
            description=f"Unarchived property '{property_obj.property_name}'"
        )
        messages.success(request, 'Property unarchived successfully.')
    return redirect('archived_items')

class ArchivedItemsView(PermissionRequiredMixin, TemplateView):
    template_name = 'app/archived_items.html'
    permission_required = 'app.view_admin_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get archived supplies
        supplies = Supply.objects.filter(is_archived=True).select_related(
            'category', 'subcategory', 'quantity_info'
        ).order_by('supply_name')
        
        # Generate barcodes for supplies
        for supply in supplies:
            supply.barcode = generate_barcode(f"SUP-{supply.id}")
        
        # Group supplies by category
        supplies_by_category = defaultdict(list)
        for supply in supplies:
            category_name = supply.category.name if supply.category else 'Uncategorized'
            supplies_by_category[category_name].append(supply)
        
        # Get archived properties
        properties = Property.objects.filter(is_archived=True).select_related('category').order_by('property_name')
        
        # Generate barcodes for properties
        for prop in properties:
            barcode_number = prop.property_number if prop.property_number else f"PROP-{prop.id}"
            prop.barcode = generate_barcode(barcode_number)
        
        # Group properties by category
        properties_by_category = defaultdict(list)
        for prop in properties:
            category_name = prop.category.name if prop.category else 'Uncategorized'
            properties_by_category[category_name].append(prop)
        
        context.update({
            'supplies_by_category': dict(supplies_by_category),
            'properties_by_category': dict(properties_by_category),
        })
        return context

@permission_required('app.view_admin_module')
@login_required
def update_supply_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('id')
        new_name = request.POST.get('name')
       
        try:
            category = SupplyCategory.objects.get(id=category_id)
            old_name = category.name
            category.name = new_name
            category.save()
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                model_name='SupplyCategory',
                object_repr=str(category),
                description=f"Updated category name from '{old_name}' to '{new_name}'"
            )
           
            # Return more data for UI update
            return JsonResponse({
                'success': True,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'supply_count': category.supply_set.count()
                }
            })
        except SupplyCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
           
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@permission_required('app.view_admin_module')
@login_required
def delete_supply_category(request, category_id):
    if request.method == 'POST':
        try:
            category = SupplyCategory.objects.get(id=category_id)
            category_name = category.name
            category.delete()
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='delete',
                model_name='SupplyCategory',
                object_repr=category_name,
                description=f"Deleted supply category '{category_name}'"
            )
           
            messages.success(request, 'Category deleted successfully.')
        except SupplyCategory.DoesNotExist:
            messages.error(request, 'Category not found.')
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')
           
    return redirect('supply_list')

@permission_required('app.view_admin_module')
@login_required
def update_supply_subcategory(request):
    if request.method == 'POST':
        subcategory_id = request.POST.get('id')
        new_name = request.POST.get('name')
       
        try:
            subcategory = SupplySubcategory.objects.get(id=subcategory_id)
            old_name = subcategory.name
            subcategory.name = new_name
            subcategory.save()
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                model_name='SupplySubcategory',
                object_repr=str(subcategory),
                description=f"Updated subcategory name from '{old_name}' to '{new_name}'"
            )
           
            # Return more data for UI update
            return JsonResponse({
                'success': True,
                'subcategory': {
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'supply_count': subcategory.supply_set.count()
                }
            })
        except SupplySubcategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Subcategory not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
           
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@permission_required('app.view_admin_module')
@login_required
def delete_supply_subcategory(request, subcategory_id):
    if request.method == 'POST':
        try:
            print(f"Attempting to delete subcategory {subcategory_id}")
            subcategory = SupplySubcategory.objects.get(id=subcategory_id)
            subcategory_name = subcategory.name
           
            # Check if there are any supplies using this subcategory
            supply_count = subcategory.supply_set.count()
            print(f"Subcategory {subcategory_name} has {supply_count} supplies")
           
            if subcategory.supply_set.exists():
                print(f"Cannot delete subcategory {subcategory_name} - has supplies assigned")
                messages.error(request, 'Cannot delete subcategory that has supplies assigned to it.')
                return redirect('supply_list')
               
            subcategory.delete()
            print(f"Successfully deleted subcategory {subcategory_name}")
           
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action='delete',
                model_name='SupplySubcategory',
                object_repr=subcategory_name,
                description=f"Deleted supply subcategory '{subcategory_name}'"
            )
           
            messages.success(request, 'Subcategory deleted successfully.')
        except SupplySubcategory.DoesNotExist:
            print(f"Subcategory {subcategory_id} not found")
            messages.error(request, 'Subcategory not found.')
        except Exception as e:
            print(f"Error deleting subcategory: {str(e)}")
            messages.error(request, f'Error deleting subcategory: {str(e)}')
           
    return redirect('supply_list')

def supply_list(request):
    # Redirect to the class-based view
    return redirect('supplies')


# Batch Request Item Management Views
@permission_required('app.view_admin_module')
@login_required
@require_POST
def approve_batch_item(request, batch_id, item_id):
    """Approve an individual item in a batch request"""
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    item = get_object_or_404(SupplyRequestItem, id=item_id, batch_request=batch_request)
    
    # Get approved quantity from form
    approved_quantity = request.POST.get('approved_quantity', item.quantity)
    try:
        approved_quantity = int(approved_quantity)
        if approved_quantity <= 0 or approved_quantity > item.quantity:
            messages.error(request, f'Invalid approved quantity. Must be between 1 and {item.quantity}.')
            return redirect('batch_request_detail', batch_id=batch_id)
    except (ValueError, TypeError):
        approved_quantity = item.quantity
    
    # Mark item as approved
    item.approved = True
    item.status = 'approved'  # Also update the status field
    item.approved_quantity = approved_quantity
    remarks = request.POST.get('remarks', '')
    if remarks:
        item.remarks = remarks
    item.save()
    
    # Check if all items in the batch are processed
    total_items = batch_request.items.count()
    approved_items = batch_request.items.filter(approved=True).count()
    rejected_items = batch_request.items.filter(approved=False, status='rejected').count()
    processed_items = approved_items + rejected_items
    
    # Update batch status
    if processed_items == total_items:
        # All items have been processed (approved or rejected)
        if approved_items > 0:
            batch_request.status = 'for_claiming'
        else:
            batch_request.status = 'rejected'
    elif approved_items > 0:
        batch_request.status = 'partially_approved'
    
    batch_request.save()
    
    # Create notification for user (individual item notification)
    Notification.objects.create(
        user=batch_request.user,
        message=f"Item '{item.supply.supply_name}' in your batch request #{batch_request.id} has been approved for {item.approved_quantity} units.",
        remarks=remarks
    )
    
    # Send batch completion email ONLY if all items are now processed
    if processed_items == total_items:
        from .utils import send_batch_request_completion_email
        approved_items = batch_request.items.filter(status='approved')
        rejected_items = batch_request.items.filter(status='rejected')
        send_batch_request_completion_email(batch_request, approved_items, rejected_items)
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='approve',
        model_name='SupplyRequestItem',
        object_repr=f"Batch #{batch_id} - {item.supply.supply_name}",
        description=f"Approved {item.approved_quantity} out of {item.quantity} units of {item.supply.supply_name} in batch request #{batch_id}"
    )
    
    # Remove success message since user can see status change immediately on the page
    # messages.success(request, f'Item "{item.supply.supply_name}" approved successfully.')
    return redirect('batch_request_detail', batch_id=batch_id)

@permission_required('app.view_admin_module')
@login_required
@require_POST
def reject_batch_item(request, batch_id, item_id):
    """Reject an individual item in a batch request"""
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    item = get_object_or_404(SupplyRequestItem, id=item_id, batch_request=batch_request)
    
    # Mark item as not approved and add remarks
    item.approved = False
    item.status = 'rejected'  # Also update the status field
    remarks = request.POST.get('remarks', '')
    if remarks:
        item.remarks = remarks
    item.save()
    
    # Check if all items in the batch are processed
    total_items = batch_request.items.count()
    approved_items = batch_request.items.filter(approved=True).count()
    rejected_items = batch_request.items.filter(approved=False, status='rejected').count()
    processed_items = approved_items + rejected_items
    
    # Update batch status
    if processed_items == total_items:
        # All items have been processed (approved or rejected)
        if approved_items > 0:
            batch_request.status = 'for_claiming'
        else:
            batch_request.status = 'rejected'
    elif approved_items > 0:
        batch_request.status = 'partially_approved'
    
    batch_request.save()
    
    # Create notification for user (individual item notification)
    Notification.objects.create(
        user=batch_request.user,
        message=f"Item '{item.supply.supply_name}' in your batch request #{batch_request.id} has been rejected.",
        remarks=remarks
    )
    
    # Send batch completion email ONLY if all items are now processed
    if processed_items == total_items:
        from .utils import send_batch_request_completion_email
        approved_items = batch_request.items.filter(status='approved')
        rejected_items = batch_request.items.filter(status='rejected')
        send_batch_request_completion_email(batch_request, approved_items, rejected_items)
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='reject',
        model_name='SupplyRequestItem',
        object_repr=f"Batch #{batch_id} - {item.supply.supply_name}",
        description=f"Rejected {item.quantity} units of {item.supply.supply_name} in batch request #{batch_id}"
    )
    
    # Remove success message since user can see status change immediately on the page
    # messages.success(request, f'Item "{item.supply.supply_name}" rejected successfully.')
    return redirect('batch_request_detail', batch_id=batch_id)

@permission_required('app.view_admin_module')
@login_required
def batch_request_detail(request, batch_id):
    """View detailed information about a batch request with individual item actions"""
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        remarks = request.POST.get('remarks', '')
        
        if item_id:
            item = get_object_or_404(SupplyRequestItem, id=item_id, batch_request=batch_request)
            
            if action == 'approve':
                item.status = 'approved'
                if remarks:
                    item.remarks = remarks
                item.save()
                
                # Create notification
                Notification.objects.create(
                    user=batch_request.user,
                    message=f"Item '{item.supply.supply_name}' in your batch request #{batch_request.id} has been approved.",
                    remarks=remarks
                )
                
                messages.success(request, f'Item "{item.supply.supply_name}" approved successfully.')
                
            elif action == 'reject':
                item.status = 'rejected'
                if remarks:
                    item.remarks = remarks
                item.save()
                
                # Create notification
                Notification.objects.create(
                    user=batch_request.user,
                    message=f"Item '{item.supply.supply_name}' in your batch request #{batch_request.id} has been rejected.",
                    remarks=remarks
                )
                
                messages.success(request, f'Item "{item.supply.supply_name}" rejected successfully.')
            
            # Update batch status based on individual item statuses
            total_items = batch_request.items.count()
            approved_items = batch_request.items.filter(status='approved').count()
            rejected_items = batch_request.items.filter(status='rejected').count()
            pending_items = batch_request.items.filter(status='pending').count()
            processed_items = approved_items + rejected_items
            
            if processed_items == total_items:
                # All items have been processed (approved or rejected)
                if approved_items > 0:
                    # At least some items were approved
                    batch_request.status = 'for_claiming'
                    if approved_items == total_items:
                        batch_request.approved_date = timezone.now()
                else:
                    # All items were rejected
                    batch_request.status = 'rejected'
            elif approved_items > 0:
                # Some approved, some still pending
                batch_request.status = 'partially_approved'
            else:
                # No items approved yet (either all pending or all rejected)
                if rejected_items > 0 and pending_items > 0:
                    # Some rejected, some pending
                    batch_request.status = 'pending'
                else:
                    # All pending or all rejected
                    batch_request.status = 'pending' if pending_items > 0 else 'rejected'
            
            batch_request.save()
            
            # Send batch completion email ONLY if all items are now processed
            if processed_items == total_items:
                from .utils import send_batch_request_completion_email
                approved_items_qs = batch_request.items.filter(status='approved')
                rejected_items_qs = batch_request.items.filter(status='rejected')
                send_batch_request_completion_email(batch_request, approved_items_qs, rejected_items_qs)
        
        return redirect('batch_request_detail', batch_id=batch_id)
    
    context = {
        'batch_request': batch_request,
        'items': batch_request.items.all().order_by('supply__supply_name')
    }
    
    return render(request, 'app/batch_request_detail.html', context)


# Claiming Workflow Views
@permission_required('app.view_admin_module')
@login_required
@require_POST
def claim_batch_items(request, batch_id):
    """
    Handle claiming of all approved items in a batch request.
    This will deduct stock and mark items as completed.
    """
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    
    # Only allow claiming if batch is in for_claiming status
    if batch_request.status != 'for_claiming':
        messages.error(request, 'This request is not available for claiming.')
        return redirect('user_supply_requests')
    
    # Get all approved items that haven't been claimed yet
    approved_items = batch_request.items.filter(status='approved', claimed_date__isnull=True)
    
    if not approved_items.exists():
        messages.error(request, 'No approved items available for claiming.')
        return redirect('user_supply_requests')
    
    # Check stock availability for all items before processing
    insufficient_stock_items = []
    for item in approved_items:
        available_quantity = 0
        if hasattr(item.supply, 'quantity_info') and item.supply.quantity_info:
            available_quantity = item.supply.quantity_info.current_quantity or 0
        
        # Handle case where approved_quantity might be None (fallback to requested quantity)
        approved_qty = item.approved_quantity or item.quantity or 0
        
        if available_quantity < approved_qty:
            insufficient_stock_items.append(f"{item.supply.supply_name} (available: {available_quantity}, needed: {approved_qty})")
    
    if insufficient_stock_items:
        messages.error(request, f"Insufficient stock for items: {', '.join(insufficient_stock_items)}")
        return redirect('user_supply_requests')
    
    # Process each approved item
    claimed_items = []
    for item in approved_items:
        # Handle case where approved_quantity might be None (fallback to requested quantity)
        approved_qty = item.approved_quantity or item.quantity or 0
        
        # Deduct from stock
        if hasattr(item.supply, 'quantity_info') and item.supply.quantity_info:
            current_qty = item.supply.quantity_info.current_quantity or 0
            item.supply.quantity_info.current_quantity = max(0, current_qty - approved_qty)
            item.supply.quantity_info.save()
        
        # Update the approved_quantity if it was None
        if item.approved_quantity is None:
            item.approved_quantity = item.quantity
        
        # Mark item as completed and claimed
        item.status = 'completed'
        item.claimed_date = timezone.now()
        item.save()
        
        claimed_items.append(item)
        
        # Log activity
        ActivityLog.log_activity(
            user=request.user,
            action='claim',
            model_name='SupplyRequestItem',
            object_repr=f"Batch #{batch_id} - {item.supply.supply_name}",
            description=f"Claimed {item.approved_quantity or item.quantity} units of {item.supply.supply_name} from batch request #{batch_id}"
        )
    
    # Update batch status and dates
    batch_request.status = 'completed'
    batch_request.claimed_date = timezone.now()
    batch_request.completed_date = timezone.now()
    batch_request.claimed_by = request.user
    batch_request.save()
    
    # Create notification for the requester
    Notification.objects.create(
        user=batch_request.user,
        message=f"Your supply request #{batch_request.id} has been completed and items have been claimed.",
        remarks=f"Total items claimed: {len(claimed_items)}"
    )
    
    # Log batch completion
    ActivityLog.log_activity(
        user=request.user,
        action='complete',
        model_name='SupplyRequestBatch',
        object_repr=f"Batch #{batch_id}",
        description=f"Completed batch request #{batch_id} with {len(claimed_items)} items claimed"
    )
    
    return redirect('user_supply_requests')


@permission_required('app.view_admin_module') 
@login_required
@require_POST
def claim_individual_item(request, batch_id, item_id):
    """
    Handle claiming of an individual approved item.
    This will deduct stock and mark the specific item as completed.
    """
    batch_request = get_object_or_404(SupplyRequestBatch, id=batch_id)
    item = get_object_or_404(SupplyRequestItem, id=item_id, batch_request=batch_request)
    
    # Only allow claiming if item is approved and not yet claimed
    if item.status != 'approved' or item.claimed_date is not None:
        messages.error(request, 'This item is not available for claiming.')
        return redirect('batch_request_detail', batch_id=batch_id)
    
    # Check stock availability
    available_quantity = 0
    if hasattr(item.supply, 'quantity_info') and item.supply.quantity_info:
        available_quantity = item.supply.quantity_info.current_quantity or 0
    
    # Handle case where approved_quantity might be None (fallback to requested quantity)
    approved_qty = item.approved_quantity or item.quantity or 0
    
    if available_quantity < approved_qty:
        messages.error(request, f"Insufficient stock for {item.supply.supply_name}. Available: {available_quantity}, needed: {approved_qty}")
        return redirect('batch_request_detail', batch_id=batch_id)
    
    # Deduct from stock
    if hasattr(item.supply, 'quantity_info') and item.supply.quantity_info:
        current_qty = item.supply.quantity_info.current_quantity or 0
        item.supply.quantity_info.current_quantity = max(0, current_qty - approved_qty)
        item.supply.quantity_info.save()
    
    # Update the approved_quantity if it was None
    if item.approved_quantity is None:
        item.approved_quantity = item.quantity
    
    # Mark item as completed and claimed
    item.status = 'completed'
    item.claimed_date = timezone.now()
    item.save()
    
    # Check if all approved items in the batch are now completed
    remaining_approved_items = batch_request.items.filter(status='approved', claimed_date__isnull=True)
    if not remaining_approved_items.exists():
        # All approved items have been claimed, mark batch as completed
        batch_request.status = 'completed'
        batch_request.completed_date = timezone.now()
        if not batch_request.claimed_date:
            batch_request.claimed_date = timezone.now()
        if not batch_request.claimed_by:
            batch_request.claimed_by = request.user
        batch_request.save()
        
        # Notify user
        Notification.objects.create(
            user=batch_request.user,
            message=f"Your supply request #{batch_request.id} has been completed.",
            remarks="All approved items have been claimed."
        )
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='claim',
        model_name='SupplyRequestItem',
        object_repr=f"Batch #{batch_id} - {item.supply.supply_name}",
        description=f"Claimed {item.approved_quantity or item.quantity} units of {item.supply.supply_name} from batch request #{batch_id}"
    )
    
    return redirect('batch_request_detail', batch_id=batch_id)

# Batch Borrow Request Management Views
@permission_required('app.view_admin_module')
@login_required
def borrow_batch_request_detail(request, batch_id):
    """View detailed information about a batch borrow request with individual item actions"""
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        remarks = request.POST.get('remarks', '')
        
        if item_id:
            item = get_object_or_404(BorrowRequestItem, id=item_id, batch_request=batch_request)
            
            if action == 'approve':
                # Check availability before approving
                available_quantity = item.property.quantity or 0
                approved_quantity = int(request.POST.get('approved_quantity', item.quantity))
                
                if approved_quantity > available_quantity:
                    messages.error(request, f'Only {available_quantity} units of {item.property.property_name} are available.')
                    return redirect('borrow_batch_request_detail', batch_id=batch_id)
                
                item.status = 'approved'
                item.approved_quantity = approved_quantity
                if remarks:
                    item.remarks = remarks
                item.save()
                
                # Create notification
                Notification.objects.create(
                    user=batch_request.user,
                    message=f"Item '{item.property.property_name}' in your batch borrow request #{batch_request.id} has been approved for {approved_quantity} units.",
                    remarks=remarks
                )
                
                messages.success(request, f'Item "{item.property.property_name}" approved successfully.')
                
            elif action == 'reject':
                item.status = 'rejected'
                if remarks:
                    item.remarks = remarks
                item.save()
                
                # Create notification
                Notification.objects.create(
                    user=batch_request.user,
                    message=f"Item '{item.property.property_name}' in your batch borrow request #{batch_request.id} has been rejected.",
                    remarks=remarks
                )
                
                messages.success(request, f'Item "{item.property.property_name}" rejected successfully.')
            
            # Update batch status based on individual item statuses
            total_items = batch_request.items.count()
            approved_items = batch_request.items.filter(status='approved').count()
            rejected_items = batch_request.items.filter(status='rejected').count()
            pending_items = batch_request.items.filter(status='pending').count()
            processed_items = approved_items + rejected_items
            
            if processed_items == total_items:
                # All items have been processed (approved or rejected)
                if approved_items > 0:
                    # At least some items were approved
                    batch_request.status = 'for_claiming'
                    if approved_items == total_items:
                        batch_request.approved_date = timezone.now()
                else:
                    # All items were rejected
                    batch_request.status = 'rejected'
            elif approved_items > 0:
                # Some approved, some still pending
                batch_request.status = 'partially_approved'
            else:
                # No items approved yet (either all pending or all rejected)
                if rejected_items > 0 and pending_items > 0:
                    # Some rejected, some pending
                    batch_request.status = 'pending'
                else:
                    # All pending or all rejected
                    batch_request.status = 'pending' if pending_items > 0 else 'rejected'
            
            batch_request.save()
            
            # Send borrow batch completion email ONLY if all items are now processed
            if processed_items == total_items:
                # All items have been processed, send completion email
                from .utils import send_borrow_batch_request_completion_email
                approved_items_qs = batch_request.items.filter(status='approved')
                rejected_items_qs = batch_request.items.filter(status='rejected')
                send_borrow_batch_request_completion_email(batch_request, approved_items_qs, rejected_items_qs)
        
        return redirect('borrow_batch_request_detail', batch_id=batch_id)
    
    context = {
        'batch': batch_request,
        'items': batch_request.items.all().order_by('property__property_name')
    }
    
    return render(request, 'app/borrow_batch_request_detail.html', context)

@permission_required('app.view_admin_module')
@login_required
@require_POST
def claim_borrow_batch_items(request, batch_id):
    """
    Handle claiming of all approved items in a batch borrow request.
    This will deduct stock and mark items as active.
    """
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    
    # Only allow claiming if batch is in for_claiming status
    if batch_request.status != 'for_claiming':
        messages.error(request, 'This request is not available for claiming.')
        return redirect('user_borrow_requests')
    
    # Get all approved items that haven't been claimed yet
    approved_items = batch_request.items.filter(status='approved', claimed_date__isnull=True)
    
    if not approved_items.exists():
        messages.error(request, 'No approved items available for claiming.')
        return redirect('user_borrow_requests')
    
    # Check stock availability for all items before processing
    insufficient_stock_items = []
    for item in approved_items:
        available_quantity = item.property.quantity or 0
        approved_qty = item.approved_quantity or item.quantity or 0
        
        if available_quantity < approved_qty:
            insufficient_stock_items.append(f"{item.property.property_name} (need: {approved_qty}, available: {available_quantity})")
    
    if insufficient_stock_items:
        messages.error(request, f"Insufficient stock for: {', '.join(insufficient_stock_items)}")
        return redirect('user_borrow_requests')
    
    # Process all approved items
    claimed_items = []
    
    for item in approved_items:
        approved_qty = item.approved_quantity or item.quantity or 0
        
        # Deduct from property quantity
        item.property.quantity -= approved_qty
        item.property.save()
        
        # Update the approved_quantity if it was None
        if item.approved_quantity is None:
            item.approved_quantity = item.quantity
        
        # Mark item as active and claimed
        item.status = 'active'
        item.claimed_date = timezone.now()
        item.save()
        
        claimed_items.append(item)
        
        # Log activity
        ActivityLog.log_activity(
            user=request.user,
            action='claim',
            model_name='BorrowRequestItem',
            object_repr=f"Batch #{batch_id} - {item.property.property_name}",
            description=f"Claimed {approved_qty} units of {item.property.property_name} from batch borrow request #{batch_id}"
        )
    
    # Update batch status and dates
    batch_request.status = 'active'
    batch_request.claimed_date = timezone.now()
    batch_request.claimed_by = request.user
    batch_request.save()
    
    # Create notification for the requester
    Notification.objects.create(
        user=batch_request.user,
        message=f"Your borrow request #{batch_request.id} is now active and items have been claimed.",
        remarks=f"Total items claimed: {len(claimed_items)}. Please return by: {batch_request.latest_return_date}"
    )
    
    # Log batch activation
    ActivityLog.log_activity(
        user=request.user,
        action='activate',
        model_name='BorrowRequestBatch',
        object_repr=f"Batch #{batch_id}",
        description=f"Activated batch borrow request #{batch_id} with {len(claimed_items)} items claimed"
    )
    
    messages.success(request, f'Successfully claimed {len(claimed_items)} items.')
    return redirect('user_borrow_requests')

@permission_required('app.view_admin_module')
@login_required
@require_POST
def return_borrow_batch_items(request, batch_id):
    """
    Handle returning of all active items in a batch borrow request.
    This will increase stock and mark items as returned.
    """
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    
    # Only allow returning if batch is in active or overdue status
    if batch_request.status not in ['active', 'overdue']:
        messages.error(request, 'This request is not available for returning.')
        return redirect('user_borrow_requests')
    
    # Get all active items
    active_items = batch_request.items.filter(status__in=['active', 'overdue'])
    
    if not active_items.exists():
        messages.error(request, 'No active items available for returning.')
        return redirect('user_borrow_requests')
    
    # Process all active items
    returned_items = []
    
    for item in active_items:
        approved_qty = item.approved_quantity or item.quantity or 0
        
        # Add back to property quantity
        item.property.quantity += approved_qty
        item.property.save()
        
        # Mark item as returned
        item.status = 'returned'
        item.actual_return_date = timezone.now().date()
        item.save()
        
        returned_items.append(item)
        
        # Log activity
        ActivityLog.log_activity(
            user=request.user,
            action='return',
            model_name='BorrowRequestItem',
            object_repr=f"Batch #{batch_id} - {item.property.property_name}",
            description=f"Returned {approved_qty} units of {item.property.property_name} from batch borrow request #{batch_id}"
        )
    
    # Update batch status and dates
    batch_request.status = 'returned'
    batch_request.returned_date = timezone.now()
    batch_request.completed_date = timezone.now()
    batch_request.save()
    
    # Create notification for the requester
    Notification.objects.create(
        user=batch_request.user,
        message=f"Your borrow request #{batch_request.id} has been marked as returned.",
        remarks="Thank you for returning all items."
    )
    
    # Log batch completion
    ActivityLog.log_activity(
        user=request.user,
        action='return',
        model_name='BorrowRequestBatch',
        object_repr=f"Batch #{batch_id}",
        description=f"Completed batch borrow request #{batch_id} with {len(returned_items)} items returned"
    )
    
    messages.success(request, f'Successfully returned {len(returned_items)} items.')
    return redirect('user_borrow_requests')

class UserBorrowRequestBatchListView(LoginRequiredMixin, ListView):
    """View for displaying batch borrow requests - shows all for admin, user's own for regular users"""
    model = BorrowRequestBatch
    template_name = 'app/borrow_batch.html'
    context_object_name = 'batch_requests'
    paginate_by = 10

    def get_queryset(self):
        # Check for overdue batches before getting the queryset
        BorrowRequestBatch.check_overdue_batches()
        
        queryset = BorrowRequestBatch.objects \
            .select_related('user', 'user__userprofile', 'claimed_by') \
            .prefetch_related('items__property') \
            .order_by('request_date')
        
        # If user has admin permissions, show all requests
        # If user is regular user, show only their requests
        if self.request.user.has_perm('app.view_admin_module'):
            # Admin users see all requests
            return queryset
        else:
            # Regular users see only their own requests
            return queryset.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the current tab from request
        current_tab = self.request.GET.get('tab', 'pending')
        
        # Get search and filter parameters
        search_query = self.request.GET.get('search', '').strip()
        department_filter = self.request.GET.get('department', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        # Base queryset with related data
        base_queryset = BorrowRequestBatch.objects.select_related('user', 'user__userprofile', 'user__userprofile__department').prefetch_related('items__property').order_by('request_date')
        
        # Apply user filtering based on permissions
        if self.request.user.has_perm('app.view_admin_module'):
            # Admin users see all requests
            pass  # No additional filtering needed
        else:
            # Regular users see only their own requests
            base_queryset = base_queryset.filter(user=self.request.user)
        
        # Apply search filter
        if search_query:
            base_queryset = base_queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(purpose__icontains=search_query) |
                Q(items__property__property_name__icontains=search_query)
            ).distinct()
        
        # Apply department filter
        if department_filter:
            base_queryset = base_queryset.filter(user__userprofile__department__name=department_filter)
        
        # Apply date filters
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                base_queryset = base_queryset.filter(request_date__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                base_queryset = base_queryset.filter(request_date__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Get filtered requests by status
        pending_requests = base_queryset.filter(status='pending')
        partially_approved_requests = base_queryset.filter(status='partially_approved')
        for_claiming_requests = base_queryset.filter(status='for_claiming')
        active_requests = base_queryset.filter(status='active')
        returned_requests = base_queryset.filter(status='returned')
        overdue_requests = base_queryset.filter(status='overdue')
        rejected_requests = base_queryset.filter(status='rejected')
        
        # Pagination for each tab
        paginator_pending = Paginator(pending_requests, self.paginate_by)
        paginator_partially_approved = Paginator(partially_approved_requests, self.paginate_by)
        paginator_for_claiming = Paginator(for_claiming_requests, self.paginate_by)
        paginator_active = Paginator(active_requests, self.paginate_by)
        paginator_returned = Paginator(returned_requests, self.paginate_by)
        paginator_overdue = Paginator(overdue_requests, self.paginate_by)
        paginator_rejected = Paginator(rejected_requests, self.paginate_by)
        
        # Get page numbers for each tab
        page_pending = self.request.GET.get('pending_page', 1)
        page_partially_approved = self.request.GET.get('partially_approved_page', 1)
        page_for_claiming = self.request.GET.get('for_claiming_page', 1)
        page_active = self.request.GET.get('active_page', 1)
        page_returned = self.request.GET.get('returned_page', 1)
        page_overdue = self.request.GET.get('overdue_page', 1)
        page_rejected = self.request.GET.get('rejected_page', 1)
        
        context.update({
            'current_tab': current_tab,
            'pending_requests': paginator_pending.get_page(page_pending),
            'partially_approved_requests': paginator_partially_approved.get_page(page_partially_approved),
            'for_claiming_requests': paginator_for_claiming.get_page(page_for_claiming),
            'active_requests': paginator_active.get_page(page_active),
            'returned_requests': paginator_returned.get_page(page_returned),
            'overdue_requests': paginator_overdue.get_page(page_overdue),
            'rejected_requests': paginator_rejected.get_page(page_rejected),
            'search_query': search_query,
            'department_filter': department_filter,
            'date_from': date_from,
            'date_to': date_to,
            'departments': Department.objects.all(),
        })
        
        return context


# Individual Borrow Item Management Views for Batch Requests
@permission_required('app.view_admin_module')
@login_required
@require_POST
def approve_borrow_item(request, batch_id, item_id):
    """Approve an individual item in a batch borrow request"""
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    item = get_object_or_404(BorrowRequestItem, id=item_id, batch_request=batch_request)
    
    # Get approved quantity from form
    approved_quantity = request.POST.get('approved_quantity', item.quantity)
    try:
        approved_quantity = int(approved_quantity)
        if approved_quantity <= 0 or approved_quantity > item.quantity:
            messages.error(request, f'Invalid approved quantity. Must be between 1 and {item.quantity}.')
            return redirect('borrow_batch_request_detail', batch_id=batch_id)
    except (ValueError, TypeError):
        approved_quantity = item.quantity
    
    # Check if enough property units are available
    available_quantity = item.property.quantity or 0
    if approved_quantity > available_quantity:
        messages.error(request, f'Only {available_quantity} units of {item.property.property_name} are available.')
        return redirect('borrow_batch_request_detail', batch_id=batch_id)
    
    # Mark item as approved
    item.approved = True
    item.status = 'approved'
    item.approved_quantity = approved_quantity
    remarks = request.POST.get('remarks', '')
    if remarks:
        item.remarks = remarks
    item.save()
    
    # Check if all items in the batch are processed
    total_items = batch_request.items.count()
    approved_items = batch_request.items.filter(approved=True).count()
    rejected_items = batch_request.items.filter(approved=False, status='rejected').count()
    processed_items = approved_items + rejected_items
    
    # Update batch status
    if processed_items == total_items:
        # All items have been processed (approved or rejected)
        if approved_items > 0:
            batch_request.status = 'for_claiming'
        else:
            batch_request.status = 'rejected'
    elif approved_items > 0:
        batch_request.status = 'partially_approved'
    
    batch_request.save()
    
    # Send borrow batch completion email ONLY if all items are now processed
    if processed_items == total_items:
        # All items have been processed, send completion email
        from .utils import send_borrow_batch_request_completion_email
        approved_items_qs = batch_request.items.filter(status='approved')
        rejected_items_qs = batch_request.items.filter(status='rejected')
        send_borrow_batch_request_completion_email(batch_request, approved_items_qs, rejected_items_qs)
    
    # Create notification for user
    Notification.objects.create(
        user=batch_request.user,
        message=f"Item '{item.property.property_name}' in your batch borrow request #{batch_request.id} has been approved for {item.approved_quantity} units.",
        remarks=remarks
    )
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='approve',
        model_name='BorrowRequestItem',
        object_repr=f"Batch #{batch_id} - {item.property.property_name}",
        description=f"Approved {item.approved_quantity} out of {item.quantity} units of {item.property.property_name} in batch borrow request #{batch_id}"
    )
    
    return redirect('borrow_batch_request_detail', batch_id=batch_id)


@permission_required('app.view_admin_module')
@login_required
@require_POST
def reject_borrow_item(request, batch_id, item_id):
    """Reject an individual item in a batch borrow request"""
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    item = get_object_or_404(BorrowRequestItem, id=item_id, batch_request=batch_request)
    
    # Mark item as not approved and add remarks
    item.approved = False
    item.status = 'rejected'
    remarks = request.POST.get('remarks', '')
    if remarks:
        item.remarks = remarks
    item.save()
    
    # Check if all items in the batch are processed
    total_items = batch_request.items.count()
    approved_items = batch_request.items.filter(approved=True).count()
    rejected_items = batch_request.items.filter(approved=False, status='rejected').count()
    processed_items = approved_items + rejected_items
    
    # Update batch status
    if processed_items == total_items:
        # All items have been processed (approved or rejected)
        if approved_items > 0:
            batch_request.status = 'for_claiming'
        else:
            batch_request.status = 'rejected'
    elif approved_items > 0:
        batch_request.status = 'partially_approved'
    
    batch_request.save()
    
    # Send borrow batch completion email ONLY if all items are now processed
    if processed_items == total_items:
        # All items have been processed, send completion email
        from .utils import send_borrow_batch_request_completion_email
        approved_items_qs = batch_request.items.filter(status='approved')
        rejected_items_qs = batch_request.items.filter(status='rejected')
        send_borrow_batch_request_completion_email(batch_request, approved_items_qs, rejected_items_qs)
    
    # Create notification for user
    Notification.objects.create(
        user=batch_request.user,
        message=f"Item '{item.property.property_name}' in your batch borrow request #{batch_request.id} has been rejected.",
        remarks=remarks
    )
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='reject',
        model_name='BorrowRequestItem',
        object_repr=f"Batch #{batch_id} - {item.property.property_name}",
        description=f"Rejected {item.quantity} units of {item.property.property_name} in batch borrow request #{batch_id}"
    )
    
    return redirect('borrow_batch_request_detail', batch_id=batch_id)


@permission_required('app.view_admin_module')
@login_required
@require_POST
def claim_individual_borrow_item(request, batch_id, item_id):
    """
    Handle claiming of an individual approved borrow item.
    This will deduct stock and mark the specific item as active.
    """
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    item = get_object_or_404(BorrowRequestItem, id=item_id, batch_request=batch_request)
    
    # Only allow claiming if item is approved and not yet claimed
    if item.status != 'approved' or item.claimed_date is not None:
        messages.error(request, 'This item is not available for claiming.')
        return redirect('borrow_batch_request_detail', batch_id=batch_id)
    
    # Check stock availability
    available_quantity = item.property.quantity or 0
    approved_qty = item.approved_quantity or item.quantity or 0
    
    if available_quantity < approved_qty:
        messages.error(request, f"Insufficient stock for {item.property.property_name}. Available: {available_quantity}, needed: {approved_qty}")
        return redirect('borrow_batch_request_detail', batch_id=batch_id)
    
    # Deduct from property stock
    item.property.quantity -= approved_qty
    item.property.save()
    
    # Update the approved_quantity if it was None
    if item.approved_quantity is None:
        item.approved_quantity = item.quantity
    
    # Mark item as active and claimed
    item.status = 'active'
    item.claimed_date = timezone.now()
    item.save()
    
    # Check if all approved items in the batch are now active
    remaining_approved_items = batch_request.items.filter(status='approved', claimed_date__isnull=True)
    if not remaining_approved_items.exists():
        # All approved items have been claimed, mark batch as active
        batch_request.status = 'active'
        if not batch_request.claimed_date:
            batch_request.claimed_date = timezone.now()
        if not batch_request.claimed_by:
            batch_request.claimed_by = request.user
        batch_request.save()
        
        # Notify user
        Notification.objects.create(
            user=batch_request.user,
            message=f"Your borrow request #{batch_request.id} is now active.",
            remarks="All approved items have been claimed. Please return by the specified dates."
        )
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='claim',
        model_name='BorrowRequestItem',
        object_repr=f"Batch #{batch_id} - {item.property.property_name}",
        description=f"Claimed {item.approved_quantity or item.quantity} units of {item.property.property_name} from batch borrow request #{batch_id}"
    )
    
    return redirect('borrow_batch_request_detail', batch_id=batch_id)


@permission_required('app.view_admin_module')
@login_required
@require_POST
def return_individual_borrow_item(request, batch_id, item_id):
    """
    Handle returning of an individual active borrow item.
    This will increase stock and mark the specific item as returned.
    """
    batch_request = get_object_or_404(BorrowRequestBatch, id=batch_id)
    item = get_object_or_404(BorrowRequestItem, id=item_id, batch_request=batch_request)
    
    # Only allow returning if item is active or overdue
    if item.status not in ['active', 'overdue']:
        messages.error(request, 'This item is not available for returning.')
        return redirect('borrow_batch_request_detail', batch_id=batch_id)
    
    # Add back to property stock
    approved_qty = item.approved_quantity or item.quantity or 0
    item.property.quantity += approved_qty
    item.property.save()
    
    # Mark item as returned
    item.status = 'returned'
    item.actual_return_date = timezone.now().date()
    item.save()
    
    # Check if all active items in the batch are now returned
    remaining_active_items = batch_request.items.filter(status__in=['active', 'overdue'])
    if not remaining_active_items.exists():
        # All items have been returned, mark batch as returned
        batch_request.status = 'returned'
        batch_request.returned_date = timezone.now()
        batch_request.completed_date = timezone.now()
        batch_request.save()
        
        # Notify user
        Notification.objects.create(
            user=batch_request.user,
            message=f"Your borrow request #{batch_request.id} has been completed.",
            remarks="All items have been successfully returned."
        )
    
    # Log activity
    ActivityLog.log_activity(
        user=request.user,
        action='return',
        model_name='BorrowRequestItem',
        object_repr=f"Batch #{batch_id} - {item.property.property_name}",
        description=f"Returned {approved_qty} units of {item.property.property_name} from batch borrow request #{batch_id}"
    )
    
    return redirect('borrow_batch_request_detail', batch_id=batch_id)


class AdminProfileView(PermissionRequiredMixin, View):
    permission_required = 'auth.view_user'
    template_name = 'app/admin_profile.html'
    
    def get(self, request):
        from .forms import AdminProfileUpdateForm
        form = AdminProfileUpdateForm(user=request.user)
        
        # Get user profile or create one if it doesn't exist
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        return render(request, self.template_name, {
            'form': form,
            'user_profile': user_profile
        })
    
    def post(self, request):
        from .forms import AdminProfileUpdateForm
        form = AdminProfileUpdateForm(user=request.user, data=request.POST)
        
        # Get user profile or create one if it doesn't exist
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if form.is_valid():
            # Update user fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            
            # Update phone in user profile
            user_profile.phone = form.cleaned_data['phone']
            user_profile.save()
            
            # Handle password change if provided
            if form.cleaned_data.get('new_password'):
                request.user.set_password(form.cleaned_data['new_password'])
                # Update session auth hash to prevent logout
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                
                # Log password change activity
                ActivityLog.log_activity(
                    user=request.user,
                    action='change_password',
                    model_name='User',
                    object_repr=request.user.username,
                    description="Admin changed their password"
                )
            
            request.user.save()
            
            # Log profile update activity
            ActivityLog.log_activity(
                user=request.user,
                action='update',
                model_name='UserProfile',
                object_repr=f"{request.user.get_full_name() or request.user.username}",
                description="Admin updated their profile information"
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('admin_profile')
        
        return render(request, self.template_name, {
            'form': form,
            'user_profile': user_profile
        })

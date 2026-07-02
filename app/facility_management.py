from calendar import Calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from .forms import FacilityForm, FacilityReservationForm
from .models import Facility, FacilityReservation


def _parse_month_year(request):
    today = timezone.localdate()
    month = request.GET.get('month') or request.POST.get('month') or str(today.month)
    year = request.GET.get('year') or request.POST.get('year') or str(today.year)

    try:
        month = int(month)
        if month < 1 or month > 12:
            raise ValueError
    except (TypeError, ValueError):
        month = today.month

    try:
        year = int(year)
        if year < 1900:
            raise ValueError
    except (TypeError, ValueError):
        year = today.year

    return year, month


def _month_navigation(year, month):
    current = date(year, month, 1)
    previous_month = current - timedelta(days=1)
    next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    today = timezone.localdate()

    return {
        'previous_year': previous_month.year,
        'previous_month': previous_month.month,
        'next_year': next_month.year,
        'next_month': next_month.month,
        'today_year': today.year,
        'today_month': today.month,
    }


def _format_reservation_range(reservation):
    start = timezone.localtime(reservation.start_datetime)
    end = timezone.localtime(reservation.end_datetime)

    if start.date() == end.date():
        return f"{start.strftime('%b %d, %I:%M %p')} - {end.strftime('%I:%M %p')}"

    return f"{start.strftime('%b %d, %I:%M %p')} - {end.strftime('%b %d, %I:%M %p')}"


def _local_date(value):
    return timezone.localtime(value).date() if timezone.is_aware(value) else value.date()


def _build_calendar_data(facility, year, month):
    calendar = Calendar(firstweekday=6)
    month_weeks = calendar.monthdatescalendar(year, month)
    month_start = date(year, month, 1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    reservations = []
    if facility:
        reservations = list(
            FacilityReservation.objects.filter(
                facility=facility,
                start_datetime__date__lte=month_end,
                end_datetime__date__gte=month_start,
            ).order_by('start_datetime', 'end_datetime')
        )

    day_map = {}
    for week in month_weeks:
        for current_day in week:
            day_map[current_day] = []

    for reservation in reservations:
        current_day = max(_local_date(reservation.start_datetime), month_start)
        last_day = min(_local_date(reservation.end_datetime), month_end)
        while current_day <= last_day:
            if current_day in day_map:
                local_start = timezone.localtime(reservation.start_datetime)
                local_end = timezone.localtime(reservation.end_datetime)
                day_map[current_day].append({
                    'id': reservation.id,
                    'purpose': reservation.purpose,
                    'reserver_name': reservation.reserver_name,
                    'status': reservation.status,
                    'status_display': reservation.get_status_display(),
                    'status_class': f'status-{reservation.status}',
                    'time_range': _format_reservation_range(reservation),
                    'start_display': local_start,
                    'end_display': local_end,
                })
            current_day += timedelta(days=1)

    weeks = []
    for week in month_weeks:
        week_days = []
        for current_day in week:
            week_days.append({
                'date': current_day,
                'day_number': current_day.day,
                'in_current_month': current_day.month == month,
                'is_today': current_day == timezone.localdate(),
                'reservations': day_map.get(current_day, []),
            })
        weeks.append(week_days)

    return weeks


def _build_facility_context(request, include_management_data=True):
    facilities = Facility.objects.order_by('name')
    facility_id = request.GET.get('facility') or request.POST.get('facility')

    if facility_id:
        selected_facility = facilities.filter(pk=facility_id).first()
    else:
        selected_facility = facilities.first()

    year, month = _parse_month_year(request)
    navigation = _month_navigation(year, month)

    context = {
        'facilities': facilities,
        'selected_facility': selected_facility,
        'selected_facility_id': selected_facility.id if selected_facility else '',
        'year': year,
        'month': month,
        'month_name': date(year, month, 1).strftime('%B %Y'),
        'calendar_weeks': _build_calendar_data(selected_facility, year, month),
        'navigation': navigation,
    }

    if include_management_data:
        edit_facility_id = request.GET.get('edit_facility') or request.POST.get('edit_facility')
        edit_reservation_id = request.GET.get('edit_reservation') or request.POST.get('edit_reservation')

        facility_instance = None
        if edit_facility_id:
            facility_instance = Facility.objects.filter(pk=edit_facility_id).first()

        reservation_instance = None
        if edit_reservation_id:
            reservation_instance = FacilityReservation.objects.select_related('facility').filter(pk=edit_reservation_id).first()

        facility_form = FacilityForm(instance=facility_instance)
        reservation_form = FacilityReservationForm(instance=reservation_instance)

        if not reservation_instance and selected_facility:
            reservation_form.initial.setdefault('facility', selected_facility)

        all_reservations = FacilityReservation.objects.select_related('facility').order_by('-start_datetime')
        reservation_facility_filter = request.GET.get('facility') or request.POST.get('facility')
        status_filter = request.GET.get('status', '')

        if reservation_facility_filter:
            all_reservations = all_reservations.filter(facility_id=reservation_facility_filter)
        if status_filter:
            all_reservations = all_reservations.filter(status=status_filter)

        paginator = Paginator(all_reservations, 15)
        page_number = request.GET.get('page') or request.POST.get('page') or 1
        reservations_page = paginator.get_page(page_number)

        context.update({
            'active_tab': request.GET.get('tab') or request.POST.get('tab') or 'calendar',
            'facility_form': facility_form,
            'reservation_form': reservation_form,
            'reservations_page': reservations_page,
            'status_filter': status_filter,
            'reservation_facility_filter': reservation_facility_filter or '',
        })

    return context


class FacilityReservationsManagementView(PermissionRequiredMixin, TemplateView):
    template_name = 'app/facility_reservations_management.html'
    permission_required = 'app.view_admin_module'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_facility_context(self.request, include_management_data=True))
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'save_facility':
            facility_id = request.POST.get('facility_id')
            instance = Facility.objects.filter(pk=facility_id).first() if facility_id else None
            form = FacilityForm(request.POST, instance=instance)
            if form.is_valid():
                facility = form.save()
                messages.success(request, f'Facility "{facility.name}" has been saved.')
                return redirect(f"{request.path}?tab=calendar&facility={facility.id}")

            return render(request, self.template_name, self.get_context_data(
                facility_form=form,
                selected_facility=instance,
            ))

        if action == 'delete_facility':
            facility_id = request.POST.get('facility_id')
            facility = get_object_or_404(Facility, pk=facility_id)
            facility_name = facility.name
            facility.delete()
            messages.success(request, f'Facility "{facility_name}" has been removed.')
            return redirect(request.path)

        if action == 'save_reservation':
            reservation_id = request.POST.get('reservation_id')
            instance = FacilityReservation.objects.filter(pk=reservation_id).first() if reservation_id else None
            form = FacilityReservationForm(request.POST, instance=instance)
            if form.is_valid():
                reservation = form.save()
                messages.success(request, 'Reservation has been saved.')
                local_start = timezone.localtime(reservation.start_datetime)
                return redirect(
                    f"{request.path}?tab=list&facility={reservation.facility_id}&month={local_start.month}&year={local_start.year}"
                )

            return render(request, self.template_name, self.get_context_data(
                reservation_form=form,
                selected_facility=self.get_selected_facility(request),
            ))

        if action == 'delete_reservation':
            reservation_id = request.POST.get('reservation_id')
            reservation = get_object_or_404(FacilityReservation, pk=reservation_id)
            facility_id = reservation.facility_id
            reservation.delete()
            messages.success(request, 'Reservation has been removed.')
            return redirect(f"{request.path}?tab=list&facility={facility_id}")

        messages.error(request, 'Unsupported action.')
        return redirect(request.path)


class PublicFacilityReservationsView(TemplateView):
    template_name = 'app/facility_reservations_public.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_facility_context(self.request, include_management_data=False))
        context['active_tab'] = 'calendar'
        return context

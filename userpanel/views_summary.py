# Additional views for user requests summary
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app.models import SupplyRequestBatch, BorrowRequestBatch, ReservationBatch


class UserRequestsSummaryView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View for users to see a summary of all their requested items, filterable by year with PDF export"""
    template_name = 'userpanel/user_requests_summary.html'
    permission_required = 'app.view_user_module'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get separate filters for tally and items
        tally_year_filter = self.request.GET.get('tally_year', '')
        tally_month_filter = self.request.GET.get('tally_month', '')
        items_year_filter = self.request.GET.get('items_year', '')
        items_month_filter = self.request.GET.get('items_month', '')
        
        # Initialize items summary
        items_summary = []
        
        # Get all supply requests - for items table use items_year_filter and items_month_filter
        supply_batches = SupplyRequestBatch.objects.filter(user=self.request.user)
        if items_year_filter:
            supply_batches = supply_batches.filter(request_date__year=items_year_filter)
        if items_month_filter:
            supply_batches = supply_batches.filter(request_date__month=items_month_filter)
        
        for batch in supply_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Supply',
                    'item_name': item.supply.supply_name,
                    'category': item.supply.category.name if item.supply.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'purpose': batch.purpose,
                    'request_id': f"SB-{batch.id}"
                })
        
        # Get all borrow requests
        borrow_batches = BorrowRequestBatch.objects.filter(user=self.request.user)
        if items_year_filter:
            borrow_batches = borrow_batches.filter(request_date__year=items_year_filter)
        if items_month_filter:
            borrow_batches = borrow_batches.filter(request_date__month=items_month_filter)
        
        for batch in borrow_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Borrow',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'return_date': item.return_date,
                    'purpose': batch.purpose,
                    'request_id': f"BB-{batch.id}"
                })
        
        # Get all reservations
        reservation_batches = ReservationBatch.objects.filter(user=self.request.user)
        if items_year_filter:
            reservation_batches = reservation_batches.filter(request_date__year=items_year_filter)
        if items_month_filter:
            reservation_batches = reservation_batches.filter(request_date__month=items_month_filter)
        
        for batch in reservation_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Reservation',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.quantity if item.status == 'approved' else 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'needed_date': item.needed_date,
                    'return_date': item.return_date,
                    'purpose': batch.purpose,
                    'request_id': f"RB-{batch.id}"
                })
        
        # Sort by date (most recent first)
        items_summary.sort(key=lambda x: x['request_date'], reverse=True)
        
        # Get available years for filter dropdown
        all_years = set()
        for model in [SupplyRequestBatch, BorrowRequestBatch, ReservationBatch]:
            years = model.objects.filter(user=self.request.user).dates('request_date', 'year')
            all_years.update([date.year for date in years])
        
        available_years = sorted(list(all_years), reverse=True)
        
        # Calculate statistics (before pagination) - based on items_year/month filters
        total_items = len(items_summary)
        total_requested = sum(item['quantity'] for item in items_summary)
        total_approved = sum(item['approved_quantity'] for item in items_summary)
        
        # Group by type
        supply_count = len([i for i in items_summary if i['type'] == 'Supply'])
        borrow_count = len([i for i in items_summary if i['type'] == 'Borrow'])
        reservation_count = len([i for i in items_summary if i['type'] == 'Reservation'])
        
        # Build separate tally data using tally_year_filter and tally_month_filter
        tally_items = []
        
        # Get all supply requests for tally - ONLY COMPLETED/CLAIMED SUPPLIES
        tally_supply_batches = SupplyRequestBatch.objects.filter(user=self.request.user)
        if tally_year_filter:
            tally_supply_batches = tally_supply_batches.filter(request_date__year=tally_year_filter)
        if tally_month_filter:
            tally_supply_batches = tally_supply_batches.filter(request_date__month=tally_month_filter)
        
        for batch in tally_supply_batches:
            # Only include completed supply items (those that have been claimed)
            for item in batch.items.filter(status='completed'):
                tally_items.append({
                    'type': 'Supply',
                    'item_name': item.supply.supply_name,
                    'category': item.supply.category.name if item.supply.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                })
        
        # Get all borrow requests for tally
        tally_borrow_batches = BorrowRequestBatch.objects.filter(user=self.request.user)
        if tally_year_filter:
            tally_borrow_batches = tally_borrow_batches.filter(request_date__year=tally_year_filter)
        if tally_month_filter:
            tally_borrow_batches = tally_borrow_batches.filter(request_date__month=tally_month_filter)
        
        for batch in tally_borrow_batches:
            for item in batch.items.all():
                tally_items.append({
                    'type': 'Borrow',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                })
        
        # Get all reservations for tally
        tally_reservation_batches = ReservationBatch.objects.filter(user=self.request.user)
        if tally_year_filter:
            tally_reservation_batches = tally_reservation_batches.filter(request_date__year=tally_year_filter)
        if tally_month_filter:
            tally_reservation_batches = tally_reservation_batches.filter(request_date__month=tally_month_filter)
        
        for batch in tally_reservation_batches:
            for item in batch.items.all():
                tally_items.append({
                    'type': 'Reservation',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.quantity if item.status == 'approved' else 0,
                })
        
        # Build item tally (group by item name and type)
        tally_dict = {}
        for item in tally_items:
            key = f"{item['type']}_{item['item_name']}"
            if key not in tally_dict:
                tally_dict[key] = {
                    'type': item['type'],
                    'item_name': item['item_name'],
                    'category': item['category'],
                    'total_quantity': 0,
                    'total_approved': 0,
                    'request_count': 0,
                }
            tally_dict[key]['total_quantity'] += item['quantity']
            tally_dict[key]['total_approved'] += item['approved_quantity']
            tally_dict[key]['request_count'] += 1
        
        tally_data = sorted(tally_dict.values(), key=lambda x: x['total_quantity'], reverse=True)
        
        # Pagination for both tally and items
        # Tally pagination
        tally_paginator = Paginator(tally_data, 10)  # 10 items per page
        tally_page = self.request.GET.get('tally_page', 1)
        
        try:
            tally_page_obj = tally_paginator.page(tally_page)
        except PageNotAnInteger:
            tally_page_obj = tally_paginator.page(1)
        except EmptyPage:
            tally_page_obj = tally_paginator.page(tally_paginator.num_pages)
        
        # Items pagination
        paginator = Paginator(items_summary, 10)  # 10 items per page
        page = self.request.GET.get('page', 1)
        
        try:
            items_page = paginator.page(page)
        except PageNotAnInteger:
            items_page = paginator.page(1)
        except EmptyPage:
            items_page = paginator.page(paginator.num_pages)
        
        # Define month names
        month_names = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        
        context.update({
            'items_summary': items_page,
            'items_year_filter': items_year_filter,
            'items_month_filter': items_month_filter,
            'tally_year_filter': tally_year_filter,
            'tally_month_filter': tally_month_filter,
            'tally_data': tally_page_obj,
            'available_years': available_years,
            'month_names': month_names,
            'total_items': total_items,
            'total_requested': total_requested,
            'total_approved': total_approved,
            'supply_count': supply_count,
            'borrow_count': borrow_count,
            'reservation_count': reservation_count,
        })
        
        return context


@login_required
@permission_required('app.view_user_module')
def export_requests_summary_pdf(request):
    """Export user's requests summary as PDF"""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    from django.utils import timezone
    import traceback
    
    try:
        # Get year and month filters
        year_filter = request.GET.get('year', '')
        month_filter = request.GET.get('month', '')
        
        # Create the HttpResponse object with PDF headers
        response = HttpResponse(content_type='application/pdf')
        
        # Build filename with filters
        filter_text = []
        if year_filter:
            filter_text.append(f"Year_{year_filter}")
        if month_filter:
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            filter_text.append(f"Month_{month_names[int(month_filter)]}")
        
        filename = f'My_Requests_Summary_{"_".join(filter_text) if filter_text else "All_Time"}_{timezone.now().strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create the PDF object using BytesIO buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#152d64'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Title
        title_text = f"My Requests Summary"
        if year_filter or month_filter:
            title_text += " -"
            if year_filter:
                title_text += f" Year {year_filter}"
            if month_filter:
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                              'July', 'August', 'September', 'October', 'November', 'December']
                title_text += f" {month_names[int(month_filter)]}"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # User info
        user = request.user
        user_name = f"{user.first_name} {user.last_name}" if user.first_name or user.last_name else user.username
        department = user.userprofile.department.name if hasattr(user, 'userprofile') and user.userprofile.department else "N/A"
        
        info_text = f"<b>Requester:</b> {user_name} | <b>Department:</b> {department} | <b>Generated:</b> {timezone.now().strftime('%B %d, %Y %I:%M %p')}"
        info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#495057'))
        elements.append(Paragraph(info_text, info_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Get items summary
        items_summary = []
        
        # Get all supply requests
        supply_batches = SupplyRequestBatch.objects.filter(user=request.user)
        if year_filter:
            supply_batches = supply_batches.filter(request_date__year=year_filter)
        if month_filter:
            supply_batches = supply_batches.filter(request_date__month=month_filter)
        
        for batch in supply_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Supply',
                    'item_name': item.supply.supply_name,
                    'category': item.supply.category.name if item.supply.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'request_id': f"SB-{batch.id}"
                })
        
        # Get all borrow requests
        borrow_batches = BorrowRequestBatch.objects.filter(user=request.user)
        if year_filter:
            borrow_batches = borrow_batches.filter(request_date__year=year_filter)
        if month_filter:
            borrow_batches = borrow_batches.filter(request_date__month=month_filter)
        
        for batch in borrow_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Borrow',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.approved_quantity or 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'request_id': f"BB-{batch.id}"
                })
        
        # Get all reservations
        reservation_batches = ReservationBatch.objects.filter(user=request.user)
        if year_filter:
            reservation_batches = reservation_batches.filter(request_date__year=year_filter)
        if month_filter:
            reservation_batches = reservation_batches.filter(request_date__month=month_filter)
        
        for batch in reservation_batches:
            for item in batch.items.all():
                items_summary.append({
                    'type': 'Reservation',
                    'item_name': item.property.property_name,
                    'category': item.property.category.name if item.property.category else 'Uncategorized',
                    'quantity': item.quantity,
                    'approved_quantity': item.quantity if item.status == 'approved' else 0,
                    'status': item.get_status_display(),
                    'request_date': batch.request_date,
                    'request_id': f"RB-{batch.id}"
                })
        
        # Sort by date
        items_summary.sort(key=lambda x: x['request_date'], reverse=True)
        
        # Statistics
        total_items = len(items_summary)
        total_requested = sum(item['quantity'] for item in items_summary)
        total_approved = sum(item['approved_quantity'] for item in items_summary)
        
        stats_text = f"<b>Total Items:</b> {total_items} | <b>Total Quantity Requested:</b> {total_requested} | <b>Total Quantity Approved:</b> {total_approved}"
        elements.append(Paragraph(stats_text, info_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if not items_summary:
            no_data_text = "No requests found for the selected period."
            elements.append(Paragraph(no_data_text, styles['Normal']))
        else:
            # Create table data
            table_data = [
                ["Request ID", "Type", "Item Name", "Category", "Req\nQty", "App\nQty", "Status", "Request Date"]
            ]
            
            for item in items_summary:
                table_data.append([
                    item['request_id'],
                    item['type'],
                    item['item_name'][:40] + '...' if len(item['item_name']) > 40 else item['item_name'],
                    item['category'][:20] + '...' if len(item['category']) > 20 else item['category'],
                    str(item['quantity']),
                    str(item['approved_quantity']),
                    item['status'],
                    item['request_date'].strftime('%m/%d/%Y')
                ])
            
            # Create table with column widths
            col_widths = [0.9*inch, 0.8*inch, 2.2*inch, 1.3*inch, 0.5*inch, 0.5*inch, 1.0*inch, 0.9*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            main_table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#152d64')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Body styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (4, 1), (5, -1), 'CENTER'),  # Quantity columns centered
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('LEFTPADDING', (0, 1), (-1, -1), 4),
                ('RIGHTPADDING', (0, 1), (-1, -1), 4),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#152d64')),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(main_table)
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error generating PDF: {str(e)}")
        print(traceback.format_exc())
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

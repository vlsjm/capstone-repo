"""
PDF generation utilities for generating requisition and issue slips.
"""
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime


def generate_requisition_slip_pdf(batch_request):
    """
    Generate a requisition and issue slip PDF that exactly matches the official form format.
    This serves as a receipt/documentation for the supply request.
    """
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for the 'Flowable' objects
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Regular text style
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    )
    
    # Title
    story.append(Paragraph("REQUISITION AND ISSUE SLIP", title_style))
    story.append(Spacer(1, 15))
    
    # Request Number, Entity Name, and Department in aligned table
    request_num = f"REQ-{batch_request.id:03d}"
    entity_text = f"Entity Name: CvSU - Bacoor City Campus"
    department_name = batch_request.user.userprofile.department.name if batch_request.user.userprofile.department else "N/A"
    dept_text = f"Department/Office: {department_name}"
    
    # Create aligned table for request number, entity name, and department
    info_data = [
        [request_num],
        [entity_text],
        [dept_text]
    ]
    info_table = Table(info_data, colWidths=[7.5*inch])
    info_table.setStyle(TableStyle([
        # Request number row
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        
        # Entity name row
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('ALIGN', (0, 1), (-1, 1), 'LEFT'),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        
        # Department row with grid
        ('FONTSIZE', (0, 2), (-1, 2), 10),
        ('ALIGN', (0, 2), (-1, 2), 'LEFT'),
        ('TOPPADDING', (0, 2), (-1, 2), 8),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 8),
        ('GRID', (0, 2), (-1, 2), 1, colors.black),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5))
    
    # Main table headers
    headers = [
        "Stock No.", "Unit", "Requisition\nDescription", "Quantity", 
        "Stock Available?\nYes    No", "Issue\nQuantity", "Remarks"
    ]
    
    # Prepare table data with items
    table_data = [headers]
    
    # Add items
    for item in batch_request.items.all().order_by('supply__supply_name'):
        stock_no = f"SUP-{item.supply.id:03d}"
        unit = "pcs"  # Default unit
        description = item.supply.supply_name
        req_quantity = str(item.quantity)
        
        # Stock availability
        available_qty = item.supply.quantity_info.current_quantity if hasattr(item.supply, 'quantity_info') else 0
        stock_available = "✓ Yes" if available_qty > 0 else "✓ No"
        
        # Issue quantity (approved quantity)
        issue_qty = str(item.approved_quantity) if item.approved_quantity else ""
        
        # Remarks
        remarks = item.remarks if item.remarks else ""
        
        table_data.append([
            stock_no, unit, description, req_quantity, stock_available, issue_qty, remarks
        ])
    
    # Add empty rows to match the form (minimum 15 rows total)
    while len(table_data) < 16:  # 1 header + 15 data rows
        table_data.append(["", "", "", "", "", "", ""])
    
    # Create main table
    main_table = Table(table_data, colWidths=[0.8*inch, 0.6*inch, 2.2*inch, 0.8*inch, 1.0*inch, 0.8*inch, 1.3*inch])
    main_table.setStyle(TableStyle([
        # Header row
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # All cells
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        
        # Description column left align
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('ALIGN', (6, 1), (6, -1), 'LEFT'),  # Remarks column
    ]))
    
    story.append(main_table)
    story.append(Spacer(1, 10))
    
    # Purpose section
    purpose_data = [
        [f"Purpose: {batch_request.purpose}"]
    ]
    purpose_table = Table(purpose_data, colWidths=[7.5*inch])
    purpose_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(purpose_table)
    story.append(Spacer(1, 10))
    
    # Signature section
    signature_headers = ["", "Requested by:", "Approved by:", "Issued by:", "Received by:"]
    
    # Get names for signatures
    requester_name = f"{batch_request.user.first_name} {batch_request.user.last_name}" if batch_request.user.first_name else batch_request.user.username
    requester_designation = batch_request.user.userprofile.designation if batch_request.user.userprofile and batch_request.user.userprofile.designation else batch_request.user.userprofile.department.name if batch_request.user.userprofile.department else ""
    
    # Get approved by name and designation from tracked user
    approved_by_name = ""
    approved_by_designation = ""
    if batch_request.approved_by:
        approved_by_name = f"{batch_request.approved_by.first_name} {batch_request.approved_by.last_name}" if batch_request.approved_by.first_name else batch_request.approved_by.username
        if batch_request.approved_by.userprofile:
            approved_by_designation = batch_request.approved_by.userprofile.designation if batch_request.approved_by.userprofile.designation else ""
    
    # Get issued by name and designation from tracked user (claimed_by)
    issued_by_name = ""
    issued_by_designation = ""
    if batch_request.claimed_by:
        issued_by_name = f"{batch_request.claimed_by.first_name} {batch_request.claimed_by.last_name}" if batch_request.claimed_by.first_name else batch_request.claimed_by.username
        if batch_request.claimed_by.userprofile:
            issued_by_designation = batch_request.claimed_by.userprofile.designation if batch_request.claimed_by.userprofile.designation else ""
    
    # Received by - the requester receives the items (only if claimed/completed)
    received_by_name = ""
    received_by_designation = ""
    received_by_date = ""
    
    # Only populate received by if the request is completed/claimed
    if batch_request.status == 'completed' and batch_request.claimed_by:
        received_by_name = requester_name
        received_by_designation = requester_designation
        received_by_date = batch_request.completed_date.strftime("%m/%d/%Y") if batch_request.completed_date else ""
    
    # Create paragraph style for wrapping text
    wrap_style = ParagraphStyle(
        'WrapText',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        leading=11
    )
    
    wrap_style_small = ParagraphStyle(
        'WrapTextSmall',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_LEFT,
        leading=10
    )
    
    signature_data = [
        signature_headers,
        ["Signature:", "", "", "", ""],
        ["Name:", 
         Paragraph(requester_name, wrap_style), 
         Paragraph(approved_by_name, wrap_style), 
         Paragraph(issued_by_name, wrap_style), 
         Paragraph(received_by_name, wrap_style)],
        ["Designation:", 
         Paragraph(requester_designation, wrap_style_small),
         Paragraph(approved_by_designation, wrap_style_small),
         Paragraph(issued_by_designation, wrap_style_small),
         Paragraph(received_by_designation, wrap_style_small)],
        ["Date:", 
         batch_request.request_date.strftime("%m/%d/%Y") if batch_request.request_date else "",
         batch_request.approved_date.strftime("%m/%d/%Y") if batch_request.approved_date else "",
         batch_request.completed_date.strftime("%m/%d/%Y") if batch_request.completed_date else "",
         received_by_date]
    ]
    
    signature_table = Table(signature_data, colWidths=[1.0*inch, 1.625*inch, 1.625*inch, 1.625*inch, 1.625*inch], 
                           rowHeights=[None, 30, None, None, 20])
    signature_table.setStyle(TableStyle([
        # All cells
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Header row bold
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),  # First column bold
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # Header row middle aligned
        
        # Align text
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # First column center aligned
        ('ALIGN', (1, 2), (-1, -1), 'LEFT'),  # Names and designations left aligned
        
        # Allow text wrapping for name and designation rows
        ('FONTSIZE', (0, 3), (-1, 3), 8),  # Smaller font for designation to fit
    ]))
    
    story.append(signature_table)
    
    # Build PDF
    doc.build(story)
    
    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


def download_requisition_slip(batch_request):
    """
    Generate and return an HTTP response with the requisition slip PDF for download.
    """
    pdf_data = generate_requisition_slip_pdf(batch_request)
    
    # Create the HttpResponse object with PDF content
    response = HttpResponse(pdf_data, content_type='application/pdf')
    
    # Generate professional filename with requester name and department
    # Sanitize names by removing/replacing special characters
    if batch_request.user.first_name and batch_request.user.last_name:
        first_name = batch_request.user.first_name.replace(' ', '_')
        last_name = batch_request.user.last_name.replace(' ', '_')
        requester_name = f"{last_name}_{first_name}"
    else:
        requester_name = batch_request.user.username.replace(' ', '_')
    
    # Get department code safely
    try:
        department = batch_request.user.userprofile.department.code if batch_request.user.userprofile.department else "DEPT"
    except:
        department = "DEPT"
    
    date_str = batch_request.request_date.strftime('%Y%m%d')
    request_id = f"{batch_request.id:03d}"
    
    # Format: RIS_DepartmentCode_LastName_FirstName_RequestID_Date.pdf
    filename = f"RIS_{department}_{requester_name}_{request_id}_{date_str}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def view_requisition_slip(batch_request):
    """
    Generate and return an HTTP response to view the requisition slip PDF in browser.
    """
    pdf_data = generate_requisition_slip_pdf(batch_request)
    
    # Create the HttpResponse object with PDF content for viewing
    response = HttpResponse(pdf_data, content_type='application/pdf')
    
    # Generate professional filename with requester name and department
    # Sanitize names by removing/replacing special characters
    if batch_request.user.first_name and batch_request.user.last_name:
        first_name = batch_request.user.first_name.replace(' ', '_')
        last_name = batch_request.user.last_name.replace(' ', '_')
        requester_name = f"{last_name}_{first_name}"
    else:
        requester_name = batch_request.user.username.replace(' ', '_')
    
    # Get department code safely
    try:
        department = batch_request.user.userprofile.department.code if batch_request.user.userprofile.department else "DEPT"
    except:
        department = "DEPT"
    
    date_str = batch_request.request_date.strftime('%Y%m%d')
    request_id = f"{batch_request.id:03d}"
    
    # Format: RIS_DepartmentCode_LastName_FirstName_RequestID_Date.pdf
    filename = f"RIS_{department}_{requester_name}_{request_id}_{date_str}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

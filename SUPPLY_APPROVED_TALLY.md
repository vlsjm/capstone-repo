# Supply Approved Tally - Admin Feature

## Overview
The Supply Approved Tally page has been created to allow administrators to view a comprehensive summary of all approved supply items and their given quantities.

## Features

### 1. **Summary Cards**
   - **Total Item Types**: Shows the count of unique supply items that have been approved
   - **Total Quantity Given**: Displays the sum of all approved quantities across all items
   - **Total Requests**: Shows the number of individual approval records

### 2. **Detailed Tally Table**
   The table displays:
   - **Supply Item Name**: Name of the approved supply
   - **Unit**: Standard unit of measure (pcs, boxes, reams, etc.)
   - **Total Approved Quantity**: Sum of all approved quantities for this item
   - **Number of Requests**: How many times this item was requested and approved
   - **Actions**: View inventory or request details

### 3. **Data Aggregation**
   - Pulls data from approved and completed batch supply requests
   - Groups supplies by name
   - Calculates approved quantities per item
   - Tracks which batches each item came from

### 4. **Export Capabilities**
   - **Print**: Print-friendly version of the page
   - **Export CSV**: Download the tally as a CSV file for further analysis

## Access
- **URL**: `/supply-approved-tally/`
- **Permission**: Admin Only (requires `app.view_admin_module` permission)
- **Navigation**: Can be accessed from the admin dashboard or supply management section

## How It Works

### Data Source
The page retrieves data from:
1. `SupplyRequestItem` model - Individual items in batch requests
2. Filters for approved items in approved/completed requests
3. Aggregates by supply name and unit

### Calculation Logic
For each supply:
- `total_approved_quantity`: Sum of `approved_quantity` (or `quantity` if not set)
- `num_requests`: Count of individual request items for that supply
- Unit: Pulled from the Supply model

## Components

### Views (`app/views.py`)
```python
@login_required
@permission_required('app.view_admin_module', raise_exception=True)
def supply_approved_tally(request):
    """Admin page to view the approved supplies tally"""
```

### URLs (`app/urls.py`)
```python
path('supply-approved-tally/', views.supply_approved_tally, name='supply_approved_tally'),
```

### Template (`app/templates/app/supply_approved_tally.html`)
- Responsive design matching admin dashboard
- Summary cards for key metrics
- Interactive table with search and filter capability
- Export options (print and CSV)
- Modal for detailed information (expandable)

## Responsive Design
- Desktop: Full table with all columns
- Tablet: Optimized column widths
- Mobile: Stacked layout with essential information

## Future Enhancements
Potential improvements include:
1. Date range filters for historical tracking
2. Department-wise tally
3. User-specific request tracking
4. Real-time supply deductions
5. PDF report generation with detailed breakdowns
6. Comparison with previous periods

## Database Queries
The view uses the following Django ORM queries:
- `SupplyRequestItem.objects.filter(status='approved', batch_request__status__in=['approved', 'for_claiming', 'completed'])`
- Aggregation by supply name using Python dictionaries
- Select related queries for performance optimization

## Notes
- The page only shows approved items from batch requests
- Legacy single-item requests are not included (they use the old `SupplyRequest` model)
- Quantities are based on `approved_quantity` if set, otherwise falls back to requested `quantity`

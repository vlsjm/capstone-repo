# Borrow Request Batch Return Date Implementation

## Summary
Updated the borrow request system to enforce a **single return date for all items in one request**, matching the pattern used in the reservation system. This ensures proper tracking and prevents discrepancies when items have different return dates within the same request.

## Changes Made

### 1. Frontend Template Changes (`user_unified_request.html`)

#### A. Added Borrow Period Section (Top-Level)
- **Location**: Before the "Add Item to List" section
- **What Changed**: 
  - Added a new "Return Period (All Items)" section with styling matching the reservation system
  - Single date input field: `#borrow-batch-return-date`
  - Information message: "This return date will apply to all items in your borrow request"
  - Minimum date constraint set to tomorrow

#### B. Removed Per-Item Return Date Fields
- **In Form**: Removed the individual return date input from the add item form
- **In Table**: 
  - Removed the "Return Date" column from the borrow items table
  - Table now only shows: Item, Quantity, Purpose, Actions
  - Removed return date edit inputs from table rows

#### C. Updated Table Display
- **Old Columns**: Item | Quantity | Return Date | Purpose | Actions (5 columns)
- **New Columns**: Item | Quantity | Purpose | Actions (4 columns)

#### D. Added Hidden Field
- Added `#borrow-batch-return-date-hidden` to submit form to pass batch return date to backend

### 2. JavaScript Logic Changes

#### A. Batch Return Date Validation
- **Function**: Modified `#add-borrow-form` submit handler
- **New Validation**:
  - Checks if batch return date is set BEFORE allowing items to be added
  - Shows error: "Please set the return date first in the 'Return Period' section"
  - Focuses on the batch date input if not set

#### B. Form Data Passing
- **Change**: Batch return date from `#borrow-batch-return-date` is now appended to form data as `return_date`
- **Result**: All items in cart use the same return date

#### C. Table Row Generation
- **Old**: Each row had a per-item return date edit input
- **New**: No return date field in rows (it's batch-wide)
- **Purpose Field**: Now shows first 5 words of purpose text

#### D. Auto-Save for Borrow Items
- **Old**: Auto-save on quantity OR return date change
- **New**: Auto-save ONLY on quantity change
- **Removed**: Return date edit listener (no longer applicable)

#### E. Submit Form Handler
- **New Validation**: Before submit, checks that batch return date is set
- **New Action**: Copies batch return date to hidden field `#borrow-batch-return-date-hidden` before submission

#### F. Minimum Date Setup
- Added: `$('#borrow-batch-return-date').attr('min', minDate);`
- Sets minimum date to tomorrow, same as reservation system

### 3. Backend Changes (`userpanel/views.py`)

#### A. `add_to_borrow_list()` Function
- **Parameter Change**: Now expects batch `return_date` from form instead of per-item date
- **Processing**: All items added to cart use the same return date
- **When Item Exists**: Updates quantity but keeps same return date (batch date)
- **Behavior**: Now matches reservation add function pattern

#### B. `update_borrow_list_item()` Function
- **Removed**: `return_date` parameter handling
- **Updated**: Function now ONLY updates quantity
- **Removed Code**: Date validation logic (no longer needed)
- **Updated Docstring**: "return date is batch-wide and cannot be changed per-item"

#### C. `submit_borrow_list_request()` Function
- **New Parameter**: Extracts `batch_return_date` from POST data
- **New Validation**: 
  - Checks that batch return date is provided
  - Validates batch date is in the future
  - Returns error if validation fails
- **Item Creation**: All items created with same `batch_return_date_obj` return date
- **Activity Logging**: Now logs the batch return date in the description

#### D. Key Behavioral Changes
- Single return date passed to ALL items in batch
- Each `BorrowRequestItem` gets the same return date
- No per-item date variation is possible
- Ensures consistent tracking and reporting

## Benefits

1. **Consistent Tracking**: All items in a borrow request have the same return date
2. **Simpler UX**: Users set one date, not multiple dates per item
3. **Matches Reservation Pattern**: Consistent with how the reservation system works
4. **Better Data Integrity**: No possibility of mixed return dates in single request
5. **Easier Admin Review**: Cleaner data for staff reviewing requests

## User Flow

1. User navigates to Borrow Request section
2. **First**: Sets "Return Date" in "Return Period (All Items)" section
3. **Then**: Selects items and adds them to list (items use batch return date)
4. **Quantity**: Can be adjusted per-item via edit inputs
5. **Purpose**: Must be entered for each item (or general notes on submission)
6. **Submit**: All items submitted with the same return date

## Data Model Impact

- `BorrowRequestItem.return_date`: Now guaranteed to be the same for all items in a batch
- Existing data is not affected (only new requests use this pattern)
- Query optimization: Can now group by return_date more predictably

## Testing Recommendations

1. ✅ Add multiple items to borrow list
2. ✅ Verify all items use the same return date in database
3. ✅ Try to submit without setting batch return date (should error)
4. ✅ Edit quantities of items (should not affect return date)
5. ✅ View request details to confirm single return date per batch
6. ✅ Test with different dates to ensure batch date is enforced

## Files Modified

1. `userpanel/templates/userpanel/user_unified_request.html`
   - HTML structure and styling
   - JavaScript event handlers and validation

2. `userpanel/views.py`
   - `add_to_borrow_list()` - Line 1393
   - `update_borrow_list_item()` - Line 1509  
   - `submit_borrow_list_request()` - Line 1568

# PPMP Year Deduction Issue - Root Cause Analysis and Solution

## Issue Description
When approving a batch request with multiple PPMP year matches (e.g., 2024 and 2026), selecting to deduct from 2024 sometimes also deducts from 2026.

## Root Cause Investigation

### Architecture Overview
1. **Frontend (batch_request_detail.html)**: Displays PPMP year selection modal and collects user allocations
2. **Backend (app/views.py)**: 
   - `get_ppmp_year_options`: Returns available PPMP years with matched items
   - `approve_batch_item`: Processes the allocation and updates PPMP released quantities
3. **Data Model (app/models.py)**:
   - `PPMP`: One per department per year
   - `PPMPItem`: Individual line items within a PPMP, each with unique ID and linked to one PPMP/year

### Potential Root Causes

#### 1. **Same ppmp_item_id sent for multiple years (UNLIKELY)**
Each PPMPItem has a unique database ID and is linked to exactly one PPMP year via foreign key. This has been verified by the debug script.

#### 2. **First-item-only approach (MOST LIKELY)**
When there are multiple matched items within a year, the backend only sends the **first** matched item's ID:

```python
# app/views.py, line ~7156
first_item = year_data['matched_items'][0] if year_data['matched_items'] else None
...
'ppmp_item_id': first_item.id if first_item else None,
```

**Problem**: If a supply (e.g., "Ballpen") has 3 different variants in the PPMP:
- 2024: Items #100, #101, #102 (sends only #100)
- 2026: Items #200, #201, #202 (sends only #200)

The frontend receives:
- 2024 → ppmp_item_id: 100
- 2026 → ppmp_item_id: 200

This should work correctly since 100 and 200 are different items...

#### 3. **Frontend data attribute confusion (POSSIBLE)**
The HTML template creates inputs with `data-ppmp-item-id` attributes. If these aren't properly scoped or if there's JavaScript state pollution, the wrong ID could be sent.

#### 4. **Caching or stale data (POSSIBLE)**
If the year options modal is opened multiple times without proper cleanup, old `data-ppmp-item-id` values might persist.

## Diagnostic Improvements Added

### 1. Enhanced Backend Logging
Added comprehensive logging in `app/views.py`:
- Logs all matched PPMP items for each year (not just the first one)
- Logs allocation processing start/end
- Logs year verification checks
- Logs each PPMP item update with before/after values

### 2. Enhanced Frontend Logging  
Added detailed console logging in the JavaScript:
- Logs full year options received from server
- Logs all matched items with their IDs for each year
- Logs input element data attributes when building allocations
- Logs each allocation being added with full details

## How to Reproduce and Debug

### Step 1: Reproduce the Issue
1. Create a batch supply request for an item that exists in multiple PPMP years (e.g., "Ballpen" in both 2024 and 2026)
2. As admin, go to approve the request
3. When the PPMP year selection modal appears, allocate to 2024 only
4. Submit the approval
5. Check if 2026 was also deducted

### Step 2: Check the Logs
1. Open browser Developer Tools (F12) → Console tab
2. Look for the console.log outputs:
   - "RECEIVED YEAR OPTIONS FROM SERVER" - shows what ppmp_item_ids came from backend
   - "Adding allocation" - shows what's being sent to backend
3. Check Django server logs for:
   - "BEGIN ALLOCATION PROCESSING" - shows received allocations
   - Year verification messages
   - PPMP item update messages

### Step 3: Verify Data Integrity
Run the debug script:
```bash
cd "C:\Users\johnm\OneDrive\Desktop\Resource Hive\capstone-repo"
py debug_ppmp_years.py
```

This will verify:
- Each PPMP item has a unique ID
- Each PPMP item belongs to exactly one year
- No duplicate IDs across years

## Expected Behavior

### Correct Flow:
1. User requests 10 units of "Ballpen"
2. System finds matches:
   - 2024: Item #7869 (remaining: 3 units)
   - 2026: Item #7437 (remaining: 8 units)
3. User allocates: 2024 → 3 units, 2026 → 7 units
4. Frontend sends:
   ```json
   [
     {"year": 2024, "ppmp_item_id": 7869, "quantity": 3},
     {"year": 2026, "ppmp_item_id": 7437, "quantity": 7}
   ]
   ```
5. Backend updates:
   - Item #7869: released 0 → 3 (year verified: 2024 ✓)
   - Item #7437: released 2 → 9 (year verified: 2026 ✓)

### Incorrect Flow (Bug):
1. Same setup as above
2. User allocates: 2024 → 3 units (leaves 2026 at 0)
3. Frontend sends:
   ```json
   [
     {"year": 2024, "ppmp_item_id": 7869, "quantity": 3},
     {"year": 2026, "ppmp_item_id": 7869, "quantity": 0}  // WRONG! Same item ID
   ]
   ```
4. Backend processing:
   - First allocation: year=2024, ppmp_item_id=7869 → Update succeeds
   - Second allocation: year=2026, ppmp_item_id=7869 → Year verification FAILS (item belongs to 2024, not 2026)
   - Result: Only 2024 updated (correct), but if year check wasn't there, both would update

## Preventive Measures Implemented

### 1. Year Verification Check (Already in place)
```python
if ppmp_item.ppmp.year != alloc_year:
    logger.error(f"Year mismatch! Skipping...")
    continue
```
This prevents updating the wrong year even if frontend sends wrong data.

### 2. Detailed Logging (Now added)
Helps track exactly which ppmp_item_id is being used for each year.

## Recommended Solutions

### Short-term Solution: Add Data Validation
Add frontend validation to ensure each year gets a unique ppmp_item_id:

```javascript
// Before confirming allocation
const yearItemMap = new Map();
allocations.forEach(alloc => {
    if (yearItemMap.has(alloc.year) && yearItemMap.get(alloc.year) !== alloc.ppmp_item_id) {
        console.error(`Duplicate year ${alloc.year} with different item IDs!`);
    }
    yearItemMap.set(alloc.year, alloc.ppmp_item_id);
});
```

### Mid-term Solution: Support Multiple Items Per Year
Instead of sending only the first matched item ID, send all matched item IDs and let the backend distribute the quantity:

```python
'ppmp_item_ids': [item.id for item in year_data['matched_items']],
'items_details': [...]  # Already sent
```

Then in the approval logic, distribute the allocated quantity across all matched items proportionally or FIFO.

### Long-term Solution: Granular Item Selection
Allow admin to select exactly which PPMP item(s) to deduct from when there are multiple matches within a year.

## Testing Checklist

- [ ] Reproduce the issue with logging enabled
- [ ] Verify console logs show correct ppmp_item_ids for each year
- [ ] Verify backend logs show correct year verification
- [ ] Check if year mismatch errors appear in logs
- [ ] Verify PPMP item IDs are unique in database
- [ ] Test with supplies that have multiple variants in same year
- [ ] Test with supplies that exist across multiple years
- [ ] Verify released quantities update correctly

## Files Modified

1. `app/views.py` - Enhanced logging in `get_ppmp_year_options` and `approve_batch_item`
2. `app/templates/app/batch_request_detail.html` - Enhanced JavaScript console logging
3. `debug_ppmp_years.py` - Created diagnostic script

## Next Steps

1. **Run a test approval** with the enhanced logging to see exactly what's happening
2. **Capture the console logs and server logs** when the bug occurs
3. **Analyze the logs** to see if:
   - The same ppmp_item_id is being sent for multiple years
   - The year verification is failing (which means frontend sent wrong data)
   - Something else is happening
4. Based on the logs, implement the appropriate fix from the solutions above

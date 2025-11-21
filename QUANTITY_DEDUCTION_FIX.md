# Quantity Deduction Fix - Reservation to Borrow Request Workflow

## Problem Identified

There was a **duplicate quantity reservation** issue in the workflow:

1. When a **Reservation is approved** → `reserved_quantity` is increased
2. When the **needed date arrives** → An auto-generated `BorrowRequest` is created with status `'approved'`
3. When `BorrowRequestItem` is created with status `'approved'` → `reserved_quantity` is increased **AGAIN** (duplicate!)
4. When items are **claimed/activated** → Only the borrow request reserved quantity is released
5. Result: The original reservation reserved quantity remains locked indefinitely

## Root Cause

- `ReservationItem.save()` reserves quantity when status becomes 'approved'
- `BorrowRequestItem.save()` was independently reserving quantity when status is 'approved'
- The auto-generation logic didn't differentiate between:
  - Borrow requests created from user submissions (new, independent)
  - Borrow requests auto-generated from reservations (already reserved)

## Solution Implemented

### 1. **Added `from_reservation` Field** 
   - New field in `BorrowRequestItem` model to track if item was auto-generated from a reservation
   - Migration: `0087_borrowrequestitem_from_reservation.py`

### 2. **Modified `BorrowRequestItem.save()` Logic**
   - When `from_reservation=True`: **Skip all reserved quantity management**
   - This prevents duplicate reservation since the quantity is already reserved by ReservationItem
   - Only regular borrow requests (from_reservation=False) manage their own reserved quantities

### 3. **Fixed `ReservationItem.save()` Transition**
   - Changed 'approved' → 'active' transition behavior:
     - **OLD**: Deducted from both `reserved_quantity` AND `quantity` immediately
     - **NEW**: Only releases the `reserved_quantity` (transitions to borrow request control)
   - Actual quantity deduction happens only when borrow request is claimed

### 4. **Updated Auto-Generation Logic**
   - Both `ReservationBatch.check_and_update_batches()` and `Reservation.check_and_update_reservations()`
   - Now set `from_reservation=True` when creating BorrowRequestItems
   - This prevents duplicate quantity reservation

## Workflow After Fix

```
┌─────────────────────────────────────────────────────────────────┐
│                         RESERVATION FLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. USER SUBMITS RESERVATION
   └─> ReservationItem.status = 'pending'
   └─> reserved_quantity = 0 (not yet reserved)

2. ADMIN APPROVES RESERVATION
   └─> ReservationItem.status = 'approved'
   └─> reserved_quantity += qty  ✓ RESERVED

3. NEEDED DATE ARRIVES (AUTOMATIC)
   └─> Auto-generate BorrowRequestBatch
   └─> Create BorrowRequestItem with from_reservation=True
   └─> BorrowRequestItem.save() → SKIPS reserved quantity logic (already reserved)
   └─> ReservationItem.status = 'active'
   └─> reserved_quantity -= qty  ✓ RELEASE (transfer to borrow control)

4. USER CLAIMS ITEMS
   └─> claim_borrow_batch_items() called
   └─> property.quantity -= qty  ✓ DEDUCT ACTUAL STOCK
   └─> BorrowRequestItem.status = 'active'
   └─> BorrowRequestItem.save() → Skips (from_reservation=True)

5. USER RETURNS ITEMS
   └─> return_borrow_batch_items() called
   └─> property.quantity += qty  ✓ RESTORE STOCK
   └─> BorrowRequestItem.status = 'returned'
   └─> ReservationItem.status = 'completed'

RESULT: No duplicate reserved quantities! ✓
```

## Key Changes Summary

| Component | Change | File | Benefit |
|-----------|--------|------|---------|
| BorrowRequestItem | Added `from_reservation` field | models.py:2034 | Track auto-generated items |
| BorrowRequestItem.save() | Skip reserved logic if from_reservation=True | models.py:2055-2060 | Prevent duplicate reservation |
| ReservationItem.save() | Release reserved qty on 'approved'→'active' | models.py:1026-1031 | Correct quantity state transition |
| ReservationBatch.check_and_update_batches() | Set from_reservation=True on creation | models.py:917 | Mark auto-generated items |
| Reservation.check_and_update_reservations() | Set from_reservation=True on creation | models.py:1316 | Mark auto-generated items (legacy) |

## Testing Recommendations

1. **Create a test reservation** → Verify reserved_quantity increases by exactly qty
2. **Approve the reservation** → Verify reserved_quantity stays the same
3. **Wait for needed_date** → Verify auto-generated borrow request is created
4. **Check property quantity** → Ensure no extra deduction occurs
5. **Claim items** → Verify actual quantity deducts exactly once
6. **Return items** → Verify quantity is restored exactly
7. **Final check** → Verify reserved_quantity = 0 at end of workflow

## Migration Applied

```bash
python manage.py makemigrations app
python manage.py migrate
```

- Migration: `0087_borrowrequestitem_from_reservation.py`
- Status: ✓ Applied successfully

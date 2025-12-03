# Admin Permission System - Testing Guide

## Overview
The admin permission system has been fully implemented and enforced across all views. This guide will help you test that limited-access admins are properly restricted.

## Permission Types Implemented

1. **approve_supply_request** - Approve/reject supply requests
2. **approve_borrow_request** - Approve/reject borrow requests  
3. **approve_reservation** - Approve/reject reservations
4. **report_bad_stock** - Report items as damaged/bad stock
5. **edit_supply** - Edit supply details
6. **edit_property** - Edit property details
7. **manage_users** - Create/manage user accounts
8. **delete_archived_items** - Delete archived supplies/properties
9. **report_lost_items** - Report items as lost
10. **manage_lost_items** - Mark items as lost/found, delete lost item reports

## Protected Views

### Function-Based Views with @admin_permission_required
- `edit_supply` - requires 'edit_supply'
- `edit_property` - requires 'edit_property'
- `report_bad_stock` - requires 'report_bad_stock'
- `approve_batch_item` - requires 'approve_supply_request'
- `reject_batch_item` - requires 'approve_supply_request'
- `approve_borrow_item` - requires 'approve_borrow_request'
- `reject_borrow_item` - requires 'approve_borrow_request'
- `approve_reservation_item` - requires 'approve_reservation'
- `reject_reservation_item` - requires 'approve_reservation'
- `approve_reservation_batch` - requires 'approve_reservation'
- `reject_reservation_batch` - requires 'approve_reservation'
- `create_user` - requires 'manage_users'
- `delete_archived_supply` - requires 'delete_archived_items'
- `delete_archived_property` - requires 'delete_archived_items'
- `report_lost_item` - requires 'report_lost_items'
- `mark_lost_item_found` - requires 'manage_lost_items'
- `mark_property_as_lost` - requires 'manage_lost_items'
- `delete_lost_item` - requires 'manage_lost_items'

### Class-Based Views with AdminPermissionMixin
- `UserProfileListView` (manage users page) - requires 'manage_users'

## Testing Steps

### 1. Create Test Admin Account
1. Go to Manage Users page
2. Create a new admin account with:
   - Role: Admin
   - Check "Has Limited Access"
3. Save the account

### 2. Test Individual Permissions

#### Test: Edit Supply Permission Only
1. Open the permissions modal for the test admin
2. Grant ONLY "Edit Supply" permission
3. Save permissions
4. Log in as test admin
5. Verify:
   - ✅ Can access Edit Supply pages
   - ❌ Cannot approve supply requests
   - ❌ Cannot approve borrow requests
   - ❌ Cannot approve reservations
   - ❌ Cannot manage users
   - ❌ Cannot delete archived items
   - ❌ Cannot manage lost items
   - ❌ Cannot edit properties
   - ❌ Cannot report bad stock

#### Test: Approve Supply Requests Only
1. Grant ONLY "Approve/Reject Supply Requests" permission
2. Log in as test admin
3. Verify:
   - ✅ Can approve/reject individual supply request items
   - ✅ Can approve/reject entire supply request batches
   - ❌ Cannot edit supplies
   - ❌ Cannot approve borrow requests
   - ❌ Cannot approve reservations

#### Test: Manage Users Only
1. Grant ONLY "Manage Users/Create Accounts" permission
2. Log in as test admin
3. Verify:
   - ✅ Can access Manage Users page
   - ✅ Can create new user accounts
   - ✅ Can edit user profiles
   - ❌ Cannot open/edit permissions modal (this is intentional)
   - ❌ Cannot perform any other admin actions

#### Test: Multiple Permissions
1. Grant both "Edit Supply" and "Edit Property" permissions
2. Log in as test admin
3. Verify:
   - ✅ Can edit supplies
   - ✅ Can edit properties
   - ❌ Cannot approve requests
   - ❌ Cannot manage users

### 3. Test Full Access Admin
1. Create/edit an admin account
2. Uncheck "Has Limited Access" (or leave unchecked)
3. Verify:
   - ✅ Can perform ALL admin actions
   - ✅ Can access permissions management
   - ✅ No restrictions applied

### 4. Test Superuser
1. Log in as superuser
2. Verify:
   - ✅ Can perform ALL actions regardless of permissions
   - ✅ No restrictions applied

## Expected Error Messages

When a limited-access admin tries to access a restricted page:
- Error message: "You don't have permission to perform this action."
- Redirected to dashboard

When accessing via direct URL:
- HTTP 403 Forbidden or redirect with error message

## Permission Behavior

### Full-Access Admins (has_limited_access = False)
- Have access to ALL admin features
- Permissions are ignored
- Can manage permissions for limited-access admins

### Limited-Access Admins (has_limited_access = True)
- Can ONLY perform actions for which they have explicit permissions
- Cannot access permissions management
- Restricted by @admin_permission_required decorators

### Superusers
- Have complete access to everything
- Bypass all permission checks
- Can access Django admin panel

## Troubleshooting

### Admin can still access everything
- Check if "Has Limited Access" is checked for the user
- Verify user is not a superuser
- Check browser cache/cookies (try incognito mode)
- Verify migrations were applied: `python manage.py migrate`

### Permission changes not taking effect
- Log out and log back in
- Clear browser cache
- Check database: `AdminPermission.objects.all()` should show 9 permissions
- Check user profile: `user.userprofile.admin_permissions.all()`

### Getting 500 errors
- Check server console for Python errors
- Verify all decorators are properly imported
- Check that AdminPermissionMixin is before PermissionRequiredMixin in class inheritance

## Database Verification

### Check Permissions Exist
```python
from app.models import AdminPermission
print(AdminPermission.objects.all().count())  # Should be 9
print(list(AdminPermission.objects.values_list('codename', flat=True)))
```

### Check User Permissions
```python
from app.models import UserProfile
user = UserProfile.objects.get(user__username='test_admin')
print(f"Has limited access: {user.has_limited_access}")
print(f"Permissions: {list(user.admin_permissions.values_list('codename', flat=True))}")
```

### Initialize Permissions (if missing)
```python
from app.models import AdminPermission
AdminPermission.initialize_permissions()
```

## Notes

- The permissions modal is intentionally restricted to full-access admins only
- Limited-access admins cannot modify their own or others' permissions
- All permission checks happen at the view level (server-side)
- Frontend restrictions (hiding buttons/links) should be added for better UX
- Permission checks are enforced even if accessing URLs directly

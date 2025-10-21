# Phase 2: Display Updates - Quick Reference Guide

## When You're Ready for Phase 2
This guide shows you exactly what to change to update the UI to display available vs reserved quantities.

## Option 1: Simple Display Update

### File: `app/templates/app/supply.html`
**Find this section** (around line 200-250 in the supply list table):
```html
<td>{{ supply.quantity_info.current_quantity }}</td>
```

**Replace with:**
```html
<td>
    {{ supply.quantity_info.available_quantity }}
    {% if supply.quantity_info.reserved_quantity > 0 %}
        <small class="text-muted">({{ supply.quantity_info.reserved_quantity }} reserved)</small>
    {% endif %}
</td>
```

### File: `userpanel/templates/userpanel/user_request.html`
**Find the available supplies display** (where users see stock levels):
```javascript
// In the JavaScript section, update stock display
stockElement.textContent = `Stock: ${supply.quantity_info.current_quantity}`;
```

**Replace with:**
```javascript
stockElement.textContent = `Available: ${supply.quantity_info.available_quantity}`;
if (supply.quantity_info.reserved_quantity > 0) {
    stockElement.textContent += ` (${supply.quantity_info.reserved_quantity} reserved)`;
}
```

### File: `app/views.py` - Supply List Context
**Find the SupplyListView.get_context_data** (around line 1420):

**No changes needed!** The `available_quantity` property is automatically available in templates.

## Option 2: Enhanced Display with Color Coding

Add this CSS to your stylesheets:
```css
.stock-info {
    display: flex;
    flex-direction: column;
}

.stock-available {
    font-weight: bold;
    color: #28a745;
}

.stock-reserved {
    font-size: 0.85em;
    color: #6c757d;
}

.stock-low {
    color: #ffc107;
}

.stock-critical {
    color: #dc3545;
}
```

Then update the supply table cell:
```html
<td>
    <div class="stock-info">
        <span class="stock-available {% if supply.quantity_info.available_quantity <= supply.quantity_info.minimum_threshold %}stock-critical{% elif supply.quantity_info.available_quantity <= supply.quantity_info.minimum_threshold * 2 %}stock-low{% endif %}">
            {{ supply.quantity_info.available_quantity }} available
        </span>
        {% if supply.quantity_info.reserved_quantity > 0 %}
            <span class="stock-reserved">{{ supply.quantity_info.reserved_quantity }} reserved</span>
        {% endif %}
        <span class="text-muted" style="font-size: 0.8em;">Total: {{ supply.quantity_info.current_quantity }}</span>
    </div>
</td>
```

## Option 3: Progressive Enhancement (Safest)

Keep showing both quantities during transition period:

```html
<td>
    <div class="stock-display">
        <strong>Available:</strong> {{ supply.quantity_info.available_quantity }}<br>
        <small class="text-muted">
            On Hand: {{ supply.quantity_info.current_quantity }}
            {% if supply.quantity_info.reserved_quantity > 0 %}
                | Reserved: {{ supply.quantity_info.reserved_quantity }}
            {% endif %}
        </small>
    </div>
</td>
```

## Files to Update for Complete Phase 2

1. **Supply List Page** (`app/templates/app/supply.html`)
   - Main table display
   - Quick view modal
   - Edit modal stock display

2. **User Request Page** (`userpanel/templates/userpanel/user_request.html`)
   - Available supplies dropdown
   - Stock level indicators
   - Request form validation

3. **Admin Request Pages** (`app/templates/app/requests.html`, `batch_request_detail.html`)
   - Stock availability checks during approval
   - Warning messages for low stock

4. **Dashboard** (`app/templates/app/dashboard.html`)
   - Low stock warnings (should use available_quantity)
   - Stock status badges

## Testing Phase 2 Updates

After making changes, test:
1. ✅ Supply list shows available quantity correctly
2. ✅ Reserved quantities are visible when > 0
3. ✅ User request form prevents over-requesting
4. ✅ Admin approval shows correct available stock
5. ✅ Dashboard low-stock alerts use available_quantity

## Rollback Plan
If Phase 2 causes issues, you can easily revert templates to show `current_quantity` again. The backend logic (Phase 1) will continue protecting against overbooking regardless of what the UI shows.

---

**Remember**: Phase 1 (backend) is already protecting you from overbooking. Phase 2 just makes it visible to users!

# CvSU Inventory Count Form - Quick Reference

## 🚀 Quick Start

### How to Generate the Form

1. **Login** to the admin panel
2. Go to **Property** page
3. Click **Actions** (⋮) dropdown
4. Select **Export to Excel**
5. Choose **📋 CvSU Inventory Count Form (Above ₱50,000.00)**
6. Click **Generate CvSU Inventory Count Form**
7. Download starts automatically!

## 📋 What Gets Exported?

### ✅ Included
- Properties with **unit value > ₱50,000**
- Grouped by **PPE Account Group** (category)
- Official CvSU header with logo
- Complete table with 11 columns

### ❌ Not Included
- Properties with unit value ≤ ₱50,000
- Archived properties
- Properties without categories (go to "Uncategorized" sheet)

## 📊 Output Format

**File Name:** `Inventory_Count_Over50k_YYYYMMDD_HHMMSS.xlsx`

**Structure:**
- Multiple sheets (one per category)
- Each sheet has:
  - CvSU official header
  - Logo at top center
  - PPE Account Group label
  - Data table with borders

## 📑 Table Columns

1. **Article/Item** - Property name
2. **Description** - Detailed description
3. **Old Property No.** - Previous number (if changed)
4. **New Property No.** - Current property number
5. **Unit of Measure** - e.g., Unit, Piece, Set
6. **Unit Value** - Currency formatted (₱#,##0.00)
7. **Quantity per Property Count** - Recorded quantity
8. **Quantity per Physical Count** - Physical count
9. **Location/Whereabouts** - Building, Floor, Room
10. **Condition** - Good/Repair/Unserviceable/Obsolete
11. **Remarks** - Empty for manual entry

## 🎨 Visual Features

- ✅ Professional borders on all cells
- ✅ Wrapped text in headers
- ✅ Proper column widths
- ✅ Currency formatting
- ✅ CvSU logo (if available)
- ✅ Centered headers
- ✅ Consistent spacing

## 🔧 Technical Details

**Endpoint:** `/export-inventory-count-form/`  
**Function:** `export_inventory_count_form_cvsu()`  
**Method:** GET (via form POST)  
**Authentication:** Required (login)

## ⚠️ Requirements

1. **Logo File:** `static/images/cvsu logo.png`
2. **Properties:** Must have `unit_value > 50000`
3. **Categories:** Properties should have categories assigned
4. **Permissions:** User must be logged in

## 🐛 Common Issues

### No data exported?
→ Check if properties exist with unit_value > ₱50,000

### Logo missing?
→ Ensure `static/images/cvsu logo.png` exists (export still works without it)

### Button not responding?
→ Check browser console for errors

### Categories not showing correctly?
→ Verify properties have categories assigned

## 📈 Example Use Cases

1. **Annual Inventory** - Generate for year-end physical count
2. **Audit Preparation** - Export for external auditors
3. **Department Reports** - Filtered by category
4. **Asset Verification** - Compare property count vs physical count
5. **High-Value Tracking** - Monitor expensive equipment

## 💡 Tips

- **Best Practice:** Run exports regularly for backup
- **Physical Count:** Use "Quantity per Physical Count" column during inventory
- **Remarks:** Leave empty for manual notes during counting
- **Multiple Sheets:** Each category gets its own sheet for easier organization
- **Print Ready:** Format is designed for printing on A4/Letter paper

## 📞 Need Help?

Check the full documentation: `CVSU_INVENTORY_COUNT_FORM_GUIDE.md`

---

**Quick Reference Version:** 1.0  
**Last Updated:** October 19, 2025

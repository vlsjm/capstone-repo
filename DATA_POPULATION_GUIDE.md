# Resource Hive Sample Data Population Guide

## Overview

The Resource Hive system now includes comprehensive sample data for testing system capabilities and performance. The sample data has been populated using Django management commands that generate realistic test data across supplies, properties, and their associated categories.

## Current Database Status

### Supply Data
- **Total Supply Records:** 250
- **Total Quantity in Stock:** 62,791 units
- **Total Reserved Quantity:** 14,662 units
- **Total Available Quantity:** 48,129 units
- **Average Stock per Item:** 251 units
- **Supply Status:**
  - Available: 243 (97.2%)
  - Low Stock: 7 (2.8%)
  - Out of Stock: 0 (0.0%)

### Property Data
- **Total Property Records:** 150
- **Total Property Quantity:** 7,674 units
- **Average Quantity per Property:** 51 units
- **Property Conditions:**
  - In good condition: 63 (42.0%)
  - Needing repair: 80 (53.3%)
  - Obsolete: 4 (2.7%)
  - Unserviceable: 3 (2.0%)
- **Property Availability:**
  - Available: 63 (42.0%)
  - Not Available: 87 (58.0%)

### Classification Data
- **Supply Categories:** 10
- **Supply Subcategories:** 20
- **Property Categories:** 10
- **Unique Locations:** 11

### Performance Testing Metrics
- **Total Records:** 400
- **Total Quantity Units:** 70,465
- **Data Diversity:** 4 conditions, 10 supply categories, 10 property categories, 11 locations

---

## Management Commands

### 1. `populate_sample_data` - Main Data Population Command

This command creates realistic sample data for testing the Resource Hive system.

#### Usage

```bash
# Create default 50 supplies and 50 properties
python manage.py populate_sample_data

# Create custom amounts
python manage.py populate_sample_data --supplies 100 --properties 150

# View help
python manage.py populate_sample_data --help
```

#### Options

- `--supplies COUNT` : Number of supply records to create (default: 50)
- `--properties COUNT` : Number of property records to create (default: 50)
- `--cleanup` : Display cleanup instructions for manual database reset

#### What It Creates

**Supply Records include:**
- Unique supply names with realistic items (paper, computers, furniture, etc.)
- Random category and subcategory assignments
- Description fields for context
- Random date_received (past 365 days)
- Random expiration dates (future 30-365 days)
- Availability flags
- Barcode generation (auto-generated)

**Property Records include:**
- Unique property numbers (PROP-XXXXXX format)
- Property names with realistic items
- Category assignments with UACS codes
- Unit of measure and unit values
- Overall quantities (randomized)
- Locations (11 different locations)
- Accountable persons
- Year acquired (2015-2024)
- Condition states (In good condition, Needing repair, Obsolete, Unserviceable)
- Availability status

**Categories include:**
- Supply Categories: Office Supplies, IT Equipment, Furniture, Janitorial Supplies, Safety Equipment, Tools & Hardware, Laboratory Equipment, Medical Supplies, Kitchen Supplies, Cleaning Materials
- Supply Subcategories: Paper Products, Writing Instruments, Stationery, Computers & Laptops, Monitors & Peripherals, Network Equipment, Office Chairs, Desks & Tables, Storage Cabinets, Mops & Brooms, and more
- Property Categories: Computer Equipment, Office Furniture, Vehicles, Laboratory Equipment, Communication Equipment, Medical Equipment, Tools & Equipment, Machinery, Educational Equipment, Electrical Equipment

### 2. `populate_supply_quantities` - Populate Missing Quantity Records

This command creates SupplyQuantity records for supplies that don't have quantity information.

#### Usage

```bash
python manage.py populate_supply_quantities
```

#### What It Does

- Scans all Supply records for missing SupplyQuantity entries
- Creates quantity records with:
  - Random current quantities (5-500 units)
  - Random reserved quantities (0-50% of current)
  - Random minimum thresholds (5-50 units)
- Reports statistics on created records

---

## Sample Data Features for Testing

### Realistic Supply Data
- Mixed availability statuses (low stock, available, out of stock)
- Varied quantities suitable for inventory management testing
- Expiration date management for perishable items
- Reserved quantities for demand forecasting

### Realistic Property Data
- Multiple condition states for asset tracking
- Location-based filtering capabilities
- Accountable person assignments
- Acquisition year tracking for depreciation analysis
- Reserved quantities for resource planning

### Test Scenarios Supported

1. **Inventory Management**
   - Low stock alerts (7 supplies in low stock)
   - Out of stock detection
   - Reserved quantity tracking (14,662 units reserved)

2. **Asset Management**
   - Property condition tracking (63 items needing repair, 4 obsolete)
   - Location-based queries (11 locations)
   - Accountability and assignment

3. **Category Navigation**
   - 30+ different supply types across categories
   - 10 property categories with UACS codes
   - Subcategory filtering

4. **Performance Testing**
   - 400+ total records for query optimization
   - 70,465 total quantity units for aggregation testing
   - Realistic data distributions

---

## Cleanup Instructions

If you need to completely reset the database and start fresh:

### Option 1: Manual Database Cleanup

Connect to your PostgreSQL database and run:

```sql
-- Connect to your database first
TRUNCATE TABLE app_supplyhistory CASCADE;
TRUNCATE TABLE app_propertyhistory CASCADE;
TRUNCATE TABLE app_supplyquantity RESTART IDENTITY CASCADE;
TRUNCATE TABLE app_supply RESTART IDENTITY CASCADE;
TRUNCATE TABLE app_property RESTART IDENTITY CASCADE;
TRUNCATE TABLE app_supplycategory RESTART IDENTITY CASCADE;
TRUNCATE TABLE app_supplysubcategory RESTART IDENTITY CASCADE;
TRUNCATE TABLE app_propertycategory RESTART IDENTITY CASCADE;
```

Then run the population commands again to repopulate fresh data.

### Option 2: Full Database Reset

```bash
# Drop and recreate the database
python manage.py flush  # WARNING: This deletes all data including users!

# Run migrations
python manage.py migrate

# Repopulate sample data
python manage.py populate_sample_data --supplies 100 --properties 100
python manage.py populate_supply_quantities
```

---

## Adding More Data

To add additional sample data without clearing existing data:

```bash
# Add 50 more supplies and properties to existing data
python manage.py populate_sample_data --supplies 50 --properties 50
```

The system will automatically handle ID sequences and avoid duplicates for properties.

---

## Viewing the Data

### Via Django Admin

1. Start the development server: `python manage.py runserver`
2. Navigate to `http://localhost:8000/admin`
3. Look for:
   - Supplies and SupplyQuantity
   - Properties and PropertyHistory
   - Categories and Subcategories

### Via Django Shell

```bash
python manage.py shell
```

Then execute:

```python
from app.models import Supply, Property, SupplyQuantity

# View supplies
supplies = Supply.objects.all()[:5]
for supply in supplies:
    print(f"{supply.supply_name}: {supply.quantity_info.current_quantity} units")

# View properties
properties = Property.objects.all()[:5]
for prop in properties:
    print(f"{prop.property_name} ({prop.condition}): {prop.quantity} units")
```

---

## Testing Recommendations

### Unit Testing
- Use this data for testing ORM queries and model methods
- Verify quantity calculations and availability logic

### Integration Testing
- Test inventory management workflows
- Test asset assignment and tracking
- Test category filtering and search

### Performance Testing
- Test query performance with 250+ supply records
- Test aggregation queries on 70K+ quantity units
- Test filtering by multiple criteria (category, location, condition)

### UI Testing
- Test data display and pagination
- Test search and filter functionality
- Test edit and update operations

---

## Notes

- All sample data is generated with realistic values suitable for testing
- Dates are automatically set within reasonable ranges
- Barcodes are auto-generated for all supplies and properties
- No real sensitive data is used (all fictional)
- Supply availability is calculated based on quantity thresholds
- Property availability is based on condition and quantity

---

## Command Execution History

**Initial Population:**
- Created 250 supply records with 10 categories and 20 subcategories
- Created 150 property records with 10 property categories
- Populated 250 SupplyQuantity records with realistic quantities

**Total Inventory:**
- 62,791 units in supply stock
- 7,674 units in property inventory
- Ready for comprehensive system and performance testing

---

Last Updated: November 7, 2025
Resource Hive System Version: Capstone Project

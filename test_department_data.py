#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

# Now we can import Django models
from app.models import Department, SupplyRequest, BorrowRequest, Reservation, UserProfile

def test_department_data():
    print("=== Testing Department Request Data ===\n")
    
    # Check if departments exist
    departments = Department.objects.all()
    print(f"Total departments: {departments.count()}")
    for dept in departments:
        print(f"- {dept.name}")
    
    print()
    
    # Check if users have departments assigned
    user_profiles = UserProfile.objects.filter(department__isnull=False)
    print(f"Users with departments assigned: {user_profiles.count()}")
    for profile in user_profiles:
        print(f"- {profile.user.username} -> {profile.department.name}")
    
    print()
    
    # Check requests by department
    for department in departments:
        supply_request_count = SupplyRequest.objects.filter(
            user__userprofile__department=department
        ).count()
        
        borrow_request_count = BorrowRequest.objects.filter(
            user__userprofile__department=department
        ).count()
        
        reservation_count = Reservation.objects.filter(
            user__userprofile__department=department
        ).count()
        
        total_requests = supply_request_count + borrow_request_count + reservation_count
        
        print(f"{department.name}:")
        print(f"  Supply Requests: {supply_request_count}")
        print(f"  Borrow Requests: {borrow_request_count}")
        print(f"  Reservations: {reservation_count}")
        print(f"  Total: {total_requests}")
        print()

if __name__ == "__main__":
    test_department_data()

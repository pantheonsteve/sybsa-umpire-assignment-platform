#!/usr/bin/env python
"""
Script to create test users for the Umpire Assignment Platform.
Creates an admin user and a sample umpire user with linked profile.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umpire_assigner.settings')
django.setup()

from django.contrib.auth.models import User
from assignments.models import Umpire

def create_test_users():
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Created admin user - Username: admin, Password: admin123")
    else:
        print("Admin user already exists")
    
    # Create umpire user
    umpire_user, created = User.objects.get_or_create(
        username='jdoe',
        defaults={
            'email': 'john.doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_staff': False
        }
    )
    if created:
        umpire_user.set_password('umpire123')
        umpire_user.save()
        print("Created umpire user - Username: jdoe, Password: umpire123")
        
        # Create or link umpire profile
        umpire, ump_created = Umpire.objects.get_or_create(
            email='john.doe@example.com',
            defaults={
                'user': umpire_user,
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+1234567890',
                'adult': True,
                'patched': True
            }
        )
        if not ump_created and not umpire.user:
            umpire.user = umpire_user
            umpire.save()
            print("Linked existing umpire profile to user")
        elif ump_created:
            print("Created umpire profile for John Doe")
    else:
        print("Umpire user already exists")
    
    # Create another umpire user
    umpire_user2, created = User.objects.get_or_create(
        username='jsmith',
        defaults={
            'email': 'jane.smith@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'is_staff': False
        }
    )
    if created:
        umpire_user2.set_password('umpire123')
        umpire_user2.save()
        print("Created umpire user - Username: jsmith, Password: umpire123")
        
        # Create or link umpire profile
        umpire2, ump_created = Umpire.objects.get_or_create(
            email='jane.smith@example.com',
            defaults={
                'user': umpire_user2,
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone': '+1234567891',
                'adult': False,
                'patched': False
            }
        )
        if not ump_created and not umpire2.user:
            umpire2.user = umpire_user2
            umpire2.save()
            print("Linked existing umpire profile to user")
        elif ump_created:
            print("Created umpire profile for Jane Smith")
    else:
        print("Umpire user 2 already exists")

if __name__ == '__main__':
    create_test_users()
    print("\nTest users created successfully!")
    print("\nYou can now login with:")
    print("  Admin: username='admin', password='admin123'")
    print("  Umpire 1: username='jdoe', password='umpire123'")
    print("  Umpire 2: username='jsmith', password='umpire123'")
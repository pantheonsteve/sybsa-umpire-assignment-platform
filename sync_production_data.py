#!/usr/bin/env python
"""
Simple script to sync production data to local database
Run this from your project root: python sync_production_data.py
"""

import os
import subprocess
import sys
from datetime import datetime

# Production database URL from Render
PROD_DB_URL = "postgresql://umpireassigner_user:DRvGcZ0sqz9K7TQRwcJCHFNZXzhmcxEK@dpg-cslmrdt6l47c73abqa00-a.oregon-postgres.render.com/umpireassigner"

def main():
    print("=" * 50)
    print("Production to Local Database Sync")
    print("=" * 50)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Check if user wants to proceed
    print("\n⚠️  WARNING: This will replace ALL data in your local database!")
    response = input("Continue? (y/N): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    # Method 1: Using Django fixtures (works across different database types)
    print("\nMethod 1: Using Django fixtures")
    print("-" * 30)
    
    # Step 1: Backup local data
    print("1. Creating backup of local data...")
    local_backup = f"local_backup_{timestamp}.json"
    try:
        subprocess.run([
            sys.executable, "manage.py", "dumpdata",
            "--indent", "2",
            "-o", local_backup
        ], check=True)
        print(f"   ✅ Local backup saved to {local_backup}")
    except subprocess.CalledProcessError:
        print("   ⚠️  Could not create local backup (might be empty database)")
    
    # Step 2: Export from production
    print("\n2. To export from production, run this command on Render shell:")
    print(f"   python manage.py dumpdata --indent 2 > production_data.json")
    print("   Then download the file to this directory")
    print("\n3. Once you have production_data.json, run:")
    print("   python manage.py flush --no-input")
    print("   python manage.py loaddata production_data.json")
    
    print("\n" + "=" * 50)
    print("Method 2: Using pg_dump (PostgreSQL only)")
    print("-" * 30)
    
    # Check if pg_dump is available
    try:
        subprocess.run(["pg_dump", "--version"], 
                      capture_output=True, check=True)
        
        print("1. Exporting production database...")
        dump_file = f"production_dump_{timestamp}.sql"
        
        result = subprocess.run([
            "pg_dump", PROD_DB_URL
        ], capture_output=True, text=True, check=True)
        
        with open(dump_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"   ✅ Production data exported to {dump_file}")
        
        print("\n2. To import to local PostgreSQL:")
        print(f"   psql -U postgres -d umpireassigner_local < {dump_file}")
        print("\n   Or if using different database:")
        print(f"   psql -U [username] -d [database] < {dump_file}")
        
    except FileNotFoundError:
        print("❌ pg_dump not found. Install PostgreSQL client tools:")
        print("   Mac: brew install postgresql")
        print("   Ubuntu: sudo apt-get install postgresql-client")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running pg_dump: {e}")
        print("   Check your connection to the production database")
    
    print("\n" + "=" * 50)
    print("Quick Setup for Local PostgreSQL")
    print("-" * 30)
    print("1. Install PostgreSQL: brew install postgresql")
    print("2. Start PostgreSQL: brew services start postgresql")
    print("3. Create database: createdb umpireassigner_local")
    print("4. Update .env file:")
    print("   DATABASE_URL=postgresql://localhost/umpireassigner_local")
    print("5. Run migrations: python manage.py migrate")

if __name__ == "__main__":
    main()
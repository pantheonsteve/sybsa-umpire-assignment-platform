#!/usr/bin/env python
"""
Direct database-to-database transfer script
Copies data from production to local PostgreSQL
"""

import psycopg2
from psycopg2 import sql
import sys

# Database URLs
PROD_DB_URL = "postgresql://sybsa_umpire_platform_user:LWmUGvxC8x0IQXYjSbcf6N5zTv1mcn6l@dpg-d30csgripnbc73d5342g-a.virginia-postgres.render.com/sybsa_umpire_platform?sslmode=require"
LOCAL_DB_URL = "postgresql://localhost/umpireassigner_local"

# Tables in dependency order (foreign keys considered)
TABLES_IN_ORDER = [
    # Django system tables first
    'django_content_type',
    'auth_permission',
    'auth_group',
    'auth_group_permissions',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
    'django_admin_log',
    'django_session',
    'django_migrations',
    
    # App tables in dependency order
    'assignments_leagueadmin',
    'assignments_coach',
    'assignments_town',
    'assignments_team',
    'assignments_umpire',
    'assignments_game',
    'assignments_umpireassignment',
    'assignments_umpirepayment',
    'assignments_payrate',
    'assignments_umpireavailability',
]

def transfer_table(prod_conn, local_conn, table_name):
    """Transfer a single table from production to local"""
    print(f"Transferring {table_name}...", end=" ")
    
    try:
        with prod_conn.cursor() as prod_cur:
            with local_conn.cursor() as local_cur:
                # Get all data from production
                prod_cur.execute(f"SELECT * FROM {table_name}")
                rows = prod_cur.fetchall()
                
                if not rows:
                    print("(empty)")
                    return
                
                # Get column names
                prod_cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = [row[0] for row in prod_cur.fetchall()]
                
                # Clear local table (but keep structure)
                local_cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                
                # Insert data
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                
                for row in rows:
                    local_cur.execute(insert_query, row)
                
                local_conn.commit()
                print(f"✓ ({len(rows)} rows)")
                
    except Exception as e:
        print(f"✗ Error: {e}")
        local_conn.rollback()
        raise

def main():
    print("=" * 60)
    print("Production to Local Database Transfer")
    print("=" * 60)
    
    # Auto-confirm for automation
    print("\n⚠️  WARNING: This will REPLACE all data in your local database!")
    print("Auto-confirming for automation...")
    
    print("\nConnecting to databases...")
    
    try:
        # Connect to both databases
        prod_conn = psycopg2.connect(PROD_DB_URL)
        local_conn = psycopg2.connect(LOCAL_DB_URL)
        
        print("✓ Connected to production database")
        print("✓ Connected to local database")
        
        print("\nTransferring data...")
        print("-" * 40)
        
        # Transfer each table
        for table in TABLES_IN_ORDER:
            transfer_table(prod_conn, local_conn, table)
        
        print("-" * 40)
        print("\n✅ Transfer complete!")
        
        # Close connections
        prod_conn.close()
        local_conn.close()
        
        print("\nYour local database now contains all production data.")
        print("\nTo test:")
        print("  source venv/bin/activate")
        print("  export DATABASE_URL=postgresql://localhost/umpireassigner_local")
        print("  python manage.py runserver")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Database connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if PostgreSQL is running: brew services list")
        print("2. Check if local database exists: psql -l")
        print("3. Verify production database is accessible")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
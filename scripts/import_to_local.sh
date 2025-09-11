#!/bin/bash

# Import production data to local PostgreSQL database
# Usage: ./scripts/import_to_local.sh <backup_file.sql>

echo "==================================="
echo "Local Database Import Script"
echo "==================================="

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql>"
    echo "Example: $0 production_backup_20240101_120000.sql"
    exit 1
fi

BACKUP_FILE=$1

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file '$BACKUP_FILE' not found!"
    exit 1
fi

# Local database settings (adjust these as needed)
LOCAL_DB_NAME="umpireassigner_local"
LOCAL_DB_USER="postgres"
LOCAL_DB_HOST="localhost"
LOCAL_DB_PORT="5432"

echo "Backup file: $BACKUP_FILE"
echo "Target database: $LOCAL_DB_NAME"
echo ""
echo "⚠️  WARNING: This will replace ALL data in your local database!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Step 1: Create backup of current local database (safety first!)
echo "Creating backup of current local database..."
LOCAL_BACKUP="local_backup_before_import_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -d $LOCAL_DB_NAME > "$LOCAL_BACKUP" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Local backup created: $LOCAL_BACKUP"
else
    echo "⚠️  Warning: Could not create local backup (database might not exist yet)"
fi

# Step 2: Drop and recreate the local database
echo ""
echo "Recreating local database..."
psql -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -c "DROP DATABASE IF EXISTS $LOCAL_DB_NAME;" 2>/dev/null
psql -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -c "CREATE DATABASE $LOCAL_DB_NAME;" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Error creating database. Make sure PostgreSQL is running locally."
    echo ""
    echo "To install PostgreSQL on Mac:"
    echo "brew install postgresql"
    echo "brew services start postgresql"
    exit 1
fi

# Step 3: Import the production backup
echo ""
echo "Importing production data..."
psql -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -d $LOCAL_DB_NAME < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Import successful!"
    echo ""
    echo "Next steps:"
    echo "1. Update your .env file with local database settings:"
    echo "   DATABASE_URL=postgresql://$LOCAL_DB_USER@$LOCAL_DB_HOST:$LOCAL_DB_PORT/$LOCAL_DB_NAME"
    echo ""
    echo "2. Run migrations (in case of schema differences):"
    echo "   python manage.py migrate"
    echo ""
    echo "3. Start your local server:"
    echo "   python manage.py runserver"
    echo ""
    echo "If you need to restore your original local data:"
    echo "psql -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -d $LOCAL_DB_NAME < $LOCAL_BACKUP"
else
    echo ""
    echo "❌ Import failed!"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check PostgreSQL is running: brew services list"
    echo "2. Check your PostgreSQL user exists: psql -U $LOCAL_DB_USER -l"
    echo "3. You may need to create the user: createuser -s $LOCAL_DB_USER"
    echo ""
    echo "To restore your original local data:"
    echo "psql -h $LOCAL_DB_HOST -p $LOCAL_DB_PORT -U $LOCAL_DB_USER -d $LOCAL_DB_NAME < $LOCAL_BACKUP"
    exit 1
fi
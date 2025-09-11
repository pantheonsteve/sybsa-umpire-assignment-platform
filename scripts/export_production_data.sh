#!/bin/bash

# Export production data from Render PostgreSQL to local
# This script creates a backup of your production database

echo "==================================="
echo "Production Database Export Script"
echo "==================================="

# Production database URL (you'll need to set this)
# You can get this from your Render dashboard
PROD_DATABASE_URL="postgresql://umpireassigner_user:DRvGcZ0sqz9K7TQRwcJCHFNZXzhmcxEK@dpg-cslmrmt6l47c73abqa00-a.oregon-postgres.render.com/umpireassigner"

# Output file with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="production_backup_${TIMESTAMP}.sql"

echo "Exporting production database..."
echo "Output file: ${OUTPUT_FILE}"

# Method 1: Using pg_dump directly (recommended)
pg_dump "${PROD_DATABASE_URL}" > "${OUTPUT_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ Export successful!"
    echo "Backup saved to: ${OUTPUT_FILE}"
    echo ""
    echo "File size: $(du -h ${OUTPUT_FILE} | cut -f1)"
    echo ""
    echo "To import this data locally, run:"
    echo "./scripts/import_to_local.sh ${OUTPUT_FILE}"
else
    echo "❌ Export failed!"
    echo "Please check your database URL and connection"
    exit 1
fi

# Alternative Method 2: Using Django dumpdata (if pg_dump doesn't work)
# This creates JSON fixtures that can be loaded with loaddata
echo ""
echo "Alternative: Creating Django fixtures..."
echo "You can also export using Django's dumpdata on your production server:"
echo ""
echo "# SSH into your Render instance or run in Render shell:"
echo "python manage.py dumpdata --indent 2 > fixtures_${TIMESTAMP}.json"
echo ""
echo "# Then load locally with:"
echo "python manage.py loaddata fixtures_${TIMESTAMP}.json"
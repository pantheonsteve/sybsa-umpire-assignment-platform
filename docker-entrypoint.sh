#!/bin/bash
set -e

echo "Waiting for database..."
while ! python -c "
import os, sys
if os.environ.get('DATABASE_URL'):
    import psycopg2
    import dj_database_url
    db = dj_database_url.parse(os.environ['DATABASE_URL'])
    conn = psycopg2.connect(
        dbname=db['NAME'], user=db['USER'], password=db['PASSWORD'],
        host=db['HOST'], port=db['PORT']
    )
    conn.close()
" 2>/dev/null; do
    echo "Database not ready, retrying in 2s..."
    sleep 2
done
echo "Database is ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
fi

exec "$@"

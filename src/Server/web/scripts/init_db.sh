#!/bin/bash

# Database initialization script for PrometheanProxy web interface
# This script waits for the database to be ready and runs migrations

set -e

echo "Waiting for database to be ready..."

# Wait for PostgreSQL to be ready
if [ -n "$DB_HOST" ]; then
    echo "Using PostgreSQL at $DB_HOST:$DB_PORT"

    # Wait up to 30 seconds for database
    for i in {1..30}; do
        if python << END
import psycopg2
import os
import sys

try:
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'promethean'),
        user=os.getenv('DB_USER', 'promethean'),
        password=os.getenv('DB_PASSWORD', 'promethean_password'),
        host=os.getenv('DB_HOST', 'db'),
        port=os.getenv('DB_PORT', '5432')
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
END
        then
            echo "Database is ready!"
            break
        fi
        echo "Waiting for database... ($i/30)"
        sleep 1
    done
else
    echo "Using SQLite database"
fi

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist
echo "Checking for admin user..."
python << END
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'promethean_web.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@promethean.local')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
END

echo "Database initialization complete!"
echo ""
echo "================================"
echo "Default Admin Credentials:"
echo "Username: admin"
echo "Password: admin"
echo "================================"
echo ""
echo "Starting Django server..."

# Execute the main command (passed as arguments to this script)
exec "$@"

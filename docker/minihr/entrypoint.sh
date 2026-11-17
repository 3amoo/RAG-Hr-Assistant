#!/bin/bash
set -e

echo "Running database migrations..."
cd /app/models/db_schemes/mini_hr/
alembic -c alembic.ini upgrade head
cd /app

echo "Starting: $*"
exec "$@"

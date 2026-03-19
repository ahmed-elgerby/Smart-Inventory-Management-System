#!/bin/bash
# Wait for PostgreSQL to be ready before starting the alert service

set -e

HOST=${DB_HOST:=localhost}
PORT=${DB_PORT:=5432}
USER=${DB_USER:=postgres}
PASSWORD=${DB_PASSWORD:=postgres}
TIMEOUT=${DB_TIMEOUT:=30}

echo "🔄 Waiting for PostgreSQL at $HOST:$PORT..."

start_time=$(date +%s)
while true; do
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  
  if [ $elapsed -gt $TIMEOUT ]; then
    echo "❌ Timeout waiting for PostgreSQL after ${TIMEOUT}s"
    exit 1
  fi
  
  if PGPASSWORD=$PASSWORD psql -h "$HOST" -p "$PORT" -U "$USER" -d "postgres" -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready!"
    break
  fi
  
  echo "⏳ PostgreSQL not ready yet... retrying in 2s"
  sleep 2
done

echo "🚀 Starting alert service..."
exec python alert_microservice.py

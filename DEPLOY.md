# Deployment & Troubleshooting Guide

## Quick Start: Fresh Deploy

```powershell
cd \\wsl.localhost\Ubuntu\root\DevOps\Project\ClaudeLast

# Stop and remove everything
docker-compose down
docker volume rm claudelast_pg_data

# Rebuild and start fresh
docker-compose up --build -d

# Wait 35-40 seconds for services to initialize
# Check logs
docker logs -f BE
docker logs -f Alert_Service
docker logs -f FE
```

## Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

## What Was Fixed

### 1. Docker Startup Race Condition ✅
- **Problem**: Services started before database was ready, causing "failed to fetch username/password" error
- **Solution**: 
  - Added PostgreSQL health check to database service
  - Added `wait-for-db.sh` scripts to all services
  - Services now wait for database to be ready before starting
  - Added `restart: unless-stopped` for reliability

### 2. Picture Upload Failures ✅
- **Problem**: `Failed to fetch` error when uploading photos or item pictures
- **Solution**:
  - Fixed nginx proxy configuration to properly strip `/api/` prefix with trailing slash
  - Increased buffer sizes: `proxy_buffers 4 256k`
  - Added `client_max_body_size 10M` to allow larger uploads
  - Improved error handling in frontend with console logging

### 3. Login Request 404 Error ✅
- **Problem**: 401/404 when submitting username and password
- **Solution**:
  - Fixed nginx `proxy_pass http://backend:5000/;` (added trailing slash) to strip `/api/` prefix correctly
  - Now `/api/auth/login` correctly routes to `http://backend:5000/auth/login`

## Testing Checklist

### 1. Login Flow
- [ ] Open http://localhost
- [ ] Enter username: `admin` and password: `admin123`
- [ ] Click "Sign In"
- [ ] Should see welcome screen with "Proceed" button

### 2. Profile Photo Upload
- [ ] Go to **Settings** → **My Profile**
- [ ] Click **📷 Change Photo**
- [ ] Select an image file (JPG, PNG, or WebP)
- [ ] Preview should update immediately
- [ ] Click **Save Changes**
- [ ] Should see "Settings saved!" message
- [ ] Photo should appear in sidebar
- [ ] Photo should persist after refresh/login

### 3. Item Picture Upload
- [ ] Go to **Inventory**
- [ ] Click **✏️** on any item to edit
- [ ] Click **📷 Change Picture**
- [ ] Select an image file
- [ ] Preview should update immediately
- [ ] The picture should save automatically
- [ ] Click **Save Changes**
- [ ] Photo should appear in inventory table

### 4. Dashboard Charts
- [ ] Login as admin/manager
- [ ] Go to **Dashboard**
- [ ] Should see:
  - [ ] Stat cards (Total SKUs, Low Stock, Out of Stock, Active Alerts, Inventory Value)
  - [ ] Line chart (Inventory Trend)
  - [ ] Donut chart (Items by Category)
  - [ ] Pie chart (All Products Quantity Share)
  - [ ] Horizontal bar breakdown (Top 12 items)
- [ ] Open browser DevTools (F12) **Console** tab
- [ ] Should see NO RED ERRORS (only warnings for missing data are OK)

### 5. Alerts System
- [ ] Verify alerts show on dashboard
- [ ] Go to **Inventory**
- [ ] Click **-** to reduce an item's quantity
- [ ] Alerts should update within 15 seconds
- [ ] Low stock items should show in alerts (quantity < min_quantity)
- [ ] Out of stock items should show in alerts (quantity = 0)

## Troubleshooting

### "Failed to fetch" errors
1. Check browser **DevTools > Console** for specific error messages
2. Run `docker logs FE` to see nginx errors
3. Run `docker logs BE` to see backend errors
4. Ensure services are fully initialized (wait 40 seconds after `up`)

### Photos not uploading
1. Check file size is under 5MB
2. Check browser console for error messages with response code
3. Verify authorization header is being sent: `Authorization: Bearer <token>`
4. Check backend logs for upload errors

### Charts not displaying
1. Open DevTools > Console and look for chart-related errors
2. Check if `state.analytics` is null/undefined
3. Verify `/analytics/summary` endpoint is working:
   ```bash
   docker exec BE curl -H "Authorization: Bearer <token>" http://localhost:5000/analytics/summary
   ```

### Database connection errors
1. Check logs: `docker logs Our_DB`
2. Verify database is healthy: `docker exec Our_DB pg_isready -U postgres`
3. Try full restart with clean volume:
   ```bash
   docker-compose down
   docker volume rm claudelast_pg_data
   docker-compose up --build -d
   ```

## Logs to Monitor

```powershell
# Backend (API server)
docker logs -f BE

# Alert service
docker logs -f Alert_Service

# Frontend (Nginx)
docker logs -f FE

# Database
docker logs -f Our_DB

# All services
docker-compose logs -f
```

## Environment Variables

All services use these environment variables (set in docker-compose.yml):
- `DB_HOST=db`
- `DB_PORT=5432`
- `DB_USER=postgres`
- `DB_PASSWORD=postgres`
- `DB_NAME=inventory`

To change defaults, edit `docker-compose.yml` and rebuild.

## Performance Notes

- Initial startup takes 35-40 seconds (database initialization + health checks)
- Picture uploads timeout after 300 seconds (5 minutes)
- Maximum upload size: 10MB (configurable in nginx.conf)
- Alert checks run every 15 seconds
- Charts render on-demand (not cached)

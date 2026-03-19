# Rebuild Instructions for Database Schema Update

The following changes require a complete database rebuild:

## Changes Made:
1. ✅ Added picture upload support to items table
2. ✅ Fixed stock synchronization in backend
3. ✅ Fixed alert refresh in frontend after inventory updates
4. ✅ Fixed profile picture upload error handling

## Database Schema Updates:
- `items` table now has `picture` (BYTEA) and `picture_filename` columns
- Alert resolution logic has been verified

## How to Rebuild

### Option 1: Complete Docker Rebuild (Recommended)
```bash
cd \\wsl.localhost\Ubuntu\root\DevOps\Project\ClaudeLast

# Stop all containers
docker-compose down

# Remove the database volume to force recreation
docker volume rm claudelast_pg_data

# Rebuild and start fresh
docker-compose up --build -d

# Wait 10-15 seconds for services to initialize
```

### Option 2: Just Rebuild Containers (if volume persists)
```bash
# Stop containers
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Start containers
docker-compose up -d
```

## Verify the Fix

### 1. Check Picture Upload
1. Go to Settings → My Profile
2. Click "Change Photo" 
3. Upload an image
4. Verify no errors appear
5. Refresh the page - photo should persist

### 2. Check Alert Resolution
1. Go to Inventory
2. Find an item with low stock or out of stock
3. Increase its quantity (use +/- buttons)
4. **Important**: If quantity goes back to normal (above min), the alert should disappear immediately
5. Check Dashboard → the alert count should decrease
6. Check the active alerts list - the item should no longer appear

### 3. Verify Database
```bash
# Connect to database
docker exec -it Our_DB psql -U postgres -d inventory

# Check schema
\d items

# Should show picture and picture_filename columns
SELECT column_name FROM information_schema.columns WHERE table_name='items';

# Check alerts
SELECT id, item_id, alert_type, status FROM alerts LIMIT 10;
```

## Troubleshooting

### If alerts still appear after restocking:
```bash
# Check alert service logs
docker logs Alert_Service

# Check backend logs  
docker logs BE

# Check database connection
docker exec -it Our_DB psql -U postgres -d inventory -c "SELECT COUNT(*) FROM alerts WHERE status='active';"
```

### If picture upload still fails:
```bash
# Check backend logs
docker logs BE

# Verify photo column exists
docker exec -it Our_DB psql -U postgres -d inventory -c "\d users"
```

## Expected Results After Rebuild

✅ **Picture Upload** - Should show success message and persist after refresh
✅ **Alert Resolution** - When you restock an item, its alert should disappear instantly from:
  - Active alerts list
  - Dashboard alert count
  - Chart/pie chart should update

If issues persist after rebuild, check the container logs for specific error messages.

# Pictures Directory

This directory contains item product pictures and fallback images.

## About Item Pictures

**Important**: Item pictures are stored in the **PostgreSQL database**, not in this filesystem directory!

- Upload endpoint: POST `/api/items/<item_id>/picture`
- Download endpoint: GET `/api/items/<item_id>/picture`
- Database field: `items.picture` (BYTEA) and `items.picture_filename` (VARCHAR)
- Max file size: 5MB

## Files in This Directory

### Local Placeholder Assets

- **placeholder.svg** - Default "No Image Available" placeholder shown when item picture is missing
  - Displayed when API returns 404 for `/api/items/<item_id>/picture`
  - Dimensions: 400x400px
  - Format: SVG (scalable)

## Usage in Frontend

```html
<!-- Display item picture with fallback -->
<img id="item-pic-123" 
     data-item-id="123"
     src="/api/items/123/picture" 
     alt="Item Picture"
     onerror="this.src='/assets/pictures/placeholder.svg'"
     style="width:300px; height:300px; object-fit:cover;">
```

```javascript
// Upload new item picture
async function uploadItemPicture(itemId, file) {
  const formData = new FormData();
  formData.append('picture', file);
  const response = await fetch(`/api/items/${itemId}/picture`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token() },
    body: formData
  });
  if (response.ok) {
    // Refresh image by adding cache-bust parameter
    document.getElementById(`item-pic-${itemId}`).src = 
      `/api/items/${itemId}/picture?t=${Date.now()}`;
  }
}
```

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- GIF (.gif)
- SVG (.svg)

## Best Practices

1. **Image Dimensions**: Upload images at least 400x400px for good quality
2. **File Size**: Keep file sizes under 2MB for faster uploads
3. **Format**: JPEG for photographs, PNG for graphics with transparency
4. **Naming**: Use descriptive filenames when uploading

## Example Workflow

1. User uploads item picture via web interface
2. Picture is sent to `/api/items/{itemId}/picture` endpoint
3. Backend stores picture in database with filename
4. Frontend fetches picture via `/api/items/{itemId}/picture`
5. If picture missing, falls back to `placeholder.svg`

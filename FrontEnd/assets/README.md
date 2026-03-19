# Frontend Assets

This directory contains all static assets for the Inventory Management System frontend.

## Directory Structure

### `/logos`
- **Purpose**: Store company logos, brand images, and system branding assets
- **Recommended files**:
  - `logo.png` - Main company logo (500x500px)
  - `logo-small.png` - Favicon-sized logo (64x64px)
  - `logo-white.png` - White version for dark backgrounds
  - `favicon.ico` - Browser tab icon

### `/pictures`
- **Purpose**: Item product pictures and inventory images
- **How it works**: 
  - Item pictures are uploaded through the web interface
  - Stored in the database (BYTEA field in items table)
  - Accessible via API: `/api/items/<item_id>/picture`
  - This folder contains local copies/templates only
- **Recommended files**:
  - `placeholder.png` - Default image when item has no picture (400x400px)
  - `no-image.svg` - SVG fallback for missing images

### `/icons`
- **Purpose**: UI icons, category icons, and status indicators
- **Recommended files**:
  - `category-*.svg` - Icons for different product categories
  - `status-*.svg` - Status indicator icons
  - `action-*.svg` - Action button icons

## File Guidelines

### Image Formats
- **Logos**: PNG (transparent) or SVG (scalable)
- **Product Pictures**: JPEG or PNG (max 5MB per upload via API)
- **Icons**: SVG (recommended) or PNG

### Naming Convention
- Use lowercase with hyphens: `product-image.png`
- Include size when relevant: `logo-64x64.png`
- Use descriptive names: `category-electronics.svg`

## Usage Examples

### In HTML/CSS
```html
<!-- Static logos -->
<img src="/assets/logos/logo.png" alt="Company Logo">

<!-- Item pictures (loaded from database) -->
<img src="/api/items/123/picture" alt="Item Picture">

<!-- Fallback for missing item pictures -->
<img src="/assets/pictures/placeholder.png" alt="No image available">
```

### In JavaScript
```javascript
// Upload item picture
const formData = new FormData();
formData.append('picture', fileInput.files[0]);
fetch('/api/items/123/picture', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ' + token() },
  body: formData
});

// Display item picture with fallback
const img = new Image();
img.src = `/api/items/123/picture`;
img.onerror = () => { img.src = '/assets/pictures/placeholder.png'; };
```

## Note on Item Pictures

- Item pictures are stored in the **database** (not the filesystem)
- Upload via: POST `/api/items/<item_id>/picture`
- Download via: GET `/api/items/<item_id>/picture`
- Maximum file size: 5MB (configurable via `MAX_CONTENT_LENGTH`)
- Supported formats: Any image format that browsers support (JPEG, PNG, WebP, GIF, etc.)

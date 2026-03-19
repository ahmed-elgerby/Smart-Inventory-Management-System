# Icons Directory

Store SVG and PNG icons for the inventory management system UI.

## Icon Categories

### Category Icons
- `category-electronics.svg` - Electronics/gadgets
- `category-furniture.svg` - Furniture
- `category-clothing.svg` - Clothing/apparel
- `category-office-supplies.svg` - Office supplies
- `category-tools.svg` - Tools/equipment
- `category-food.svg` - Food/beverages
- Add more as needed for your inventory categories

### Status Icons
- `status-in-stock.svg` - Item is in stock
- `status-low-stock.svg` - Item running low on stock
- `status-out-of-stock.svg` - Item completely out of stock
- `status-unavailable.svg` - Item unavailable/discontinued

### Action Icons
- `upload-picture.svg` - Upload/change item picture
- `download-report.svg` - Download report
- `edit-item.svg` - Edit item details
- `delete-item.svg` - Delete/remove item

## Icon Specifications

### SVG Format (Recommended)
- **Resolution**: Scalable (any size without pixelation)
- **File Size**: Typically 1-5KB per icon
- **Color**: Use CSS variables for theming support:
  - `fill="currentColor"` for dynamic coloring
  - Or hardcode as `fill="#3b82f6"` for brand colors

### PNG Format (Fallback)
- **Resolution**: Minimum 64x64px, recommended 128x128px or 256x256px
- **Background**: Transparent PNG
- **File Size**: 2-10KB per icon

## Usage Examples

### In HTML
```html
<!-- SVG icon from file -->
<img src="/assets/icons/category-electronics.svg" alt="Electronics" width="24">

<!-- SVG with dynamic color -->
<svg class="icon" width="24" height="24" viewBox="0 0 24 24">
  <use href="/assets/icons/status-in-stock.svg#icon"></use>
</svg>

<!-- Icon with tailwind classes -->
<img src="/assets/icons/status-low-stock.svg" alt="Low Stock" class="w-6 h-6 text-yellow-500">
```

### In CSS
```css
.btn-upload::before {
  content: '';
  display: inline-block;
  width: 20px;
  height: 20px;
  background-image: url('/assets/icons/upload-picture.svg');
  background-size: contain;
  margin-right: 0.5rem;
}
```

## Creating Your Own Icons

### Free Icon Resources
- [Feather Icons](https://feathericons.com/) - Minimalist SVG icons
- [Heroicons](https://heroicons.com/) - Beautiful SVG icons by Tailwind Labs
- [Font Awesome](https://fontawesome.com/) - Comprehensive icon library
- [Tabler Icons](https://tabler-icons.io/) - SVG icon set

### Converting Icons to SVG
1. Export as SVG from design tool (Figma, Adobe XD, etc.)
2. Optimize using [SVGO](https://svgo.dev/)
3. Add viewBox attribute if missing: `viewBox="0 0 24 24"`
4. Test in browser for correct display

## Icon Size Guidelines

| Context | Size |
|---------|------|
| Favicon | 16x16, 32x32, 64x64px |
| Navigation menu | 20x20, 24x24px |
| Buttons | 16x16, 20x20px |
| Card headers | 24x24px |
| Large displays | 48x48, 64x64px |

## Color Scheme

Use the system color variables for consistency:
- Primary: `#3b82f6` (blue)
- Success: `#34d399` (green)
- Warning: `#fbbf24` (amber)
- Danger: `#f87171` (red)
- Muted: `#94a3b8` (gray)

## File Naming Convention

- Use lowercase with hyphens: `icon-name.svg`
- Be descriptive: `status-out-of-stock.svg` not `icon3.svg`
- Use prefixes for categories: `category-*`, `status-*`, `action-*`

# Watermark Tool

A comprehensive PDF and image watermarking tool that adds diagonal repeated watermark text to documents. The tool raster-flattens PDFs and images while overlaying customizable watermarks with precise control over appearance and positioning.

## Features

- **Multi-format support**: Process PDFs and common image formats (PNG, JPEG, etc.)
- **Smart DPI detection**: Automatically determines optimal resolution for PDF processing
- **Customizable watermarks**: Control angle, opacity, color, spacing, and font
- **Page selection**: Apply watermarks to specific pages or page ranges
- **Batch processing**: Handle multiple files efficiently
- **Quality control**: Configurable JPEG quality and output formats
- **Text wrapping**: Intelligent text wrapping or single-line mode
- **Analysis mode**: Inspect document properties without processing

## Installation

```bash
# Install from local directory
pip install .

# Or install in development mode
pip install -e .
```

## Quick Start

```bash
# Basic watermarking
watermark input.pdf output.pdf "CONFIDENTIAL"

# With custom styling
watermark --angle 45 --opacity 0.5 --color "#FF0000" input.pdf output.pdf "DRAFT"

# JPEG output with quality control
watermark --format jpeg --quality 95 input.pdf output.pdf "SAMPLE"

# Process specific pages
watermark --pages "1-3,5,7-" input.pdf output.pdf "INTERNAL USE"
```

## Command Line Usage

### Basic Syntax
```bash
watermark [options] input output TEXT
# or
watermark [options] --text TEXT input output
```

### Watermark Styling Options
- `--text TEXT`: Watermark text (alternative to positional argument)
- `--angle DEGREES`: Rotation angle (default: 35.0)
- `--opacity FLOAT`: Transparency level 0-1 (default: 0.38)
- `--color HEX`: Color as hex code (default: #707070)
- `--sparsity FLOAT`: Pattern spacing multiplier (default: 1.3)
- `--font PATH`: Custom TTF/TTC font file path
- `--no-wrap`: Force single-line watermark (disable text wrapping)

### Text Sizing Options
- `--target-width-frac FLOAT`: Target fraction of page width for text (default: 0.6)
- `--min-font-frac FLOAT`: Minimum font size as fraction of page width (default: 0.03)
- `--max-font-frac FLOAT`: Maximum font size as fraction of page width (default: 0.12)
- `--line-spacing-frac FLOAT`: Line spacing as fraction of font size (default: 0.2)

### Processing Options
- `--dpi VALUE`: Rasterization DPI (integer or 'auto', default: auto)
- `--min-auto-dpi INT`: Lower bound for auto DPI (default: 60)
- `--max-auto-dpi INT`: Upper bound for auto DPI (default: 400)
- `--format FORMAT`: Output format: auto, png, jpeg (default: auto)
- `--quality INT`: JPEG quality 1-100 (default: 85)
- `--pages RANGE`: Page selection (e.g., '1-3,5,7-')

### Utility Options
- `--analyze`: Analyze input file and print DPI details without processing
- `--verbose`: Enable detailed per-page logging
- `--help`: Show complete help information

## Examples

### Basic Watermarking
```bash
# Simple watermark
watermark document.pdf watermarked.pdf "CONFIDENTIAL"

# Using --text flag
watermark --text "DRAFT COPY" document.pdf watermarked.pdf
```

### Custom Styling
```bash
# Red diagonal watermark at 45 degrees
watermark --angle 45 --color "#FF0000" --opacity 0.6 doc.pdf out.pdf "URGENT"

# Large, sparse watermark pattern
watermark --sparsity 2.0 --max-font-frac 0.15 doc.pdf out.pdf "SAMPLE"

# Custom font
watermark --font /path/to/font.ttf doc.pdf out.pdf "CUSTOM"
```

### Output Control
```bash
# High-quality JPEG output
watermark --format jpeg --quality 95 doc.pdf out.pdf "HIGH QUALITY"

# PNG output with high DPI
watermark --format png --dpi 300 doc.pdf out.pdf "PRINT READY"
```

### Page Selection
```bash
# First 3 pages only
watermark --pages "1-3" doc.pdf out.pdf "PREVIEW"

# Pages 1, 3, and 5 through end
watermark --pages "1,3,5-" doc.pdf out.pdf "SELECTED"

# All pages except first and last
watermark --pages "2-" doc.pdf temp.pdf "CONTENT"
watermark --pages "1-n-1" temp.pdf out.pdf "CONTENT"  # (requires manual calculation)
```

### Analysis and Inspection
```bash
# Analyze PDF properties
watermark --analyze document.pdf output.pdf "TEXT"

# Verbose processing with details
watermark --verbose doc.pdf out.pdf "DETAILED"
```

## Programmatic API

### PDF Operations
```python
from watermark import raster_flatten_pdf_with_watermark, analyze_pdf

# Basic PDF watermarking
raster_flatten_pdf_with_watermark(
    "input.pdf",
    "output.pdf",
    "WATERMARK TEXT",
    dpi=200,
    angle=35,
    opacity=0.4
)

# Analyze PDF properties
dpi_info = analyze_pdf("document.pdf")
```

### Image Operations
```python
from watermark import images_to_pdf_with_watermark

# Convert images to watermarked PDF
images_to_pdf_with_watermark(
    "image.png",
    "output.pdf",
    "WATERMARK",
    dpi=300,
    img_format="png"
)
```

### Advanced Rendering
```python
from watermark import make_watermark_overlay, load_font
from PIL import Image

# Create custom watermark overlay
font = load_font(size=48, font_path="custom.ttf")
overlay = make_watermark_overlay(
    width=1000,
    height=800,
    text="CUSTOM WATERMARK",
    font=font,
    angle=45,
    opacity=0.5
)
```

### Utility Functions
```python
from watermark import (
    parse_hex_color,
    parse_page_range,
    is_pdf_file,
    is_image_file,
    extract_image_dpi
)

# Parse color codes
color = parse_hex_color("#FF0000")  # Returns RGB tuple

# Parse page ranges
pages = parse_page_range("1-3,5,7-")  # Returns set of page numbers

# File type detection
if is_pdf_file("document.pdf"):
    print("PDF detected")

if is_image_file("image.png"):
    print("Image detected")
```

## File Format Support

### Input Formats
- **PDF**: Any PDF readable by PyMuPDF
- **Images**: PNG, JPEG, TIFF, BMP, and other PIL-supported formats

### Output Format
- **PDF**: Always outputs PDF format regardless of input type
- **Embedded Images**: PNG or JPEG based on `--format` setting

## Technical Details

- **Dependencies**: Pillow (PIL) for image processing, PyMuPDF for PDF handling
- **Python**: Requires Python 3.11 or later
- **DPI Handling**: Automatic DPI detection for optimal quality/size balance
- **Memory**: Efficient processing with controlled memory usage for large files
- **Font Rendering**: System font support with optional custom font loading

## Testing

Run the smoke tests to verify installation:

```bash
python tests/smoke_test.py
```

## Legacy Compatibility

The legacy script `watermark_pdf.py` remains available as a thin wrapper for backward compatibility with existing workflows.

## License

This project is available for use under standard software licensing terms.

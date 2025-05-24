from construct import *
from typing import List, Dict, Any, Tuple
import colorsys
import html
import textwrap

def create_svg(flattened_data: List[Dict[str, Any]], 
                        raw_data: bytes,
                        title: str = "Binary Format",
                        width: int = 1200,
                        height: int = None) -> str:
    """
    Args:
        flattened_data: Output from flatten_construct_offsets()
        raw_data: The raw binary data
        title: Title for the format (e.g., "GRAPHICS INTERCHANGE FORMAT")
        width: SVG width in pixels
        height: SVG height in pixels (auto-calculated if None)
    
    Returns:
        SVG string
    """
    
    # Filter out items without offset information
    items_with_offsets = [item for item in flattened_data if item['start'] is not None]
    
    if not items_with_offsets:
        return '<svg><text x="10" y="20">No offset data available</text></svg>'
    
    # Group items by their top-level parent
    sections = {}
    for item in items_with_offsets:
        parts = item['name'].split('.')
        section = parts[0]
        if section not in sections:
            sections[section] = []
        sections[section].append(item)
    
    # Calculate required height if not provided
    if height is None:
        # Calculate based on content
        hex_rows = min(6, (len(raw_data) + 15) // 16)
        hex_height = hex_rows * 22 + 60
        sections_height = sum(70 + len(items) * 22 for items in sections.values()) + len(sections) * 20
        height = max(800, 140 + max(hex_height + 200, sections_height) + 150)
    
    # Start building SVG with dark background
    svg_parts = []
    svg_parts.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
    
    # Dark theme styles
    svg_parts.append('''
    <defs>
        <style>
            .background { fill: #1a1a1a; }
            .title { font-family: Arial, sans-serif; font-size: 52px; font-weight: normal; letter-spacing: 8px; word-spacing: 20px; }
            .title-orange { fill: #FF6600; }
            .title-white { fill: #FFFFFF; }
            .section-title { font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; fill: #FFFFFF; }
            .field-name { font-family: Consolas, Monaco, monospace; font-size: 13px; fill: #FFD700; }
            .field-value { font-family: Consolas, Monaco, monospace; font-size: 13px; fill: #FFFFFF; }
            .field-label { font-family: Consolas, Monaco, monospace; font-size: 11px; fill: #999; text-transform: uppercase; letter-spacing: 1px; }
            .hex-text { font-family: Consolas, Monaco, monospace; font-size: 13px; font-weight: 500; fill: #FFFFFF; }
            .hex-offset { font-family: Consolas, Monaco, monospace; font-size: 12px; fill: #888; font-weight: bold; }
            .ascii-text { font-family: Consolas, Monaco, monospace; font-size: 11px; font-weight: 500; }
            .connector-line { stroke-width: 2; fill: none; opacity: 0.8; }
            .section-box { stroke: #444; stroke-width: 1.5; }
            .hex-box { fill: #2a2a2a; stroke: #444; stroke-width: 2; }
            .hex-highlight { opacity: 1; }
            .copyright { font-family: Arial, sans-serif; font-size: 11px; fill: #666; }
            .description { font-family: Georgia, serif; font-size: 15px; fill: #CCC; line-height: 1.6; }
        </style>
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    ''')
    
    # Dark background
    svg_parts.append(f'<rect width="{width}" height="{height}" class="background"/>')
    
    # Title with proper spacing
    title_text = ' '.join(title.upper().split())
    svg_parts.append(f'<text x="60" y="70" class="title">')
    words = title_text.split()
    for i, word in enumerate(words):
        if i % 2 == 0:
            svg_parts.append(f'<tspan class="title-orange">{word}</tspan>')
        else:
            svg_parts.append(f'<tspan class="title-white">{word}</tspan>')
        if i < len(words) - 1:
            svg_parts.append(' ')
    svg_parts.append('</text>')
    
    # Hex dump on the left
    hex_x = 60
    hex_y = 140
    bytes_per_row = 16
    rows_to_show = min(6, (len(raw_data) + bytes_per_row - 1) // bytes_per_row)
    hex_width = 650  # Increased to accommodate ASCII
    hex_height = rows_to_show * 22 + 50
    
    # Draw hex dump box
    svg_parts.append(f'<rect x="{hex_x}" y="{hex_y}" width="{hex_width}" height="{hex_height}" class="hex-box"/>')
    
    # Create color palette for sections
    color_palette = {
        'header': '#FF6B6B',
        'logical_screen': '#4ECDC4', 
        'global_color_table': '#95E1D3',
        'image': '#F38181',
        'trailer': '#AA96DA',
        'default': '#FFD93D'
    }
    
    # Create a map of byte positions to fields for continuous coloring
    byte_field_map = {}
    for item in items_with_offsets:
        section = item['name'].split('.')[0]
        color = color_palette.get(section, color_palette['default'])
        for pos in range(item['start'], item['end']):
            byte_field_map[pos] = (section, color)
    
    # Draw continuous colored backgrounds first
    for row in range(rows_to_show):
        offset = row * bytes_per_row
        y = hex_y + 35 + row * 22
        
        # Group consecutive bytes with same color
        col = 0
        while col < bytes_per_row and offset + col < len(raw_data):
            byte_offset = offset + col
            if byte_offset in byte_field_map:
                section, color = byte_field_map[byte_offset]
                # Find how many consecutive bytes have the same color
                consecutive = 1
                while (col + consecutive < bytes_per_row and 
                       offset + col + consecutive < len(raw_data) and
                       offset + col + consecutive in byte_field_map and
                       byte_field_map[offset + col + consecutive][0] == section):
                    consecutive += 1
                
                # Draw continuous background for hex
                x = hex_x + 70 + col * 26
                width_bg = consecutive * 26 - 4
                svg_parts.append(f'<rect x="{x-3}" y="{y-15}" width="{width_bg}" height="18" fill="{color}" opacity="0.3"/>')
                
                # Draw continuous background for ASCII
                ascii_x = hex_x + 490 + col * 10
                ascii_width = consecutive * 10 - 2
                svg_parts.append(f'<rect x="{ascii_x-1}" y="{y-15}" width="{ascii_width}" height="18" fill="{color}" opacity="0.3"/>')
                
                col += consecutive
            else:
                col += 1
    
    # Draw hex values and ASCII
    for row in range(rows_to_show):
        offset = row * bytes_per_row
        y = hex_y + 35 + row * 22
        
        # Offset
        svg_parts.append(f'<text x="{hex_x + 15}" y="{y}" class="hex-offset">{offset:02X}:</text>')
        
        # Hex values
        for col in range(bytes_per_row):
            byte_offset = offset + col
            if byte_offset < len(raw_data):
                x = hex_x + 70 + col * 26
                hex_val = f"{raw_data[byte_offset]:02X}"
                svg_parts.append(f'<text x="{x}" y="{y}" class="hex-text">{hex_val}</text>')
        
        # ASCII representation with color coding
        ascii_x = hex_x + 490
        for col in range(min(bytes_per_row, len(raw_data) - offset)):
            byte_offset = offset + col
            byte_val = raw_data[byte_offset]
            char = chr(byte_val) if 32 <= byte_val < 127 else '·'
            x = ascii_x + col * 10
            
            # Get color for ASCII character
            ascii_color = '#666'  # default
            if byte_offset in byte_field_map:
                _, field_color = byte_field_map[byte_offset]
                ascii_color = field_color
            
            svg_parts.append(f'<text x="{x}" y="{y}" class="ascii-text" fill="{ascii_color}">{html.escape(char)}</text>')
    
    # Draw connectors and field descriptions
    section_y = hex_y
    section_x = hex_x + hex_width + 80
    
    for section_idx, (section_name, section_items) in enumerate(sections.items()):
        # Get section color
        section_color = color_palette.get(section_name, color_palette['default'])
        
        # Draw section box with section's color theme
        box_height = 50 + len(section_items) * 22
        svg_parts.append(f'<rect x="{section_x}" y="{section_y}" width="400" height="{box_height}" rx="4" fill="{section_color}" opacity="0.15" stroke="{section_color}" class="section-box"/>')
        
        # Section title bar with stronger color
        svg_parts.append(f'<rect x="{section_x}" y="{section_y}" width="400" height="35" rx="4" fill="{section_color}" opacity="0.3"/>')
        
        # Section title
        section_title = section_name.upper().replace('_', ' ')
        svg_parts.append(f'<text x="{section_x + 15}" y="{section_y + 25}" class="section-title" filter="url(#glow)">{section_title}</text>')
        
        # Draw smooth connector with section color
        connector_start_x = hex_x + hex_width
        connector_start_y = hex_y + 40 + (section_idx * 30)
        connector_end_x = section_x
        connector_end_y = section_y + box_height // 2
        
        control_x = (connector_start_x + connector_end_x) / 2
        svg_parts.append(f'''<path d="M {connector_start_x} {connector_start_y} 
                          C {control_x} {connector_start_y}, {control_x} {connector_end_y}, 
                          {connector_end_x} {connector_end_y}" 
                          class="connector-line" stroke="{section_color}"/>''')
        
        # Column headers
        field_y = section_y + 45
        svg_parts.append(f'<text x="{section_x + 150}" y="{field_y}" text-anchor="end" class="field-label">Fields</text>')
        svg_parts.append(f'<text x="{section_x + 180}" y="{field_y}" class="field-label">Values</text>')
        
        # Divider line
        svg_parts.append(f'<line x1="{section_x + 15}" y1="{field_y + 5}" x2="{section_x + 385}" y2="{field_y + 5}" stroke="{section_color}" stroke-width="1" opacity="0.3"/>')
        
        field_y += 20
        for item in section_items:
            # Field name
            field_name = item['name'].split('.')[-1]
            svg_parts.append(f'<text x="{section_x + 145}" y="{field_y}" text-anchor="end" class="field-name">{field_name}</text>')
            
            # Field value
            value_str = format_field_value(item)
            svg_parts.append(f'<text x="{section_x + 180}" y="{field_y}" class="field-value">{html.escape(value_str)}</text>')
            
            field_y += 20
        
        section_y += box_height + 20
    
    # Add visual sample if it's an image format
    if any('width' in item['name'] and 'height' in item['name'] for item in items_with_offsets):
        sample_x = 60
        sample_y = hex_y + hex_height + 40
        svg_parts.append(f'<rect x="{sample_x}" y="{sample_y}" width="120" height="80" stroke="#444" stroke-width="2" fill="#2a2a2a"/>')
        svg_parts.append(f'<text x="{sample_x + 60}" y="{sample_y - 10}" text-anchor="middle" class="field-label">Visual Sample</text>')
        
        # Draw colored rectangles
        colors = ['#FF6B6B', '#4ECDC4', '#95E1D3']
        for i, color in enumerate(colors):
            svg_parts.append(f'<rect x="{sample_x + 10 + i * 35}" y="{sample_y + 20}" width="30" height="40" fill="{color}"/>')
    
    # Add format description at bottom
    desc_y = height - 120
    svg_parts.append(f'<line x1="60" y1="{desc_y - 20}" x2="{width - 60}" y2="{desc_y - 20}" stroke="#444" stroke-width="1"/>')
    
    description_lines = [
        f"THE {title.upper()} STRUCTURE.",
        f"Total size: {len(raw_data)} bytes | {len(sections)} sections | {len(items_with_offsets)} fields",
        "Each colored region in the hex dump corresponds to a field in the structure."
    ]
    
    for i, line in enumerate(description_lines):
        style = "description" if i == 0 else "copyright"
        y_offset = desc_y + (i * 25)
        svg_parts.append(f'<text x="60" y="{y_offset}" class="{style}">{line}</text>')
    
    # Add attribution
    svg_parts.append(f'<text x="{width - 60}" y="{height - 20}" text-anchor="end" class="copyright">Binary Structure Visualization</text>')
    
    svg_parts.append('</svg>')
    
    return ''.join(svg_parts)


def format_field_value(item):
    """Format field values for display."""
    value = item['value']
    
    if isinstance(value, bytes):
        if len(value) <= 6:
            return ' '.join(f'{b:02X}' for b in value)
        else:
            return ' '.join(f'{b:02X}' for b in value[:6]) + '...'
    elif isinstance(value, int):
        if item['length'] and item['length'] == 1:
            return f"{value}"
        elif item['length'] and item['length'] == 2:
            return f"{value} (0x{value:04X})"
        elif item['length'] and item['length'] == 4:
            return f"{value} (0x{value:08X})"
        else:
            return str(value)
    elif isinstance(value, str):
        if len(value) > 20:
            return value[:20] + '...'
        return value
    elif isinstance(value, (dict, Container)):
        return f"[{len(value)} fields]"
    else:
        return str(value)[:30]


def create_compact_svg(flattened_data: List[Dict[str, Any]], 
                                raw_data: bytes,
                                struct_name: str = "Binary Structure",
                                width: int = 800,
                                height: int = 600) -> str:
    """
    Create a more compact GIF-style visualization suitable for embedding.
    """
    
    items_with_offsets = [item for item in flattened_data if item['start'] is not None]
    
    svg_parts = []
    svg_parts.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">')
    
    # Styles
    svg_parts.append('''
    <defs>
        <style>
            .struct-name { font: bold 32px Arial; }
            .orange { fill: #FF6600; }
            .field-name { font: 12px monospace; fill: #FF0066; }
            .field-value { font: 12px monospace; fill: #0066FF; }
            .hex-text { font: 11px monospace; }
            .section { font: bold 16px Arial; }
            .line { stroke: #333; stroke-width: 1.5; fill: none; }
        </style>
    </defs>
    <rect width="100%" height="100%" fill="white"/>
    ''')
    
    # Title with alternating colors
    words = struct_name.upper().split()
    x = 20
    for i, word in enumerate(words):
        color = "orange" if i % 2 == 0 else ""
        svg_parts.append(f'<text x="{x}" y="40" class="struct-name {color}">{word}</text>')
        x += len(word) * 20 + 10
    
    # Simplified hex view
    hex_y = 80
    svg_parts.append(f'<rect x="20" y="{hex_y}" width="300" height="150" stroke="#333" stroke-width="2" fill="white"/>')
    
    # Show first few bytes
    for row in range(min(6, len(raw_data) // 16 + 1)):
        y = hex_y + 25 + row * 20
        offset = row * 16
        svg_parts.append(f'<text x="30" y="{y}" class="hex-text">{offset:02X}:</text>')
        
        for col in range(min(16, len(raw_data) - offset)):
            x = 70 + col * 18
            byte_val = raw_data[offset + col]
            
            # Color based on field
            color = "#000"
            for item in items_with_offsets:
                if item['start'] <= offset + col < item['end']:
                    # Generate color based on field name
                    color = f"hsl({hash(item['name']) % 360}, 70%, 50%)"
                    break
            
            svg_parts.append(f'<text x="{x}" y="{y}" class="hex-text" fill="{color}">{byte_val:02X}</text>')
    
    # Field descriptions with connecting lines
    field_x = 380
    field_y = hex_y + 20
    
    # Group by top-level
    sections = {}
    for item in items_with_offsets[:10]:  # Limit to first 10 items
        section = item['name'].split('.')[0]
        if section not in sections:
            sections[section] = []
        sections[section].append(item)
    
    for section, items in sections.items():
        # Section header
        svg_parts.append(f'<text x="{field_x}" y="{field_y}" class="section">{section.upper()}</text>')
        field_y += 25
        
        # Draw connection line
        svg_parts.append(f'<path d="M 320 {hex_y + 75} L 360 {hex_y + 75} L 360 {field_y - 20} L 370 {field_y - 20}" class="line"/>')
        
        for item in items:
            name = item['name'].split('.')[-1]
            value = str(item['value'])[:15]
            if len(str(item['value'])) > 15:
                value += "..."
            
            svg_parts.append(f'<text x="{field_x}" y="{field_y}" class="field-name">{name}</text>')
            svg_parts.append(f'<text x="{field_x + 100}" y="{field_y}" class="field-value">{html.escape(value)}</text>')
            field_y += 18
        
        field_y += 15
    
    svg_parts.append('</svg>')
    return ''.join(svg_parts)


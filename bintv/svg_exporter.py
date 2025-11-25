import html
from construct import Container, ListContainer

# Import enhanced v2 exporter
from bintv.svg_exporter_v2 import (
    create_svg_v2, 
    create_poster_svg,
    CorkamistyleSVGExporter,
    format_raw_hex,
    format_decoded_value,
    detect_value_type,
    ValueRepr
)

def format_value_condensed(val):
    """
    Creates a condensed, human-readable string representation of a value.
    Useful for showing 'Processed' data (e.g. decrypted bytes, parsed ints).
    """
    if isinstance(val, (bytes, bytearray)):
        if not val:
            return "b''"
        
        # Heuristic: If it looks like a printable string, show it as text
        # Check first 16 bytes for non-printable chars
        is_text = True
        sample = val[:16]
        for b in sample:
            if not (32 <= b < 127):
                is_text = False
                break
        
        if is_text:
            text = val.decode('ascii', errors='ignore')
            if len(val) > 16:
                return f'b"{text}..."'
            return f'b"{text}"'
        else:
            # Show Hex preview
            hex_str = sample.hex(' ').upper()
            if len(val) > 16:
                return f"[{len(val)}] {hex_str}..."
            return f"[{len(val)}] {hex_str}"

    if isinstance(val, int):
        # Show Dec and Hex
        return f"{val} (0x{val:X})"
        
    if isinstance(val, str):
        clean = val.replace('\n', '\\n').replace('\r', '\\r')
        if len(clean) > 24:
            return f'"{clean[:24]}..."'
        return f'"{clean}"'
        
    if val is None:
        return ""
        
    # Fallback for other types
    s = str(val)
    if len(s) > 24:
        return f"{s[:24]}..."
    return s

def create_svg_legacy(flattened_data, raw_data, title="BINARY STRUCTURE", width=1400):
    """
    Generates a 'Corkami-style' technical poster SVG with funneling connectors.
    Includes Processed Value view.
    """
    
    # --- 1. FILTER & PREP DATA ---
    filtered_data = []
    excluded_names = {'offset1', 'offset2', 'length'}
    
    # Determine interesting rows for sparse view
    hex_cols = 16
    interesting_rows = set()
    interesting_rows.add(0)
    interesting_rows.add((len(raw_data) - 1) // hex_cols)
    
    for field in flattened_data:
        name = field['name'].split('.')[-1]
        
        if (name in excluded_names or 
            name.startswith('_') or 
            '_io' in name or 
            'subcon' in name):
            continue
            
        # Only add to list if it's not a container (containers usually don't have interesting 'values' to show directly)
        # But we keep them for hierarchy if needed. For now, we accept everything passed.
        filtered_data.append(field)
        
        if field['start'] is not None:
            start_row = field['start'] // hex_cols
            end_row = (field['end'] - 1) // hex_cols
            interesting_rows.add(start_row)
            interesting_rows.add(end_row)
    
    flattened_data = filtered_data
    
    sorted_rows = sorted(list(interesting_rows))
    rows_to_render = []
    if sorted_rows:
        prev = sorted_rows[0]
        rows_to_render.append(prev)
        for r in sorted_rows[1:]:
            if r > prev + 1:
                rows_to_render.append('SKIP')
            if r != prev:
                rows_to_render.append(r)
            prev = r

    # --- 2. CONFIGURATION & STYLES ---
    
    hex_row_h = 24
    skip_row_h = 15
    field_row_h = 28
    
    hex_visual_height = 0
    for r in rows_to_render:
        hex_visual_height += skip_row_h if r == 'SKIP' else hex_row_h
        
    total_field_rows = len(flattened_data)
    content_height = max(hex_visual_height, total_field_rows * field_row_h)
    height = content_height + 250 
    
    bg_color = "#151515"
    text_main = "#eeeeee"
    text_dim = "#666666"
    
    from bintv.neon_pallete import generate_text_colors
    palette = generate_text_colors(len(flattened_data))

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    
    svg.append(f'''
    <defs>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&amp;family=Neucha&amp;display=swap');
            
            .bg {{ fill: {bg_color}; }}
            .title {{ font-family: 'Neucha', 'Comic Sans MS', sans-serif; font-size: 48px; fill: {text_main}; }}
            .subtitle {{ font-family: 'Fira Code', monospace; font-size: 14px; fill: {text_dim}; }}
            
            .hex-byte {{ font-family: 'Fira Code', monospace; font-size: 13px; }}
            .hex-ascii {{ font-family: 'Fira Code', monospace; font-size: 13px; opacity: 0.7; }}
            .hex-offset {{ font-family: 'Fira Code', monospace; font-size: 12px; fill: {text_dim}; }}
            .hex-skip {{ font-family: 'Fira Code', monospace; font-size: 12px; fill: {text_dim}; text-anchor: middle; }}
            
            .field-name {{ font-family: 'Fira Code', monospace; font-size: 15px; font-weight: 600; }}
            .field-value {{ font-family: 'Fira Code', monospace; font-size: 14px; fill: {text_main}; opacity: 0.9; }}
            
            .connector {{ fill: none; stroke-width: 1.5; opacity: 0.8; }}
            .funnel-line {{ stroke-width: 2; opacity: 0.5; }}
            
            .glow {{ filter: url(#glow); }}
        </style>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
    </defs>
    <rect width="100%" height="100%" class="bg"/>
    ''')

    # --- 3. LAYOUT CALCULATIONS ---
    
    margin_x = 30
    margin_y = 100
    
    hex_byte_w = 22
    ascii_byte_w = 9
    
    x_offset_col = margin_x
    x_hex_col = x_offset_col + 50
    x_ascii_col = x_hex_col + (hex_cols * hex_byte_w) + 15
    x_funnel_start = x_ascii_col + (hex_cols * ascii_byte_w) + 10
    
    # Columns for the Tree View
    x_tree_name = x_funnel_start + 100
    x_tree_value = x_tree_name + 200 # Offset for the value column
    
    safe_title = html.escape(title)
    svg.append(f'<text x="{width/2}" y="50" text-anchor="middle" class="title glow">{safe_title}</text>')
    svg.append(f'<text x="{width/2}" y="75" text-anchor="middle" class="subtitle">Generated by BinTV</text>')

    # --- 4. RENDER SPARSE HEX DUMP ---
    
    byte_row_map = {}
    
    y_cursor = margin_y
    
    for row_item in rows_to_render:
        if row_item == 'SKIP':
            center_hex = x_hex_col + (8 * hex_byte_w)
            center_ascii = x_ascii_col + (8 * ascii_byte_w)
            svg.append(f'<text x="{center_hex}" y="{y_cursor}" class="hex-skip">⋮</text>')
            svg.append(f'<text x="{center_ascii}" y="{y_cursor}" class="hex-skip">⋮</text>')
            y_cursor += skip_row_h
        else:
            i = row_item * hex_cols
            svg.append(f'<text x="{x_offset_col}" y="{y_cursor}" class="hex-offset">{i:04X}</text>')
            
            chunk = raw_data[i:i+hex_cols]
            for c_idx, byte in enumerate(chunk):
                abs_idx = i + c_idx
                
                byte_color = text_dim
                for f_idx, field in enumerate(flattened_data):
                    if field['start'] is not None and field['start'] <= abs_idx < field['end']:
                        byte_color = palette[f_idx % len(palette)]
                        break
                
                bx = x_hex_col + (c_idx * hex_byte_w)
                svg.append(f'<text x="{bx}" y="{y_cursor}" class="hex-byte" fill="{byte_color}">{byte:02X}</text>')
                
                ax = x_ascii_col + (c_idx * ascii_byte_w)
                char = chr(byte) if 32 <= byte < 127 else '.'
                char = html.escape(char)
                svg.append(f'<text x="{ax}" y="{y_cursor}" class="hex-ascii" fill="{byte_color}">{char}</text>')
                
                byte_row_map[abs_idx] = y_cursor
            
            y_cursor += hex_row_h

    # --- 5. RENDER PARSED TREE & FUNNELS ---
    
    y_cursor = margin_y
    
    for f_idx, field in enumerate(flattened_data):
        field_color = palette[f_idx % len(palette)]
        
        display_name = field['name'].split('.')[-1]
        display_name = html.escape(display_name)
        
        # Prepare Condensed Value
        val_str = format_value_condensed(field['value'])
        val_str = html.escape(val_str)
        
        # 1. Render Field Name
        svg.append(f'<text x="{x_tree_name}" y="{y_cursor}" class="field-name" fill="{field_color}">{display_name}</text>')
        
        # 2. Render Field Value (Processed Info)
        if val_str:
             svg.append(f'<text x="{x_tree_value}" y="{y_cursor}" class="field-value">{val_str}</text>')
        
        # --- FUNNEL LOGIC ---
        if field['start'] is not None:
            start_y = margin_y
            if field['start'] in byte_row_map:
                start_y = byte_row_map[field['start']]
            
            end_idx = field['end'] - 1
            end_y = start_y
            if end_idx in byte_row_map:
                end_y = byte_row_map[end_idx]
            
            bracket_x = x_funnel_start
            mid_data_y = (start_y + end_y) / 2
            
            svg.append(f'<path d="M {bracket_x} {start_y - 5} L {bracket_x} {end_y - 5}" stroke="{field_color}" class="funnel-line" />')
            
            text_x = x_tree_name - 10
            text_y = y_cursor - 5
            
            cx1 = bracket_x + 40
            cx2 = text_x - 40
            
            path = f"M {bracket_x} {mid_data_y - 5} C {cx1} {mid_data_y - 5}, {cx2} {text_y}, {text_x} {text_y}"
            svg.append(f'<path d="{path}" stroke="{field_color}" class="connector" />')
            
            svg.append(f'<circle cx="{bracket_x}" cy="{mid_data_y - 5}" r="2" fill="{field_color}" />')

        y_cursor += field_row_h

    svg.append('</svg>')
    return "\n".join(svg)


# Default to new Corkami-style exporter
def create_svg(flattened_data, raw_data, title="BINARY STRUCTURE", width=1600, use_legacy=False):
    """
    Generate SVG visualization of binary structure.
    
    By default uses the new Corkami-style visualization (v2).
    Set use_legacy=True to use the original simpler visualization.
    
    Args:
        flattened_data: List of field dictionaries from construct parsing
        raw_data: Raw binary data
        title: Title for the visualization
        width: SVG width in pixels
        use_legacy: Use legacy visualization style
        
    Returns:
        SVG string
    """
    if use_legacy:
        return create_svg_legacy(flattened_data, raw_data, title, width)
    return create_svg_v2(flattened_data, raw_data, title, width)

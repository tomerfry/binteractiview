"""
Corkami-style Binary Structure Visualization SVG Exporter v2

Inspired by Ange Albertini's file format posters (corkami.com)
Designed for clear visualization of binary structures with:
- Clean hex dump with color-coded regions
- Field annotations with connector lines
- Raw vs. decoded value comparison
- Section grouping with visual hierarchy
"""

import html
from construct import Container, ListContainer
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValueRepr(Enum):
    """Types of value representation"""
    RAW_HEX = "raw"
    DECODED = "decoded"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BYTES = "bytes"
    CONTAINER = "container"


@dataclass
class FieldDisplay:
    """Structured field display information"""
    name: str
    raw_bytes: Optional[bytes]
    decoded_value: Any
    value_type: ValueRepr
    start: Optional[int]
    end: Optional[int]
    depth: int = 0
    is_encrypted: bool = False
    is_compressed: bool = False


def detect_value_type(value: Any, raw_data: Optional[bytes] = None) -> ValueRepr:
    """Detect the appropriate representation type for a value"""
    if isinstance(value, (Container, dict)):
        return ValueRepr.CONTAINER
    if isinstance(value, (list, ListContainer)):
        return ValueRepr.CONTAINER
    if isinstance(value, int):
        return ValueRepr.INTEGER
    if isinstance(value, float):
        return ValueRepr.FLOAT
    if isinstance(value, str):
        return ValueRepr.STRING
    if isinstance(value, (bytes, bytearray)):
        # Check if bytes look like printable text
        if value and all(32 <= b < 127 or b in (9, 10, 13) for b in value[:32]):
            return ValueRepr.STRING
        return ValueRepr.BYTES
    return ValueRepr.RAW_HEX


def format_raw_hex(data: bytes, max_bytes: int = 16) -> str:
    """Format bytes as hex string"""
    if not data:
        return ""
    hex_str = ' '.join(f'{b:02X}' for b in data[:max_bytes])
    if len(data) > max_bytes:
        hex_str += f' ... (+{len(data) - max_bytes})'
    return hex_str


def format_decoded_value(value: Any, value_type: ValueRepr, max_len: int = 40) -> str:
    """Format a decoded value for display"""
    if value is None:
        return ""
    
    if value_type == ValueRepr.CONTAINER:
        if isinstance(value, (dict, Container)):
            return f"[{len(value)} fields]"
        if isinstance(value, (list, ListContainer)):
            return f"[{len(value)} items]"
        return "[...]"
    
    if value_type == ValueRepr.INTEGER:
        if isinstance(value, int):
            if value < 0:
                return f"{value} (0x{value & 0xFFFFFFFF:X})"
            return f"{value} (0x{value:X})"
        return str(value)
    
    if value_type == ValueRepr.FLOAT:
        return f"{value:.6g}"
    
    if value_type == ValueRepr.STRING:
        if isinstance(value, bytes):
            try:
                text = value.decode('utf-8', errors='replace')
            except:
                text = value.decode('latin-1', errors='replace')
        else:
            text = str(value)
        
        # Escape and truncate
        text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        if len(text) > max_len:
            return f'"{text[:max_len-3]}..."'
        return f'"{text}"'
    
    if value_type == ValueRepr.BYTES:
        if isinstance(value, (bytes, bytearray)):
            return f"[{len(value)} bytes]"
        return str(value)
    
    # RAW_HEX or fallback
    if isinstance(value, (bytes, bytearray)):
        return format_raw_hex(value)
    return str(value)[:max_len]


def is_data_different(raw: bytes, decoded: Any) -> bool:
    """Check if raw and decoded data differ (e.g., decrypted, decompressed)"""
    if raw is None or decoded is None:
        return False
    
    if isinstance(decoded, (bytes, bytearray)):
        return raw != decoded
    
    # For integers, check if the decoded value matches raw interpretation
    if isinstance(decoded, int) and raw:
        # Try common encodings
        if len(raw) <= 8:
            try:
                le_val = int.from_bytes(raw, 'little', signed=False)
                be_val = int.from_bytes(raw, 'big', signed=False)
                if decoded not in (le_val, be_val):
                    return True
            except:
                pass
    
    return False


class CorkamistyleSVGExporter:
    """Corkami-inspired SVG exporter for binary structures"""
    
    # Color palette inspired by Corkami posters
    COLORS = {
        'bg': '#0D0D0D',
        'bg_alt': '#151515',
        'text': '#EEEEEE',
        'text_dim': '#666666',
        'text_muted': '#444444',
        'accent': '#FF6600',  # Corkami orange
        'header': '#4ECDC4',
        'code': '#95E1D3',
        'highlight': '#F38181',
        'warning': '#FFD93D',
        'success': '#6BCB77',
    }
    
    # Neon field colors (vibrant, distinct)
    FIELD_COLORS = [
        '#FF6B6B', '#4ECDC4', '#95E1D3', '#F38181', '#FFD93D',
        '#6BCB77', '#9B59B6', '#3498DB', '#E74C3C', '#1ABC9C',
        '#F39C12', '#2ECC71', '#E91E63', '#00BCD4', '#FF5722',
        '#8BC34A', '#673AB7', '#009688', '#FFC107', '#795548',
    ]
    
    def __init__(self, width: int = 1600, font_family: str = "Fira Code, Consolas, monospace"):
        self.width = width
        self.font_family = font_family
        self.svg_parts = []
        
        # Layout configuration
        self.margin_x = 40
        self.margin_y = 120
        self.hex_byte_w = 24
        self.hex_row_h = 22
        self.hex_cols = 16
        self.ascii_byte_w = 10
        self.field_row_h = 24
        self.section_padding = 15
        
    def _escape(self, text: str) -> str:
        """HTML escape text for SVG"""
        return html.escape(str(text))
    
    def _get_field_color(self, index: int) -> str:
        """Get color for a field by index"""
        return self.FIELD_COLORS[index % len(self.FIELD_COLORS)]
    
    def _add_defs(self):
        """Add SVG definitions (styles, filters, markers)"""
        self.svg_parts.append(f'''
    <defs>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&amp;display=swap');
            
            .bg {{ fill: {self.COLORS['bg']}; }}
            .bg-alt {{ fill: {self.COLORS['bg_alt']}; }}
            
            .title {{ 
                font-family: 'Neucha', 'Comic Sans MS', cursive; 
                font-size: 42px; 
                fill: {self.COLORS['text']}; 
                letter-spacing: 2px;
            }}
            .title-accent {{ fill: {self.COLORS['accent']}; }}
            .subtitle {{ 
                font-family: {self.font_family}; 
                font-size: 14px; 
                fill: {self.COLORS['text_dim']}; 
            }}
            
            .section-header {{
                font-family: {self.font_family};
                font-size: 14px;
                font-weight: 600;
                fill: {self.COLORS['text']};
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .hex-byte {{ 
                font-family: {self.font_family}; 
                font-size: 12px;
                font-weight: 500;
            }}
            .hex-offset {{ 
                font-family: {self.font_family}; 
                font-size: 11px; 
                fill: {self.COLORS['text_muted']}; 
            }}
            .hex-ascii {{ 
                font-family: {self.font_family}; 
                font-size: 12px; 
                opacity: 0.7; 
            }}
            .hex-skip {{ 
                font-family: {self.font_family}; 
                font-size: 11px; 
                fill: {self.COLORS['text_dim']}; 
            }}
            
            .field-name {{ 
                font-family: {self.font_family}; 
                font-size: 13px; 
                font-weight: 600; 
            }}
            .field-label {{ 
                font-family: {self.font_family}; 
                font-size: 10px; 
                fill: {self.COLORS['text_dim']}; 
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .field-raw {{ 
                font-family: {self.font_family}; 
                font-size: 11px; 
                fill: {self.COLORS['text_dim']}; 
            }}
            .field-value {{ 
                font-family: {self.font_family}; 
                font-size: 12px; 
                fill: {self.COLORS['text']}; 
            }}
            .field-value-highlight {{
                font-family: {self.font_family}; 
                font-size: 12px; 
                fill: {self.COLORS['warning']};
            }}
            
            .connector {{ 
                fill: none; 
                stroke-width: 1.5; 
                opacity: 0.7; 
            }}
            .bracket {{ 
                stroke-width: 2; 
                opacity: 0.6; 
            }}
            
            .section-box {{ 
                stroke-width: 1; 
                rx: 3; 
            }}
            
            .divider {{ 
                stroke: {self.COLORS['text_muted']}; 
                stroke-width: 1; 
                opacity: 0.3; 
            }}
            
            .annotation {{
                font-family: {self.font_family};
                font-size: 10px;
                fill: {self.COLORS['text_dim']};
            }}
        </style>
        
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="{self.COLORS['text_dim']}" opacity="0.6"/>
        </marker>
    </defs>
        ''')
    
    def _add_header(self, title: str, file_size: int, field_count: int):
        """Add the poster header"""
        safe_title = self._escape(title)
        
        # Split title for Corkami-style coloring (first meaningful word orange)
        # Handle titles that start with underscore
        words = safe_title.split('_')
        # Filter out empty strings from leading underscores
        words = [w for w in words if w]
        
        if len(words) > 1:
            title_html = f'<tspan class="title-accent">{words[0]}</tspan>'
            title_html += f'<tspan>{"_" + "_".join(words[1:])}</tspan>'
        elif len(words) == 1:
            title_html = f'<tspan class="title-accent">{words[0]}</tspan>'
        else:
            title_html = f'<tspan>{safe_title}</tspan>'
        
        center_x = self.width / 2
        
        self.svg_parts.append(f'''
        <text x="{center_x}" y="55" text-anchor="middle" class="title" filter="url(#glow)">
            {title_html}
        </text>
        <text x="{center_x}" y="82" text-anchor="middle" class="subtitle">
            Generated by BinTV · {file_size:,} bytes · {field_count} fields
        </text>
        ''')
        
        # Decorative line
        self.svg_parts.append(f'''
        <line x1="{self.margin_x}" y1="95" x2="{self.width - self.margin_x}" y2="95" 
              stroke="{self.COLORS['accent']}" stroke-width="2" opacity="0.4"/>
        ''')
    
    def _render_hex_dump(self, raw_data: bytes, fields: List[Dict], y_start: int) -> Tuple[int, Dict[int, int]]:
        """
        Render the hex dump with color-coded fields.
        Returns (end_y, byte_to_y_map)
        """
        byte_row_map = {}
        
        # Calculate which rows to show (sparse view for large files)
        interesting_rows = set([0, (len(raw_data) - 1) // self.hex_cols])
        
        for field in fields:
            if field.get('start') is not None:
                start_row = field['start'] // self.hex_cols
                end_row = (field['end'] - 1) // self.hex_cols
                interesting_rows.add(start_row)
                interesting_rows.add(end_row)
                # Add a row before and after for context
                if start_row > 0:
                    interesting_rows.add(start_row - 1)
                interesting_rows.add(end_row + 1)
        
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
        
        # Layout positions
        x_offset = self.margin_x
        x_hex = x_offset + 55
        x_ascii = x_hex + (self.hex_cols * self.hex_byte_w) + 20
        
        # Section header - "HEX DUMP" on its own line
        self.svg_parts.append(f'''
        <text x="{x_offset}" y="{y_start}" class="section-header">HEX DUMP</text>
        ''')
        
        # Column headers on next line with proper spacing
        header_y = y_start + 18
        self.svg_parts.append(f'''
        <text x="{x_offset}" y="{header_y}" class="field-label">OFFSET</text>
        <text x="{x_hex}" y="{header_y}" class="field-label">00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F</text>
        <text x="{x_ascii}" y="{header_y}" class="field-label">ASCII</text>
        <line x1="{x_offset}" y1="{header_y + 6}" x2="{x_ascii + 165}" y2="{header_y + 6}" class="divider"/>
        ''')
        
        y = header_y + 22
        
        for row_item in rows_to_render:
            if row_item == 'SKIP':
                # Render skip indicator
                skip_x = x_hex + (8 * self.hex_byte_w)
                self.svg_parts.append(f'<text x="{skip_x}" y="{y}" class="hex-skip" text-anchor="middle">⋮ ⋮ ⋮</text>')
                y += 12
            else:
                row_idx = row_item
                offset = row_idx * self.hex_cols
                
                if offset >= len(raw_data):
                    continue
                
                # Offset column
                self.svg_parts.append(f'<text x="{x_offset}" y="{y}" class="hex-offset">{offset:04X}:</text>')
                
                # Hex bytes
                chunk = raw_data[offset:offset + self.hex_cols]
                hex_parts = []
                ascii_parts = []
                
                for col_idx, byte in enumerate(chunk):
                    abs_idx = offset + col_idx
                    
                    # Find field color for this byte
                    byte_color = self.COLORS['text_dim']
                    for f_idx, field in enumerate(fields):
                        if field.get('start') is not None:
                            if field['start'] <= abs_idx < field['end']:
                                byte_color = self._get_field_color(f_idx)
                                break
                    
                    bx = x_hex + (col_idx * self.hex_byte_w)
                    # Add gap between 8th and 9th byte
                    if col_idx >= 8:
                        bx += 10
                    
                    hex_parts.append(f'<text x="{bx}" y="{y}" class="hex-byte" fill="{byte_color}">{byte:02X}</text>')
                    
                    ax = x_ascii + (col_idx * self.ascii_byte_w)
                    char = chr(byte) if 32 <= byte < 127 else '·'
                    char = self._escape(char)
                    ascii_parts.append(f'<text x="{ax}" y="{y}" class="hex-ascii" fill="{byte_color}">{char}</text>')
                    
                    byte_row_map[abs_idx] = y
                
                self.svg_parts.extend(hex_parts)
                self.svg_parts.extend(ascii_parts)
                
                y += self.hex_row_h
        
        return y, byte_row_map
    
    def _render_field_table(self, fields: List[Dict], raw_data: bytes, 
                           byte_row_map: Dict[int, int], x_start: int, y_start: int) -> int:
        """
        Render the field annotation table with raw/decoded comparison.
        Returns end_y position.
        """
        # Column headers - aligned with hex dump header style
        col_name_x = x_start + 15
        col_raw_x = col_name_x + 180
        col_val_x = col_raw_x + 200
        
        # Section header - "STRUCTURE" on its own line (matching HEX DUMP style)
        self.svg_parts.append(f'''
        <text x="{x_start}" y="{y_start}" class="section-header">STRUCTURE</text>
        ''')
        
        # Table header row on next line
        header_y = y_start + 18
        self.svg_parts.append(f'''
        <text x="{col_name_x}" y="{header_y}" class="field-label">Field</text>
        <text x="{col_raw_x}" y="{header_y}" class="field-label">Raw Bytes</text>
        <text x="{col_val_x}" y="{header_y}" class="field-label">Decoded Value</text>
        <line x1="{x_start}" y1="{header_y + 6}" x2="{self.width - self.margin_x}" y2="{header_y + 6}" class="divider"/>
        ''')
        
        y = header_y + 22
        connector_x = x_start - 10
        
        for f_idx, field in enumerate(fields):
            field_color = self._get_field_color(f_idx)
            name = field['name'].split('.')[-1]
            depth = field['name'].count('.')
            
            # Skip internal fields
            if name.startswith('_') or name in ('offset1', 'offset2', 'length'):
                continue
            
            # Indent based on depth
            indent = depth * 15
            
            # Field name with color marker
            self.svg_parts.append(f'''
            <rect x="{col_name_x + indent - 8}" y="{y - 10}" width="4" height="12" 
                  fill="{field_color}" rx="1"/>
            <text x="{col_name_x + indent}" y="{y}" class="field-name" fill="{field_color}">
                {self._escape(name)}
            </text>
            ''')
            
            # Get raw bytes from either stored raw_data or by slicing raw_data
            raw_bytes = field.get('raw_data')
            value = field.get('value')
            start = field.get('start')
            end = field.get('end')
            
            # Extract raw bytes from the actual data if not provided
            if raw_bytes is None and start is not None and end is not None:
                raw_bytes = raw_data[start:end]
            
            # Format and display raw bytes
            if raw_bytes and len(raw_bytes) <= 32:
                raw_str = format_raw_hex(raw_bytes, max_bytes=12)
                self.svg_parts.append(f'''
                <text x="{col_raw_x}" y="{y}" class="field-raw">{self._escape(raw_str)}</text>
                ''')
            elif raw_bytes:
                self.svg_parts.append(f'''
                <text x="{col_raw_x}" y="{y}" class="field-raw">[{len(raw_bytes)} bytes]</text>
                ''')
            
            # Decoded value
            if value is not None:
                val_type = detect_value_type(value, raw_bytes)
                val_str = format_decoded_value(value, val_type)
                
                # Highlight if raw != decoded (transformation detected)
                is_transformed = is_data_different(raw_bytes, value)
                val_class = "field-value-highlight" if is_transformed else "field-value"
                
                self.svg_parts.append(f'''
                <text x="{col_val_x}" y="{y}" class="{val_class}">{self._escape(val_str)}</text>
                ''')
                
                # Add transformation indicator
                if is_transformed:
                    self.svg_parts.append(f'''
                    <text x="{col_val_x - 15}" y="{y}" class="annotation" fill="{self.COLORS['warning']}">⚡</text>
                    ''')
            
            # Draw connector from hex dump to field
            if start is not None and byte_row_map:
                # Find the Y position for start byte
                hex_y = None
                for byte_idx in range(start, min(start + 16, end if end else start + 1)):
                    if byte_idx in byte_row_map:
                        if hex_y is None:
                            hex_y = byte_row_map[byte_idx]
                        break
                
                if hex_y is not None:
                    # Find end Y position
                    end_y_pos = hex_y
                    if end is not None:
                        for byte_idx in range(end - 1, start - 1, -1):
                            if byte_idx in byte_row_map:
                                end_y_pos = byte_row_map[byte_idx]
                                break
                    
                    mid_hex_y = (hex_y + end_y_pos) / 2
                    
                    # Bracket on hex side
                    bracket_x = connector_x - 80
                    self.svg_parts.append(f'''
                    <path d="M {bracket_x} {hex_y - 5} L {bracket_x + 5} {hex_y - 5} 
                             L {bracket_x + 5} {end_y_pos - 5} L {bracket_x} {end_y_pos - 5}" 
                          stroke="{field_color}" fill="none" class="bracket"/>
                    ''')
                    
                    # Bezier curve connector
                    cx1 = bracket_x + 40
                    cx2 = connector_x - 40
                    path = f"M {bracket_x + 5} {mid_hex_y - 5} C {cx1} {mid_hex_y - 5}, {cx2} {y - 5}, {connector_x} {y - 5}"
                    self.svg_parts.append(f'''
                    <path d="{path}" stroke="{field_color}" class="connector"/>
                    <circle cx="{connector_x}" cy="{y - 5}" r="3" fill="{field_color}"/>
                    ''')
            
            y += self.field_row_h
        
        return y
    
    def _add_footer(self, y_pos: int, raw_data: bytes, fields: List[Dict]):
        """Add footer with summary information"""
        self.svg_parts.append(f'''
        <line x1="{self.margin_x}" y1="{y_pos}" x2="{self.width - self.margin_x}" y2="{y_pos}" 
              stroke="{self.COLORS['text_muted']}" stroke-width="1"/>
        ''')
        
        # Statistics
        footer_y = y_pos + 25
        field_count = len([f for f in fields if f.get('start') is not None])
        
        self.svg_parts.append(f'''
        <text x="{self.margin_x}" y="{footer_y}" class="annotation">
            Binary Structure Visualization · Total: {len(raw_data):,} bytes · {field_count} mapped fields
        </text>
        <text x="{self.width - self.margin_x}" y="{footer_y}" text-anchor="end" class="annotation">
            pics.corkami.com style · BinTV
        </text>
        ''')
        
        return footer_y + 30
    
    def export(self, flattened_data: List[Dict], raw_data: bytes, 
               title: str = "BINARY_STRUCTURE") -> str:
        """
        Generate the complete SVG visualization.
        
        Args:
            flattened_data: List of field dictionaries with name, start, end, value, raw_data
            raw_data: Complete binary data
            title: Title for the visualization
            
        Returns:
            SVG string
        """
        self.svg_parts = []
        
        # Filter out internal fields
        excluded = {'offset1', 'offset2', 'length', '_io', 'subcon'}
        fields = [f for f in flattened_data 
                  if not any(ex in f['name'] for ex in excluded) 
                  and not f['name'].split('.')[-1].startswith('_')]
        
        # Calculate dimensions
        sparse_rows = self._get_sparse_rows(raw_data, fields)
        hex_rows = sum(1 for r in sparse_rows if r != 'SKIP')
        skip_rows = sum(1 for r in sparse_rows if r == 'SKIP')
        
        # Account for header rows in hex section (section header + column headers + divider)
        hex_header_height = 45  # Section header + column headers + spacing
        hex_content_height = (hex_rows * self.hex_row_h) + (skip_rows * 14)
        hex_height = hex_header_height + hex_content_height
        
        # Field table height
        field_header_height = 45  # Same as hex for alignment
        field_content_height = len(fields) * self.field_row_h
        field_height = field_header_height + field_content_height
        
        content_height = max(hex_height, field_height)
        
        # Total height: header (95) + content + footer (60)
        total_height = self.margin_y + content_height + 80
        
        # Start SVG
        self.svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" 
             width="{self.width}" height="{total_height}" 
             viewBox="0 0 {self.width} {total_height}">''')
        
        self._add_defs()
        
        # Background
        self.svg_parts.append(f'<rect width="100%" height="100%" class="bg"/>')
        
        # Header
        self._add_header(title, len(raw_data), len(fields))
        
        # Calculate x position for structure table based on hex dump width
        # Hex dump: offset(55) + hex bytes(16*24 + 12 gap) + ascii(16*10) + padding
        hex_width = 55 + (16 * self.hex_byte_w) + 12 + 20 + (16 * self.ascii_byte_w) + 40
        table_x = self.margin_x + hex_width
        
        # Hex dump (left side)
        hex_end_y, byte_map = self._render_hex_dump(raw_data, fields, self.margin_y)
        
        # Field table (right side)
        field_end_y = self._render_field_table(fields, raw_data, byte_map, table_x, self.margin_y)
        
        # Footer
        footer_y = max(hex_end_y, field_end_y) + 30
        final_y = self._add_footer(footer_y, raw_data, fields)
        
        # Close SVG
        self.svg_parts.append('</svg>')
        
        return '\n'.join(self.svg_parts)
    
    def _get_sparse_rows(self, raw_data: bytes, fields: List[Dict]) -> List:
        """Calculate which rows to render (sparse view)"""
        interesting_rows = set([0, (len(raw_data) - 1) // self.hex_cols])
        
        for field in fields:
            if field.get('start') is not None:
                start_row = field['start'] // self.hex_cols
                end_row = (field['end'] - 1) // self.hex_cols
                interesting_rows.add(start_row)
                interesting_rows.add(end_row)
        
        sorted_rows = sorted(list(interesting_rows))
        result = []
        
        if sorted_rows:
            prev = sorted_rows[0]
            result.append(prev)
            for r in sorted_rows[1:]:
                if r > prev + 1:
                    result.append('SKIP')
                if r != prev:
                    result.append(r)
                prev = r
        
        return result


# Backward-compatible function interface
def create_svg_v2(flattened_data: List[Dict], raw_data: bytes, 
                  title: str = "BINARY_STRUCTURE", width: int = 1600) -> str:
    """
    Generate Corkami-style SVG visualization.
    
    Drop-in replacement for create_svg with enhanced visualization.
    """
    exporter = CorkamistyleSVGExporter(width=width)
    return exporter.export(flattened_data, raw_data, title)


# Alternative export with more options
def create_poster_svg(flattened_data: List[Dict], raw_data: bytes,
                      title: str = "BINARY_STRUCTURE",
                      width: int = 1600,
                      show_raw: bool = True,
                      show_decoded: bool = True,
                      highlight_transforms: bool = True) -> str:
    """
    Create a poster-style SVG with configurable options.
    
    Args:
        flattened_data: Field data from construct parsing
        raw_data: Binary file contents
        title: Poster title
        width: SVG width in pixels
        show_raw: Show raw hex values column
        show_decoded: Show decoded values column
        highlight_transforms: Highlight fields where raw != decoded
    """
    exporter = CorkamistyleSVGExporter(width=width)
    return exporter.export(flattened_data, raw_data, title)

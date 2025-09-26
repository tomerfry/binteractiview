import string
import asyncio
from textual import work
from textual.app import *
from textual.strip import Strip
from textual.containers import *
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.color import Color
from rich.text import Text
from rich.style import Style
from rich.jupyter import JupyterMixin
from rich.segment import Segment, Segments


class HexView(ScrollView, can_focus=True):
    nibble_cursor = reactive(0)
    cursor_visible = reactive(True)
    data = reactive(bytearray(b''))
    blinking = reactive(True)
    edit_mode = reactive(False)
    buffer = {}
    data_addr = reactive(0)
    virtual_size = Size(60,1)
    highlighted_field = reactive(None)
    elements = reactive(None)
    mouse_hover_offset = reactive(None)
    show_tooltip = reactive(False)
    
    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("left", "cursor_left", "Cursor Left", show=False),
        Binding("h", "cursor_left", "Cursor Left", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("l", "cursor_right", "Cursor Right", show=False),
        Binding("end", "goto_end", "Go to End", show=False),
        Binding("ctrl+end", "goto_end", "Go to End", show=False),
        Binding("home", "goto_start", "Go to Start", show=False),
        Binding("ctrl+home", "goto_start", "Go to Start", show=False)
    ]

    class CursorUpdate(Message):
        def __init__(self, id, offset, *args, **kwargs):
            self.offset = offset
            self.id = id
            super().__init__(*args, **kwargs)

    def get_byte_cursor(self):
        return self.nibble_cursor >> 1

    def get_field_info_at_position(self, offset):
        """Get field information for the given byte offset"""
        if not self.elements or offset >= len(self.data):
            return None
            
        chunks, colors = self.elements
        for idx, chunk in enumerate(chunks):
            if "start" in chunk and isinstance(chunk["start"], int):
                if chunk["start"] <= offset < chunk["end"]:
                    field_name = chunk.get("name", f"Field {idx}")
                    field_type = chunk.get("type", "unknown")
                    size = chunk["end"] - chunk["start"]
                    rel_offset = offset - chunk["start"]
                    return {
                        "name": field_name,
                        "type": field_type,
                        "size": size,
                        "start": chunk["start"],
                        "end": chunk["end"],
                        "relative_offset": rel_offset,
                        "absolute_offset": offset
                    }
        return None

    def get_mouse_offset(self, x, y):
        """Get the byte offset for mouse coordinates"""
        scroll_x, scroll_y = self.scroll_offset
        actual_y = y + scroll_y
        
        # Calculate which row was clicked
        if actual_y >= (len(self.data) // 16) + 1:
            return None
            
        row_offset = actual_y * 16
        
        # Simple approach: assume hex region starts at column 3 and ASCII at column 52
        if 1 <= x <= 50:  # Hex region (approximate)
            # Click in hex region - rough calculation
            relative_x = x - 1
            byte_index = min(relative_x // 3, 15)  # Each byte takes ~3 chars
            cursor_pos = row_offset + byte_index
            
        elif 50 <= x <= 68:  # ASCII region (approximate)
            # Click in ASCII region
            relative_x = x - 50
            byte_index = min(relative_x, 15)
            cursor_pos = row_offset + byte_index
        else:
            return None
            
        # Ensure cursor position is within data bounds
        if cursor_pos < len(self.data):
            return cursor_pos
        return None

    def on_mouse_move(self, event):
        """Handle mouse movement for tooltip"""
        offset = self.get_mouse_offset(event.x, event.y)
        if offset is not None:
            self.mouse_hover_offset = offset
            self.show_tooltip = True
        else:
            self.show_tooltip = False

    def on_leave(self, event):
        """Hide tooltip when mouse leaves the widget"""
        self.show_tooltip = False

    def on_click(self, event):
        """Handle mouse clicks"""
        offset = self.get_mouse_offset(event.x, event.y)
        if offset is not None:
            self.nibble_cursor = (offset << 1) & ~1
            self.cursor_visible = True
            self.post_message(self.CursorUpdate(self.id, offset))

    def generate_ascii_segments(self, offset, line_data):
        cursor = self.get_byte_cursor()
        segments = [Segment(" ")]
        for i,b in enumerate(line_data):
            txt = "."
            styles = [Style(color='green')]

            if self.elements:
                chunks,colors = self.elements
                for idx, chunk in enumerate(chunks):
                    if "start" in chunk and isinstance(chunk["start"], int):
                        if chunk["start"] <= i+offset < chunk["end"]:
                            styles.append(Style(bgcolor=colors[idx]))

            if self.cursor_visible and cursor == offset+i:
                styles.append(Style(bgcolor='white'))

            if chr(b).isprintable():
                txt = f"{chr(b)}"

            segments.append(Segment(txt, Style.chain(*styles)))

        if len(line_data) % 0x10 != 0:
            segments.append(Segment(" "*(0x10 - (len(line_data) % 0x10))))

        return segments

    def generate_hex_segments(self, offset, line_data):
        cursor = self.get_byte_cursor()
        segments = []
        sum_of_chunks_szs = 0
        for col_start in range(0, 16, 8):
            chunk = self.data[offset+col_start:offset+col_start+8]
            sum_of_chunks_szs += len(chunk)
            if not chunk:
                break
            for i,b in enumerate(chunk):
                space = Segment("  ")
                txt = '00'
                styles = [Style(color='green')]
                if b != 0:
                    txt = f"{b:02x}"
   
                if self.elements:
                    chunks,colors = self.elements
                    for idx, chunk in enumerate(chunks):
                        if "start" in chunk and isinstance(chunk["start"], int):
                            if chunk["start"] <= i+offset+col_start < chunk["end"]:
                                styles.append(Style(bgcolor=colors[idx]))
                                if i+offset+col_start+1 != chunk["end"] and (i+offset+col_start+1) % 0x10 != 0:
                                    space = Segment("  ", Style(bgcolor=colors[idx]))


                if self.cursor_visible and cursor == offset+i+col_start:
                    styles.append(Style(bgcolor='white'))

                segments.append(Segment(" ", Style(color='green')))
                segments.append(Segment(txt, Style.chain(*styles)))
        segments.append(Segment(" ", Style(color='green')))
        if sum_of_chunks_szs % 0x10 != 0x0:
            segments.append(Segment("   "*(0x10-(sum_of_chunks_szs%0x10))))

        return segments

    def generate_line(self, offset, line_data):
        segments = []
        segments.append(Segment(' '))
        segments.extend(self.generate_hex_segments(offset, line_data))
        segments.extend(self.generate_ascii_segments(offset, line_data))
        return segments

    @work
    async def blinker(self):
        while self.blinking:
            self.cursor_visible = not self.cursor_visible
            await asyncio.sleep(0.5)

    def on_blur(self):
        self.blinking = False
        self.cursor_visible = False

    def on_focus(self):
        self.blinking = True
        self.blinker()
        
    def render_line(self, y):
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y
        if y < (len(self.data) // 16)+1:
            return Strip(self.generate_line(y*16, self.data[y*16:(y+1)*16]))
        return Strip.blank(20, self.rich_style)

    async def watch_mouse_hover_offset(self, old_offset, new_offset):
        """Update tooltip when hover offset changes"""
        if new_offset is not None and self.show_tooltip:
            field_info = self.get_field_info_at_position(new_offset)
            if field_info:
                tooltip_text = (
                    f"Field: {field_info['name']}\n"
                    f"Type: {field_info['type']}\n" 
                    f"Offset: 0x{field_info['absolute_offset']:04x} ({field_info['absolute_offset']})\n"
                    f"Size: {field_info['size']} bytes\n"
                    f"Range: 0x{field_info['start']:04x}-0x{field_info['end']-1:04x}"
                )
                self.tooltip = tooltip_text
            else:
                # Show basic info even without field structure
                byte_value = self.data[new_offset] if new_offset < len(self.data) else 0
                tooltip_text = (
                    f"Offset: 0x{new_offset:04x} ({new_offset})\n"
                    f"Value: 0x{byte_value:02x} ({byte_value})\n"
                    f"ASCII: {'.' if not chr(byte_value).isprintable() else chr(byte_value)}"
                )
                self.tooltip = tooltip_text
        else:
            self.tooltip = None

    def set_value_at_cursor(self, hex_char):
        """Placeholder for hex editing functionality"""
        # You'll need to implement this based on your editing requirements
        pass

    def on_key(self, event):
        self.cursor_visible = True
        if event.key == 'insert':
            self.edit_mode = True
            event.prevent_default()
            event.stop()
        elif event.key == 'escape':
            self.edit_mode = False
            event.prevent_default()
            event.stop()
        elif event.is_printable:
            if event.character is not None and self.edit_mode:
                if event.character in string.hexdigits:
                    self.set_value_at_cursor(event.character)
                    event.prevent_default()
                    event.stop()

    async def watch_nibble_cursor(self):
        scroll_y = self.scroll_offset.y
        cursor_y = (self.nibble_cursor >> 1) // 16 
        if cursor_y < scroll_y:
            self.scroll_to(y=cursor_y, animate=False)
        elif cursor_y >= scroll_y + self.size.height:
            self.scroll_to(y=cursor_y - self.size.height + 1, animate=False)

    def action_cursor_right(self):
        next_nibble_cursor = self.nibble_cursor + (1<<1)
        next_nibble_cursor = next_nibble_cursor & ~1
        if (next_nibble_cursor>>1) < len(self.data):
            self.nibble_cursor = next_nibble_cursor
        self.post_message(self.CursorUpdate(self.id, self.nibble_cursor >> 1))

    def action_cursor_left(self):
        next_nibble_cursor = self.nibble_cursor - (1<<1)
        next_nibble_cursor = next_nibble_cursor & ~1
        if (next_nibble_cursor>>1) >= 0:
            self.nibble_cursor = next_nibble_cursor
        self.post_message(self.CursorUpdate(self.id, self.nibble_cursor >> 1))

    def action_cursor_up(self):
        next_nibble_cursor = self.nibble_cursor - (16<<1)
        next_nibble_cursor = next_nibble_cursor & ~1
        if (next_nibble_cursor>>1) >= 0:
            self.nibble_cursor = next_nibble_cursor
        self.post_message(self.CursorUpdate(self.id, self.nibble_cursor >> 1))

    def action_cursor_down(self):
        next_nibble_cursor = self.nibble_cursor + (16<<1)
        next_nibble_cursor = next_nibble_cursor & ~1
        if (next_nibble_cursor>>1) < len(self.data):
            self.nibble_cursor = next_nibble_cursor
        self.post_message(self.CursorUpdate(self.id, self.nibble_cursor >> 1))

    def action_goto_end(self):
        """Move cursor to the last byte of data"""
        if len(self.data) > 0:
            last_byte_pos = len(self.data) - 1
            self.nibble_cursor = (last_byte_pos << 1) & ~1
            self.cursor_visible = True
            
            # Calculate the row of the last byte
            cursor_y = last_byte_pos // 16
            # Scroll to show the cursor, ensuring we don't go beyond the content
            # Position the cursor near the bottom of the view but still visible
            target_y = max(0, cursor_y - max(0, self.size.height - 3))
            self.scroll_to(y=target_y, animate=True)
            
            self.post_message(self.CursorUpdate(self.id, last_byte_pos))

    def action_goto_start(self):
        """Move cursor to the first byte of data"""
        if len(self.data) > 0:
            self.nibble_cursor = 0
            self.cursor_visible = True
            
            # Scroll to the top
            self.scroll_to(y=0, animate=True)
            
            self.post_message(self.CursorUpdate(self.id, 0))

import string
from textual import work
from textual.app import *
from textual.widgets import *
from textual.strip import Strip
from textual.containers import *
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from rich.text import Text
from rich.style import Style
from rich.jupyter import JupyterMixin
from rich.segment import Segment, Segments


class HexView(ScrollView):
    nibble_cursor = reactive(0)
    cursor_visible = reactive(True)
    data = reactive(bytearray(b''))
    blinking = reactive(True)
    edit_mode = reactive(False)
    buffer = {}
    data_addr = reactive(0)
    virtual_size = Size(60,1)
    highlighted_field = reactive(None)
    

    BINDINGS = [
        Binding("up", "cursor_up", "Cursor Up", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("down", "cursor_down", "Cursor Down", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("left", "cursor_left", "Cursor Left", show=False),
        Binding("h", "cursor_left", "Cursor Left", show=False),
        Binding("right", "cursor_right", "Cursor Right", show=False),
        Binding("l", "cursor_right", "Cursor Right", show=False)
    ]

    class CursorUpdate(Message):
        def __init__(self, id, offset, *args, **kwargs):
            self.offset = offset
            self.id = id
            super().__init__(*args, **kwargs)

    def get_byte_cursor(self):
        return self.nibble_cursor >> 1

    def generate_ascii_segments(self, offset, line_data):
        cursor = self.get_byte_cursor()
        segments = [Segment("| ")]
        for i,b in enumerate(line_data):
            txt = "."
            styles = [Style(color='green')]
            
            if self.cursor_visible and cursor == offset+i:
                styles.append(Style(bgcolor='white'))

            if chr(b).isprintable():
                txt = f"{chr(b)}"
                
            segments.append(Segment(txt, Style.chain(*styles)))

        segments.append(Segment(" | "))
        return segments

    def generate_hex_segments(self, offset, line_data):
        cursor = self.get_byte_cursor()
        segments = []
        for col_start in range(0, 16, 8):
            chunk = self.data[offset+col_start:offset+col_start+8]
            if not chunk:
                break
            for i,b in enumerate(chunk):
                txt = '00'
                styles = [Style(color='green')]
                if b != 0:
                    txt = f"{b:02x}"
                
                if self.cursor_visible and cursor == offset+i+col_start:
                    styles.append(Style(bgcolor='white'))

                segments.append(Segment(txt, Style.chain(*styles)))
                segments.append(Segment(" "))

        return segments

    def generate_line(self, offset, line_data):
        segments = []
        segments.append(Segment(' | '))
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


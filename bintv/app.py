from bintv.svg_exporter import *
from bintv.widgets.hex_view import *
from bintv.widgets.reactive_construct_tree import *
from bintv.neon_pallete import *

from textual.app import App
from textual.geometry import Size 
from textual.containers import Grid, Vertical, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Placeholder, DirectoryTree, TextArea, TabbedContent, TabPane, Log, Static, Button, Label

import io
import os
import re
import json
import struct as struct_module
import construct
from construct import *
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor

PY_LANGUAGE = Language(tspython.language())

RAWCOPY_MAPPER_QUERY = b'(binary_operator operator: "/" (_) @primitives)'


class ConfirmExitScreen(ModalScreen):
    """Modal screen to confirm saving changes before exit."""
    
    BINDINGS = [("escape", "dismiss", "Close")]
    
    CSS = """
    ConfirmExitScreen {
        align: center middle;
    }
    
    #confirm-dialog {
        width: 60;
        height: auto;
        border: thick $error 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #confirm-dialog Label {
        margin: 1 0;
    }
    
    #confirm-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    #confirm-buttons Button {
        margin: 0 1;
    }
    """
    
    class ExitChoice(Exception):
        """Custom exception to carry exit choice."""
        def __init__(self, choice: str):
            self.choice = choice
            super().__init__()
    
    def __init__(self, has_unsaved_changes: bool):
        super().__init__()
        self.has_unsaved_changes = has_unsaved_changes
  
    def compose(self):
        with Grid(id="confirm-dialog"):
            yield Label("You have unsaved changes.\nDo you want to save before quitting?")

            with Horizontal(id="confirm-buttons"):
                # These IDs match the on_button_pressed handler you wrote
                yield Button("Save & Exit", variant="primary", id="save-exit")
                yield Button("Discard & Exit", variant="error", id="no-save-exit")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-exit":
            self.dismiss("save")
        elif event.button.id == "no-save-exit":
            self.dismiss("exit")
        elif event.button.id == "cancel":
            self.dismiss("cancel")


class AlignmentScreen(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]
    
    def __init__(self, targets, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.targets = targets

    def compose(self):
        with Horizontal():
            for target in self.targets:
                yield Static("asdfasddf")

PRIMITIVES = dir(construct)
PRIMITIVES.sort(key=lambda x: len(x), reverse=True)

class BintvApp(App):
    DEFAULT_CSS = '''
    Screen {
        layers: below above log;
        align: center middle;
    }

    #construct-editor {
        layer: below;
        height: 50%;
        min-width: 25%;
    }
    
    #construct-tree {
        layer: below;
        height: 50%;
        min-width: 25%;
    }
    
    #hex-view {
        layer: below;
        height: 100%;
        min-width: 75%;
    }

    #hex-view-bottom-line {
        layer: below;
        height: 1;
        min-width: 75%;
    }

    #file-chooser {
        layer: above;
        width: 50%;
        height: 50%;
        border: tall blue;
    }

    #log-panel {
        layer: log;
        width: 50%;
        height: 50%;
        border: solid $primary;
        background: $panel;
        visibility: hidden;
    }
    '''
    BINDINGS = [
        ("ctrl+o", "load_binary", "Load binary file"), 
        ("ctrl+t", "align", "Align multiple files"), 
        ("ctrl+e", "export", "Export SVG from Content"), 
        ("ctrl+l", "toggle_log", "Toggle Log Panel"), 
        ("ctrl+q", "quit", "Quit application")
    ]

    def __init__(self, target):
        super().__init__()
        self.data = bytearray(b"")
        self.original_data = bytearray(b"")  # Store original data for comparison
        self.target = target
        self.offset = 0
        self.pane_count = 0
        self.has_unsaved_changes = False
        self.modified_fields = {}  # Track which fields have been modified

    def action_load_binary(self):
        if not self.query_one("#file-chooser").visible:
            self.query_one("#file-chooser").visible = True            
            self.set_focus(self.query_one("#file-chooser"))
        else:
            self.query_one("#file-chooser").visible = False 

    def action_align(self):
        self.push_screen(AlignmentScreen(targets=['a', 'b']))

    def action_export(self):
        if self._flattened_construct_data and self.data:
            filename = f"binteractiview_{self.target.replace('.', '').replace('/', '')}.svg"
            with open(filename, "w") as f:
                f.write(create_svg(self._flattened_construct_data, self.data, title=f"{self.target.split('.')[-2].replace('/', '')}"))
            self.log_message(f"Exported to {filename}")

    def action_toggle_log(self):
        if not self.query_one("#log-panel").visible:
            self.query_one("#log-panel").visible = True
            self.set_focus(self.query_one("#log-panel"))
        else:
            self.query_one("#log-panel").visible = False

    def action_quit(self):
        """Handle quit action with save confirmation."""
        async def handle_exit_choice(choice: str) -> None:
            if choice == "save":
                # Save the modified file
                if self.save_modified_file():
                    self.exit()
            elif choice == "exit":
                # Exit without saving
                self.exit()
            # If "cancel", do nothing
        
        # Show confirmation dialog
        confirm_screen = ConfirmExitScreen(self.has_unsaved_changes)
        self.push_screen(confirm_screen, handle_exit_choice)

    def save_modified_file(self) -> bool:
        """Save the modified binary data to /tmp directory."""
        try:
            # Generate filename based on original file
            base_name = os.path.basename(self.target)
            name, ext = os.path.splitext(base_name)
            output_path = f"/tmp/{name}_modified{ext}"
            
            # Write the modified data
            with open(output_path, "wb") as f:
                f.write(self.data)
            
            self.log_message(f"✅ Saved modified file to: {output_path}", level="info")
            return True
        except Exception as e:
            self.log_message(f"❌ Error saving file: {str(e)}", level="error")
            return False

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to the log view."""
        try:
            log = self.query_one("#log-panel", Log)
            
            # Add color coding based on level
            if level == "error":
                formatted_message = f"[red]ERROR: {message}[/]"
            elif level == "warning":
                formatted_message = f"[yellow]WARN: {message}[/]"
            else:
                formatted_message = f"[green]INFO: {message}[/]"
            
            log.write_line(formatted_message)
        except Exception:
            # If log panel doesn't exist yet, just pass
            pass

    def compose(self):
        with Horizontal():
            with Vertical():
                yield TextArea(id="construct-editor", text="Struct(\"content\" / GreedyBytes)")
                
                # FIX: Added "Struct Data" label here
                yield ReactiveConstructTree("Struct Data", id="construct-tree")
                
            with Vertical():
                with TabbedContent(id="tabbed-content"):
                    if self.target:
                        yield TabPane(f"HexPane-{self.pane_count}", id=f"hex-pane-{self.pane_count}")
        yield Log(id="log-panel", auto_scroll=True, highlight=True)
        yield DirectoryTree("./", id="file-chooser")

    def flatten_construct_offsets(self, parent_prefix=""):
        result = []
        def process_item(name, value, parent_prefix=""):
            full_name = f"{parent_prefix}.{name}" if parent_prefix else name
            if hasattr(value, "offset1") and hasattr(value, "offset2"):
                result.append({
                    "name": full_name,
                    "start": value.offset1,
                    "end": value.offset2,
                    "length": value.length,
                    "value": value.value,
                    "raw_data": value.data if hasattr(value, "data") else None
                })

                if isinstance(value.value, (dict, Container)):
                    for sub_name, sub_value in value.items():
                        process_item(sub_name, sub_value, full_name)

            elif isinstance(value, (dict, Container)):
                for sub_name, sub_value in value.items():
                    process_item(sub_name, sub_value, full_name)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    process_item(f"[{i}]", item, full_name)
            else:
                result.append({
                    "name": full_name,
                    "start": None,
                    "end": None,
                    "length": None,
                    "value": value,
                    "raw_data": None
                })

        if isinstance(self._parsed_data, (dict, Container)):
            for name, value in self._parsed_data.items():
                process_item(name, value, parent_prefix)
        else:
            process("root", self._parsed_data, parent_prefix)

        return result

    def _on_mount(self):
        self.log_message("Application Started!")
        self.set_focus(self.query_one("#file-chooser"))
        self.query_one("#construct-editor").language = "python"
        if self.target:
            self.on_directory_tree_file_selected(DirectoryTree.FileSelected(None, self.target), inc_count=False)
        self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))

    def eval_with_ts(self, text):
        text_bytes = bytes(text, 'utf-8')
        tree = Parser(PY_LANGUAGE).parse(text_bytes)
        qc = QueryCursor(Query(PY_LANGUAGE, RAWCOPY_MAPPER_QUERY))
        caps = set([cap.text for cap in qc.captures(tree.root_node)['primitives']])
        self.log_message(f"Captured primitives: {caps}")

        new_pattern = b'RawCopy(' + text_bytes[:] + b')'
        for cap in caps:
            new_pattern = new_pattern.replace(cap, b'RawCopy(' + cap + b')')
        return eval(new_pattern)

    def on_text_area_changed(self, msg):
        try:
            self._subcons_text = msg.text_area.text
            self._construct = self.eval_with_ts(self._subcons_text)
            self._parsed_data = self._construct.parse(self.data)
            self.query_one("#construct-tree").parsed_data = self._parsed_data
            self._flattened_construct_data = self.flatten_construct_offsets()
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").elements = (self._flattened_construct_data, neon_background_colors(len(self._flattened_construct_data)))
            self.log_message(f"Successfully parsed {len(self._flattened_construct_data)} fields")
        except Exception as e:
            self.log_message(f"Parse error: {str(e)}", level="error")

    def on_tabbed_content_tab_activated(self, msg):
        try:
            self.data = self.query_one(f"#{msg.pane.id}-hex-view").data
            self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
        except Exception as e:
            pass

    def on_directory_tree_file_selected(self, msg, inc_count=True):
        if inc_count:
            self.pane_count += 1
            self.query_one("#tabbed-content").add_pane(TabPane(f"HexPane-{self.pane_count}", id=f"hex-pane-{self.pane_count}"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(HexView(id=f"hex-pane-{self.pane_count}-hex-view"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(Static(hex(0x0), id=f"hex-pane-{self.pane_count}-hex-view-bottom-line"))
        self.set_focus(self.query_one(f"#hex-pane-{self.pane_count}-hex-view"))
        self.target = msg.path
        with open(msg.path, "rb") as f:
            self.data = bytearray(f.read())
            self.original_data = bytearray(self.data)  # Keep original copy
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = self.data
   
        self.query_one(f"#hex-pane-{self.pane_count}-hex-view").virtual_size = Size(60, len(self.data) // 60)
        self.query_one(f"#hex-pane-{self.pane_count}-hex-view").width = 60
        self.query_one(f"#hex-pane-{self.pane_count}-hex-view").height = len(self.data) // 60

        self.query_one("#file-chooser").visible = False
        self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
        self.on_hex_view_cursor_update(HexView.CursorUpdate(f"hex-pane-{self.pane_count}-hex-view", 0x0))
        
        self.log_message(f"Loaded file: {msg.path} ({len(self.data)} bytes)")

    def on_hex_view_cursor_update(self, msg):
        the_name = "root"

        for item in self._flattened_construct_data:
            name = item["name"]
            start = item["start"]
            end = item["end"]
            if end and name and start <= msg.offset and msg.offset < end:
                the_name = name
        self.query_one(f"#{msg.id}-bottom-line").update(f"{hex(msg.offset)} - Currently on field {the_name}")
        self.query_one(f"#{msg.id}").highlighted_field = (name, start, end)

    def on_reactive_construct_tree_field_edit_request(self, msg: ReactiveConstructTree.FieldEditRequest) -> None:
        """
        Handle the patch request from the tree.
        1. Update the bytearray.
        2. Refresh Hex View.
        3. Re-parse the tree to show new values/offsets.
        """
        try:
            # --- 1. PREPARE DATA ---
            start_offset = msg.offset
            length = msg.length
            
            # Convert the input value (int, string, etc.) to raw bytes
            # We use the helper method _value_to_bytes (see below)
            new_bytes = self._value_to_bytes(msg.value, msg.value_type, length, msg.value)

            # Safety check: Ensure we don't accidentally resize the file 
            # (unless your format supports shifting bytes, but usually we just overwrite)
            if len(new_bytes) != length:
                self.log_message(f"⚠️ Size mismatch! Expected {length} bytes, got {len(new_bytes)}.", level="warning")
                # Optional: Handle resizing if you really want to support it
                # For now, we abort to prevent corruption
                if len(new_bytes) > length:
                    new_bytes = new_bytes[:length]
                else:
                    new_bytes = new_bytes.ljust(length, b'\x00')

            # --- 2. PATCH DATA ---
            # Update the in-memory binary
            self.data[start_offset : start_offset + length] = new_bytes
            
            # Mark as modified for the "Save on Exit" dialog
            self.has_unsaved_changes = True

            # --- 3. UPDATE UI ---
            
            # A. Update Hex View immediately
            current_hex_pane = self.query_one(f"#hex-pane-{self.pane_count}-hex-view")
            current_hex_pane.data = self.data
            
            # B. Re-parse the Construct logic
            # This will refresh the tree values and recalculate all offsets
            # (in case the change affects subsequent fields)
            self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))

            self.log_message(f"✅ Patched {msg.field_name} at 0x{start_offset:X}", level="info")

        except Exception as e:
            self.log_message(f"❌ Failed to patch: {e}", level="error")

    def _value_to_bytes(self, value, value_type: str, expected_size: int, original_value) -> bytes:
        """Helper to pack values back into bytes."""
        import struct
        
        try:
            if isinstance(value, bytes):
                return value
                
            if value_type in ["byte", "int", "word", "dword"]:
                # Simple packing heuristics. 
                # Ideally, you'd use the Construct object itself to build, 
                # but for raw patching, struct packing is faster and often sufficient.
                
                is_signed = expected_size in [1, 2, 4, 8] and int(value) < 0
                
                if expected_size == 1:
                    fmt = 'b' if is_signed else 'B'
                elif expected_size == 2:
                    fmt = '<h' if is_signed else '<H' # Assume Little Endian
                elif expected_size == 4:
                    fmt = '<i' if is_signed else '<I'
                elif expected_size == 8:
                    fmt = '<q' if is_signed else '<Q'
                else:
                    # Fallback for weird sizes (e.g. 3 bytes): manual int-to-bytes
                    return int(value).to_bytes(expected_size, byteorder='little', signed=is_signed)
                    
                return struct.pack(fmt, int(value))

            elif value_type == "float":
                if expected_size == 4: return struct.pack('<f', float(value))
                if expected_size == 8: return struct.pack('<d', float(value))

            elif value_type == "str":
                return str(value).encode('utf-8')

            return bytes(value) # Last resort
            
        except Exception as e:
            raise ValueError(f"Conversion failed: {e}")

    def on_reactive_construct_tree_goto_offset_request(self, msg: ReactiveConstructTree.GotoOffsetRequest) -> None:
        """Handle goto offset request from tree."""
        # Set cursor to the specified offset in hex view
        hex_view = self.query_one(f"#hex-pane-{self.pane_count}-hex-view")
        hex_view.nibble_cursor = (msg.offset << 1) & ~1
        hex_view.cursor_visible = True
        
        # Scroll to show the cursor
        cursor_y = msg.offset // 16
        hex_view.scroll_to(y=cursor_y, animate=True)
        
        # Update cursor position display
        hex_view.post_message(HexView.CursorUpdate(hex_view.id, msg.offset))
        
        self.log_message(f"Jumped to offset 0x{msg.offset:04x}")

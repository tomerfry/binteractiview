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
    
    def compose(self) -> ComposeResult:
        message = "You have unsaved changes. Do you want to save them before exiting?" if self.has_unsaved_changes else "Are you sure you want to exit?"
        
        with Vertical(id="confirm-dialog"):
            yield Label(f"[bold yellow]⚠️  Exit Confirmation[/]")
            yield Label(message)
            with Horizontal(id="confirm-buttons"):
                if self.has_unsaved_changes:
                    yield Button("💾 Save & Exit", variant="primary", id="save-exit")
                    yield Button("🚫 Exit Without Saving", variant="error", id="no-save-exit")
                    yield Button("Cancel", variant="default", id="cancel")
                else:
                    yield Button("Yes, Exit", variant="error", id="no-save-exit")
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
                yield ReactiveConstructTree(id="construct-tree")
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

    def on_reactive_construct_tree_edit_value_request(self, msg: ReactiveConstructTree.FieldEditRequest) -> None:
        """Handle field edit request from the tree."""
        def handle_edit_result(edited: bool) -> None:
            if edited:
                # Value was edited, will be handled by on_edit_value_screen_value_edited
                pass
        
        # Show edit dialog
        edit_screen = EditValueScreen(
            field_name=msg.field_name,
            field_path=msg.field_path,
            current_value=msg.value,
            value_type=msg.value_type
        )
        self.push_screen(edit_screen, handle_edit_result)

    def on_edit_value_screen_value_edited(self, msg: EditValueScreen.ValueEdited) -> None:
        """Handle the value edit from EditValueScreen."""
        try:
            # Find the field in flattened data to get offset information
            target_field = None
            for item in self._flattened_construct_data:
                if item["name"] == msg.field_path.lstrip("/"):
                    target_field = item
                    break
            
            if not target_field or target_field["start"] is None:
                self.log_message(f"Cannot edit field without offset information", level="error")
                return
            
            start_offset = target_field["start"]
            end_offset = target_field["end"]
            field_size = end_offset - start_offset
            
            # Convert the new value to bytes based on type
            new_bytes = self._value_to_bytes(msg.new_value, msg.value_type, field_size, msg.old_value)
            
            if len(new_bytes) != field_size:
                self.log_message(
                    f"Size mismatch: new value is {len(new_bytes)} bytes, field is {field_size} bytes",
                    level="error"
                )
                return
            
            # Update the data
            self.data[start_offset:end_offset] = new_bytes
            
            # Update hex view
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = self.data
            
            # Mark as having unsaved changes
            self.has_unsaved_changes = True
            self.modified_fields[msg.field_path] = {
                "old": msg.old_value,
                "new": msg.new_value,
                "offset": start_offset
            }
            
            # Reparse with the updated data
            self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
            
            self.log_message(
                f"✅ Updated {msg.field_path}: {msg.old_value} → {msg.new_value} at offset 0x{start_offset:04x}",
                level="info"
            )
            
        except Exception as e:
            self.log_message(f"Error updating field: {str(e)}", level="error")

    def _value_to_bytes(self, value, value_type: str, expected_size: int, original_value) -> bytes:
        """Convert a value to bytes based on its type."""
        
        if isinstance(value, bytes):
            return value
        
        elif value_type in ["byte", "word", "dword", "int"]:
            # Determine endianness and signedness from original value context
            # For simplicity, we'll try to match the size
            if expected_size == 1:
                # Byte
                if isinstance(original_value, int) and original_value < 0:
                    return struct_module.pack('b', value)
                else:
                    return struct_module.pack('B', value)
            elif expected_size == 2:
                # Word - assume little endian for now
                if isinstance(original_value, int) and original_value < 0:
                    return struct_module.pack('<h', value)
                else:
                    return struct_module.pack('<H', value)
            elif expected_size == 4:
                # Dword - assume little endian
                if isinstance(original_value, int) and original_value < 0:
                    return struct_module.pack('<i', value)
                else:
                    return struct_module.pack('<I', value)
            elif expected_size == 8:
                # Qword - assume little endian
                if isinstance(original_value, int) and original_value < 0:
                    return struct_module.pack('<q', value)
                else:
                    return struct_module.pack('<Q', value)
            else:
                raise ValueError(f"Unsupported integer size: {expected_size}")
        
        elif value_type == "float":
            if expected_size == 4:
                return struct_module.pack('<f', value)
            elif expected_size == 8:
                return struct_module.pack('<d', value)
            else:
                raise ValueError(f"Unsupported float size: {expected_size}")
        
        elif value_type == "str":
            # Convert string to bytes
            encoded = value.encode('utf-8')
            if len(encoded) > expected_size:
                encoded = encoded[:expected_size]
            elif len(encoded) < expected_size:
                # Pad with nulls
                encoded += b'\x00' * (expected_size - len(encoded))
            return encoded
        
        elif value_type == "bool":
            return b'\x01' if value else b'\x00'
        
        else:
            raise ValueError(f"Cannot convert type {value_type} to bytes")

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

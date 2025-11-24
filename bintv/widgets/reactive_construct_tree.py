from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Tree, Label, Input, Button, Static
from textual.widgets.tree import TreeNode
from textual.message import Message
from textual.events import Click, Key
from textual.screen import ModalScreen
from textual.containers import Grid, Horizontal, Vertical
from rich.text import Text
from typing import Dict, Any, Optional
from datetime import datetime
from construct import Container, ListContainer
import struct
import base64

# --- 1. The Dynamic Tooltip Editor ---
class EditValueScreen(ModalScreen):
    """A minimal, tooltip-style popover for quick editing."""

    CSS = """
    EditValueScreen {
        align: left top;
        background: transparent;
    }

    #popover-container {
        width: 40;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 0 1;
        /* box-shadow is not supported in Textual yet */
    }

    .info-label {
        color: $text-muted;
        text-style: italic;
        padding-top: 1;
    }
    
    #value-input {
        width: 100%;
        margin-top: 0;
        margin-bottom: 1;
        border: none;
        background: $surface-lighten-1;
    }
    
    #value-input:focus {
        border: none;
    }
    """

    def __init__(self, x: int, y: int, field_name: str, current_value: any, value_type: str):
        super().__init__()
        self.target_x = x
        self.target_y = y
        self.field_name = field_name
        self.current_value = current_value
        self.value_type = value_type

    def compose(self) -> ComposeResult:
        with Vertical(id="popover-container"):
            # A small label to show what we are editing
            yield Label(f"Edit {self.field_name} ({self.value_type})", classes="info-label")
            
            # The input field
            yield Input(
                value=self._get_initial_text(),
                id="value-input",
                classes="compact"
            )

    def on_mount(self):
        # Position the popover near the cursor/node
        container = self.query_one("#popover-container")
        container.styles.offset = (self.target_x, self.target_y)
        
        # Auto-focus the input so user can type immediately
        self.query_one("#value-input").focus()

    def _get_initial_text(self):
        val = self.current_value
        if val is None:
            return ""
        if isinstance(val, bytes):
            return val.hex(" ")
        if isinstance(val, int):
            return f"0x{val:X}"
        return str(val)

    def on_key(self, event: Key) -> None:
        """Handle special keys for the modal."""
        if event.key == "escape":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._attempt_save()
    
    # Also support clicking outside to cancel
    def on_click(self, event: Click) -> None:
        if event.widget == self:
            self.dismiss(None)

    def _attempt_save(self):
        input_widget = self.query_one("#value-input", Input)
        raw_text = input_widget.value.strip()

        try:
            new_value = self._parse_value(raw_text)
            self.dismiss(new_value)
        except ValueError as e:
            input_widget.styles.background = "#550000" # Visual error feedback
            self.notify(str(e), severity="error")

    def _parse_value(self, text: str):
        if not text: return None
        
        if self.value_type in ["byte", "word", "dword", "int"]:
            text = text.replace("_", "")
            base = 16 if text.lower().startswith("0x") else 10
            return int(text, base)
        elif self.value_type == "bytes":
            clean = text.replace(" ", "").replace(":", "").replace("0x", "")
            return bytes.fromhex(clean)
        elif self.value_type == "bool":
            return text.lower() in ("true", "1", "yes", "on")
        elif self.value_type == "float":
            return float(text)
        return text


# --- 2. The Context Menu Screen ---
class ContextMenu(ModalScreen):
    """A pop-up context menu."""

    CSS = """
    ContextMenu {
        align: left top;
        background: transparent;
    }

    #menu-container {
        width: 30;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 0;
    }
    
    #menu-container Button {
        width: 100%;
        height: auto;
        border: none;
        background: transparent;
        color: $text;
        text-align: left;
        padding-left: 1;
    }
    
    #menu-container Button:hover {
        background: $accent;
        color: $text;
    }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, x: int, y: int, field_data: dict):
        super().__init__()
        self.menu_x = x
        self.menu_y = y
        self.field_data = field_data

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            yield Button("✏️ Edit Value", id="edit-value")
            yield Button("📋 Copy Value", id="copy-value")
            yield Button("🚀 Go to Offset", id="goto-offset")

    def on_mount(self):
        container = self.query_one("#menu-container")
        container.styles.offset = (self.menu_x, self.menu_y)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss((event.button.id, self.field_data))
    
    def on_click(self, event: Click) -> None:
        if event.widget == self:
            self.dismiss(None)


# --- 3. The Reactive Tree Widget ---
class ReactiveConstructTree(Tree):
    """A custom Tree widget that displays Construct parsed data structures."""

    BINDINGS = [
        ("menu", "show_context_menu", "Context Menu"),       
        ("right", "show_context_menu", "Context Menu"),  
    ]

    parsed_data = reactive(None)
    _expanded_paths = set()

    class GotoOffsetRequest(Message):
        def __init__(self, offset: int):
            self.offset = offset
            super().__init__()

    class FieldEditRequest(Message):
        def __init__(self, field_path: str, field_name: str, value: Any, value_type: str, offset: int, length: int):
            self.field_path = field_path
            self.field_name = field_name
            self.value = value
            self.value_type = value_type
            self.offset = offset
            self.length = length
            super().__init__()

    def _log(self, message: str, level: str = "info"):
        if hasattr(self.app, "log_message"):
            self.app.log_message(message, level=level)

    def action_show_context_menu(self) -> None:
        node = self.cursor_node
        if not node: return

        # Calculate coordinates for the menu
        relative_y = self.cursor_line - self.scroll_offset.y
        if 0 <= relative_y < self.size.height:
            screen_x = self.region.x + 8
            screen_y = self.region.y + relative_y + 1
            self._show_context_menu(node, screen_x, screen_y)
        else:
            self._log("⚠️ Node is off-screen", level="warning")

    def on_click(self, event: Click) -> None:
        if event.button != 3: return
        
        node = self.get_node_at_line(event.y + self.scroll_offset.y)
        if node:
            self._show_context_menu(node, event.screen_x, event.screen_y)

    def _show_context_menu(self, node, x: int, y: int):
        if not node.data or "value" not in node.data:
            self._log("❌ No value data in node", level="warning")
            return

        field_data = {
            "path": node.data.get("path", ""),
            "key": node.data.get("key", ""),
            "value": node.data.get("value"),
            "node": node,
            "trigger_x": x,
            "trigger_y": y
        }
        
        menu = ContextMenu(x, y, field_data)
        self.app.push_screen(menu, self.handle_menu_result)

    def handle_menu_result(self, result: tuple) -> None:
        if not result: return

        action, field_data = result
        field_name = field_data.get("key", "unknown")
        
        if action == "edit-value":
            self.trigger_edit_flow(field_data)

        elif action == "copy-value":
            value = field_data.get("value")
            if value is not None:
                if isinstance(value, bytes):
                    copy_text = value.hex()
                elif isinstance(value, int):
                    copy_text = f"{value} (0x{value:X})"
                else:
                    copy_text = str(value)
                
                try:
                    encoded = base64.b64encode(copy_text.encode()).decode()
                    osc52 = f"\033]52;c;{encoded}\007"
                    self.app.console.file.write(osc52)
                    self.app.console.file.flush()
                    self._log(f"📋 Copied: {copy_text[:30]}...")
                except Exception:
                    pass
                    
        elif action == "goto-offset":
            field_path = field_data.get("path", "")
            start_offset, _ = self._get_field_offsets(field_path)
            if start_offset is not None:
                self.post_message(self.GotoOffsetRequest(start_offset))
            else:
                self._log(f"❌ No offset found for {field_name}", level="warning")

    def trigger_edit_flow(self, field_data):
        field_path = field_data.get("path")
        current_value = field_data.get("value")
        field_key = field_data.get("key")
        
        # Use the coordinates where the menu was triggered
        target_x = field_data.get("trigger_x", 10)
        target_y = field_data.get("trigger_y", 10)
        
        start_offset, end_offset = self._get_field_offsets(field_path)
        
        if start_offset is None or end_offset is None:
             self._log(f"❌ Cannot edit '{field_key}': Offset information missing.", level="error")
             self.app.notify("Cannot edit: Offset missing (field might not use RawCopy)", severity="error")
             return

        value_type, _, _ = self.get_value_type_style(current_value)

        # Launch the new Tooltip Editor
        edit_screen = EditValueScreen(target_x, target_y, field_key, current_value, value_type)
        
        def finish_edit(new_value):
            if new_value is not None:
                length = end_offset - start_offset
                self.post_message(
                    self.FieldEditRequest(
                        field_path=field_path,
                        field_name=field_key,
                        value=new_value,
                        value_type=value_type,
                        offset=start_offset,
                        length=length
                    )
                )

        self.app.push_screen(edit_screen, finish_edit)

    def _get_field_offsets(self, field_path: str) -> tuple:
        """Robust offset finder (checks parent containers)."""
        if not self.parsed_data: return (None, None)
        
        parts = field_path.split("/")[1:]
        current = self.parsed_data
        parent = None
        
        try:
            for part in parts:
                parent = current
                if isinstance(current, (dict, Container)):
                    current = current[part]
                elif isinstance(current, (list, ListContainer)):
                    idx = int(part.strip("[]"))
                    current = current[idx]
            
            # Check self
            if hasattr(current, "offset1") and hasattr(current, "offset2"):
                return (current.offset1, current.offset2)
            # Check parent
            if parent and hasattr(parent, "offset1") and hasattr(parent, "offset2"):
                return (parent.offset1, parent.offset2)
                
        except (KeyError, IndexError, ValueError, AttributeError):
            pass
        
        return (None, None)
    
    def update_tree(self) -> None:
        self._save_expanded_paths()
        self.root.remove_children()
        if self.parsed_data is not None:
            self.populate_node(self.root, self.parsed_data)
        self.root.expand()
        self._restore_expanded_paths()
    
    def _save_expanded_paths(self) -> None:
        self._expanded_paths = set()
        def _collect(node, current_path):
            if node.is_expanded:
                self._expanded_paths.add(current_path)
            for child in node.children:
                _collect(child, f"{current_path}/{child.label.plain}")
        _collect(self.root, self.root.label.plain)
    
    def _restore_expanded_paths(self) -> None:
        def _expand(node, current_path):
            if current_path in self._expanded_paths:
                node.expand()
            for child in node.children:
                _expand(child, f"{current_path}/{child.label.plain}")
        _expand(self.root, self.root.label.plain)
    
    def watch_parsed_data(self, new_data) -> None:
        self.update_tree()
    
    def get_value_type_style(self, value):
        if value is None:
            return "null", "red", "null"
        elif isinstance(value, bool):
            return "bool", "yellow", str(value).lower()
        elif isinstance(value, int):
            if -128 <= value <= 255:
                hex_val = f"0x{value:02X}"
                return "byte", "magenta", f"{value} ({hex_val})"
            elif -32768 <= value <= 65535:
                hex_val = f"0x{value:04X}"
                return "word", "magenta", f"{value} ({hex_val})"
            elif -2147483648 <= value <= 4294967295:
                hex_val = f"0x{value:08X}"
                return "dword", "magenta", f"{value} ({hex_val})"
            else:
                hex_val = f"0x{value:X}"
                return "int", "blue", f"{value} ({hex_val})"
        elif isinstance(value, float):
            return "float", "blue", f"{value}"
        elif isinstance(value, bytes):
            if len(value) <= 16:
                hex_str = value.hex()
                hex_formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
                return "bytes", "green", f"{hex_formatted}"
            else:
                hex_preview = value[:8].hex()
                hex_formatted = ' '.join(hex_preview[i:i+2] for i in range(0, len(hex_preview), 2))
                return "bytes", "green", f"{hex_formatted}... ({len(value)} bytes)"
        elif isinstance(value, str):
            if len(value) > 32:
                return "str", "green", f'"{value[:29]}..."'
            return "str", "green", f'"{value}"'
        elif isinstance(value, datetime):
            return "datetime", "cyan", value.isoformat()
        elif isinstance(value, (Container, dict)):
            return "struct", "bold cyan", "{...}"
        elif isinstance(value, (ListContainer, list)):
            return "array", "bold magenta", f"[{len(value)} items]"
        else:
            return type(value).__name__, "dim", str(value)
    
    def populate_node(self, node: TreeNode, data, path: str = "") -> None:
        if isinstance(data, (Container, dict)):
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                
                current_path = f"{path}/{key}"
                key_text = Text(str(key), style="bold cyan")
                
                if isinstance(value, (Container, dict, ListContainer, list)) and value:
                    value_type, value_style, display_value = self.get_value_type_style(value)
                    key_text.append(f" ({value_type})", style="dim")
                    child = node.add(key_text, data={"path": current_path, "key": key, "value": value})
                    self.populate_node(child, value, current_path)
                else:
                    value_type, value_style, display_value = self.get_value_type_style(value)
                    key_text.append(f" ({value_type}): ", style="dim")
                    key_text.append(display_value, style=value_style)
                    node.add_leaf(key_text, data={"path": current_path, "key": key, "value": value})
                        
        elif isinstance(data, (ListContainer, list)):
            for i, item in enumerate(data):
                current_path = f"{path}/{i}"
                index_text = Text(f"[{i}]", style="magenta")
                
                if isinstance(item, (Container, dict, ListContainer, list)) and item:
                    value_type, value_style, display_value = self.get_value_type_style(item)
                    index_text.append(f" ({value_type})", style="dim")
                    child = node.add(index_text, data={"path": current_path, "index": i, "value": item})
                    self.populate_node(child, item, current_path)
                else:
                    value_type, value_style, display_value = self.get_value_type_style(item)
                    index_text.append(f" ({value_type}): ", style="dim")
                    index_text.append(display_value, style=value_style)
                    node.add_leaf(index_text, data={"path": current_path, "index": i, "value": item})

    def find_node_by_path(self, path):
        parts = path.split("/")
        current = self.root
        for part in parts[1:]:
            for child in current.children:
                node_data = child.data
                if node_data:
                    if "key" in node_data and str(node_data["key"]) == part:
                        current = child
                        break
                    elif "index" in node_data and str(node_data["index"]) == part:
                        current = child
                        break
            else:
                return None
        return current

from textual.app import App, ComposeResult
from textual.widgets import Tree, Input, Button, Label
from textual.widgets.tree import TreeNode
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.message import Message
from rich.text import Text
from typing import Dict, Any, Optional, Union, List
import struct
import asyncio
import base64
from datetime import datetime

# You would normally import construct, but we'll mock the Container class for the example
try:
    from construct import Container, ListContainer
except ImportError:
    # Mock Container class for environments without construct installed
    class Container(dict):
        pass
    class ListContainer(list):
        pass


class EditValueScreen(ModalScreen):
    """Modal screen for editing field values."""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    
    CSS = """
    EditValueScreen {
        align: center middle;
    }
    
    #edit-dialog {
        width: 60;
        height: auto;
        border: thick $primary 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #edit-dialog Label {
        margin: 1 0;
    }
    
    #edit-dialog Input {
        margin: 1 0;
    }
    
    #edit-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    #edit-buttons Button {
        margin: 0 1;
    }
    """
    
    class ValueEdited(Message):
        """Message sent when a value is edited."""
        def __init__(self, field_path: str, old_value: Any, new_value: Any, value_type: str):
            self.field_path = field_path
            self.old_value = old_value
            self.new_value = new_value
            self.value_type = value_type
            super().__init__()
    
    def __init__(self, field_name: str, field_path: str, current_value: Any, value_type: str):
        super().__init__()
        self.field_name = field_name
        self.field_path = field_path
        self.current_value = current_value
        self.value_type = value_type
    
    def compose(self) -> ComposeResult:
        with Vertical(id="edit-dialog"):
            yield Label(f"Edit Field: [bold cyan]{self.field_name}[/]")
            yield Label(f"Type: [yellow]{self.value_type}[/]")
            yield Label(f"Current Value: [green]{self._format_current_value()}[/]")
            yield Label("New Value:")
            yield Input(
                placeholder=self._get_placeholder(),
                value=self._get_initial_input_value(),
                id="value-input"
            )
            with Horizontal(id="edit-buttons"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")
    
    def _format_current_value(self) -> str:
        """Format the current value for display."""
        if isinstance(self.current_value, bytes):
            if len(self.current_value) <= 16:
                return self.current_value.hex(' ')
            else:
                return self.current_value[:16].hex(' ') + f"... ({len(self.current_value)} bytes)"
        elif isinstance(self.current_value, int):
            return f"{self.current_value} (0x{self.current_value:X})"
        else:
            return str(self.current_value)
    
    def _get_placeholder(self) -> str:
        """Get placeholder text based on value type."""
        if self.value_type in ["byte", "word", "dword", "int"]:
            return "Enter decimal or hex (0x...)"
        elif self.value_type == "bytes":
            return "Enter hex bytes (e.g., DEADBEEF or DE AD BE EF)"
        elif self.value_type == "str":
            return "Enter string value"
        elif self.value_type == "float":
            return "Enter floating point number"
        elif self.value_type == "bool":
            return "Enter true/false or 1/0"
        else:
            return "Enter new value"
    
    def _get_initial_input_value(self) -> str:
        """Get initial value for input field."""
        if isinstance(self.current_value, bytes):
            return self.current_value.hex()
        elif isinstance(self.current_value, int):
            return str(self.current_value)
        elif isinstance(self.current_value, bool):
            return "true" if self.current_value else "false"
        elif isinstance(self.current_value, str):
            return self.current_value
        else:
            return str(self.current_value)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()
    
    def action_save(self) -> None:
        """Save the edited value."""
        input_widget = self.query_one("#value-input", Input)
        new_value_str = input_widget.value.strip()
        
        try:
            new_value = self._parse_input(new_value_str)
            self.post_message(
                self.ValueEdited(
                    field_path=self.field_path,
                    old_value=self.current_value,
                    new_value=new_value,
                    value_type=self.value_type
                )
            )
            self.dismiss(True)
        except ValueError as e:
            # Show error in the input field or as a message
            input_widget.placeholder = f"Error: {str(e)}"
            input_widget.value = ""
    
    def _parse_input(self, value_str: str) -> Any:
        """Parse the input string based on the field type."""
        if not value_str:
            raise ValueError("Value cannot be empty")
        
        if self.value_type in ["byte", "word", "dword", "int"]:
            # Handle hex or decimal integers
            if value_str.lower().startswith("0x"):
                return int(value_str, 16)
            else:
                return int(value_str, 10)
        
        elif self.value_type == "bytes":
            # Handle hex bytes with or without spaces
            hex_str = value_str.replace(" ", "").replace(":", "")
            if len(hex_str) % 2 != 0:
                raise ValueError("Hex string must have even number of characters")
            try:
                return bytes.fromhex(hex_str)
            except ValueError:
                raise ValueError("Invalid hex string")
        
        elif self.value_type == "str":
            return value_str
        
        elif self.value_type == "float":
            return float(value_str)
        
        elif self.value_type == "bool":
            lower = value_str.lower()
            if lower in ["true", "1", "yes"]:
                return True
            elif lower in ["false", "0", "no"]:
                return False
            else:
                raise ValueError("Boolean must be true/false or 1/0")
        
        else:
            # For unknown types, try to return as string
            return value_str
    
    def action_cancel(self) -> None:
        """Cancel the edit."""
        self.dismiss(False)


class ContextMenu(ModalScreen):
    """A simple context menu screen."""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]
    
    CSS = """
    ContextMenu {
        align: left top;
    }
    
    #context-menu {
        width: auto;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 0;
    }
    
    #context-menu Button {
        width: 100%;
        border: none;
        text-align: left;
    }
    
    #context-menu Button:hover {
        background: $primary;
    }
    """
    
    class MenuItemSelected(Message):
        """Message sent when a menu item is selected."""
        def __init__(self, action: str, field_data: Dict):
            self.action = action
            self.field_data = field_data
            super().__init__()
    
    def __init__(self, x: int, y: int, field_data: Dict):
        super().__init__()
        self.menu_x = x
        self.menu_y = y
        self.field_data = field_data
    
    def compose(self) -> ComposeResult:
        with Vertical(id="context-menu"):
            yield Button("✏️  Edit Value", id="edit-value")
            yield Button("📋 Copy Value", id="copy-value")
            yield Button("📍 Go to Offset", id="goto-offset")
    
    def on_mount(self) -> None:
        """Position the menu at the cursor location."""
        menu = self.query_one("#context-menu")
        # Adjust position to be near the click but within bounds
        menu.styles.offset = (self.menu_x, self.menu_y)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle menu item selection."""
        action = event.button.id
        self.post_message(self.MenuItemSelected(action, self.field_data))
        self.dismiss()


class ReactiveConstructTree(Tree):
    """A custom Tree widget that displays Construct parsed data structures with context menu support."""
    
    # Define a reactive variable to store the parsed data
    parsed_data = reactive(None)
    
    # Track expanded paths for maintaining state when data refreshes
    _expanded_paths = set()
    
    class FieldEditRequest(Message):
        """Message sent when a field edit is requested."""
        def __init__(self, field_path: str, field_name: str, value: Any, value_type: str, start_offset: int, end_offset: int):
            self.field_path = field_path
            self.field_name = field_name
            self.value = value
            self.value_type = value_type
            self.start_offset = start_offset
            self.end_offset = end_offset
            super().__init__()
    
    class GotoOffsetRequest(Message):
        """Message sent when goto offset is requested."""
        def __init__(self, offset: int):
            self.offset = offset
            super().__init__()
    
    def __init__(
        self,
        label: str = "Parsed Data",
        parsed_data: Optional[Union[Container, ListContainer, dict, list]] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize the ReactiveConstructTree widget.
        
        Args:
            label: The root node label
            parsed_data: Initial parsed data from construct
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(label, name=name, id=id, classes=classes)
        if parsed_data is not None:
            self.parsed_data = parsed_data
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Initial tree population
        self.update_tree()
    
    def on_click(self, event) -> None:
        """Handle clicks on tree nodes."""
        # Check if it's a right-click (button 3)
        if event.button != 3:
            return
        
        # Get the node at the click position
        node = self.get_node_at_line(event.y + self.scroll_offset.y)
        if node and node.data and "value" in node.data:
            # Get click position for menu placement
            x, y = event.screen_x, event.screen_y
            
            # Show context menu
            field_data = {
                "path": node.data.get("path", ""),
                "key": node.data.get("key", ""),
                "value": node.data.get("value"),
                "node": node
            }
            
            # Store field data for the message handler
            self._current_field_data = field_data
            
            # Push context menu screen
            menu_screen = ContextMenu(x, y, field_data)
            self.app.push_screen(menu_screen)
    
    def on_context_menu_menu_item_selected(self, message: ContextMenu.MenuItemSelected) -> None:
        """Handle context menu item selection."""
        if not hasattr(self, '_current_field_data'):
            return
        
        field_data = self._current_field_data
        
        if message.action == "edit-value":
            # Extract field info for editing
            field_name = field_data.get("key", "unknown")
            field_path = field_data.get("path", "")
            value = field_data.get("value")
            
            # Determine value type
            value_type, _, _ = self.get_value_type_style(value)
            
            # Try to get offset information from parsed data
            start_offset, end_offset = self._get_field_offsets(field_path)
            
            # Post message to app to handle the edit
            self.post_message(
                self.FieldEditRequest(
                    field_path, 
                    field_name, 
                    value, 
                    value_type,
                    start_offset,
                    end_offset
                )
            )
        elif message.action == "copy-value":
            # Copy value to system clipboard using OSC 52 escape sequence
            value = field_data.get("value")
            if value is not None:
                # Format value for copying
                if isinstance(value, bytes):
                    copy_text = value.hex()
                elif isinstance(value, int):
                    copy_text = f"{value} (0x{value:X})"
                else:
                    copy_text = str(value)
                
                # Try to copy to clipboard using OSC 52 (works in many terminals)
                import base64
                try:
                    encoded = base64.b64encode(copy_text.encode()).decode()
                    # OSC 52 escape sequence for clipboard
                    osc52 = f"\033]52;c;{encoded}\007"
                    self.app.console.file.write(osc52)
                    self.app.console.file.flush()
                    self.app.log_message(f"Copied to clipboard: {copy_text[:50]}{'...' if len(copy_text) > 50 else ''}")
                except Exception as e:
                    self.app.log_message(f"Copy failed (clipboard not available): {copy_text[:100]}", level="warning")
        elif message.action == "goto-offset":
            start_offset, _ = self._get_field_offsets(field_data.get("path", ""))
            if start_offset is not None:
                self.post_message(self.GotoOffsetRequest(start_offset))
    
    def _get_field_offsets(self, field_path: str) -> tuple:
        """Get start and end offsets for a field by path."""
        # Navigate through parsed_data to find the field with offset information
        if not self.parsed_data:
            return (None, None)
        
        parts = field_path.split("/")[1:]  # Remove empty first part
        current = self.parsed_data
        
        try:
            for part in parts:
                if isinstance(current, (dict, Container)):
                    current = current[part]
                elif isinstance(current, (list, ListContainer)):
                    idx = int(part.strip("[]"))
                    current = current[idx]
            
            # Check if current has offset information (RawCopy wrapper)
            if hasattr(current, "offset1") and hasattr(current, "offset2"):
                return (current.offset1, current.offset2)
            
        except (KeyError, IndexError, ValueError, AttributeError):
            pass
        
        return (None, None)
    
    def update_tree(self) -> None:
        """Update the tree based on the current parsed data."""
        # Remember expanded nodes
        self._save_expanded_paths()
        
        # Clear existing nodes
        self.root.remove_children()
        
        # Repopulate with current data
        if self.parsed_data is not None:
            self.populate_node(self.root, self.parsed_data)
        
        # Expand the root node and restore previously expanded paths
        self.root.expand()
        self._restore_expanded_paths()
    
    def _save_expanded_paths(self) -> None:
        """Save the currently expanded paths."""
        self._expanded_paths = set()
        
        def _collect_expanded_paths(node, current_path):
            if node.is_expanded:
                self._expanded_paths.add(current_path)
            
            for child in node.children:
                _collect_expanded_paths(child, f"{current_path}/{child.label.plain}")
        
        _collect_expanded_paths(self.root, self.root.label.plain)
    
    def _restore_expanded_paths(self) -> None:
        """Restore previously expanded paths."""
        def _expand_saved_paths(node, current_path):
            if current_path in self._expanded_paths:
                node.expand()
            
            for child in node.children:
                _expand_saved_paths(child, f"{current_path}/{child.label.plain}")
        
        _expand_saved_paths(self.root, self.root.label.plain)
    
    def watch_parsed_data(self, new_data) -> None:
        """Watch for changes in the parsed data and update the tree.
        
        Args:
            new_data: The new parsed data
        """
        # When parsed data changes, update the tree
        self.update_tree()
    
    def get_value_type_style(self, value):
        """Determine the type and appropriate style for a value.
        
        Args:
            value: The value to analyze
            
        Returns:
            Tuple of (type_str, style, display_value)
        """
        if value is None:
            return "null", "red", "null"
        elif isinstance(value, bool):
            return "bool", "yellow", str(value).lower()
        elif isinstance(value, int):
            if -128 <= value <= 255:  # Byte-sized
                hex_val = f"0x{value:02X}"
                return "byte", "magenta", f"{value} ({hex_val})"
            elif -32768 <= value <= 65535:  # Word-sized
                hex_val = f"0x{value:04X}"
                return "word", "magenta", f"{value} ({hex_val})"
            elif -2147483648 <= value <= 4294967295:  # Dword-sized
                hex_val = f"0x{value:08X}"
                return "dword", "magenta", f"{value} ({hex_val})"
            else:
                hex_val = f"0x{value:X}"
                return "int", "blue", f"{value} ({hex_val})"
        elif isinstance(value, float):
            return "float", "blue", f"{value}"
        elif isinstance(value, bytes):
            if len(value) <= 16:  # Short byte strings
                hex_str = value.hex()
                hex_formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
                return "bytes", "green", f"{hex_formatted}"
            else:  # Longer byte strings
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
        """Recursively populate a node with parsed data.
        
        Args:
            node: The node to populate
            data: The data to add to the node
            path: Current path in the data structure
        """
        if isinstance(data, (Container, dict)):
            # Process Construct Container or dictionary
            for key, value in data.items():
                if key.startswith("_"):  # Skip private attributes
                    continue
                
                current_path = f"{path}/{key}"
                key_text = Text(str(key), style="bold cyan")
                
                if isinstance(value, (Container, dict, ListContainer, list)) and value:
                    # For non-empty collections, create a branch
                    value_type, value_style, display_value = self.get_value_type_style(value)
                    key_text.append(f" ({value_type})", style="dim")
                    child = node.add(key_text, data={"path": current_path, "key": key})
                    self.populate_node(child, value, current_path)
                else:
                    # For simple values, show type and value
                    value_type, value_style, display_value = self.get_value_type_style(value)
                    key_text.append(f" ({value_type}): ", style="dim")
                    key_text.append(display_value, style=value_style)
                    node.add_leaf(key_text, data={"path": current_path, "key": key, "value": value})
                        
        elif isinstance(data, (ListContainer, list)):
            # Process Construct ListContainer or list
            for i, item in enumerate(data):
                current_path = f"{path}/{i}"
                index_text = Text(f"[{i}]", style="magenta")
                
                if isinstance(item, (Container, dict, ListContainer, list)) and item:
                    # For non-empty collections, create a branch
                    value_type, value_style, display_value = self.get_value_type_style(item)
                    index_text.append(f" ({value_type})", style="dim")
                    child = node.add(index_text, data={"path": current_path, "index": i})
                    self.populate_node(child, item, current_path)
                else:
                    # For simple values, show type and value
                    value_type, value_style, display_value = self.get_value_type_style(item)
                    index_text.append(f" ({value_type}): ", style="dim")
                    index_text.append(display_value, style=value_style)
                    node.add_leaf(index_text, data={"path": current_path, "index": i, "value": item})
    
    def find_node_by_path(self, path):
        """Find a node by its path.
        
        Args:
            path: The path to search for
            
        Returns:
            The node if found, None otherwise
        """
        parts = path.split("/")
        current = self.root
        
        for part in parts[1:]:  # Skip the root part
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
                return None  # Path not found
                
        return current
    
    def expand_path(self, path):
        """Expand all nodes along a path.
        
        Args:
            path: The path to expand
        """
        parts = path.split("/")
        current_path = parts[0]
        current = self.root
        current.expand()
        
        for part in parts[1:]:
            current_path += f"/{part}"
            node = self.find_node_by_path(current_path)
            if node:
                node.expand()

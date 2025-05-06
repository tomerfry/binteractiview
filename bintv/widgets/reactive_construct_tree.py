from textual.app import App, ComposeResult
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.reactive import reactive
from rich.text import Text
from typing import Dict, Any, Optional, Union, List
import struct
import asyncio
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

class ReactiveConstructTree(Tree):
    """A custom Tree widget that displays Construct parsed data structures."""
    
    # Define a reactive variable to store the parsed data
    parsed_data = reactive(None)
    
    # Track expanded paths for maintaining state when data refreshes
    _expanded_paths = set()
    
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


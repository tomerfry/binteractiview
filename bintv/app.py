from bintv.svg_exporter import *
from bintv.rawcopy_proxy import *
from bintv.widgets.hex_view import *
from bintv.widgets.reactive_construct_tree import *

from textual.app import App
from textual.geometry import Size 
from textual.containers import Grid
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Placeholder, DirectoryTree, TextArea, TabbedContent, TabPane, Log

import io
import re
import json
import construct
from construct import *
import construct.core as construct_core

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
    BINDINGS = [("ctrl+o", "load_binary", "Load binary file"), ("ctrl+t", "align", "Align multiple files"), ("ctrl+e", "export", "Export SVG from Content"), ("ctrl+l", "toggle_log", "Toggle Log Panel"), ("ctrl+q", "quit", "Quit application")]

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
            with open("out.svg", "w") as f:
                f.write(create_svg(self._flattened_construct_data, self.data))
            self.log_message("Exported to SVG")

    def action_toggle_log(self):
        if not self.query_one("#log-panel").visible:
            self.query_one("#log-panel").visible = True
            self.set_focus(self.query_one("#log-panel"))
        else:
            self.query_one("#log-panel").visible = False

    def action_quit(self):
        self.exit()

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to the log view."""
        try:
            log = self.query_one("#log-panel", Log)
            
            # Add color coding based on level
            if level == "error":
                formatted_message = f"ERROR: {message}"
            elif level == "warning":
                formatted_message = f"WARN: {message}"
            else:
                formatted_message = f"INFO: {message}"
            
            log.write_line(formatted_message)
        except Exception:
            # If log panel doesn't exist yet, just pass
            pass

    def __init__(self, target):
        super().__init__()
        self.data = bytearray(b"")
        self.target = target
        self.offset = 0
        self.pane_count = 0
    
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
            self.query_one(f"#hex-pane-{self.pane_count}").mount(HexView(id=f"hex-pane-{self.pane_count}-hex-view"))
            self.query_one(f"#hex-pane-{self.pane_count}").mount(Static(hex(0x0), id=f"hex-pane-{self.pane_count}-hex-view-bottom-line"))
            self.query_one("#file-chooser").visible = False
            with open(self.target, "rb") as f:
                self.data = f.read()
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = bytearray(self.data)
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").virtual_size = Size(60, len(self.data) // 60)
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").scrollable_size = Size(60, len(self.data) // 60)

            self.pane_count += 1
            self._parsed_data = self._construct.parse(self.data)
            self.query_one("#construct-tree").parsed_data = self._parsed_data
            self.on_hex_view_cursor_update(HexView.CursorUpdate(f"hex-pane-{self.pane_count}-hex-view", 0x0))

    def on_text_area_changed(self, msg):
        try:
            self._subcons_text = msg.text_area.text
            self._construct = eval_with_rawcopy(self._subcons_text)
            self._parsed_data = self._construct.parse(self.data)
            self.log_message(self._parsed_data)
            self.query_one("#construct-tree").parsed_data = self._parsed_data
            self._flattened_construct_data = self.flatten_construct_offsets()
            self.log_message(self._flattened_construct_data)
        except Exception as e:
            self.log_message(str(e))

    def on_tabbed_content_tab_activated(self, msg):
        try:
            self.data = self.query_one(f"#{msg.pane.id}-hex-view").data
            self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
        except Exception as e:
            pass

    def on_directory_tree_file_selected(self, msg):
        self.pane_count += 1
        self.query_one("#tabbed-content").add_pane(TabPane(f"HexPane-{self.pane_count}", id=f"hex-pane-{self.pane_count}"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(HexView(id=f"hex-pane-{self.pane_count}-hex-view"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(Static(hex(0x0), id=f"hex-pane-{self.pane_count}-hex-view-bottom-line"))
        self.query_one(f"#hex-pane-{self.pane_count}-hex-view").virtual_size = Size(60, len(self.data) // 60)
        self.query_one(f"#hex-pane-{self.pane_count}-hex-view").scrollable_size = Size(60, len(self.data) // 60)
        self.set_focus(self.query_one(f"#hex-pane-{self.pane_count}-hex-view"))

        with open(msg.path, "rb") as f:
            self.data = f.read()
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = bytearray(self.data)
   
        self.query_one("#file-chooser").visible = False
        self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
        self.on_hex_view_cursor_update(HexView.CursorUpdate(f"hex-pane-{self.pane_count}-hex-view", 0x0))

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



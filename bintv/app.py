import json

from textual.app import App
from widgets.hex_view import *
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Placeholder, DirectoryTree, TextArea, TabbedContent, TabPane

from construct import *
import construct.core as construct_core


class BintvApp(App):
    DEFAULT_CSS = '''
    Screen {
        layers: below above;
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
    '''
    
    BINDINGS = [("ctrl+l", "load_binary", "Load binary file"), ("ctrl+q", "quit", "Quit application")]

    def action_load_binary(self):
        if not self.query_one("#file-chooser").visible:
            self.query_one("#file-chooser").visible = True            
            self.set_focus(self.query_one("#file-chooser"))
        else:
            self.query_one("#file-chooser").visible = False 

    def action_quit(self):
        self.exit()

    def __init__(self, target):
        super().__init__()
        self.data = bytearray(b"")
        self.target = target
        self.offset = 0
        self.pane_count = 0
    
    def evaluate_construct_expr(self, msg):
        self._subcons_text = msg.text_area.text
        self._construct = eval(self._subcons_text)
        self._construct.parse(self.data)

    def compose(self):
        with Horizontal():
            with Vertical():
                yield TextArea(id="construct-editor")
                yield Tree("Construct", id="construct-tree")
            with Vertical():
                with TabbedContent(id="tabbed-content"):
                    self.pane_count += 1
                    yield TabPane(f"HexPane-{self.pane_count}", id=f"hex-pane-{self.pane_count}")
        yield DirectoryTree("./", id="file-chooser") 

    def _on_mount(self):
        if self.target:
            self.query_one(f"#hex-pane-{self.pane_count}").mount(HexView(id=f"hex-pane-{self.pane_count}-hex-view"))
            self.query_one(f"#hex-pane-{self.pane_count}").mount(Static(hex(0x0), id=f"hex-pane-{self.pane_count}-hex-view-bottom-line"))
            self.query_one("#file-chooser").visible = False
            with open(self.target, "rb") as f:
                self.data = f.read()
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = bytearray(self.data)

    def on_text_area_changed(self, msg):
        try:
            evaluate_construct_expr(msg)
        except Exception as e:
            pass

    def on_directory_tree_file_selected(self, msg):
        self.pane_count += 1
        self.query_one("#tabbed-content").add_pane(TabPane(f"HexPane-{self.pane_count}", id=f"hex-pane-{self.pane_count}"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(HexView(id=f"hex-pane-{self.pane_count}-hex-view"))
        self.query_one(f"#hex-pane-{self.pane_count}").mount(Static(hex(0x0), id=f"hex-pane-{self.pane_count}-hex-view-bottom-line"))

        with open(msg.path, "rb") as f:
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = bytearray(f.read())
   
        self.query_one("#file-chooser").visible = False

    def on_hex_view_cursor_update(self, msg):
        self.query_one(f"#{msg.id}-bottom-line").update(hex(msg.offset))


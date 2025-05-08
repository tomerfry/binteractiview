from bintv.widgets.hex_view import *
from bintv.widgets.reactive_construct_tree import *

from textual.app import App
from textual.geometry import Size 
from textual.containers import Grid
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Placeholder, DirectoryTree, TextArea, TabbedContent, TabPane

import json
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
    BINDINGS = [("ctrl+l", "load_binary", "Load binary file"), ("ctrl+t", "align", "Align multiple files"), ("ctrl+q", "quit", "Quit application")]

    def action_load_binary(self):
        if not self.query_one("#file-chooser").visible:
            self.query_one("#file-chooser").visible = True            
            self.set_focus(self.query_one("#file-chooser"))
        else:
            self.query_one("#file-chooser").visible = False 

    def action_align(self):
        self.push_screen(AlignmentScreen(targets=['a', 'b']))

    def action_quit(self):
        self.exit()

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
        yield DirectoryTree("./", id="file-chooser") 

    def _on_mount(self):
        self.set_focus(self.query_one("#file-chooser"))
        self.on_text_area_changed(TextArea.Changed(self.query_one("#construct-editor")))
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

    def on_text_area_changed(self, msg):
        try:
            self._subcons_text = msg.text_area.text
            self._construct = eval(self._subcons_text)
            self._parsed_data = self._construct.parse(self.data)
            self.query_one("#construct-tree").parsed_data = self._parsed_data
        except Exception as e:
            pass

    def on_tabbed_content_tab_activated(self, msg):
        try:
            self.data = self.query_one(f"#{msg.pane.id}-hex-view").data
            self._parsed_data = self._construct.parse(self.data)
            self.query_one("#construct-tree").parsed_data = self._parsed_data
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
            self.query_one(f"#hex-pane-{self.pane_count}-hex-view").data = bytearray(f.read())
   
        self.query_one("#file-chooser").visible = False

    def on_hex_view_cursor_update(self, msg):
        self.query_one(f"#{msg.id}-bottom-line").update(hex(msg.offset))


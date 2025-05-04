import json

from textual.app import App
from widgets.hex_view import *
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Placeholder, DirectoryTree, TextArea

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
    }
    '''

    def __init__(self, target):
        super().__init__()
        self.data = bytearray(b'')
        self.target = target
        self.offset = 0
    
    def evaluate_construct_expr(msg):
        self._subcons_text = msg.text_area.text
        self._construct = eval(self._subcons_text)
        self._construct.parse(self.data)

    def compose(self):
        with Horizontal():
            with Vertical():
                yield TextArea(id="construct-editor")
                yield Tree("Construct", id="construct-tree")
            with Vertical():
                yield HexView(id='hex-view')
                yield Static(hex(self.offset), id='hex-view-bottom-line')
        yield DirectoryTree("./", id="file-chooser") 

    def _on_mount(self):
        if self.target:
            self.query_one("#file-chooser").visible = False
            with open(self.target, 'rb') as f:
                self.data = f.read()
            self.query_one('#hex-view').data = bytearray(self.data)
        
    def on_hex_view_cursor_update(self, msg):
        self.offset = msg.offset
        self.query_one('#hex-view-bottom-line').update(hex(self.offset))

    def on_text_area_changed(self, msg):
        try:
            evaluate_construct_expr(msg)
        except Exception as e:
            pass


from textual.app import App
from widgets.hex_view import *
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Placeholder, DirectoryTree


class BintvApp(App):
    DEFAULT_CSS = '''
    Screen {
        height: 2fr;
        width: 6fr;
        layers: below above;
        align: center middle;
    }

    #construct-editor {
        layer: below;
        height: 1fr;
        width: 2fr;
    }
    
    #construct-data {
        layer: below;
        height: 1fr;
        width: 2fr;
    }
    
    #hex-view {
        layer: below;
        height: 2fr;
        width: 4fr;
    }

    #hex-view-bottom-line {
        layer: below;
        height: 1;
        width: 2fr;
    }

    #file-chooser {
        layer: above;
        width: 50%;
        height: 50%;
    }
    '''

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.offset = 0
    
    def compose(self):
        with Horizontal():
            with Vertical():
                yield Placeholder(id="construct-editor")
                yield Placeholder(id="construct-data")
            with Vertical():
                yield HexView(id='hex-view')
                yield Static(hex(self.offset), id='hex-view-bottom-line')
        yield DirectoryTree("./", id="file-chooser") 

    def _on_mount(self):
        if self.target:
            self.query_one("#file-chooser").visible = False
            with open(self.target, 'rb') as f:
                data = f.read()
            self.query_one('#hex-view').data = bytearray(data)
        
    def on_hex_view_cursor_update(self, msg):
        self.offset = msg.offset
        self.query_one('#hex-view-bottom-line').update(hex(self.offset))

from textual.app import App
from widgets.hex_view import *
from textual.containers import Grid
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
    
    def compose(self):
        with Horizontal():
            with Vertical():
                yield Placeholder(id="construct-editor")
                yield Placeholder(id="construct-data")
            with Vertical():
                yield HexView(id='hex-view')
                yield Static(id='hex-view-bottom-line')
        yield DirectoryTree("./", id="file-chooser") 

    def _on_mount(self):
        if self.target:
            with open(self.target, 'rb') as f:
                data = f.read()
            self.query_one('#hex-view').data = bytearray(data)

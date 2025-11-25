"""
Fuzzy Finder Widget for BinTV

Provides a searchable list with fuzzy matching for packet fields,
similar to fzf or telescope.nvim.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Static, ListView, ListItem, Label
from textual.widget import Widget
from textual.message import Message
from textual.reactive import reactive
from textual import events
from textual.binding import Binding

from typing import List, Tuple, Any, Callable, Optional
from dataclasses import dataclass
import re


@dataclass
class SearchResult:
    """A single search result"""
    text: str
    value: Any
    score: float
    highlights: List[Tuple[int, int]] = None  # Character ranges to highlight
    metadata: str = ""


class FuzzyMatcher:
    """Fuzzy string matching algorithm"""
    
    @staticmethod
    def match(query: str, text: str) -> Tuple[float, List[Tuple[int, int]]]:
        """
        Match query against text using fuzzy matching.
        Returns (score, highlight_ranges).
        """
        if not query:
            return (0.0, [])
        
        query = query.lower()
        text_lower = text.lower()
        
        # Exact match
        if query == text_lower:
            return (1.0, [(0, len(text))])
        
        # Prefix match
        if text_lower.startswith(query):
            return (0.95, [(0, len(query))])
        
        # Contains match
        idx = text_lower.find(query)
        if idx >= 0:
            return (0.8 - (idx * 0.01), [(idx, idx + len(query))])
        
        # Fuzzy subsequence match
        highlights = []
        query_idx = 0
        consecutive = 0
        score = 0.0
        last_match_idx = -2
        
        for i, char in enumerate(text_lower):
            if query_idx < len(query) and char == query[query_idx]:
                if last_match_idx == i - 1:
                    consecutive += 1
                    # Extend last highlight
                    if highlights:
                        start, _ = highlights[-1]
                        highlights[-1] = (start, i + 1)
                else:
                    consecutive = 1
                    highlights.append((i, i + 1))
                
                last_match_idx = i
                query_idx += 1
                score += 0.1 + (consecutive * 0.05)
        
        if query_idx == len(query):
            # All characters matched
            # Bonus for shorter strings
            length_bonus = max(0, 0.2 - (len(text) - len(query)) * 0.01)
            return (min(0.7, score + length_bonus), highlights)
        
        return (0.0, [])
    
    @staticmethod
    def highlight_text(text: str, highlights: List[Tuple[int, int]], 
                       style: str = "bold yellow") -> str:
        """Apply Rich markup to highlighted ranges"""
        if not highlights:
            return text
        
        result = []
        last_end = 0
        
        for start, end in sorted(highlights):
            if start > last_end:
                result.append(text[last_end:start])
            result.append(f"[{style}]{text[start:end]}[/{style}]")
            last_end = end
        
        if last_end < len(text):
            result.append(text[last_end:])
        
        return "".join(result)


class FuzzyListItem(ListItem):
    """A list item with fuzzy match highlighting"""
    
    def __init__(self, result: SearchResult, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = result
    
    def compose(self) -> ComposeResult:
        highlighted = FuzzyMatcher.highlight_text(
            self.result.text, 
            self.result.highlights or [],
            "bold cyan"
        )
        
        if self.result.metadata:
            yield Static(f"{highlighted} [dim]{self.result.metadata}[/dim]")
        else:
            yield Static(highlighted)


class FuzzyFinder(Widget):
    """
    A fuzzy finder widget with search input and results list.
    
    Similar to fzf, telescope.nvim, or VS Code's command palette.
    """
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "select", "Select"),
        Binding("up", "move_up", "Up"),
        Binding("down", "move_down", "Down"),
        Binding("ctrl+n", "move_down", "Down"),
        Binding("ctrl+p", "move_up", "Up"),
    ]
    
    DEFAULT_CSS = """
    FuzzyFinder {
        width: 100%;
        height: auto;
        max-height: 50%;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }
    
    FuzzyFinder > Input {
        width: 100%;
        margin-bottom: 1;
    }
    
    FuzzyFinder > #results-container {
        height: auto;
        max-height: 20;
        overflow-y: auto;
    }
    
    FuzzyFinder > #results-count {
        text-align: right;
        color: $text-muted;
        height: 1;
    }
    
    FuzzyFinder ListView {
        height: auto;
        max-height: 18;
    }
    
    FuzzyFinder ListItem {
        padding: 0 1;
    }
    
    FuzzyFinder ListItem:hover {
        background: $primary 30%;
    }
    
    FuzzyFinder .selected {
        background: $primary 50%;
    }
    """
    
    query = reactive("")
    selected_index = reactive(0)
    
    class Selected(Message):
        """Emitted when user selects an item"""
        def __init__(self, result: SearchResult):
            super().__init__()
            self.result = result
    
    class Closed(Message):
        """Emitted when finder is closed"""
        pass
    
    def __init__(
        self, 
        items: List[Any] = None,
        item_to_text: Callable[[Any], str] = str,
        item_to_metadata: Callable[[Any], str] = None,
        placeholder: str = "Search...",
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._items = items or []
        self._item_to_text = item_to_text
        self._item_to_metadata = item_to_metadata or (lambda x: "")
        self._placeholder = placeholder
        self._results: List[SearchResult] = []
        self._list_view: Optional[ListView] = None
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder=self._placeholder, id="fuzzy-input")
        yield Static("", id="results-count")
        with Vertical(id="results-container"):
            yield ListView(id="fuzzy-results")
    
    def on_mount(self):
        self._list_view = self.query_one("#fuzzy-results", ListView)
        self._update_results()
        self.query_one("#fuzzy-input").focus()
    
    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "fuzzy-input":
            self.query = event.value
            self._update_results()
    
    def watch_query(self, value: str):
        self._update_results()
    
    def _update_results(self):
        """Update the results list based on current query"""
        self._results.clear()
        
        for item in self._items:
            text = self._item_to_text(item)
            score, highlights = FuzzyMatcher.match(self.query, text)
            
            if score > 0 or not self.query:
                metadata = self._item_to_metadata(item)
                self._results.append(SearchResult(
                    text=text,
                    value=item,
                    score=score,
                    highlights=highlights,
                    metadata=metadata,
                ))
        
        # Sort by score descending
        self._results.sort(key=lambda r: r.score, reverse=True)
        
        # Update count display
        count_label = self.query_one("#results-count", Static)
        count_label.update(f"{len(self._results)}/{len(self._items)}")
        
        # Update list view
        self._list_view.clear()
        for result in self._results[:50]:  # Limit displayed results
            item = FuzzyListItem(result)
            self._list_view.append(item)
        
        self.selected_index = 0
        if self._results and self._list_view.children:
            self._list_view.index = 0
    
    def set_items(self, items: List[Any]):
        """Update the items to search"""
        self._items = items
        self._update_results()
    
    def action_close(self):
        self.post_message(self.Closed())
    
    def action_select(self):
        if self._results and 0 <= self.selected_index < len(self._results):
            self.post_message(self.Selected(self._results[self.selected_index]))
    
    def action_move_up(self):
        if self._results:
            self.selected_index = max(0, self.selected_index - 1)
            self._list_view.index = self.selected_index
    
    def action_move_down(self):
        if self._results:
            self.selected_index = min(len(self._results) - 1, self.selected_index + 1)
            self._list_view.index = self.selected_index
    
    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._results):
            self.post_message(self.Selected(self._results[idx]))


class PacketFieldFinder(FuzzyFinder):
    """Specialized fuzzy finder for packet fields"""
    
    DEFAULT_CSS = FuzzyFinder.DEFAULT_CSS + """
    PacketFieldFinder {
        border: solid $secondary;
    }
    
    PacketFieldFinder > Input {
        border: none;
        background: transparent;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            placeholder="Search fields (e.g., tcp.port, ip.src)...",
            *args, 
            **kwargs
        )


class PacketListFinder(FuzzyFinder):
    """Specialized fuzzy finder for packet list"""
    
    DEFAULT_CSS = FuzzyFinder.DEFAULT_CSS + """
    PacketListFinder {
        border: solid $accent;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            placeholder="Filter packets (e.g., tcp, 192.168.1.1, port 80)...",
            *args,
            **kwargs
        )


class CommandPalette(FuzzyFinder):
    """Command palette for quick actions"""
    
    DEFAULT_CSS = FuzzyFinder.DEFAULT_CSS + """
    CommandPalette {
        width: 80;
        margin: 2 10;
        border: solid $warning;
    }
    """
    
    def __init__(self, commands: List[Tuple[str, str, Callable]], *args, **kwargs):
        """
        Args:
            commands: List of (name, description, callback) tuples
        """
        self._commands = commands
        super().__init__(
            items=commands,
            item_to_text=lambda c: c[0],
            item_to_metadata=lambda c: c[1],
            placeholder="Type a command...",
            *args,
            **kwargs
        )
    
    def on_fuzzy_finder_selected(self, event: FuzzyFinder.Selected):
        # Execute the command callback
        _, _, callback = event.result.value
        callback()

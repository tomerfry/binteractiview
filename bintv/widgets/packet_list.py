"""
Packet List Widget for BinTV

Displays a list of network packets in a table format similar to Wireshark.
"""

from textual.app import ComposeResult
from textual.widgets import DataTable, Static
from textual.widget import Widget
from textual.message import Message
from textual.reactive import reactive
from textual.binding import Binding

from typing import List, Optional, Callable
from bintv.pcap_parser import ParsedPacket, format_ip, format_mac


class PacketList(Widget):
    """
    A widget that displays network packets in a table format.
    
    Columns: No. | Time | Source | Destination | Protocol | Length | Info
    """
    
    BINDINGS = [
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("g", "goto_first", "First"),
        Binding("G", "goto_last", "Last"),
        Binding("enter", "select_packet", "Select"),
        Binding("/", "search", "Search"),
    ]
    
    DEFAULT_CSS = """
    PacketList {
        height: 100%;
        width: 100%;
    }
    
    PacketList DataTable {
        height: 100%;
    }
    
    PacketList .packet-tcp {
        color: $success;
    }
    
    PacketList .packet-udp {
        color: $primary;
    }
    
    PacketList .packet-icmp {
        color: $warning;
    }
    
    PacketList .packet-arp {
        color: $secondary;
    }
    
    PacketList .packet-dns {
        color: cyan;
    }
    
    PacketList .packet-http {
        color: green;
    }
    """
    
    selected_packet_index = reactive(-1)
    
    class PacketSelected(Message):
        """Emitted when a packet is selected"""
        def __init__(self, packet: ParsedPacket, index: int):
            super().__init__()
            self.packet = packet
            self.index = index
    
    class SearchRequested(Message):
        """Emitted when user wants to search"""
        pass
    
    def __init__(self, packets: List[ParsedPacket] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._packets = packets or []
        self._filtered_indices: List[int] = []
        self._table: Optional[DataTable] = None
        self._filter_func: Optional[Callable[[ParsedPacket], bool]] = None
        self._first_timestamp: float = 0
    
    def compose(self) -> ComposeResult:
        yield DataTable(id="packet-table", cursor_type="row")
    
    def on_mount(self):
        self._table = self.query_one("#packet-table", DataTable)
        self._setup_columns()
        self._populate_table()
    
    def _setup_columns(self):
        """Setup table columns"""
        self._table.add_column("No.", width=8, key="no")
        self._table.add_column("Time", width=12, key="time")
        self._table.add_column("Source", width=18, key="src")
        self._table.add_column("Destination", width=18, key="dst")
        self._table.add_column("Protocol", width=10, key="proto")
        self._table.add_column("Length", width=8, key="len")
        self._table.add_column("Info", width=50, key="info")
    
    def _populate_table(self):
        """Populate the table with packets"""
        self._table.clear()
        self._filtered_indices.clear()
        
        if self._packets:
            self._first_timestamp = self._packets[0].timestamp
        
        for i, packet in enumerate(self._packets):
            if self._filter_func and not self._filter_func(packet):
                continue
            
            self._filtered_indices.append(i)
            
            # Calculate relative time
            rel_time = packet.timestamp - self._first_timestamp
            
            # Get protocol color
            proto = packet.protocol
            proto_style = self._get_protocol_style(proto)
            
            self._table.add_row(
                str(packet.index + 1),
                f"{rel_time:.6f}",
                packet.src_addr[:17] if packet.src_addr else "",
                packet.dst_addr[:17] if packet.dst_addr else "",
                f"[{proto_style}]{proto}[/{proto_style}]",
                str(len(packet.raw_data)),
                packet.info[:48] if packet.info else "",
                key=str(i),
            )
    
    def _get_protocol_style(self, protocol: str) -> str:
        """Get style for protocol"""
        styles = {
            'TCP': 'green',
            'UDP': 'blue',
            'ICMP': 'yellow',
            'ARP': 'magenta',
            'DNS': 'cyan',
            'HTTP': 'bold green',
            'IPv4': 'white',
            'IPv6': 'white',
        }
        return styles.get(protocol, 'white')
    
    def set_packets(self, packets: List[ParsedPacket]):
        """Set the packets to display"""
        self._packets = packets
        if self._table:
            self._populate_table()
    
    def set_filter(self, filter_func: Optional[Callable[[ParsedPacket], bool]]):
        """Set a filter function for packets"""
        self._filter_func = filter_func
        if self._table:
            self._populate_table()
    
    def clear_filter(self):
        """Clear the current filter"""
        self._filter_func = None
        if self._table:
            self._populate_table()
    
    def get_selected_packet(self) -> Optional[ParsedPacket]:
        """Get the currently selected packet"""
        if self._table and self._table.cursor_row is not None:
            row_idx = self._table.cursor_row
            if 0 <= row_idx < len(self._filtered_indices):
                packet_idx = self._filtered_indices[row_idx]
                return self._packets[packet_idx]
        return None
    
    def goto_packet(self, index: int):
        """Navigate to a specific packet by index"""
        if index in self._filtered_indices:
            row_idx = self._filtered_indices.index(index)
            self._table.move_cursor(row=row_idx)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle row selection"""
        if event.row_key:
            packet_idx = int(event.row_key.value)
            if 0 <= packet_idx < len(self._packets):
                self.selected_packet_index = packet_idx
                self.post_message(self.PacketSelected(
                    self._packets[packet_idx], 
                    packet_idx
                ))
    
    def action_cursor_down(self):
        self._table.action_cursor_down()
    
    def action_cursor_up(self):
        self._table.action_cursor_up()
    
    def action_goto_first(self):
        self._table.move_cursor(row=0)
    
    def action_goto_last(self):
        if self._filtered_indices:
            self._table.move_cursor(row=len(self._filtered_indices) - 1)
    
    def action_select_packet(self):
        packet = self.get_selected_packet()
        if packet:
            self.post_message(self.PacketSelected(packet, packet.index))
    
    def action_search(self):
        self.post_message(self.SearchRequested())


class PacketDetails(Widget):
    """
    Widget to display detailed packet information in a tree structure.
    """
    
    DEFAULT_CSS = """
    PacketDetails {
        height: 100%;
        width: 100%;
        overflow-y: auto;
        padding: 0 1;
    }
    
    PacketDetails .layer-header {
        color: $accent;
        text-style: bold;
    }
    
    PacketDetails .field-name {
        color: $primary;
    }
    
    PacketDetails .field-value {
        color: $text;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._packet: Optional[ParsedPacket] = None
        self._content = ""
    
    def compose(self) -> ComposeResult:
        yield Static(self._content, id="packet-details-content")
    
    def set_packet(self, packet: ParsedPacket):
        """Set the packet to display"""
        self._packet = packet
        self._update_display()
    
    def _update_display(self):
        """Update the display content"""
        if not self._packet:
            self._content = "[dim]No packet selected[/dim]"
        else:
            lines = []
            
            # Frame info
            lines.append(f"[bold]Frame {self._packet.index + 1}[/bold]: {len(self._packet.raw_data)} bytes")
            lines.append("")
            
            # Each layer
            for layer_name, layer_data in self._packet.layers.items():
                layer_title = layer_name.upper()
                lines.append(f"[bold cyan]▼ {layer_title}[/bold cyan]")
                
                if isinstance(layer_data, dict):
                    for field_name, field_value in layer_data.items():
                        formatted_value = self._format_field_value(field_name, field_value)
                        lines.append(f"    [green]{field_name}[/green]: {formatted_value}")
                
                lines.append("")
            
            self._content = "\n".join(lines)
        
        try:
            content_widget = self.query_one("#packet-details-content", Static)
            content_widget.update(self._content)
        except Exception:
            pass
    
    def _format_field_value(self, name: str, value) -> str:
        """Format a field value for display"""
        if isinstance(value, bytes):
            if 'mac' in name.lower() or 'hw' in name.lower():
                return format_mac(value)
            elif 'ip' in name.lower() and len(value) == 4:
                return format_ip(value)
            elif 'ip' in name.lower() and len(value) == 16:
                # IPv6
                parts = []
                for i in range(0, 16, 2):
                    parts.append(f"{value[i]:02x}{value[i+1]:02x}")
                return ":".join(parts)
            elif len(value) <= 16:
                return " ".join(f"{b:02x}" for b in value)
            else:
                return f"[{len(value)} bytes]"
        
        if isinstance(value, int):
            if name in ('src_port', 'dst_port'):
                return f"{value} ({self._get_port_name(value)})"
            elif name == 'protocol':
                return f"{value} ({self._get_protocol_name(value)})"
            elif name == 'ethertype':
                return f"0x{value:04x} ({self._get_ethertype_name(value)})"
            elif name == 'flags':
                return f"0x{value:04x}"
            return str(value)
        
        return str(value)
    
    def _get_port_name(self, port: int) -> str:
        """Get well-known port name"""
        ports = {
            20: 'FTP-DATA', 21: 'FTP', 22: 'SSH', 23: 'TELNET',
            25: 'SMTP', 53: 'DNS', 67: 'DHCP', 68: 'DHCP',
            80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS',
            993: 'IMAPS', 995: 'POP3S', 3306: 'MySQL', 5432: 'PostgreSQL',
            6379: 'Redis', 8080: 'HTTP-ALT', 8443: 'HTTPS-ALT',
        }
        return ports.get(port, '')
    
    def _get_protocol_name(self, proto: int) -> str:
        """Get IP protocol name"""
        protocols = {
            1: 'ICMP', 6: 'TCP', 17: 'UDP', 58: 'ICMPv6',
            47: 'GRE', 50: 'ESP', 51: 'AH', 89: 'OSPF',
        }
        return protocols.get(proto, '')
    
    def _get_ethertype_name(self, etype: int) -> str:
        """Get EtherType name"""
        types = {
            0x0800: 'IPv4', 0x0806: 'ARP', 0x86DD: 'IPv6',
            0x8100: 'VLAN', 0x88CC: 'LLDP',
        }
        return types.get(etype, '')

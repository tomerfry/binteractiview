"""
PCAP Viewer Application for BinTV - Simplified Version

A streamlined PCAP viewer that matches BinTV's layout:
- Top: Fuzzy search bar for filtering packets
- Left: Packet list (selectable)
- Middle: Hex dump view  
- Right: Construct-based protocol structure tree
- Same SVG export as regular BinTV
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Static, Input, DataTable, Log
from textual.binding import Binding
from textual.reactive import reactive

from bintv.pcap_parser import PCAPParser, ParsedPacket, format_ip, format_mac
from bintv.pcap_parser import EthernetHeader, IPv4Header, IPv6Header, TCPHeader, UDPHeader, ICMPHeader, ARPHeader
from bintv.widgets.hex_view import HexView
from bintv.widgets.reactive_construct_tree import ReactiveConstructTree
from bintv.neon_pallete import neon_background_colors
from bintv.svg_exporter import create_svg

from construct import Struct, Bytes, GreedyBytes

from typing import List, Optional, Tuple
import os


class PCAPViewerApp(App):
    """Simplified PCAP Viewer - matches BinTV layout"""
    
    TITLE = "BinTV PCAP Viewer"
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 3 1fr;
        grid-columns: 1fr 2fr 1fr;
    }
    
    #search-bar {
        column-span: 3;
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    
    #search-input {
        width: 100%;
    }
    
    #packet-list-container {
        height: 100%;
        border: solid $primary;
    }
    
    #packet-table {
        height: 100%;
    }
    
    #hex-view-container {
        height: 100%;
        border: solid $primary;
    }
    
    #hex-view {
        height: 100%;
    }
    
    #structure-container {
        height: 100%;
        border: solid $primary;
    }
    
    #construct-tree {
        height: 100%;
    }
    
    #log-panel {
        display: none;
        height: 10;
        column-span: 3;
        border-top: solid $primary;
    }
    
    #log-panel.visible {
        display: block;
    }
    
    DataTable > .datatable--cursor {
        background: $accent;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+e", "export_svg", "Export SVG"),
        Binding("ctrl+l", "toggle_log", "Toggle Log"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear"),
        Binding("j", "next_packet", "Next"),
        Binding("k", "prev_packet", "Previous"),
        Binding("g", "first_packet", "First"),
        Binding("G", "last_packet", "Last"),
    ]
    
    search_query = reactive("")
    selected_packet_index = reactive(-1)
    
    def __init__(self, pcap_file: str = None):
        super().__init__()
        self.pcap_file = pcap_file
        self.parser: Optional[PCAPParser] = None
        self.packets: List[ParsedPacket] = []
        self.filtered_indices: List[int] = []
        self._flattened_data: List[dict] = []
        self._current_raw_data: bytes = b''
        self._first_timestamp: float = 0
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        # Search bar spanning full width
        with Container(id="search-bar"):
            yield Input(
                placeholder="Filter packets... (e.g., tcp, 192.168.1.1, port 80)",
                id="search-input"
            )
        
        # Three-column layout: Packets | Hex | Structure
        with Container(id="packet-list-container"):
            yield DataTable(id="packet-table", cursor_type="row")
        
        with Container(id="hex-view-container"):
            yield HexView(id="hex-view")
        
        with Container(id="structure-container"):
            yield ReactiveConstructTree("Packet Structure", id="construct-tree")
        
        # Hidden log panel
        yield Log(id="log-panel", auto_scroll=True)
        
        yield Footer()
    
    def on_mount(self):
        # Setup packet table columns
        table = self.query_one("#packet-table", DataTable)
        table.add_column("#", width=5, key="no")
        table.add_column("Time", width=10, key="time")
        table.add_column("Src", width=15, key="src")
        table.add_column("Dst", width=15, key="dst")  
        table.add_column("Proto", width=6, key="proto")
        table.add_column("Info", width=20, key="info")
        
        self.log_message("BinTV PCAP Viewer ready")
        
        if self.pcap_file and os.path.exists(self.pcap_file):
            self.load_pcap(self.pcap_file)
            self.sub_title = os.path.basename(self.pcap_file)
    
    def load_pcap(self, filepath: str):
        """Load and parse a PCAP file"""
        try:
            self.log_message(f"Loading {filepath}...")
            self.parser = PCAPParser(filepath)
            self.packets = self.parser.parse()
            
            if self.packets:
                self._first_timestamp = self.packets[0].timestamp
            
            self.filtered_indices = list(range(len(self.packets)))
            self._populate_table()
            
            self.log_message(f"Loaded {len(self.packets)} packets")
            
            # Select first packet
            if self.packets:
                self._select_packet(0)
                
        except Exception as e:
            self.log_message(f"Error: {e}")
    
    def _populate_table(self):
        """Populate packet table with filtered packets"""
        table = self.query_one("#packet-table", DataTable)
        table.clear()
        
        for idx in self.filtered_indices:
            packet = self.packets[idx]
            rel_time = packet.timestamp - self._first_timestamp
            
            # Color based on protocol
            proto = packet.protocol
            if proto == "TCP":
                proto_str = f"[green]{proto}[/]"
            elif proto == "UDP":
                proto_str = f"[blue]{proto}[/]"
            elif proto == "ICMP":
                proto_str = f"[yellow]{proto}[/]"
            elif proto == "ARP":
                proto_str = f"[magenta]{proto}[/]"
            else:
                proto_str = proto
            
            table.add_row(
                str(packet.index + 1),
                f"{rel_time:.4f}",
                packet.src_addr[:14] if packet.src_addr else "-",
                packet.dst_addr[:14] if packet.dst_addr else "-",
                proto_str,
                packet.info[:18] if packet.info else "-",
                key=str(idx),
            )
    
    def _select_packet(self, packet_idx: int):
        """Select and display a packet"""
        if packet_idx < 0 or packet_idx >= len(self.packets):
            return
        
        self.selected_packet_index = packet_idx
        packet = self.packets[packet_idx]
        self._current_raw_data = packet.raw_data
        
        # Update hex view
        hex_view = self.query_one("#hex-view", HexView)
        hex_view.data = bytearray(packet.raw_data)
        
        # Build construct structure and flattened data for highlighting
        self._flattened_data = []
        struct_dict = {}
        offset = 0
        
        # Parse each layer and build structure
        if 'ethernet' in packet.layers:
            eth_data = packet.layers['ethernet']
            struct_dict['ethernet'] = {
                'dst_mac': format_mac(eth_data.get('dst_mac', b'')),
                'src_mac': format_mac(eth_data.get('src_mac', b'')),
                'ethertype': f"0x{eth_data.get('ethertype', 0):04x}",
            }
            self._flattened_data.append({
                'name': 'ethernet',
                'start': 0,
                'end': 14,
                'value': struct_dict['ethernet'],
                'raw_data': packet.raw_data[0:14],
            })
            offset = 14
        
        if 'ipv4' in packet.layers:
            ip_data = packet.layers['ipv4']
            ihl = ip_data.get('ihl', 5) * 4
            struct_dict['ipv4'] = {
                'version': ip_data.get('version', 4),
                'ihl': ip_data.get('ihl', 5),
                'total_length': ip_data.get('total_length', 0),
                'ttl': ip_data.get('ttl', 0),
                'protocol': ip_data.get('protocol', 0),
                'src_ip': format_ip(ip_data.get('src_ip', b'\x00\x00\x00\x00')),
                'dst_ip': format_ip(ip_data.get('dst_ip', b'\x00\x00\x00\x00')),
            }
            self._flattened_data.append({
                'name': 'ipv4',
                'start': offset,
                'end': offset + ihl,
                'value': struct_dict['ipv4'],
                'raw_data': packet.raw_data[offset:offset+ihl],
            })
            offset += ihl
        
        if 'ipv6' in packet.layers:
            ip6_data = packet.layers['ipv6']
            struct_dict['ipv6'] = {
                'version': ip6_data.get('version', 6),
                'payload_length': ip6_data.get('payload_length', 0),
                'next_header': ip6_data.get('next_header', 0),
                'hop_limit': ip6_data.get('hop_limit', 0),
            }
            self._flattened_data.append({
                'name': 'ipv6',
                'start': offset,
                'end': offset + 40,
                'value': struct_dict['ipv6'],
                'raw_data': packet.raw_data[offset:offset+40],
            })
            offset += 40
        
        if 'arp' in packet.layers:
            arp_data = packet.layers['arp']
            struct_dict['arp'] = {
                'operation': 'Request' if arp_data.get('operation') == 1 else 'Reply',
                'sender_hw': format_mac(arp_data.get('sender_hw_addr', b'')),
                'sender_ip': format_ip(arp_data.get('sender_proto_addr', b'')),
                'target_hw': format_mac(arp_data.get('target_hw_addr', b'')),
                'target_ip': format_ip(arp_data.get('target_proto_addr', b'')),
            }
            self._flattened_data.append({
                'name': 'arp',
                'start': offset,
                'end': offset + 28,
                'value': struct_dict['arp'],
                'raw_data': packet.raw_data[offset:offset+28],
            })
            offset += 28
        
        if 'tcp' in packet.layers:
            tcp_data = packet.layers['tcp']
            data_off = tcp_data.get('data_offset', 5) * 4
            flags = tcp_data.get('flags', 0)
            flag_strs = []
            if flags & 0x02: flag_strs.append('SYN')
            if flags & 0x10: flag_strs.append('ACK')
            if flags & 0x01: flag_strs.append('FIN')
            if flags & 0x04: flag_strs.append('RST')
            if flags & 0x08: flag_strs.append('PSH')
            
            struct_dict['tcp'] = {
                'src_port': tcp_data.get('src_port', 0),
                'dst_port': tcp_data.get('dst_port', 0),
                'seq_num': tcp_data.get('seq_num', 0),
                'ack_num': tcp_data.get('ack_num', 0),
                'flags': ','.join(flag_strs) if flag_strs else 'none',
                'window': tcp_data.get('window_size', 0),
            }
            self._flattened_data.append({
                'name': 'tcp',
                'start': offset,
                'end': offset + data_off,
                'value': struct_dict['tcp'],
                'raw_data': packet.raw_data[offset:offset+data_off],
            })
            offset += data_off
        
        if 'udp' in packet.layers:
            udp_data = packet.layers['udp']
            struct_dict['udp'] = {
                'src_port': udp_data.get('src_port', 0),
                'dst_port': udp_data.get('dst_port', 0),
                'length': udp_data.get('length', 0),
            }
            self._flattened_data.append({
                'name': 'udp',
                'start': offset,
                'end': offset + 8,
                'value': struct_dict['udp'],
                'raw_data': packet.raw_data[offset:offset+8],
            })
            offset += 8
        
        if 'icmp' in packet.layers:
            icmp_data = packet.layers['icmp']
            struct_dict['icmp'] = {
                'type': icmp_data.get('type', 0),
                'code': icmp_data.get('code', 0),
            }
            self._flattened_data.append({
                'name': 'icmp',
                'start': offset,
                'end': offset + 8,
                'value': struct_dict['icmp'],
                'raw_data': packet.raw_data[offset:offset+8],
            })
            offset += 8
        
        # Add payload if present
        if offset < len(packet.raw_data):
            payload_len = len(packet.raw_data) - offset
            struct_dict['payload'] = f"[{payload_len} bytes]"
            self._flattened_data.append({
                'name': 'payload',
                'start': offset,
                'end': len(packet.raw_data),
                'value': f"[{payload_len} bytes]",
                'raw_data': packet.raw_data[offset:],
            })
        
        # Update hex view highlighting
        if self._flattened_data:
            colors = neon_background_colors(len(self._flattened_data))
            hex_view.elements = (self._flattened_data, colors)
        
        # Update structure tree
        tree = self.query_one("#construct-tree", ReactiveConstructTree)
        tree.parsed_data = struct_dict
        
        self.log_message(f"Packet {packet_idx + 1}: {packet.protocol} {packet.src_addr} → {packet.dst_addr}")
    
    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes"""
        if event.input.id == "search-input":
            self.search_query = event.value
            self._apply_filter()
    
    def on_input_submitted(self, event: Input.Submitted):
        """Handle search submission"""
        if event.input.id == "search-input":
            # Move focus to packet table
            self.query_one("#packet-table").focus()
    
    def _apply_filter(self):
        """Apply search filter to packets"""
        query = self.search_query.lower().strip()
        
        if not query:
            self.filtered_indices = list(range(len(self.packets)))
        else:
            self.filtered_indices = []
            for i, packet in enumerate(self.packets):
                # Match against various fields
                if self._packet_matches(packet, query):
                    self.filtered_indices.append(i)
        
        self._populate_table()
        
        # Select first matching packet
        if self.filtered_indices:
            self._select_packet(self.filtered_indices[0])
    
    def _packet_matches(self, packet: ParsedPacket, query: str) -> bool:
        """Check if packet matches search query"""
        # Protocol match
        if query in packet.protocol.lower():
            return True
        
        # Address match
        if query in packet.src_addr.lower() or query in packet.dst_addr.lower():
            return True
        
        # Layer name match
        for layer in packet.layers.keys():
            if query in layer.lower():
                return True
        
        # Port match
        if 'tcp' in packet.layers:
            tcp = packet.layers['tcp']
            if query == str(tcp.get('src_port')) or query == str(tcp.get('dst_port')):
                return True
            if f"port {query}" in f"port {tcp.get('src_port')}" or f"port {query}" in f"port {tcp.get('dst_port')}":
                return True
        
        if 'udp' in packet.layers:
            udp = packet.layers['udp']
            if query == str(udp.get('src_port')) or query == str(udp.get('dst_port')):
                return True
        
        # Info match
        if query in packet.info.lower():
            return True
        
        # Field path fuzzy match
        for field in packet.fields:
            if query in field.path.lower() or query in field.name.lower():
                return True
        
        return False
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle packet selection from table"""
        if event.row_key:
            packet_idx = int(event.row_key.value)
            self._select_packet(packet_idx)
    
    def log_message(self, msg: str):
        """Log a message"""
        try:
            log = self.query_one("#log-panel", Log)
            log.write_line(msg)
        except Exception:
            pass
    
    # Actions
    
    def action_export_svg(self):
        """Export current packet as SVG"""
        if not self._flattened_data or self.selected_packet_index < 0:
            self.log_message("No packet selected")
            return
        
        packet = self.packets[self.selected_packet_index]
        filename = f"packet_{self.selected_packet_index + 1}_{packet.protocol}.svg"
        
        try:
            svg_content = create_svg(
                self._flattened_data,
                self._current_raw_data,
                title=f"Packet_{self.selected_packet_index + 1}_{packet.protocol}"
            )
            
            with open(filename, 'w') as f:
                f.write(svg_content)
            
            self.log_message(f"Exported: {filename}")
            self.notify(f"Saved {filename}")
        except Exception as e:
            self.log_message(f"Export error: {e}")
    
    def action_toggle_log(self):
        """Toggle log panel"""
        log = self.query_one("#log-panel", Log)
        log.toggle_class("visible")
    
    def action_focus_search(self):
        """Focus the search input"""
        self.query_one("#search-input", Input).focus()
    
    def action_clear_search(self):
        """Clear search and show all packets"""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.search_query = ""
        self._apply_filter()
        self.query_one("#packet-table").focus()
    
    def action_next_packet(self):
        """Select next packet"""
        table = self.query_one("#packet-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.filtered_indices) - 1:
            table.move_cursor(row=table.cursor_row + 1)
            new_idx = self.filtered_indices[table.cursor_row]
            self._select_packet(new_idx)
    
    def action_prev_packet(self):
        """Select previous packet"""
        table = self.query_one("#packet-table", DataTable)
        if table.cursor_row is not None and table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)
            new_idx = self.filtered_indices[table.cursor_row]
            self._select_packet(new_idx)
    
    def action_first_packet(self):
        """Select first packet"""
        table = self.query_one("#packet-table", DataTable)
        if self.filtered_indices:
            table.move_cursor(row=0)
            self._select_packet(self.filtered_indices[0])
    
    def action_last_packet(self):
        """Select last packet"""
        table = self.query_one("#packet-table", DataTable)
        if self.filtered_indices:
            table.move_cursor(row=len(self.filtered_indices) - 1)
            self._select_packet(self.filtered_indices[-1])


def main():
    """Entry point for PCAP viewer"""
    import sys
    
    pcap_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = PCAPViewerApp(pcap_file=pcap_file)
    app.run()


if __name__ == "__main__":
    main()

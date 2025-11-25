"""
PCAP File Parser for BinTV

Provides parsing for PCAP/PCAPNG files and common network protocols
using the construct library for binary parsing.
"""

from construct import *
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Tuple
from enum import IntEnum
import struct
import io


# ============================================================================
# Enums for Protocol Fields
# ============================================================================

class EtherType(IntEnum):
    IPv4 = 0x0800
    ARP = 0x0806
    IPv6 = 0x86DD
    VLAN = 0x8100
    LLDP = 0x88CC


class IPProtocol(IntEnum):
    ICMP = 1
    TCP = 6
    UDP = 17
    ICMPv6 = 58


class TCPFlags(IntEnum):
    FIN = 0x01
    SYN = 0x02
    RST = 0x04
    PSH = 0x08
    ACK = 0x10
    URG = 0x20
    ECE = 0x40
    CWR = 0x80


# ============================================================================
# Protocol Constructs
# ============================================================================

# Ethernet Frame Header
EthernetHeader = Struct(
    "dst_mac" / Bytes(6),
    "src_mac" / Bytes(6),
    "ethertype" / Int16ub,
)

# IPv4 Header
IPv4Header = Struct(
    "version_ihl" / Int8ub,
    "version" / Computed(this.version_ihl >> 4),
    "ihl" / Computed(this.version_ihl & 0x0F),
    "dscp_ecn" / Int8ub,
    "total_length" / Int16ub,
    "identification" / Int16ub,
    "flags_fragment" / Int16ub,
    "flags" / Computed((this.flags_fragment >> 13) & 0x07),
    "fragment_offset" / Computed(this.flags_fragment & 0x1FFF),
    "ttl" / Int8ub,
    "protocol" / Int8ub,
    "checksum" / Int16ub,
    "src_ip" / Bytes(4),
    "dst_ip" / Bytes(4),
    "options" / If(this.ihl > 5, Bytes((this.ihl - 5) * 4)),
)

# IPv6 Header
IPv6Header = Struct(
    "version_tc_fl" / Int32ub,
    "version" / Computed((this.version_tc_fl >> 28) & 0x0F),
    "traffic_class" / Computed((this.version_tc_fl >> 20) & 0xFF),
    "flow_label" / Computed(this.version_tc_fl & 0xFFFFF),
    "payload_length" / Int16ub,
    "next_header" / Int8ub,
    "hop_limit" / Int8ub,
    "src_ip" / Bytes(16),
    "dst_ip" / Bytes(16),
)

# TCP Header
TCPHeader = Struct(
    "src_port" / Int16ub,
    "dst_port" / Int16ub,
    "seq_num" / Int32ub,
    "ack_num" / Int32ub,
    "data_offset_flags" / Int16ub,
    "data_offset" / Computed((this.data_offset_flags >> 12) & 0x0F),
    "flags" / Computed(this.data_offset_flags & 0x01FF),
    "window_size" / Int16ub,
    "checksum" / Int16ub,
    "urgent_pointer" / Int16ub,
    "options" / If(this.data_offset > 5, Bytes((this.data_offset - 5) * 4)),
)

# UDP Header
UDPHeader = Struct(
    "src_port" / Int16ub,
    "dst_port" / Int16ub,
    "length" / Int16ub,
    "checksum" / Int16ub,
)

# ICMP Header
ICMPHeader = Struct(
    "type" / Int8ub,
    "code" / Int8ub,
    "checksum" / Int16ub,
    "rest_of_header" / Bytes(4),
)

# ARP Header
ARPHeader = Struct(
    "hw_type" / Int16ub,
    "proto_type" / Int16ub,
    "hw_len" / Int8ub,
    "proto_len" / Int8ub,
    "operation" / Int16ub,
    "sender_hw_addr" / Bytes(6),
    "sender_proto_addr" / Bytes(4),
    "target_hw_addr" / Bytes(6),
    "target_proto_addr" / Bytes(4),
)

# DNS Header
DNSHeader = Struct(
    "transaction_id" / Int16ub,
    "flags" / Int16ub,
    "qr" / Computed((this.flags >> 15) & 1),
    "opcode" / Computed((this.flags >> 11) & 0xF),
    "aa" / Computed((this.flags >> 10) & 1),
    "tc" / Computed((this.flags >> 9) & 1),
    "rd" / Computed((this.flags >> 8) & 1),
    "ra" / Computed((this.flags >> 7) & 1),
    "rcode" / Computed(this.flags & 0xF),
    "questions" / Int16ub,
    "answers" / Int16ub,
    "authority" / Int16ub,
    "additional" / Int16ub,
)

# HTTP Request Line (simplified)
HTTPRequestLine = Struct(
    "raw_line" / GreedyBytes,
)


# ============================================================================
# PCAP File Format Constructs
# ============================================================================

# PCAP Global Header
PCAPGlobalHeader = Struct(
    "magic_number" / Int32ub,
    "version_major" / Int16ul,
    "version_minor" / Int16ul,
    "thiszone" / Int32sl,
    "sigfigs" / Int32ul,
    "snaplen" / Int32ul,
    "network" / Int32ul,
)

# PCAP Packet Header
PCAPPacketHeader = Struct(
    "ts_sec" / Int32ul,
    "ts_usec" / Int32ul,
    "incl_len" / Int32ul,
    "orig_len" / Int32ul,
)

# PCAPNG Section Header Block
PCAPNGSectionHeader = Struct(
    "block_type" / Const(b"\x0a\x0d\x0d\x0a"),
    "block_length" / Int32ul,
    "byte_order_magic" / Int32ub,
    "major_version" / Int16ul,
    "minor_version" / Int16ul,
    "section_length" / Int64sl,
)


# ============================================================================
# Packet Data Classes
# ============================================================================

@dataclass
class ParsedField:
    """A single parsed field from a packet"""
    name: str
    path: str  # Full path like "ethernet.ipv4.tcp.src_port"
    value: Any
    raw_bytes: bytes
    offset: int
    size: int
    layer: str  # ethernet, ipv4, tcp, etc.
    
    def matches(self, query: str) -> float:
        """Return fuzzy match score (0-1) against query"""
        query = query.lower()
        name_lower = self.name.lower()
        path_lower = self.path.lower()
        
        # Exact match
        if query == name_lower or query == path_lower:
            return 1.0
        
        # Starts with
        if name_lower.startswith(query) or path_lower.startswith(query):
            return 0.9
        
        # Contains
        if query in name_lower or query in path_lower:
            return 0.7
        
        # Fuzzy substring match
        score = self._fuzzy_match(query, name_lower)
        path_score = self._fuzzy_match(query, path_lower)
        return max(score, path_score)
    
    def _fuzzy_match(self, query: str, text: str) -> float:
        """Simple fuzzy matching algorithm"""
        if not query:
            return 0.0
        
        query_idx = 0
        matches = 0
        
        for char in text:
            if query_idx < len(query) and char == query[query_idx]:
                matches += 1
                query_idx += 1
        
        if query_idx == len(query):
            # All query chars found in order
            return 0.5 + (0.3 * matches / len(text))
        
        return 0.0


@dataclass 
class ParsedPacket:
    """A fully parsed network packet"""
    index: int
    timestamp: float
    raw_data: bytes
    layers: Dict[str, Any] = field(default_factory=dict)
    fields: List[ParsedField] = field(default_factory=list)
    summary: str = ""
    
    @property
    def src_addr(self) -> str:
        """Get source address (IP or MAC)"""
        if 'ipv4' in self.layers:
            return self._format_ip(self.layers['ipv4'].get('src_ip', b''))
        if 'ipv6' in self.layers:
            return self._format_ipv6(self.layers['ipv6'].get('src_ip', b''))
        if 'ethernet' in self.layers:
            return self._format_mac(self.layers['ethernet'].get('src_mac', b''))
        return ""
    
    @property
    def dst_addr(self) -> str:
        """Get destination address (IP or MAC)"""
        if 'ipv4' in self.layers:
            return self._format_ip(self.layers['ipv4'].get('dst_ip', b''))
        if 'ipv6' in self.layers:
            return self._format_ipv6(self.layers['ipv6'].get('dst_ip', b''))
        if 'ethernet' in self.layers:
            return self._format_mac(self.layers['ethernet'].get('dst_mac', b''))
        return ""
    
    @property
    def protocol(self) -> str:
        """Get the highest layer protocol name"""
        if 'dns' in self.layers:
            return "DNS"
        if 'http' in self.layers:
            return "HTTP"
        if 'tcp' in self.layers:
            return "TCP"
        if 'udp' in self.layers:
            return "UDP"
        if 'icmp' in self.layers:
            return "ICMP"
        if 'arp' in self.layers:
            return "ARP"
        if 'ipv6' in self.layers:
            return "IPv6"
        if 'ipv4' in self.layers:
            return "IPv4"
        return "ETH"
    
    @property
    def info(self) -> str:
        """Get packet info string"""
        if self.summary:
            return self.summary
        
        parts = []
        if 'tcp' in self.layers:
            tcp = self.layers['tcp']
            parts.append(f"{tcp.get('src_port', '?')} → {tcp.get('dst_port', '?')}")
            flags = tcp.get('flags', 0)
            flag_str = []
            if flags & TCPFlags.SYN: flag_str.append('SYN')
            if flags & TCPFlags.ACK: flag_str.append('ACK')
            if flags & TCPFlags.FIN: flag_str.append('FIN')
            if flags & TCPFlags.RST: flag_str.append('RST')
            if flags & TCPFlags.PSH: flag_str.append('PSH')
            if flag_str:
                parts.append(f"[{','.join(flag_str)}]")
        elif 'udp' in self.layers:
            udp = self.layers['udp']
            parts.append(f"{udp.get('src_port', '?')} → {udp.get('dst_port', '?')}")
        elif 'arp' in self.layers:
            arp = self.layers['arp']
            op = "Request" if arp.get('operation') == 1 else "Reply"
            parts.append(f"ARP {op}")
        
        return " ".join(parts) if parts else f"{len(self.raw_data)} bytes"
    
    @staticmethod
    def _format_ip(ip_bytes: bytes) -> str:
        if len(ip_bytes) == 4:
            return ".".join(str(b) for b in ip_bytes)
        return ""
    
    @staticmethod
    def _format_ipv6(ip_bytes: bytes) -> str:
        if len(ip_bytes) == 16:
            parts = []
            for i in range(0, 16, 2):
                parts.append(f"{ip_bytes[i]:02x}{ip_bytes[i+1]:02x}")
            return ":".join(parts)
        return ""
    
    @staticmethod
    def _format_mac(mac_bytes: bytes) -> str:
        if len(mac_bytes) == 6:
            return ":".join(f"{b:02x}" for b in mac_bytes)
        return ""
    
    def search_fields(self, query: str, min_score: float = 0.3) -> List[Tuple[ParsedField, float]]:
        """Search fields by fuzzy query, return (field, score) pairs"""
        results = []
        for f in self.fields:
            score = f.matches(query)
            if score >= min_score:
                results.append((f, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def get_construct(self) -> Struct:
        """Generate a construct Struct for this packet's layers"""
        parts = []
        
        if 'ethernet' in self.layers:
            parts.append("ethernet" / EthernetHeader)
        
        if 'ipv4' in self.layers:
            parts.append("ipv4" / IPv4Header)
        elif 'ipv6' in self.layers:
            parts.append("ipv6" / IPv6Header)
        elif 'arp' in self.layers:
            parts.append("arp" / ARPHeader)
        
        if 'tcp' in self.layers:
            parts.append("tcp" / TCPHeader)
        elif 'udp' in self.layers:
            parts.append("udp" / UDPHeader)
        elif 'icmp' in self.layers:
            parts.append("icmp" / ICMPHeader)
        
        # Add payload
        parts.append("payload" / GreedyBytes)
        
        return Struct(*parts)


# ============================================================================
# PCAP Parser Class
# ============================================================================

class PCAPParser:
    """Parser for PCAP and PCAPNG files"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.packets: List[ParsedPacket] = []
        self.global_header = None
        self.is_pcapng = False
        self._field_index: Dict[str, List[int]] = {}  # field_path -> packet indices
        
    def parse(self) -> List[ParsedPacket]:
        """Parse the PCAP file and return list of packets"""
        with open(self.filepath, 'rb') as f:
            data = f.read()
        
        # Detect file format
        magic = struct.unpack('>I', data[:4])[0]
        
        if magic == 0xA1B2C3D4:  # Big-endian PCAP
            self._parse_pcap(data, big_endian=True)
        elif magic == 0xD4C3B2A1:  # Little-endian PCAP
            self._parse_pcap(data, big_endian=False)
        elif magic == 0x0A0D0D0A:  # PCAPNG
            self._parse_pcapng(data)
        else:
            raise ValueError(f"Unknown file format: magic={magic:08x}")
        
        # Build field index for fast searching
        self._build_field_index()
        
        return self.packets
    
    def _parse_pcap(self, data: bytes, big_endian: bool = False):
        """Parse classic PCAP format"""
        endian = '>' if big_endian else '<'
        
        # Parse global header (24 bytes)
        magic, ver_maj, ver_min, tz, sigfigs, snaplen, network = struct.unpack(
            f'{endian}IHHiIII', data[:24]
        )
        
        self.global_header = {
            'magic': magic,
            'version_major': ver_maj,
            'version_minor': ver_min,
            'timezone': tz,
            'snaplen': snaplen,
            'network': network,
        }
        
        # Parse packets
        offset = 24
        packet_idx = 0
        
        while offset < len(data) - 16:
            # Packet header (16 bytes)
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack(
                f'{endian}IIII', data[offset:offset+16]
            )
            offset += 16
            
            if offset + incl_len > len(data):
                break
            
            # Packet data
            packet_data = data[offset:offset + incl_len]
            offset += incl_len
            
            # Parse the packet
            timestamp = ts_sec + (ts_usec / 1_000_000)
            packet = self._parse_packet(packet_idx, timestamp, packet_data)
            self.packets.append(packet)
            packet_idx += 1
        
    def _parse_pcapng(self, data: bytes):
        """Parse PCAPNG format (simplified)"""
        self.is_pcapng = True
        offset = 0
        packet_idx = 0
        
        while offset < len(data) - 8:
            block_type = struct.unpack('<I', data[offset:offset+4])[0]
            block_len = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            if block_len < 12 or offset + block_len > len(data):
                break
            
            if block_type == 0x00000006:  # Enhanced Packet Block
                # Parse EPB
                if block_len >= 32:
                    interface_id = struct.unpack('<I', data[offset+8:offset+12])[0]
                    ts_high = struct.unpack('<I', data[offset+12:offset+16])[0]
                    ts_low = struct.unpack('<I', data[offset+16:offset+20])[0]
                    cap_len = struct.unpack('<I', data[offset+20:offset+24])[0]
                    orig_len = struct.unpack('<I', data[offset+24:offset+28])[0]
                    
                    packet_data = data[offset+28:offset+28+cap_len]
                    timestamp = (ts_high << 32 | ts_low) / 1_000_000
                    
                    packet = self._parse_packet(packet_idx, timestamp, packet_data)
                    self.packets.append(packet)
                    packet_idx += 1
            
            offset += block_len
    
    def _parse_packet(self, index: int, timestamp: float, data: bytes) -> ParsedPacket:
        """Parse a single packet's protocol layers"""
        packet = ParsedPacket(
            index=index,
            timestamp=timestamp,
            raw_data=data,
        )
        
        offset = 0
        
        # Layer 2: Ethernet
        if len(data) >= 14:
            try:
                eth = EthernetHeader.parse(data[offset:offset+14])
                packet.layers['ethernet'] = {
                    'dst_mac': eth.dst_mac,
                    'src_mac': eth.src_mac,
                    'ethertype': eth.ethertype,
                }
                self._add_fields(packet, 'ethernet', eth, offset)
                offset += 14
                ethertype = eth.ethertype
            except Exception:
                return packet
        else:
            return packet
        
        # Layer 3: Network
        if ethertype == EtherType.IPv4 and len(data) >= offset + 20:
            try:
                ipv4 = IPv4Header.parse(data[offset:])
                ihl = ipv4.ihl * 4
                packet.layers['ipv4'] = {
                    'version': ipv4.version,
                    'ihl': ipv4.ihl,
                    'total_length': ipv4.total_length,
                    'ttl': ipv4.ttl,
                    'protocol': ipv4.protocol,
                    'src_ip': ipv4.src_ip,
                    'dst_ip': ipv4.dst_ip,
                }
                self._add_fields(packet, 'ipv4', ipv4, offset)
                offset += ihl
                next_proto = ipv4.protocol
            except Exception:
                return packet
        elif ethertype == EtherType.IPv6 and len(data) >= offset + 40:
            try:
                ipv6 = IPv6Header.parse(data[offset:offset+40])
                packet.layers['ipv6'] = {
                    'version': ipv6.version,
                    'payload_length': ipv6.payload_length,
                    'next_header': ipv6.next_header,
                    'hop_limit': ipv6.hop_limit,
                    'src_ip': ipv6.src_ip,
                    'dst_ip': ipv6.dst_ip,
                }
                self._add_fields(packet, 'ipv6', ipv6, offset)
                offset += 40
                next_proto = ipv6.next_header
            except Exception:
                return packet
        elif ethertype == EtherType.ARP and len(data) >= offset + 28:
            try:
                arp = ARPHeader.parse(data[offset:offset+28])
                packet.layers['arp'] = {
                    'operation': arp.operation,
                    'sender_hw_addr': arp.sender_hw_addr,
                    'sender_proto_addr': arp.sender_proto_addr,
                    'target_hw_addr': arp.target_hw_addr,
                    'target_proto_addr': arp.target_proto_addr,
                }
                self._add_fields(packet, 'arp', arp, offset)
            except Exception:
                pass
            return packet
        else:
            return packet
        
        # Layer 4: Transport
        if next_proto == IPProtocol.TCP and len(data) >= offset + 20:
            try:
                tcp = TCPHeader.parse(data[offset:])
                data_off = tcp.data_offset * 4
                packet.layers['tcp'] = {
                    'src_port': tcp.src_port,
                    'dst_port': tcp.dst_port,
                    'seq_num': tcp.seq_num,
                    'ack_num': tcp.ack_num,
                    'data_offset': tcp.data_offset,
                    'flags': tcp.flags,
                    'window_size': tcp.window_size,
                }
                self._add_fields(packet, 'tcp', tcp, offset)
                offset += data_off
                
                # Check for HTTP
                if tcp.src_port in (80, 8080) or tcp.dst_port in (80, 8080):
                    if len(data) > offset and data[offset:offset+4] in (b'HTTP', b'GET ', b'POST', b'HEAD', b'PUT '):
                        packet.layers['http'] = {'detected': True}
                
                # Check for DNS over TCP
                if tcp.src_port == 53 or tcp.dst_port == 53:
                    if len(data) > offset + 14:
                        try:
                            dns = DNSHeader.parse(data[offset+2:offset+14])
                            packet.layers['dns'] = {
                                'transaction_id': dns.transaction_id,
                                'qr': dns.qr,
                                'questions': dns.questions,
                                'answers': dns.answers,
                            }
                            self._add_fields(packet, 'dns', dns, offset+2)
                        except Exception:
                            pass
                            
            except Exception:
                return packet
                
        elif next_proto == IPProtocol.UDP and len(data) >= offset + 8:
            try:
                udp = UDPHeader.parse(data[offset:offset+8])
                packet.layers['udp'] = {
                    'src_port': udp.src_port,
                    'dst_port': udp.dst_port,
                    'length': udp.length,
                }
                self._add_fields(packet, 'udp', udp, offset)
                offset += 8
                
                # Check for DNS
                if udp.src_port == 53 or udp.dst_port == 53:
                    if len(data) > offset + 12:
                        try:
                            dns = DNSHeader.parse(data[offset:offset+12])
                            packet.layers['dns'] = {
                                'transaction_id': dns.transaction_id,
                                'qr': dns.qr,
                                'questions': dns.questions,
                                'answers': dns.answers,
                            }
                            self._add_fields(packet, 'dns', dns, offset)
                        except Exception:
                            pass
                            
            except Exception:
                return packet
                
        elif next_proto == IPProtocol.ICMP and len(data) >= offset + 8:
            try:
                icmp = ICMPHeader.parse(data[offset:offset+8])
                packet.layers['icmp'] = {
                    'type': icmp.type,
                    'code': icmp.code,
                }
                self._add_fields(packet, 'icmp', icmp, offset)
            except Exception:
                pass
        
        # Add payload info
        if offset < len(data):
            packet.layers['payload'] = {
                'offset': offset,
                'length': len(data) - offset,
            }
        
        return packet
    
    def _add_fields(self, packet: ParsedPacket, layer: str, parsed: Container, base_offset: int):
        """Extract fields from a parsed construct Container"""
        for name, value in parsed.items():
            if name.startswith('_') or name in ('offset1', 'offset2'):
                continue
            
            path = f"{layer}.{name}"
            
            # Determine size and raw bytes
            # This is approximate - construct doesn't always expose exact offsets
            if isinstance(value, bytes):
                size = len(value)
                raw = value
            elif isinstance(value, int):
                if value < 256:
                    size = 1
                elif value < 65536:
                    size = 2
                elif value < 4294967296:
                    size = 4
                else:
                    size = 8
                raw = b''
            else:
                size = 0
                raw = b''
            
            field = ParsedField(
                name=name,
                path=path,
                value=value,
                raw_bytes=raw,
                offset=base_offset,  # Approximate
                size=size,
                layer=layer,
            )
            packet.fields.append(field)
    
    def _build_field_index(self):
        """Build index of field paths to packet indices for fast searching"""
        self._field_index.clear()
        
        for i, packet in enumerate(self.packets):
            for field in packet.fields:
                if field.path not in self._field_index:
                    self._field_index[field.path] = []
                self._field_index[field.path].append(i)
    
    def search_all_packets(self, query: str, min_score: float = 0.3) -> List[Tuple[int, ParsedField, float]]:
        """Search all packets for fields matching query"""
        results = []
        
        for i, packet in enumerate(self.packets):
            for field, score in packet.search_fields(query, min_score):
                results.append((i, field, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def filter_packets(self, expression: str) -> List[int]:
        """
        Filter packets by expression (simplified Wireshark-like syntax)
        
        Examples:
            tcp.src_port == 80
            ip.src == 192.168.1.1
            tcp.flags.syn == 1
        """
        matching = []
        
        # Parse expression (very simplified)
        parts = expression.split()
        if len(parts) >= 3:
            field_path = parts[0]
            operator = parts[1]
            value = parts[2]
            
            for i, packet in enumerate(self.packets):
                for field in packet.fields:
                    if field.path == field_path or field.name == field_path:
                        try:
                            field_val = field.value
                            if operator == '==':
                                if str(field_val) == value or field_val == int(value):
                                    matching.append(i)
                            elif operator == '!=':
                                if str(field_val) != value and field_val != int(value):
                                    matching.append(i)
                            elif operator == '>':
                                if isinstance(field_val, int) and field_val > int(value):
                                    matching.append(i)
                            elif operator == '<':
                                if isinstance(field_val, int) and field_val < int(value):
                                    matching.append(i)
                        except (ValueError, TypeError):
                            pass
        
        return list(set(matching))  # Remove duplicates


def format_mac(mac_bytes: bytes) -> str:
    """Format MAC address bytes as string"""
    return ":".join(f"{b:02x}" for b in mac_bytes)


def format_ip(ip_bytes: bytes) -> str:
    """Format IPv4 address bytes as string"""
    return ".".join(str(b) for b in ip_bytes)


def format_ipv6(ip_bytes: bytes) -> str:
    """Format IPv6 address bytes as string"""
    parts = []
    for i in range(0, 16, 2):
        parts.append(f"{ip_bytes[i]:02x}{ip_bytes[i+1]:02x}")
    return ":".join(parts)

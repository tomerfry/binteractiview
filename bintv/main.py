import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description="BinTV - Binary Structure Viewer and PCAP Analyzer"
    )
    parser.add_argument(
        "-t", "--target", 
        help="Target file (binary or PCAP)"
    )
    parser.add_argument(
        "-p", "--pcap",
        action="store_true",
        help="Force PCAP mode (auto-detected for .pcap/.pcapng files)"
    )
    parser.add_argument(
        "-e", "--export",
        help="Export SVG visualization to file"
    )
    return parser.parse_args()


def is_pcap_file(filepath: str) -> bool:
    """Check if file is a PCAP/PCAPNG based on extension or magic bytes"""
    if not filepath:
        return False
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.pcap', '.pcapng', '.cap'):
        return True
    
    # Check magic bytes
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            # PCAP magic bytes (big and little endian)
            if magic in (b'\xa1\xb2\xc3\xd4', b'\xd4\xc3\xb2\xa1'):
                return True
            # PCAPNG magic
            if magic == b'\x0a\x0d\x0d\x0a':
                return True
    except Exception:
        pass
    
    return False


def main():
    args = parse_args()
    
    # Determine which app to run
    use_pcap = args.pcap or is_pcap_file(args.target)
    
    if use_pcap:
        from bintv.pcap_app import PCAPViewerApp
        app = PCAPViewerApp(pcap_file=args.target)
    else:
        from bintv.app import BintvApp
        app = BintvApp(args.target)
    
    app.run()


if __name__ == '__main__':
    main()

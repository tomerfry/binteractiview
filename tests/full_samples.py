"""Generate full-file format examples and valid sample bytes."""
from pathlib import Path
import json, io, zipfile, tarfile, gzip, struct, zlib

formats = {}
def add(key, name, code, sample):
    formats[key] = dict(name=name, description=name + ' with headers and file contents', code=code, sample=sample.hex())

chunk = lambda kind, data: struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',1,1,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(b'\0\xff\0\0')) + chunk(b'IEND', b'')
add('png', 'PNG Image', '''# https://www.w3.org/TR/png/
Chunk = Struct("length" / Int32ub, "type" / Bytes(4),
    "data" / Bytes(this.length), "crc" / Int32ub)
format_struct = Struct(
    "signature" / Const(bytes.fromhex("89504E470D0A1A0A")),
    "chunks" / RepeatUntil(lambda obj, lst, ctx: obj.type == b"IEND", Chunk),
    Terminated,
)
''', png)

buffer = io.BytesIO()
with zipfile.ZipFile(buffer,'w') as archive: archive.writestr(zipfile.ZipInfo('test.txt'), 'hello')
add('zip','ZIP Archive', '''# ZIP records, including the central directory and archive trailer.
# Classic ZIP; ZIP64 and streaming data descriptors require extensions.
Local = Struct("version" / Int16ul, "flags" / Int16ul,
    Check(lambda ctx: not ctx.flags & 8), "compression" / Int16ul,
    "mod_time" / Int16ul, "mod_date" / Int16ul, "crc32" / Int32ul,
    "compressed_size" / Int32ul, "uncompressed_size" / Int32ul,
    "filename_length" / Int16ul, "extra_length" / Int16ul,
    "filename" / Bytes(this.filename_length), "extra" / Bytes(this.extra_length),
    "data" / Bytes(this.compressed_size))
Central = Struct("made_by" / Int16ul, "version" / Int16ul,
    "flags" / Int16ul, "compression" / Int16ul, "mod_time" / Int16ul,
    "mod_date" / Int16ul, "crc32" / Int32ul, "compressed_size" / Int32ul,
    "uncompressed_size" / Int32ul, "filename_length" / Int16ul,
    "extra_length" / Int16ul, "comment_length" / Int16ul,
    "disk" / Int16ul, "internal_attributes" / Int16ul,
    "external_attributes" / Int32ul, "local_offset" / Int32ul,
    "filename" / Bytes(this.filename_length), "extra" / Bytes(this.extra_length),
    "comment" / Bytes(this.comment_length))
End = Struct("disk" / Int16ul, "central_disk" / Int16ul,
    "disk_entries" / Int16ul, "entries" / Int16ul,
    "central_size" / Int32ul, "central_offset" / Int32ul,
    "comment_length" / Int16ul, "comment" / Bytes(this.comment_length))
Record = Struct("signature" / Int32ul,
    "body" / Switch(this.signature, {0x04034b50: Local, 0x02014b50: Central, 0x06054b50: End}, default=Error))
format_struct = Struct("records" / RepeatUntil(lambda obj, lst, ctx: obj.signature == 0x06054b50, Record), Terminated)
''',buffer.getvalue())

add('gzip','GZIP File', '''# RFC 1952; single-member gzip, optional header fields and trailer.
format_struct = Struct(
    "magic" / Const(bytes.fromhex("1F8B")), "method" / Const(8, Byte),
    "flags" / Byte, "mtime" / Int32ul, "extra_flags" / Byte, "os" / Byte,
    "extra" / If(this.flags & 4, Prefixed(Int16ul, GreedyBytes)),
    "filename" / If(this.flags & 8, CString("utf8")),
    "comment" / If(this.flags & 16, CString("utf8")),
    "header_crc" / If(this.flags & 2, Int16ul),
    "compressed_data" / Bytes(lambda ctx: len(ctx.compressed_data) if ctx._building else stream_size(ctx._io) - ctx._io.tell() - 8),
    "crc32" / Int32ul, "uncompressed_size" / Int32ul, Terminated,
)
''',gzip.compress(b'hello',mtime=0))

buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as archive:
    info=tarfile.TarInfo('test.txt'); info.size=5; archive.addfile(info,io.BytesIO(b'hello'))
add('tar','TAR Archive (POSIX)', '''# POSIX ustar entries, padded contents and end blocks.
Header = Struct("name" / Bytes(100), "mode" / Bytes(8), "uid" / Bytes(8),
    "gid" / Bytes(8), "size" / Bytes(12), "mtime" / Bytes(12),
    "checksum" / Bytes(8), "typeflag" / Byte, "linkname" / Bytes(100),
    "magic" / Bytes(6), "version" / Bytes(2), "uname" / Bytes(32),
    "gname" / Bytes(32), "devmajor" / Bytes(8), "devminor" / Bytes(8),
    "prefix" / Bytes(155), "padding" / Bytes(12))
def tar_size(ctx):
    return int(ctx.header.size.rstrip(bytes([0,32])) or b"0", 8)
Entry = Struct("header" / Header,
    "data" / Bytes(tar_size), "padding" / Bytes(lambda ctx: -tar_size(ctx) % 512))
format_struct = Struct("entries" / RepeatUntil(lambda obj, lst, ctx: obj.header.name == bytes(100), Entry),
    "end_padding" / GreedyBytes, Terminated)
''',buffer.getvalue())

# A complete empty 64-bit ELF with no program/section tables.
elf=bytes.fromhex('7F454C46020101000000000000000000')+struct.pack('<HHIQQQIHHHHHH',2,62,1,0,64,64,0,64,56,0,64,0,0)
add('elf','ELF File (32/64-bit)', '''# ELF header, program/section tables and their file-backed contents.
Ident = Struct("magic" / Const(bytes.fromhex("7F454C46")), "class" / Byte,
    "endian" / Byte, "version" / Byte, "osabi" / Byte, "abiversion" / Byte, "padding" / Bytes(7))
def elf_body(bits, little):
    u16, u32, u64 = (Int16ul, Int32ul, Int64ul) if little else (Int16ub, Int32ub, Int64ub)
    word = u64 if bits == 64 else u32
    header = Struct("type" / u16, "machine" / u16, "version" / u32,
        "entry" / word, "phoff" / word, "shoff" / word, "flags" / u32,
        "ehsize" / u16, "phentsize" / u16, "phnum" / u16,
        "shentsize" / u16, "shnum" / u16, "shstrndx" / u16)
    ph = Struct("type" / u32,
        *(["flags" / u32] if bits == 64 else []),
        "offset" / word, "vaddr" / word, "paddr" / word, "filesz" / word, "memsz" / word,
        *(["flags" / u32] if bits == 32 else []), "align" / word,
        "data" / Pointer(this.offset, Bytes(this.filesz)))
    sh = Struct("name" / u32, "type" / u32, "flags" / word,
        "addr" / word, "offset" / word, "size" / word, "link" / u32,
        "info" / u32, "addralign" / word, "entsize" / word,
        "data" / If(this.type != 8, Pointer(this.offset, Bytes(this.size))))
    return Struct("header" / header,
        "program_headers" / Pointer(this.header.phoff, Array(this.header.phnum, FixedSized(this.header.phentsize, ph))),
        "section_headers" / Pointer(this.header.shoff, Array(this.header.shnum, FixedSized(this.header.shentsize, sh))),
        "file_body" / GreedyBytes)
format_struct = Struct("ident" / Ident,
    "body" / Switch(lambda ctx: (ctx.ident["class"], ctx.ident.endian),
        {(1,1): elf_body(32,True), (1,2): elf_body(32,False),
         (2,1): elf_body(64,True), (2,2): elf_body(64,False)}, default=Error), Terminated)
''',elf)

pe=b'MZ'+bytes(58)+struct.pack('<I',64)+b'PE\0\0'+struct.pack('<HHIIIHH',0x8664,0,0,0,0,0,2)
add('pe','PE File (Windows)', '''# PE/COFF file, optional header bytes, sections and overlay.
# https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
Section = Struct("name" / Bytes(8), "virtual_size" / Int32ul,
    "virtual_address" / Int32ul, "raw_size" / Int32ul, "raw_offset" / Int32ul,
    "relocations_offset" / Int32ul, "line_numbers_offset" / Int32ul,
    "relocations_count" / Int16ul, "line_numbers_count" / Int16ul,
    "characteristics" / Int32ul,
    "data" / Pointer(this.raw_offset, Bytes(this.raw_size)))
format_struct = Struct("dos_magic" / Const(b"MZ"), "dos_header" / Bytes(58),
    "pe_offset" / Int32ul, "dos_stub" / Bytes(this.pe_offset - 64),
    "signature" / Const(bytes.fromhex("50450000")), "machine" / Int16ul,
    "section_count" / Int16ul, "timestamp" / Int32ul,
    "symbol_table_offset" / Int32ul, "symbol_count" / Int32ul,
    "optional_header_size" / Int16ul, "characteristics" / Int16ul,
    "optional_header" / Bytes(this.optional_header_size),
    "sections" / Array(this.section_count, Section), "file_body" / GreedyBytes, Terminated)
''',pe)

# JPEG segment iteration includes entropy-coded scan bytes through EOI.
from PIL import Image
buffer=io.BytesIO()
Image.new('RGB',(1,1),(255,0,0)).save(buffer,format='JPEG')
add('jpeg','JPEG Image', '''# JPEG markers, segments and entropy-coded scans (including stuffed FF bytes).
class ScanBytes(Construct):
    def _parse(self, stream, context, path):
        start = stream.tell()
        while True:
            byte = stream.read(1)
            if not byte: raise StreamError("Missing JPEG end marker")
            if byte == bytes([255]):
                marker_start = stream.tell() - 1
                code = stream.read(1)
                while code == bytes([255]): code = stream.read(1)
                if code and (code[0] == 0 or 0xD0 <= code[0] <= 0xD7): continue
                end = marker_start
                stream.seek(start)
                data = stream.read(end - start)
                return data
    def _build(self, obj, stream, context, path):
        stream.write(obj)
        return obj
Segment = Struct("marker" / Int16ub,
    "body" / If(lambda ctx: ctx.marker not in [0xFFD8,0xFFD9,0xFF01] and not 0xFFD0 <= ctx.marker <= 0xFFD7,
        Struct("length" / Int16ub, "data" / Bytes(this.length - 2))),
    "scan" / If(this.marker == 0xFFDA, ScanBytes()))
format_struct = Struct("soi" / Const(bytes.fromhex("FFD8")),
    "segments" / RepeatUntil(lambda obj, lst, ctx: obj.marker == 0xFFD9, Segment), Terminated)
''',buffer.getvalue())

def cpio_entry(name, data):
    names=name.encode()+b'\0'
    numbers=[0,0o100644,0,0,1,0,len(data),0,0,0,0,len(names),0]
    header=b'070701'+b''.join(f'{n:08x}'.encode() for n in numbers)+names
    return header+bytes(-len(header)%4)+data+bytes(-len(data)%4)
add('cpio','CPIO Archive (newc)', '''# Complete newc archive, names, contents, alignment and trailer.
HexNumber = ExprAdapter(Bytes(8), lambda obj, ctx: int(obj,16), lambda obj, ctx: f"{obj:08x}".encode())
Entry = Struct("magic" / Bytes(6), Check(lambda ctx: ctx.magic in (b"070701",b"070702")),
    "ino" / HexNumber, "mode" / HexNumber, "uid" / HexNumber, "gid" / HexNumber,
    "nlink" / HexNumber, "mtime" / HexNumber, "filesize" / HexNumber,
    "devmajor" / HexNumber, "devminor" / HexNumber, "rdevmajor" / HexNumber,
    "rdevminor" / HexNumber, "namesize" / HexNumber, "check" / HexNumber,
    "name" / Bytes(this.namesize), "name_padding" / Bytes(lambda ctx: -(110 + ctx.namesize) % 4),
    "data" / Bytes(this.filesize), "data_padding" / Bytes(lambda ctx: -ctx.filesize % 4))
format_struct = Struct("entries" / RepeatUntil(lambda obj, lst, ctx: obj.name.rstrip(bytes([0])) == b"TRAILER!!!", Entry),
    "padding" / GreedyBytes, Terminated)
''',cpio_entry('test.txt',b'hello')+cpio_entry('TRAILER!!!',b''))

root=Path(__file__).resolve().parents[1]
output='// Generated by tests/full_samples.py. Full-file defaults.\n'
output+='Object.entries('+json.dumps(formats,indent=2)+').forEach(([key, value]) => Object.assign(CONSTRUCT_LIBRARY[key], value));\n'
output+='''
// Firmware images retain opaque filesystem data after the decoded superblock.
const squashHeader = CONSTRUCT_LIBRARY.squashfs.code.replace('format_struct =', 'Superblock =');
Object.assign(CONSTRUCT_LIBRARY.squashfs, {
    name: 'SquashFS Image',
    description: 'Superblock and complete filesystem bytes (tables remain raw)',
    code: squashHeader + '\\nformat_struct = Struct("superblock" / Superblock, "filesystem_data" / GreedyBytes)\\n',
    sample: '68737173' + '00'.repeat(92)
});
const extHeader = CONSTRUCT_LIBRARY.ext4.code.replace('format_struct =', 'SuperblockPrefix =');
Object.assign(CONSTRUCT_LIBRARY.ext4, {
    name: 'EXT2/3/4 Image',
    description: 'Boot area, complete superblock and filesystem bytes (tables remain raw)',
    code: extHeader + '\\nformat_struct = Struct("boot_area" / Bytes(1024), "superblock" / SuperblockPrefix, "superblock_extension" / Bytes(940), "filesystem_data" / GreedyBytes)\\n',
    sample: '00'.repeat(1024 + 56) + '53EF' + '00'.repeat(1024 - 58)
});
// Complete BOOTP/DHCP discover, with valid field lengths.
CONSTRUCT_LIBRARY.full_dhcp.sample = 'FFFFFFFFFFFF0011223344550800' +
    '45000110123400004011000000000000FFFFFFFF' + '0044004300FC0000' +
    '010106000000000100008000' + '00'.repeat(16) + '001122334455' +
    '00'.repeat(10 + 64 + 128) + '63825363350101FF';
'''
(root/'full-formats.js').write_text(output,encoding='utf-8')

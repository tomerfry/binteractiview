"""Sync the readable Python runtime into the standalone web page."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
page = root / 'index.html'
source = (root / 'web-runtime.py').read_text(encoding='utf-8')
text = page.read_text(encoding='utf-8')
text = re.sub(r'const PYTHON_BOOTSTRAP = `.*?`;', lambda _: 'const PYTHON_BOOTSTRAP = `\n' + source.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') + '`;', text, count=1, flags=re.S)
page.write_text(text, encoding='utf-8')

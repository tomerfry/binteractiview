"""Python runtime embedded into index.html by tests/sync_web.py."""
import json
import traceback
import copy
import math
from construct import *

_ui_roots = []
_ui_stack = []
_struct = None

def load_structure(code):
    global _struct
    _struct = None
    namespace = dict(globals())
    for name in ('format_struct', 'struct', 'packet', 'header'):
        namespace.pop(name, None)
    exec(code, namespace)
    for name in ('format_struct', 'struct', 'packet', 'header'):
        if isinstance(namespace.get(name), Construct):
            _struct = namespace[name]
            return
    raise ValueError('Define format_struct = Struct(...)')

def get_type_info(sc):
    if isinstance(sc, Renamed): return get_type_info(sc.subcon)
    if isinstance(sc, (Const, Computed, Rebuild)):
        return {'type': 'const', 'value': str(getattr(sc, 'value', 'automatic'))}
    if isinstance(sc, Enum): return {'type': 'enum', 'values': list(sc.encmapping)}
    if isinstance(sc, FlagsEnum): return {'type': 'json'}
    if isinstance(sc, StringEncoded): return {'type': 'string'}
    if isinstance(sc, Adapter): return {'type': 'json'}
    if isinstance(sc, FormatField):
        fmt = sc.fmtstr
        return {'type': 'float' if fmt[-1] in 'efd' else 'integer',
                'size': sc.length, 'signed': fmt[-1] in 'bhiq',
                'endian': 'little' if fmt[0] == '<' else 'big'}
    if sc is Flag: return {'type': 'boolean', 'size': 1}
    if isinstance(sc, Bytes):
        return {'type': 'bytes', 'size': sc.length if isinstance(sc.length, int) else None}
    if sc is GreedyBytes: return {'type': 'bytes', 'size': None}
    if isinstance(sc, (Array, GreedyRange, RepeatUntil, Struct, Switch, IfThenElse)):
        return {'type': 'json'}
    if isinstance(sc, Subconstruct): return get_type_info(sc.subcon)
    return {'type': 'json'}

class InstrumentedWrapper(Subconstruct):
    def __init__(self, subcon, name):
        super().__init__(subcon)
        self.name = name

    def _parse(self, stream, context, path):
        start = stream.tell()
        node = dict(name=self.name, children=[], offset=start, length=0,
                    value=None, rawValue=None, info=get_type_info(self.subcon))
        (_ui_stack[-1]['children'] if _ui_stack else _ui_roots).append(node)
        _ui_stack.append(node)
        try:
            obj = self.subcon._parse(stream, context, path)
            node['length'] = max(0, stream.tell() - start)
            if isinstance(obj, bytes):
                node['value'] = obj[:16].hex().upper() + (f'... ({len(obj)} bytes)' if len(obj) > 16 else '')
            elif isinstance(obj, (dict, list)):
                node['value'] = f'{len(obj)} items'
            else:
                node['value'] = str(obj)
                if isinstance(obj, (int, float, str, bool)):
                    node['rawValue'] = str(obj) if (isinstance(obj, int) and abs(obj) > 2**53 - 1) or (isinstance(obj, float) and not math.isfinite(obj)) else obj
            return obj
        finally:
            _ui_stack.pop()

def instrument_structure(sc, name=''):
    if isinstance(sc, Renamed): return instrument_structure(sc.subcon, sc.name)
    clone = copy.copy(sc)
    if isinstance(sc, Struct):
        clone.subcons = [instrument_structure(sub, sub.name) for sub in sc.subcons]
    elif isinstance(sc, Switch):
        clone.cases = {key: instrument_structure(sub, str(key)) for key, sub in sc.cases.items()}
        clone.default = instrument_structure(sc.default, 'default')
    elif isinstance(sc, IfThenElse):
        clone.thensubcon = instrument_structure(sc.thensubcon, name)
        clone.elsesubcon = instrument_structure(sc.elsesubcon, name)
    elif isinstance(sc, (Array, GreedyRange, RepeatUntil, Pointer)):
        clone.subcon = instrument_structure(sc.subcon, '')
    return InstrumentedWrapper(clone, name or type(sc).__name__)

def parse_fields(data):
    global _ui_roots, _ui_stack
    _ui_roots, _ui_stack = [], []
    instrument_structure(_struct, 'root').parse(bytes(data))
    return _ui_roots[0]['children'] or _ui_roots

def extract_schema(sc):
    fields = []
    def walk(sc, path):
        if isinstance(sc, Renamed):
            walk(sc.subcon, path + [sc.name])
        elif isinstance(sc, Struct):
            for sub in sc.subcons: walk(sub, path)
        elif path:
            fields.append(dict(id='.'.join(path), name=path[-1], path=path, info=get_type_info(sc)))
    walk(sc, [])
    return fields

def json_value(value):
    if isinstance(value, bytes): return value.hex()
    if isinstance(value, dict): return {k: json_value(v) for k, v in value.items() if not k.startswith('_')}
    if isinstance(value, list): return [json_value(v) for v in value]
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 2**53 - 1: return str(value)
    return value

def get_schema_json(data=None):
    schema = extract_schema(_struct)
    values = {}
    if data is not None:
        try:
            parsed = _struct.parse(bytes(data))
            for field in schema:
                value = parsed
                for part in field['path']: value = value[part]
                value = json_value(value)
                values[field['id']] = json.dumps(value) if field['info']['type'] == 'json' else value
        except Exception:
            pass  # A new definition may not match the currently open file.
    return {'schema': schema, 'values': values}

def convert_value(sc, value, context=None):
    if isinstance(sc, Renamed): return convert_value(sc.subcon, value, context)
    if isinstance(sc, FlagsEnum): return {key: convert_value(Flag, item) for key, item in value.items()}
    if isinstance(sc, Adapter) and not isinstance(sc, (StringEncoded, Enum)): return value
    if isinstance(sc, Struct):
        local = Container(value)
        local['_'] = context
        local['_root'] = context.get('_root', context) if context is not None else local
        result = Container()
        for sub in sc.subcons:
            if sub.name in value:
                result[sub.name] = convert_value(sub, value[sub.name], local)
                local[sub.name] = result[sub.name]
        return result
    if isinstance(sc, (Array, GreedyRange, RepeatUntil)):
        return [convert_value(sc.subcon, v, context) for v in value]
    if isinstance(sc, Switch):
        key = sc.keyfunc(context) if callable(sc.keyfunc) else sc.keyfunc
        return convert_value(sc.cases.get(key, sc.default), value, context)
    if isinstance(sc, IfThenElse):
        condition = sc.condfunc(context) if callable(sc.condfunc) else sc.condfunc
        return convert_value(sc.thensubcon if condition else sc.elsesubcon, value, context)
    info = get_type_info(sc)
    kind = info['type']
    if kind == 'bytes': return bytes.fromhex(value.removeprefix('0x')) if isinstance(value, str) else bytes(value)
    if kind == 'integer':
        return int(value, 16 if value.lower().lstrip('+-').startswith('0x') else 10) if isinstance(value, str) else int(value)
    if kind == 'float': return float(value)
    if kind == 'boolean':
        if value in (True, 'true', '1', 1): return True
        if value in (False, 'false', '0', 0): return False
        raise ValueError('Boolean must be true or false')
    if isinstance(sc, Subconstruct) and kind == 'json': return convert_value(sc.subcon, value, context)
    return value

def build_and_parse_live(values_json):
    try:
        vals = json.loads(values_json)
        container = Container()
        for field in extract_schema(_struct):
            if field['info']['type'] == 'const' or field['id'] not in vals: continue
            value = vals[field['id']]
            if field['info']['type'] == 'json' and isinstance(value, str): value = json.loads(value)
            curr = container
            for part in field['path'][:-1]: curr = curr.setdefault(part, Container())
            curr[field['path'][-1]] = value
        data = _struct.build(convert_value(_struct, container))
        return {'hex': data.hex(), 'fields': parse_fields(data)}
    except Exception as exc:
        return {'error': str(exc), 'traceback': traceback.format_exc()}

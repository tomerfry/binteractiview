import types
import construct
from construct import *
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from construct.core import Path

def eval_with_rawcopy(construct_string):
    """Evaluate a construct string with RawCopy-wrapped primitives."""
    
    def SmartBytes(n):
        # For Path objects or callables, create a lambda that handles RawCopy values
        if isinstance(n, (Path, type(lambda: None))):
            def extract_value(ctx):
                # If n is a Path, resolve it first
                if isinstance(n, Path):
                    # Extract field name from path string like "this['a']" or "this.a"
                    path_str = str(n)
                    if '[' in path_str and ']' in path_str:
                        # Handle this['field'] or this["field"] format
                        start = path_str.find('[') + 1
                        end = path_str.find(']')
                        field_name = path_str[start:end].strip("'\"")
                    else:
                        # Handle this.field format
                        field_name = path_str.split('.')[-1]
                    
                    val = ctx[field_name]
                else:
                    # n is a callable
                    val = n(ctx)
                
                # Extract value from RawCopy if needed
                return getattr(val, 'value', val)
            
            return RawCopy(Bytes(extract_value))
        else:
            return RawCopy(Bytes(n))
    
    def SmartArray(n, subcon):
        if isinstance(n, (Path, type(lambda: None))):
            def extract_value(ctx):
                # If n is a Path, resolve it first
                if isinstance(n, Path):
                    # Extract field name from path string like "this['a']" or "this.a"
                    path_str = str(n)
                    if '[' in path_str and ']' in path_str:
                        # Handle this['field'] or this["field"] format
                        start = path_str.find('[') + 1
                        end = path_str.find(']')
                        field_name = path_str[start:end].strip("'\"")
                    else:
                        # Handle this.field format
                        field_name = path_str.split('.')[-1]
                    
                    val = ctx[field_name]
                else:
                    # n is a callable
                    val = n(ctx)
                
                # Extract value from RawCopy if needed
                return getattr(val, 'value', val)
            
            return RawCopy(Array(extract_value, subcon))
        else:
            return RawCopy(Array(n, subcon))
    
    namespace = {
        'Struct': Struct,
        'Sequence': Sequence,
        'Container': Container,
        'Union': Union,
        'this': this,
        'len_': len_,
        'RawCopy': RawCopy,
        
        # Wrapped primitives
        'Int8ub': RawCopy(Int8ub),
        'Int16ub': RawCopy(Int16ub),
        'Int32ub': RawCopy(Int32ub),
        'Int64ub': RawCopy(Int64ub),
        'Int8ul': RawCopy(Int8ul),
        'Int16ul': RawCopy(Int16ul),
        'Int32ul': RawCopy(Int32ul),
        'Int64ul': RawCopy(Int64ul),
        'Int8sb': RawCopy(Int8sb),
        'Int16sb': RawCopy(Int16sb),
        'Int32sb': RawCopy(Int32sb),
        'Int64sb': RawCopy(Int64sb),
        'Int8sl': RawCopy(Int8sl),
        'Int16sl': RawCopy(Int16sl),
        'Int32sl': RawCopy(Int32sl),
        'Int64sl': RawCopy(Int64sl),
        'Float32b': RawCopy(Float32b),
        'Float32l': RawCopy(Float32l),
        'Float64b': RawCopy(Float64b),
        'Float64l': RawCopy(Float64l),
        'Byte': RawCopy(Byte),
        'GreedyBytes': RawCopy(GreedyBytes),
        
        # Smart functions
        'Bytes': SmartBytes,
        'Array': SmartArray,
        'PascalString': lambda length_field, encoding=None: RawCopy(PascalString(length_field, encoding)),
        'CString': lambda encoding=None: RawCopy(CString(encoding)),
        'GreedyString': lambda encoding=None: RawCopy(GreedyString(encoding)),
        'PaddedString': lambda length, encoding=None: RawCopy(PaddedString(length, encoding)),
        'Const': lambda value, subcon=None: RawCopy(Const(value, subcon)),
        'Computed': lambda func: RawCopy(Computed(func)),
        'Rebuild': lambda subcon, func: RawCopy(Rebuild(subcon, func)),
    }
    
    return eval(construct_string, namespace)

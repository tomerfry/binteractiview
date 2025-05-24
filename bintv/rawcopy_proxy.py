import types
import construct
from construct import *
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def eval_with_rawcopy(construct_string):
    """Evaluate a construct string with RawCopy-wrapped primitives."""
    
    # Create custom namespace
    namespace = {
        # Keep these unwrapped
        'Struct': Struct,
        'Sequence': Sequence,
        'Container': Container,
        'Union': Union,
        'this': this,
        'len_': len_,
        'RawCopy': RawCopy,  # In case it's already in the string
        
        # Wrap primitives
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
        
        # Wrapped functions
        'Bytes': lambda n: RawCopy(Bytes(n)),
        'Array': lambda n, subcon: RawCopy(Array(n, subcon)),
        'PascalString': lambda length_field, encoding=None: RawCopy(PascalString(length_field, encoding)),
        'CString': lambda encoding=None: RawCopy(CString(encoding)),
        'GreedyString': lambda encoding=None: RawCopy(GreedyString(encoding)),
        'PaddedString': lambda length, encoding=None: RawCopy(PaddedString(length, encoding)),
        'Const': lambda value, subcon=None: RawCopy(Const(value, subcon)),
        'Computed': lambda func: RawCopy(Computed(func)),
        'Rebuild': lambda subcon, func: RawCopy(Rebuild(subcon, func)),
    }
    
    # Evaluate with custom namespace
    return eval(construct_string, namespace)


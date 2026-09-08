import unittest, json, sys, io
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.test-deps'))
runtime={}
exec((root/'web-runtime.py').read_text(), runtime)

class WebRuntimeTests(unittest.TestCase):
    def build(self, code, values):
        runtime['load_structure'](code)
        result=runtime['build_and_parse_live'](json.dumps(values))
        self.assertNotIn('error', result, result.get('error'))
        return result

    def test_dynamic_bytes_and_context(self):
        result=self.build('format_struct = Struct("size" / Int16ub, "data" / Bytes(this.size))', {'size':'2','data':'abcd'})
        self.assertEqual(result['hex'],'0002abcd')
        self.assertEqual(result['fields'][1]['offset'],2)

    def test_typed_values(self):
        result=self.build('format_struct = Struct("magic" / Const(b"OK"), "number" / Int64sl, "text" / CString("utf8"), "float" / Float32l, "flag" / Flag)',
                          {'number':'-9223372036854775808','text':'deadbeef','float':'1.5','flag':'false'})
        self.assertEqual(result['fields'][1]['rawValue'],'-9223372036854775808')
        self.assertEqual(result['fields'][2]['rawValue'],'deadbeef')
        self.assertEqual(result['fields'][3]['rawValue'],1.5)
        self.assertFalse(result['fields'][4]['rawValue'])
        self.assertEqual(result['fields'][1]['info']['endian'],'little')

    def test_nested_arrays(self):
        result=self.build('format_struct = Struct("items" / Array(2, Struct("id" / Byte, "data" / Bytes(1))))',
                          {'items':'[{"id":1,"data":"ab"},{"id":2,"data":"cd"}]'})
        self.assertEqual(result['hex'],'01ab02cd')

    def test_enum_flags_and_rebuild(self):
        result=self.build('format_struct = Struct("kind" / Enum(Byte, A=1, B=2), "flags" / FlagsEnum(Byte, x=1, y=2), "size" / Rebuild(Byte, len_(this.data)), "data" / Bytes(this.size))',
                          {'kind':'B','flags':'{"x":true,"y":false}','data':'abcd'})
        self.assertEqual(result['hex'],'020102abcd')

    def test_invalid_and_empty(self):
        result=self.build('format_struct = Struct("data" / GreedyBytes)', {'data':''})
        self.assertEqual(result['hex'],'')
        self.assertIn('error', runtime['build_and_parse_live']('{"data":"a"}'))

    def test_no_stale_struct(self):
        runtime['load_structure']('format_struct = Struct("a" / Byte)')
        runtime['load_structure']('packet = Struct("b" / Int16ub)')
        self.assertEqual(runtime['parse_fields'](b'\x00\x02')[0]['name'],'b')
        with self.assertRaises(ValueError): runtime['load_structure']('# empty')

    def test_existing_file_builder(self):
        samples=json.loads((root/'.test-deps/samples.json').read_text())
        for key in ('zip','png','tar','gzip','pe','elf','cpio'):
            with self.subTest(key=key):
                sample=samples[key]
                runtime['load_structure'](sample['code'])
                values=runtime['get_schema_json'](bytes.fromhex(sample['sample']))['values']
                result=runtime['build_and_parse_live'](json.dumps(values))
                self.assertNotIn('error',result,result.get('error'))
                self.assertEqual(result['hex'],sample['sample'].lower())

    def test_samples(self):
        samples=json.loads((root/'.test-deps/samples.json').read_text())
        for key, sample in samples.items():
            if sample.get('category') == 'Examples': continue
            with self.subTest(key=key):
                runtime['load_structure'](sample['code'])
                data=bytes.fromhex(sample['sample'])
                stream=io.BytesIO(data)
                runtime['_struct'].parse_stream(stream)
                self.assertEqual(stream.tell(), len(data), 'sample contains unparsed bytes')
                fields=runtime['parse_fields'](data)
                self.assertTrue(fields)

if __name__ == '__main__': unittest.main()

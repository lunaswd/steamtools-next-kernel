import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_kernel as kernel


class PackageTests(unittest.TestCase):
    def test_zip_is_deterministic_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory(prefix='kernel-package-test-') as tmp:
            root = Path(tmp)
            kernel.write_zip(root / 'a.zip', {'b.txt': b'B', 'a.txt': b'A'})
            kernel.write_zip(root / 'b.zip', {'a.txt': b'A', 'b.txt': b'B'})
            self.assertEqual((root / 'a.zip').read_bytes(), (root / 'b.zip').read_bytes())
            with zipfile.ZipFile(root / 'a.zip') as archive:
                self.assertEqual(archive.namelist(), ['a.txt', 'b.txt'])
                self.assertEqual(archive.read('a.txt'), b'A')

    def test_zip_rejects_traversal_and_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='kernel-package-test-') as tmp:
            path = Path(tmp) / 'a.zip'
            with self.assertRaises(ValueError):
                kernel.write_zip(path, {'../bad': b'A'})
            with self.assertRaises(ValueError):
                kernel.write_zip(path, {'ok': b'A'})

    def test_pe_requires_x64_dll(self):
        data = bytearray(128)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 64)
        data[64:68] = b'PE\0\0'
        struct.pack_into('<H', data, 68, 0x8664)
        struct.pack_into('<H', data, 86, 0x2000)
        kernel.require_x64_dll(data, 'valid.dll')
        struct.pack_into('<H', data, 68, 0x14c)
        with self.assertRaises(ValueError):
            kernel.require_x64_dll(data, 'x86.dll')
        with self.assertRaises(ValueError):
            kernel.require_x64_dll(b'not a DLL', 'invalid.dll')

    def test_manifest_hash_records(self):
        record = kernel.file_record('LICENSE', b'license')
        self.assertEqual(record['name'], 'LICENSE')
        self.assertEqual(record['sizeBytes'], 7)
        self.assertEqual(record['sha256'], kernel.digest(b'license'))
        self.assertEqual(json.loads(kernel.encode_json(record)), record)


if __name__ == '__main__':
    unittest.main()

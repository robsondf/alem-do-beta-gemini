import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_distribution import verify

class DistributionIntegrity(unittest.TestCase):
 def fixture(self,root):
  b=b'%PDF-1.4 current scientific edition';p=root/'edition.pdf';p.write_bytes(b)
  d={'edition':'editorial-v8-20261025','artifacts':{'edition.pdf':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}},'repository_files':{}}
  m=root/'manifest.json';m.write_text(json.dumps(d));return m,d
 def test_authentic_copy_passes(self):
  with tempfile.TemporaryDirectory() as name:
   r=Path(name);m,_=self.fixture(r);self.assertTrue(verify(r,m)['passed'])
 def test_old_pdf_with_same_name_and_size_fails(self):
  with tempfile.TemporaryDirectory() as name:
   r=Path(name);m,_=self.fixture(r);p=r/'edition.pdf';b=bytearray(p.read_bytes());b[-1]^=1;p.write_bytes(b)
   with self.assertRaisesRegex(ValueError,'Digest mismatch'):verify(r,m)
 def test_manifest_cannot_read_outside_release(self):
  with tempfile.TemporaryDirectory() as name:
   r=Path(name);m,d=self.fixture(r);d['artifacts']['../outside']=d['artifacts'].pop('edition.pdf');m.write_text(json.dumps(d))
   with self.assertRaisesRegex(ValueError,'Unsafe'):verify(r,m)

if __name__=='__main__':unittest.main()

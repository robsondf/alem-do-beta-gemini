#!/usr/bin/env python3
"""Read-only SHA-256 and ZIP verification, using Python's standard library."""
import argparse,hashlib,json,zipfile
from pathlib import Path

MANIFEST='distribution/manifest_v8_20261025.json'

def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inside(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe manifest path: '+name)
    target=(root/p).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Path escapes root: '+name)
    return target

def verify(root,manifest=None):
    root=Path(root).resolve();manifest=Path(manifest) if manifest else root/MANIFEST
    d=json.loads(manifest.read_text());assert d['edition']=='editorial-v8-20261025'
    total=0
    for group in ['artifacts','repository_files']:
        for name,item in d[group].items():
            path=inside(root,name)
            if not path.is_file():raise ValueError('Missing file: '+name)
            if path.stat().st_size!=item['bytes'] or sha256(path)!=item['sha256']:raise ValueError('Digest mismatch: '+name)
            total+=1
    for name,members in d.get('zip_members',{}).items():
        with zipfile.ZipFile(inside(root,name)) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC failure: '+name)
            if set(z.namelist())!=set(members):raise ValueError('ZIP member set differs: '+name)
            for member,item in members.items():
                inside(root,member) # reject archive traversal without extracting
                raw=z.read(member)
                if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('ZIP member differs: '+member)
    for name,expected in d.get('protected_production_pins',{}).items():
        if sha256(inside(root,name))!=expected:raise ValueError('Frozen production source differs: '+name)
    if d.get('pdf_equivalences'):
        for current,versioned in d['pdf_equivalences'].items():
            if inside(root,current).read_bytes()!=inside(root,versioned).read_bytes():raise ValueError('PDF copies differ: '+current)
    return dict(passed=True,edition=d['edition'],checked_files=total,checked_zip_members=sum(len(x) for x in d.get('zip_members',{}).values()),scope='byte identity and package integrity, not statistical or economic validation')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--manifest',type=Path);a=p.parse_args()
    try:print(json.dumps(verify(a.root,a.manifest),indent=2))
    except (ValueError,AssertionError,KeyError,zipfile.BadZipFile) as e:raise SystemExit('VERIFICATION FAILED: '+str(e))

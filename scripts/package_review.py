#!/usr/bin/env python3
"""Package the checked manuscripts and paper sources; financial caches stay external."""
import hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];EDITION='editorial-v8-20261025'

def record(path):
    b=path.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def package():
    out=ROOT/'distribution';out.mkdir(exist_ok=True)
    names={'paper/main.pdf':'distribution/alem_do_beta_v8_20261025.pdf','paper/suplemento.pdf':'distribution/suplemento_alem_do_beta_v8_20261025.pdf'}
    receipt=json.loads((ROOT/'data/editorial_v8/latex_validation.json').read_text())
    assert receipt['pdfs']['main']['pages']<=15,'Editorial target is at most15 pages, including references'
    for source,target in names.items():shutil.copy2(ROOT/source,ROOT/target)
    archive=out/'alem_do_beta_v8_overleaf_20261025.zip';members={}
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in sorted((ROOT/'paper').rglob('*')):
            if not file.is_file() or file.name in ['main.pdf','suplemento.pdf']:continue
            if file.suffix not in ['.tex','.bib','.bst','.sty','.pdf','.md']:continue
            name=file.relative_to(ROOT/'paper').as_posix();item=zipfile.ZipInfo(name,date_time=(2026,10,25,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,file.read_bytes(),compresslevel=9);members[name]=record(file)
        for name in ['docs/EDICAO_V8.md','docs/DIREITOS_E_DADOS.md','docs/resposta_pareceres_V7.md']:
            file=ROOT/name;item=zipfile.ZipInfo(name,date_time=(2026,10,25,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,file.read_bytes(),compresslevel=9);members[name]=record(file)
    sources={}
    for folder in ['paper','scripts','src','data','results','notebooks','tests']:
        for file in sorted((ROOT/folder).rglob('*')):
            if not file.is_file() or '__pycache__' in file.parts or file.suffix in ['.pyc','.aux','.log','.bbl','.blg','.out']:continue
            if file.name=='distribution_validation.json':continue # output of the verifier, not an input
            if file.relative_to(ROOT).as_posix() in ['data/README.md','results/README.md','notebooks/README.md','scripts/check_repository.py']:continue # repository-specific packaging differs in the two mirrors
            sources[file.relative_to(ROOT).as_posix()]=record(file)
    for name in ['CITATION.cff','docs/EDICAO_V8.md','docs/DIREITOS_E_DADOS.md','docs/resposta_pareceres_V7.md']:
        sources[name]=record(ROOT/name)
    protected={}
    for stage in ['j','k']:
        path=ROOT/f'data/lab03{stage}/inputs_manifest.json';m=json.loads(path.read_text());protected.update(m['source_pins']);protected[path.relative_to(ROOT).as_posix()]=record(path)['sha256']
    for name,sha in protected.items():assert record(ROOT/name)['sha256']==sha,('frozen production source changed',name)
    artifacts={name:record(ROOT/name) for name in list(names.values())+[archive.relative_to(ROOT).as_posix()]}
    manifest=dict(edition=EDITION,date='2026-10-25',source_base_public_commit='cbd16eb77969310db1d0d7e7ce3ca58e9d25137f',source_base_private_commit='3afd6f5d396b9cb0e305eff3e6b61c68e2ac3106',scope='editorial distribution; full Git archive is identified by its immutable delivery commit',artifacts=artifacts,repository_files=sources,zip_members={archive.relative_to(ROOT).as_posix():members},pdf_equivalences=names,protected_production_pins=protected,pages={k:v['pages'] for k,v in receipt['pdfs'].items()},limitations=['daily matrices and B3 caches remain on Drive; full estimator rerun requires authorized inputs','no blanket third-party license is granted','checksums establish byte identity, not statistical validity or authorship authentication'])
    dest=out/'manifest_v8_20261025.json';dest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    checks={**artifacts,dest.relative_to(ROOT).as_posix():record(dest)}
    (out/'SHA256SUMS_v8_20261025.txt').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in sorted(checks.items())))
    print(json.dumps(dict(edition=EDITION,artifacts=artifacts,repository_files=len(sources),zip_members=len(members),frozen_production_pins=len(protected)),indent=2))

if __name__=='__main__':package()

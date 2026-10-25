#!/usr/bin/env python3
"""Build the two manuscripts without running financial estimators.

Requires pdfLaTeX, BibTeX, Poppler pdfinfo and Brazilian Portuguese Babel.
The source epoch and PDF metadata are fixed; binary identity across different
TeX distributions is not promised. Every distributed PDF has its own digest.
"""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EPOCH=1792886400

def build(output,texinputs=None,copy=True,receipt=None):
    paper=ROOT/'paper';env=os.environ.copy()
    env.update(SOURCE_DATE_EPOCH=str(EPOCH),FORCE_SOURCE_DATE='1',TZ='UTC')
    env['TEXINPUTS']=':'.join(([str(texinputs.resolve())] if texinputs else [])+[str(paper),''])
    env['BIBINPUTS']=str(paper)+':';env['BSTINPUTS']=str(paper)+':'
    for command in ['pdflatex','bibtex','pdfinfo']:
        if not shutil.which(command):raise SystemExit('Missing '+command+'; install a TeX distribution and Poppler.')
    result=dict(edition='editorial-v8-20261025',source_date_epoch=EPOCH,scope='PDF compilation only; no data downloads or estimation',pdfs={})
    result['pdflatex']=subprocess.run(['pdflatex','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    for name in ['main','suplemento']:
        target=output.resolve()/name;target.mkdir(parents=True,exist_ok=True)
        # An interrupted TeX process may leave a partial .aux; builds start clean.
        for suffix in ['aux','bbl','blg','out','log','toc']:
            (target/(name+'.'+suffix)).unlink(missing_ok=True)
        for i in range(4):
            args=['pdflatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(target),name+'.tex']
            proc=subprocess.run(args,cwd=paper,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
            (target/f'pass{i}.txt').write_text(proc.stdout)
            if proc.returncode:raise RuntimeError(proc.stdout[-6000:])
            if i==0:
                bib=subprocess.run(['bibtex',name],cwd=target,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
                (target/'bibtex.txt').write_text(bib.stdout)
                if bib.returncode:raise RuntimeError(bib.stdout)
        pdf=target/(name+'.pdf');log=(target/(name+'.log')).read_text(errors='replace')
        info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout
        item=dict(bytes=pdf.stat().st_size,sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pages=int(re.search(r'Pages:\s+(\d+)',info)[1]),undefined_references=bool(re.search(r'undefined|Rerun to get',log)),missing_characters='Missing character:' in log,overfull_boxes=re.findall(r'Overfull \\hbox[^\n]*',log))
        if item['undefined_references'] or item['missing_characters']:raise RuntimeError(json.dumps(item))
        result['pdfs'][name]=item
        if copy:shutil.copy2(pdf,paper/(name+'.pdf'))
    receipt=receipt or ROOT/'data/editorial_v8/latex_validation.json';receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/'build/paper');p.add_argument('--texinputs',type=Path);p.add_argument('--no-copy',action='store_true');p.add_argument('--receipt',type=Path);a=p.parse_args()
    build(a.output_dir,a.texinputs,not a.no_copy,a.receipt)

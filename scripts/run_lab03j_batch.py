#!/usr/bin/env python3
"""One CPU batch from authenticated I export and existing11B3ZIPs;no quotation downloads."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,zipfile
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--b3-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 def call(name,*args):
  print('J:',name,flush=True);subprocess.run([sys.executable,str(ROOT/'scripts'/name),*[str(x) for x in args]],check=True)
 source=ROOT/'data/lab03j/cvm_selected_members.zip';expected=json.loads((ROOT/'data/lab03j/cvm_sources_manifest.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==expected['zip_sha256'];cvm=a.output/'cvm_sources';cvm.mkdir()
 with zipfile.ZipFile(source) as z:
  assert z.testzip() is None
  for q in expected['members']:
   b=z.read(q['path']);assert hashlib.sha256(b).hexdigest()==q['sha256'];t=cvm/q['path'];t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 inputs=a.output/'private_inputs';call('extract_lab03j_turnover.py','--b3-cache',a.b3_cache,'--i-output',a.i_output,'--output',inputs)
 prepared=a.output/'prepared_covariates';call('prepare_lab03j_covariates.py','--cvm-root',cvm,'--prices',inputs/'prices2015_private.csv.gz','--output',prepared)
 for name in ['covariates_2015.csv','size_source_audit.csv']:
  pd.testing.assert_frame_equal(pd.read_csv(prepared/name),pd.read_csv(ROOT/'data/lab03j'/name),check_exact=False,atol=1e-8,rtol=1e-12)
 out=a.output/'outputs_J';call('run_lab03j.py','--i-output',a.i_output,'--turnover',inputs/'turnover_private.csv.gz','--output',out)
 call('export_lab03j_controls.py','--i-output',a.i_output,'--output',out)
 call('verify_lab03j.py','--i-output',a.i_output,'--turnover',inputs/'turnover_private.csv.gz','--output',out)
 call('diagnose_lab03j_calibration.py','--i-output',a.i_output,'--output',out)
 call('audit_lab03j_events.py','--cvm-root',cvm,'--turnover',inputs/'turnover_private.csv.gz','--output',out)
 call('run_lab03j_successions.py','--b3-cache',a.b3_cache,'--i-output',a.i_output,'--turnover',inputs/'turnover_private.csv.gz','--output',out)
 call('verify_lab03j_successions.py','--i-output',a.i_output,'--turnover',inputs/'turnover_private.csv.gz','--output',out)
 call('build_lab03j_paper.py','--source',out,'--paper',a.output/'paper')
 print('J batch complete;only existing B3caches and received I matrices used.',flush=True)
if __name__=='__main__':main()

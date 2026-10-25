#!/usr/bin/env python3
"""Run all prespecified J controls and liquidity-change associations in one batch."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03j import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--turnover',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 r=pd.read_csv(a.i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(a.i_output/'market_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').iloc[:,0].reindex(r.index)
 assert r.shape==(2483,118) and m.notna().all()
 v=pd.read_csv(a.turnover);v['date']=pd.to_datetime(v.date.astype(str),format='%Y%m%d');vol=v.pivot(index='date',columns='papel_id',values='volume').reindex(index=r.index,columns=r.columns).fillna(0.);assert (vol.to_numpy()>=0).all()
 c=pd.read_csv(ROOT/'data/lab03j/covariates_2015.csv');assert c.papel_id.is_unique
 initial=v[v.date.dt.year.eq(2015)].groupby('papel_id').volume.sum()/246;c['log_liquidity_2015']=c.papel_id.map(np.log(initial))
 early=np.zeros(118,dtype=bool);paired=early.copy()
 for universe in ['originais_COTAHIST','universo_2015']:
  q=pd.read_csv(a.i_output/f'gaps_preserved/assets_{universe}.csv').set_index('papel_id');jj=r.columns.get_indexer(q.index);early[jj]|=q.ok_early.to_numpy();paired[jj]|=(q.ok_early&q.ok_late).to_numpy()
 assert np.isfinite(c.set_index('papel_id').reindex(r.columns).log_liquidity_2015.to_numpy()[early|paired]).all()
 mask_before=np.isfinite(r.to_numpy());table,assoc,bank,exclusions,oracle=run(r,m,vol,c,{'early':early,'theta':paired});assert oracle['passed'];assert np.array_equal(mask_before,np.isfinite(r.to_numpy()))
 table.to_csv(a.output/'controlled_regressions.csv',index=False);assoc.to_csv(a.output/'liquidity_change.csv',index=False);exclusions.to_csv(a.output/'complete_case_audit.csv',index=False);c.to_csv(a.output/'covariates_used.csv',index=False);np.savez_compressed(a.output/'bootstrap_draws.npz',**bank)
 record=dict(stage='Lab03J',environment='local_not_author_Colab',B=4999,blocks=[21,5,63],preserved_original_80_117=True,protected_missing_not_filled=True,bootstrap_beta_reestimated=True,new_outer_generators=0,regression_rows=len(table),association_rows=len(assoc),independent_dense_checks=oracle,source_filing_cutoff='2015-12-31',size_measure='disclosed-share capitalization proxy;not certified exact yearend/free float',size_missing_not_imputed=True,elapsed_seconds=time.monotonic()-start)
 (a.output/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':
 with threadpool_limits(limits=2):main()

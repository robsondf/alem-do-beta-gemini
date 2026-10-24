#!/usr/bin/env python3
"""Independent all1970 OLS sensitivity checks and read-only source reconciliation."""
import argparse,json,sys,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load
from verify_lab03e_inference import full
def verify(d,folder):
    tab=pd.read_csv(folder/'economic_sensitivities.csv');ledger=pd.read_csv(folder/'economic_ledger.csv');removed=pd.read_csv(folder/'economic_removed_observations.csv');assert len(tab)==1970 and len(ledger)==197;assert not ledger.global_homologated.any();checks=0;max_loo=0
    for panel in d['panels']:
        scenario=panel['scenario'];ref=d['matrices']['referencia_n'][scenario];m=ref['^BVSP'].to_numpy()
        for a in panel['sample'].itertuples():
            y=ref[a.ticker].to_numpy();ok=np.isfinite(y)&np.isfinite(m);X=np.column_stack([np.ones(len(m)),m>0,m,m*(m>0)]);use=ok&(m!=0);XX=X[use];bread=np.linalg.inv(XX.T@XX);co=np.linalg.lstsq(XX,y[use],rcond=None)[0];h=np.sum((XX@bread)*XX,1);inf=np.zeros(len(m));inf[use]=(XX@bread)[:,3]*(y[use]-XX@co)/(1-h);rank=np.flatnonzero(use);rank=rank[np.argsort(-abs(inf[rank]),kind='stable')]
            q=tab[(tab.scenario==scenario)&(tab.papel_id==a.papel_id)]
            for r in q.itertuples():
                keep=np.ones(len(m),bool)
                if r.diagnostic.startswith('neighbor'):
                    radius=1 if r.diagnostic.startswith('neighbor1_') else 5;missing=np.flatnonzero(~np.isfinite(y))
                    if len(missing):keep=np.min(abs(np.arange(len(m))[:,None]-missing),axis=1)>radius
                elif r.diagnostic=='Light_2024Q4' and a.ticker=='LIGT3.SA':keep=~((ref.index.year==2024)&(ref.index.month>=10))
                elif r.diagnostic.startswith('remove'):keep[rank[:1 if r.diagnostic.startswith('remove1_') else 5]]=False
                yy=d['matrices'][r.reference][scenario][a.ticker].to_numpy();valid=np.isfinite(yy)&np.isfinite(m)&keep;plus=valid&(m>0);minus=valid&(m<0);eligible=valid.sum()>=200 and valid.mean()>=.95 and min(plus.sum(),minus.sum())>=60
                assert (r.status=='estimated')==eligible;assert r.n_pairs==valid.sum();assert r.n_plus==plus.sum();assert r.n_minus==minus.sum();assert r.removed_valid==np.sum(~keep&np.isfinite(y));assert np.isnan(yy).sum()==np.isnan(y).sum()
                if eligible:
                    e,se=full(m,yy,valid,hc3=False);_,sec=full(m,yy,valid);np.testing.assert_allclose([e,se,sec],[r.delta,r.se_hac5,r.se_hc3_hac5],atol=2e-10,rtol=2e-10)
                if r.diagnostic=='remove1_largest_absolute_observation_influence':
                    change=r.delta-co[3];max_loo=max(max_loo,abs(change+inf[rank[0]]));np.testing.assert_allclose(change,-inf[rank[0]],atol=2e-10,rtol=2e-10)
                rr=removed[(removed.scenario==scenario)&(removed.papel_id==a.papel_id)&(removed.diagnostic==r.diagnostic)];assert set(rr.date)==set(ref.index[~keep&np.isfinite(y)].date.astype(str));checks+=1
            l=ledger[(ledger.scenario==scenario)&(ledger.papel_id==a.papel_id)].iloc[0];np.testing.assert_allclose(l.slope_log_return_if_market_plus1pct,.01*(co[2]+co[3]),atol=1e-12);np.testing.assert_allclose(l.slope_log_return_if_market_minus1pct,-.01*co[2],atol=1e-12)
    primary=ROOT/'data/lab03e/primary';meta=json.loads((primary/'retrieval.json').read_text())
    for item in meta:assert hashlib.sha256((primary/item['file']).read_bytes()).hexdigest()==item['sha256']
    new=pd.read_csv(primary/'fras_published_cash_inventory.csv');old=pd.read_csv(ROOT/'data/lab02/semantica_caixa_v1/recuperacao_fras_visivel_2024_2025.csv');assert len(new)==46
    for r in old.itertuples():
        match=new[(new.approval==r.approval_date)&(new.type==r.provento)];assert len(match)==1;v=match.iloc[0];assert v.payment==r.payment_date and v.ex_source==r.ex_date;np.testing.assert_allclose(float(v.cash_ON_source),r.value_per_on,atol=5.1e-7,rtol=0)
    assert int(new.ex_in_2016_2025.sum())==25 and int(new.ex_in_2021_2025.sum())==12;assert int(((new.ex_before_approval|new.payment_before_approval)&new.ex_in_2016_2025).sum())==2
    return dict(passed=True,all_sensitivity_fits_checked=checks,exact_delete_one_identities=197,max_delete_one_error=max_loo,source_rows=46,old_html_rows_reconciled=5,old_html_rounding_tolerance=5.1e-7,global_homologated=0,no_lab03e_production_imports=True)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args()
 with threadpool_limits(limits=1):record=verify(load(ROOT,a.x_archive,a.b_archive),a.output)
 (a.output/'validacao_economia_independente.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

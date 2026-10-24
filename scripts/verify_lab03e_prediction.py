#!/usr/bin/env python3
"""Independent forecasts, exact quadratic risks, direct bootstrap and coverage.

No Lab03E production imports; each operator is rebuilt in a disjoint-regime
OLS parameterization. Saved arrays are checked, never repaired.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.signal import lfilter
from scipy.linalg import toeplitz
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load
from lab03d_prediction import forecast_fold
NAMES=['gaussian_iid','gaussian_garch','gaussian_ar03']
def noise(d,seed,mi,ri):
    burn=1024 if mi==1 else 256;N=len(d['market']);rng=np.random.default_rng(np.random.SeedSequence([seed,300,mi,ri]));z=rng.normal(size=(N+burn,118));v=np.sqrt(.3)*z[:,:1]+np.sqrt(.7)*z[:,1:]
    if mi==1:
        h=np.ones(117);last=np.zeros(117);u=[]
        for t in range(N+burn):
            if t:h=.03+.05*last**2+.92*h
            last=np.sqrt(h)*v[t];u.append(last.copy())
        u=np.array(u)[burn:]
    else:
        phi=.3 if mi==2 else 0.;u=lfilter([np.sqrt(1-phi**2)],[1,-phi],v,axis=0)[burn:]
    return u*d['nuisance'].sigma.to_numpy()
def rebuild(d,W,pi):
    panel=d['panels'][pi];matrix=d['matrices']['referencia_n'][panel['scenario']];N=len(d['market']);m=d['market'];sample=panel['sample'];actual=np.full((N,len(sample)),np.nan);actual[d['dates'].get_indexer(matrix.index)]=matrix[sample.ticker].to_numpy();valid=np.isfinite(actual);targets=np.flatnonzero(d['dates'].year>=(2019 if pi==0 else 2024));T=len(targets);months=d['dates'][targets].to_period('M');keys={}
    for j in range(len(sample)):keys.setdefault(valid[:,j].tobytes(),[]).append(j)
    operators=[]
    for members in keys.values():
        tr=np.zeros((T,N));co=np.zeros_like(tr);mask=valid[:,members[0]]
        for month in months.unique():
            loc=np.flatnonzero(months==month);tt=targets[loc];train=np.arange(tt[0]-W,tt[0]);on=mask[train]&(m[train]!=0);used=train[on];mm=m[used];plus=mm>0;minus=mm<0;AR=np.column_stack([np.ones(W-1),m[train[:-1]]]);ar=np.linalg.lstsq(AR,m[train[1:]],rcond=None)[0];innov=m[train[1:]]-AR@ar;innov-=innov.mean();future=ar[0]+ar[1]*m[tt-1,None]+innov;F=np.column_stack([(future>0).mean(1),(future*(future>0)).mean(1),(future<0).mean(1),(future*(future<0)).mean(1)]);X=np.column_stack([plus,mm*plus,minus,mm*minus]);XT=np.column_stack([np.ones(len(mm)),mm]);eligible=len(mm)>=200 and len(mm)/W>=.95 and min(plus.sum(),minus.sum())>=60 and min(np.var(mm,ddof=1),np.var(mm[plus],ddof=1),np.var(mm[minus],ddof=1))>=1e-12
            if eligible:
                P=np.linalg.lstsq(X,np.eye(len(mm)),rcond=None)[0];PT=np.linalg.lstsq(XT,np.eye(len(mm)),rcond=None)[0];FT=np.column_stack([np.ones(len(tt)),future.mean(1)]);tr[np.ix_(loc,used)]=FT@PT;co[np.ix_(loc,used)]=F@P+(future==0).mean(1)[:,None]*PT[0]
            else:tr[np.ix_(loc,used)]=1/len(mm);co[np.ix_(loc,used)]=1/len(mm)
        operators.append((members,tr,co))
    return dict(W=W,pi=pi,sample=sample,assets=panel['asset_index'],valid=valid[targets],targets=targets,operators=operators)
def quadratic_risks(d,p,phi,delta):
    m=d['market'];mean=m[:,None]*d['nuisance'].beta_base.to_numpy()[p['assets']]+delta*(m*(m>0))[:,None];sd=d['nuisance'].sigma.to_numpy()[p['assets']];out=np.empty(len(sd));N=len(m);target=p['targets'];cov=toeplitz(phi**np.arange(N)) if phi else None
    for members,tr,co in p['operators']:
        qt=-tr.copy();qc=-co.copy();qt[np.arange(len(target)),target]+=1;qc[np.arange(len(target)),target]+=1
        vt=np.einsum('ij,ij->i',qt@cov,qt) if phi else (qt**2).sum(1);vc=np.einsum('ij,ij->i',qc@cov,qc) if phi else (qc**2).sum(1);bias=(qt@mean[:,members])**2-(qc@mean[:,members])**2;risk=bias+(vt-vc)[:,None]*sd[members]**2;ok=p['valid'][:,members];out[members]=(risk*ok).sum(0)/ok.sum(0)
    return out
def forecasts(p,Y):
    target=p['targets'];tr=np.empty((len(target),len(p['sample'])));co=np.empty_like(tr)
    for members,A,B in p['operators']:tr[:,members]=A@Y[:,p['assets'][members]];co[:,members]=B@Y[:,p['assets'][members]]
    actual=Y[target][:,p['assets']];loss=np.where(p['valid'],(actual-tr)**2-(actual-co)**2,0);gain=loss.sum(0)/p['valid'].sum(0);return loss,gain
def direct_bootstrap(p,loss,gain,L,seed):
    T=len(loss);rng=np.random.default_rng(np.random.SeedSequence([seed,701,p['W'],p['pi'],L]));draw=np.empty((1999,loss.shape[1]))
    for start in range(0,1999,64):
        n=min(64,1999-start);starts=rng.integers(0,T-L+1,(n,int(np.ceil(T/L))));indices=(starts[:,:,None]+np.arange(L)).reshape(n,-1)[:,:T];weights=np.array([np.bincount(ix,minlength=T) for ix in indices],float);draw[start:start+n]=(weights@loss)/(weights@p['valid'])
    lo,hi=np.quantile(draw,[.025,.975],axis=0);sd=draw.std(axis=0,ddof=1);crit=np.quantile(np.max(abs(draw-gain)/sd,axis=1),.9875);return lo,hi,sd,crit
def verify(d,folder):
    plan=json.loads((ROOT/'data/lab03e/plano_v1.json').read_text());oldseed=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text())['seed_entropy'];panels=[rebuild(d,W,pi) for W in [252,504] for pi in [0,1]];offset=np.cumsum([0]+[len(p['sample']) for p in panels]);fam=pd.read_csv(folder/'predictive_family.csv');cal=pd.read_csv(folder/'predictive_calibration.csv');f=pd.read_csv(folder/'predictive_fold_design.csv');assert (pd.to_datetime(f.max_train_date)<pd.to_datetime(f.target_start)).all();oracle_count=0;gain_count=0;bootstrap_count=0
    for mi,name in enumerate(NAMES):
        for delta in [0.,.25]:
            a=np.load(folder/(f'predictive_{name}_delta{delta:.2f}.npz'));assert a['gain'].shape==(1000,394);assert all(np.isfinite(a[k]).all() for k in a.files)
            truth=np.concatenate([quadratic_risks(d,p,.3 if mi==2 else 0.,delta) for p in panels]);np.testing.assert_allclose(truth,a['truth'],atol=1e-14,rtol=1e-8);oracle_count+=len(truth)
            for ri in [0,999]:
                Y=d['market'][:,None]*d['nuisance'].beta_base.to_numpy()+delta*(d['market']*(d['market']>0))[:,None]+noise(d,plan['seed_entropy'],mi,ri)
                for pi,p in enumerate(panels):
                    loss,gain=forecasts(p,Y);ix=slice(offset[pi],offset[pi+1]);np.testing.assert_allclose(gain,a['gain'][ri,ix],atol=1e-14,rtol=1e-8);gain_count+=len(gain)
                    # All four panels/threeL for Gaussian IID; recent504 for each other law.
                    if ri==0 and delta==0 and (mi==0 or pi==3):
                        for li,L in enumerate([21,42,63]):
                            lo,hi,se,critical=direct_bootstrap(p,loss,gain,L,oldseed);np.testing.assert_allclose(lo,a['marginal_low'][ri,ix,li],atol=1e-14,rtol=1e-8);np.testing.assert_allclose(hi,a['marginal_high'][ri,ix,li],atol=1e-14,rtol=1e-8);np.testing.assert_allclose(se,a['bootstrap_se'][ri,ix,li],atol=1e-14,rtol=1e-8);np.testing.assert_allclose(critical,a['critical'][ri,pi,li],atol=1e-9,rtol=1e-8);bootstrap_count+=1999
            for _,r in fam[(fam.mechanism==name)&(fam.delta==delta)].iterrows():
                li=[21,42,63].index(r.block_length)
                if r.method=='marginal_percentile':lo=a['marginal_low'][:,:,li];hi=a['marginal_high'][:,:,li]
                else:lo=a['gain']-a['simultaneous_width'][:,:,li];hi=a['gain']+a['simultaneous_width'][:,:,li]
                ok=(lo<=truth)&(hi>=truth);null=truth<=0;rej=lo>0;vals=[ok.mean(),ok.all(1).mean(),rej[:,null].any(1).mean() if null.any() else np.nan,rej[:,~null].mean() if (~null).any() else np.nan];np.testing.assert_allclose(vals,[r.mean_coverage,r.joint_coverage,r.fwer_gain_positive,r.power],atol=1e-14,equal_nan=True);sub=cal[(cal.mechanism==name)&(cal.delta==delta)&(cal.block_length==r.block_length)&(cal.method==r.method)];np.testing.assert_allclose(sub.coverage,ok.mean(0),atol=1e-14)
            print('Independent prediction:',name,delta,'exact oracle/all gains/coverage verified',flush=True)
    Y=np.zeros((len(d['market']),117))
    for pp in d['panels']:Y[np.ix_(pp['time_index'],pp['asset_index'])]=np.nan_to_num(d['matrices']['referencia_n'][pp['scenario']][pp['sample'].ticker].to_numpy(),nan=0.)
    obs=pd.read_csv(folder/'observed_predictive_intervals.csv');observed_checks=0
    for p in panels:
        loss,gain=forecasts(p,Y);scenario='decada' if p['pi']==0 else 'recente'
        for L in [21,42,63]:
            lo,hi,se,critical=direct_bootstrap(p,loss,gain,L,oldseed);q=obs[obs.window.eq(p['W'])&obs.scenario.eq(scenario)&obs.block_length.eq(L)];np.testing.assert_array_equal(q.papel_id,p['sample'].papel_id);np.testing.assert_allclose(q[['loss_gain','marginal_low','marginal_high','bootstrap_se','simultaneous_low','simultaneous_high']].to_numpy().T,[gain,lo,hi,se,gain-critical*se,gain+critical*se],atol=1e-14,rtol=1e-8);observed_checks+=len(q)
    for r in obs[obs.common_reused].itertuples():
        q=obs[obs.window.eq(r.window)&obs.scenario.eq('recente')&obs.block_length.eq(r.block_length)&obs.papel_id.eq(r.papel_id)].iloc[0];np.testing.assert_allclose([r.loss_gain,r.simultaneous_low,r.simultaneous_high],[q.loss_gain,q.simultaneous_low,q.simultaneous_high],atol=0,rtol=0)
    return dict(passed=True,exact_full_quadratic_risks=oracle_count,reconstructed_gain_values=gain_count,direct_bootstrap_vectors=bootstrap_count,all_observed_interval_rows=observed_checks,common_reuse_rows=int(obs.common_reused.sum()),family_rows=len(fam),asset_coverage_rows=len(cal),temporal_origins_verified=len(f),no_lab03e_production_imports=True,conditional_market_only=True)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args()
 with threadpool_limits(limits=1):record=verify(load(ROOT,a.x_archive,a.b_archive),a.output)
 (a.output/'validacao_previsao_independente.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

#!/usr/bin/env python3
"""Independent full-design OLS/HC3 sandwich, RNG and all-family audit.

No Lab03E production imports. Earlier authenticated loader is used for inputs.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.signal import lfilter
from scipy.stats import beta as betadist
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load
NAMES=['gaussian_iid','student_hetero','student_ar','garch_t5','variance_break_t5','ar06_t5']
SORTED={}
def full(m,y,on,split=None,hc3=True):
    D=(m>0).astype(float);X=np.column_stack([np.ones(len(m)),D,m,D*m]);c=np.array([0.,0,0,1])
    if split is not None:
        early=split[:,None];X=np.column_stack([X*early,X*(~early)]);c=np.r_[-c,c]
    use=on&(m!=0);xx=X[use];bread=np.linalg.inv(xx.T@xx);coef=np.linalg.lstsq(xx,y[use],rcond=None)[0];h=np.einsum('ij,ij->i',xx@bread,xx);r=(y[use]-xx@coef)/(1-h if hc3 else 1);S=np.zeros_like(X);S[use]=xx*r[:,None];meat=S.T@S
    for lag in range(1,6):
        cov=S[lag:].T@S[:-lag];meat+=(1-lag/6)*(cov+cov.T)
    n=use.sum();v=bread@meat@bread*n/(n-X.shape[1]);return c@coef,np.sqrt(c@v@c)
def law(d,seed,mi,ri):
    N=len(d['market']);burn=1024 if mi==3 else 256;rng=np.random.default_rng(np.random.SeedSequence([seed,200,mi,ri]));z=rng.standard_normal((N+burn,118)) if mi==0 else rng.standard_t(5,(N+burn,118))*np.sqrt(3/5);v=np.sqrt(.3)*z[:,:1]+np.sqrt(.7)*z[:,1:]
    if mi==3:
        vv=np.ones(117);last=np.zeros(117);u=[]
        for t in range(N+burn):
            if t:vv=.03+.05*last**2+.92*vv
            last=np.sqrt(vv)*v[t];u.append(last.copy())
        u=np.array(u)[burn:]
    else:
        phi=0 if mi<2 else (.6 if mi==5 else .3);u=lfilter([np.sqrt(1-phi**2)],[1,-phi],v,axis=0)[burn:]
        if mi in [1,2,4,5]:u=u*d['scale'][:,None]
        if mi==4:
            scale=np.where(d['dates'].year>=2020,2.,1.);u=u*(scale/np.sqrt(np.mean(scale**2)))[:,None]
    return u*d['nuisance'].sigma.to_numpy()
def ranks(t,bank,mapping,tail='two'):
    if id(bank) not in SORTED:
        # Contiguous sorted vectors avoid copying100k values at every search.
        vectors=np.ascontiguousarray(bank.transpose(0,2,1));SORTED[id(bank)]=(np.sort(vectors,axis=2),np.sort(abs(vectors),axis=2))
    signed,absolute=SORTED[id(bank)]
    out=np.empty_like(t)
    for j,g in enumerate(mapping):
        vals=[]
        for mi in range(3):
            if tail=='negative':count=np.searchsorted(signed[mi,g],t[:,j],side='right')
            else:
                ref=absolute[mi,g] if tail=='two' else signed[mi,g];target=abs(t[:,j]) if tail=='two' else t[:,j];count=bank.shape[1]-np.searchsorted(ref,target,side='left')
            vals.append((count+1)/(bank.shape[1]+1))
        out[:,j]=np.max(vals,axis=0)
    return out
def holm(p):
    ix=np.argsort(p,axis=1);v=np.take_along_axis(p,ix,1)*np.arange(p.shape[1],0,-1);v=np.clip(np.maximum.accumulate(v,axis=1),0,1);out=np.empty_like(p);np.put_along_axis(out,ix,v,1);return out
def verify(d,folder):
    plan=json.loads((ROOT/'data/lab03e/plano_v1.json').read_text());z=np.load(folder/'calibration_bank.npz');bank=z['calibration_t'];assert bank.shape==(3,99999,25);assert np.isfinite(bank).all();maps={k:z[k+'_map'] for k in ['static','annual','theta']};tasks={};catalog=pd.read_csv(folder/'bank_designs.csv');ids={p:i for i,p in enumerate(d['nuisance'].papel_id)}
    for kind,design in [('static',d['design']),('annual',d['annual_design']),('theta',d['design'].iloc[:80])]:
        for j,row in enumerate(design.itertuples()):
            if kind=='annual':p=d['panels'][0 if row.year<2021 else 1];mat=d['matrices']['referencia_n'][p['scenario']];mat=mat[mat.index.year==row.year]
            else:mat=d['matrices']['referencia_n']['decada' if kind=='theta' else row.scenario]
            ti=d['dates'].get_indexer(mat.index);m=mat['^BVSP'].to_numpy();on=np.isfinite(mat[row.ticker].to_numpy())&np.isfinite(m);split=mat.index.year<=2020 if kind=='theta' else None;task=(m,on,ti,split,ids[row.papel_id]);tasks[(kind,j)]=task
    checks=0;maxdiff=0.
    # First two draws from each independent stream and all25 designs, full4/8-column fits.
    representatives={}
    for kind in maps:
        for j,g in enumerate(maps[kind]):representatives.setdefault(g,(kind,j))
    for mi in range(3):
        for stream in range(3):
            rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],100,mi,stream]));zz=rng.standard_normal((2,len(d['market'])+256,2)) if mi==0 else rng.standard_t(5,(2,len(d['market'])+256,2))*np.sqrt(.6);v=zz[:,:,0]*np.sqrt(.3)+zz[:,:,1]*np.sqrt(.7);phi=.3 if mi==2 else 0.;u=lfilter([np.sqrt(1-phi**2)],[1,-phi],v,axis=1)[:,256:]
            if mi:u*=d['scale']
            for ri in range(2):
                for g,(kind,j) in representatives.items():
                    m,on,ti,split,_=tasks[kind,j];e,se=full(m,u[ri,ti],on,split);ref=bank[mi,stream*33333+ri,g];np.testing.assert_allclose(e/se,ref,atol=2e-10,rtol=2e-10);maxdiff=max(maxdiff,abs(e/se-ref));checks+=1
    families=pd.read_csv(folder/'inference_family.csv');power=pd.read_csv(folder/'inference_power.csv');coverage=pd.read_csv(folder/'inference_coverage.csv');family_checks=0
    critical=np.max(np.sort(abs(bank),axis=1)[:,int(np.ceil(99999*.95)),:],axis=0)
    for mi,name in enumerate(NAMES):
        a=np.load(folder/('validation_'+name+'.npz'))
        for ri in [0,999]:
            noise=law(d,plan['seed_entropy'],mi,ri)
            for (kind,j),(m,on,ti,split,asset) in tasks.items():
                e,se=full(m,noise[ti,asset],on,split);np.testing.assert_allclose([e,se],[a[kind+'_error'][ri,j],a[kind+'_se'][ri,j]],atol=2e-10,rtol=2e-10);checks+=1
        for kind in maps:
            covered=abs(a[kind+'_error'])<=a[kind+'_se']*critical[maps[kind]];tab=coverage[(coverage.kind==kind)&(coverage.mechanism==name)];np.testing.assert_allclose(covered.mean(0),tab.coverage,atol=1e-14)
        for _,row in families[families.mechanism==name].iterrows():
            if row.kind=='static':
                delta=float(row.pattern.split('_')[1]);p=ranks((a['static_error']+delta)/a['static_se'],bank,maps['static']);null=np.full(197,delta==0)
            else:
                pattern=row.pattern;value=0 if pattern=='zero' else float(pattern.split('_')[1]);truth=np.zeros(985) if pattern=='zero' else np.full(985,value) if pattern.startswith('constant') else np.where(d['annual_design'].year<2021,-value,value);theta=np.full(80,2*value if pattern.startswith('flip') else 0.);tp=ranks((a['theta_error']+theta)/a['theta_se'],bank,maps['theta']);ap=ranks((a['annual_error']+truth)/a['annual_se'],bank,maps['annual'],'positive');an=ranks((a['annual_error']+truth)/a['annual_se'],bank,maps['annual'],'negative');aa=[x[x>=0] for x in d['annual_map']];p=np.column_stack([tp,np.column_stack([ap[:,ix].max(1) for ix in aa]),np.column_stack([an[:,ix].max(1) for ix in aa])]);null=np.r_[theta==0,[not np.all(truth[ix]>0) for ix in aa],[not np.all(truth[ix]<0) for ix in aa]]
            rej=holm(p)<.05
            for key,ev in [('fwer_raw',p<.05),('fwer_adjusted',rej)]:
                result=ev[:,null].any(1).mean() if null.any() else np.nan;np.testing.assert_allclose(result,row[key],atol=1e-14,equal_nan=True)
            if (~null).any():np.testing.assert_allclose(rej[:,~null].mean(),row.power_adjusted,atol=1e-14)
            family_checks+=1
        print('Independent inference:',name,'all family tables and full-design endpoints verified',flush=True)
    # All ideal-tail probabilities/Clopper-Pearson bounds audited from direct counts.
    tails=pd.read_csv(folder/'observed_tail_precision.csv');ad=d['annual_design'];sd=d['design'];lookup={}
    for kind,des in [('static',sd),('annual',ad),('theta',sd.iloc[:80])]:
        for j,r in enumerate(des.itertuples()):lookup[(kind,r.papel_id,r.year if kind=='annual' else r.scenario)]=maps[kind][j]
    for r in tails.itertuples():
        key=(r.kind,r.papel_id,int(r.year) if r.kind=='annual' else r.scenario);g=lookup[key];v=bank[NAMES.index(r.mechanism),:,g];k=int(np.count_nonzero(abs(v)>=abs(r.t_observed))) if r.tail=='two' else int(np.count_nonzero(v>=r.t_observed)) if r.tail=='positive' else int(np.count_nonzero(v<=r.t_observed));assert k==r.exceedances;lo=0 if k==0 else betadist.ppf(.025,k,99999-k+1);hi=1 if k==99999 else betadist.ppf(.975,k+1,99999-k);np.testing.assert_allclose([r.p_rank,r.ideal_tail_lower,r.ideal_tail_upper],[(k+1)/100000,lo,hi],atol=2e-15)
    return dict(passed=True,full_OLS_sandwich_fits=checks,all_family_rows=family_checks,all_tail_intervals=len(tails),bank_shape=list(bank.shape),maximum_bank_statistic_difference=maxdiff,no_lab03e_production_imports=True)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args()
 with threadpool_limits(limits=1):record=verify(load(ROOT,a.x_archive,a.b_archive),a.output)
 (a.output/'validacao_inferencia_independente.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

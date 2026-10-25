#!/usr/bin/env python3
"""Finite conditional size/liquidity null calibration; no fitted-DGP assertion."""
import argparse,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_lab03k import prepare
from lab03j import block_weights
from lab03k import design,delta_weights

def wilson(k,n):
    p=k/n;z=1.959963984540054;den=1+z*z/n;center=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(rate=float(p),wilson_low=float(center-half),wilson_high=float(center+half),MC_se=float(np.sqrt(p*(1-p)/n)))

def components(rng,shape,law):
    R,T,N=shape
    if law=='normal_iid':return rng.normal(size=shape)
    if law=='t5_deterministic_volatility':
        h=np.where(np.arange(T)<T//2,1.,2.);h/=np.sqrt(np.mean(h*h))
        return rng.standard_t(5,size=shape)*np.sqrt(3/5)*h[None,:,None]
    if law!='t5_GARCH':raise ValueError(law)
    v=np.ones((R,N));out=np.empty(shape)
    for t in range(T+500):
        e=rng.standard_t(5,size=(R,N))*np.sqrt(3/5)*np.sqrt(v)
        v=.05+.05*e*e+.90*v
        if t>=500:out[:,t-500,:]=e
    return out

def calibrate(i_output,j_batch,output):
    start=time.monotonic();r,m,c,_,_,ids,_=prepare(i_output,j_batch)
    jj=ids['union118'];R=r.iloc[:,jj].to_numpy();M=m.to_numpy();names=r.columns[jj];T,N=R.shape
    A=np.zeros((4,N));sigma=np.zeros(N)
    for ci,(cohort,base) in enumerate(ids.items()):
        cc=c.iloc[base];X,_=design(cc.log_liquidity_2015.to_numpy(),cc.log_size.to_numpy(),cc.sector.to_numpy());ix=names.get_indexer(r.columns[base]);A[ci*2:ci*2+2,ix]=np.linalg.pinv(X)[1:3]
        # Fixed sector-dependent nuisance Delta lies in both null projections.
        nuisance=np.array([sorted(c.sector.dropna().unique()).index(s)*.03 for s in cc.sector]);assert np.max(abs(np.linalg.pinv(X)[1:3]@nuisance))<1e-10
    for i in range(N):
        residual=[]
        for sign in [M>0,M<0]:
            v=sign&np.isfinite(R[:,i]);X=np.column_stack([np.ones(v.sum()),M[v]]);y=R[v,i];residual.extend(y-X@np.linalg.lstsq(X,y,rcond=None)[0])
        sigma[i]=np.sqrt(np.mean(np.square(residual)))
    W,_=block_weights(T,21,np.random.default_rng(20261025+21),4999);W=np.vstack([np.ones((1,T)),W]);groups={}
    for i in range(N):groups.setdefault(np.isfinite(R[:,i]).tobytes(),[]).append(i)
    qgroups=[]
    for members in groups.values():qgroups.append((np.array(members),delta_weights(np.isfinite(R[:,members[0]]),M,W)))
    # Independent weighted OLS oracle for the acceleration, including nonzero means.
    rng=np.random.default_rng(991);sample=rng.normal(size=(T,N))*sigma+M[:,None]*(np.arange(N)/N)[None,:]
    fast=np.zeros((4,4));checks=0;maxerr=0.
    for members,Q in qgroups:fast+=Q[:4]@(sample[:,members]@A[:,members].T)
    for b in range(4):
        dd=[]
        for i in range(N):
            slopes=[]
            for sign in [M>0,M<0]:
                v=sign&np.isfinite(R[:,i])&(W[b]>0);X=np.column_stack([np.ones(v.sum()),M[v]]);sw=np.sqrt(W[b,v]);slopes.append(np.linalg.lstsq(X*sw[:,None],sample[v,i]*sw,rcond=None)[0][1]);checks+=1
            dd.append(slopes[0]-slopes[1])
        maxerr=max(maxerr,float(np.max(abs(fast[b]-A@dd))))
    assert maxerr<1e-9
    records=[];summary=[]
    for case,(law,rho) in enumerate((law,rho) for law in ['normal_iid','t5_deterministic_volatility','t5_GARCH'] for rho in [.04,.30]):
        rng=np.random.default_rng(20261028+case);case_rows=[]
        for first in range(0,1000,25):
            n=min(25,1000-first);comp=components(rng,(n,T,N+1),law)
            eps=sigma[None,None,:]*(np.sqrt(rho)*comp[:,:,:1]+np.sqrt(1-rho)*comp[:,:,1:])
            draws=np.zeros((5000,n,4))
            for members,Q in qgroups:
                aggregate=np.einsum('rti,ki->trk',eps[:,:,members],A[:,members],optimize=True).reshape(T,n*4)
                draws+=(Q@aggregate).reshape(5000,n,4)
            point=draws[0];boot=draws[1:];err=boot-point
            quant=np.quantile(err,[.025,.975],axis=0);cover=(point-quant[1]<=0)&(point-quant[0]>=0)
            probs=np.empty((n,2))
            for ci in range(2):
                d=boot[:,:,ci*2:ci*2+2];center=d-d.mean(0);cov=np.einsum('bri,brj->rij',center,center)/4998
                if np.any(np.linalg.cond(cov)>1e12):raise ValueError('singular simulated covariance')
                inv=np.linalg.inv(cov);pp=point[:,ci*2:ci*2+2];ee=err[:,:,ci*2:ci*2+2]
                stat=np.einsum('ri,rij,rj->r',pp,inv,pp);radius=np.einsum('bri,rij,brj->br',ee,inv,ee)
                probs[:,ci]=(1+(radius>=stat).sum(0))/5000
            any_reject=2*probs.min(1)<=.05
            for k in range(n):
                row=dict(generator=law,rho=rho,replication=first+k,p_original=float(probs[k,0]),p_union=float(probs[k,1]),Holm2_any_reject=bool(any_reject[k]))
                for col,label in enumerate(['original_lambda','original_gamma','union_lambda','union_gamma']):row['covered_'+label]=bool(cover[k,col])
                case_rows.append(row)
            if (first+25)%250==0:print('K calibration',law,'rho',rho,first+25,'/1000',flush=True)
        records+=case_rows;df=pd.DataFrame(case_rows)
        for target,col in [('joint_Holm2_FWER','Holm2_any_reject')]+[(s,'covered_'+s) for s in ['original_lambda','original_gamma','union_lambda','union_gamma']]:
            summary.append(dict(generator=law,rho=rho,R=1000,B=4999,block=21,target=target,**wilson(int(df[col].sum()),1000)))
        pd.DataFrame(records).to_csv(output/'calibration_replications.csv.gz',index=False);pd.DataFrame(summary).to_csv(output/'calibration_summary.csv',index=False)
        print('K calibration case complete',law,rho,'elapsed',round(time.monotonic()-start,1),flush=True)
    receipt=dict(passed=True,scope='six finite conditional null laws, not universal coverage or DGP compatibility',R_per_case=1000,B=4999,block=21,mask_groups=len(groups),dense_weighted_regime_fits=checks,max_oracle_error=maxerr,elapsed_seconds=time.monotonic()-start)
    (output/'calibration_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--j-batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=2):calibrate(a.i_output,a.j_batch,a.output)

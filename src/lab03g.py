"""Post-v3 aggregate temporal/microstructure inference and fixed-design size study.

Response-linear weighted OLS operators exactly refit each bootstrap design.
No market downloads, return filling, primary overwrites or adaptive stopping.
"""
from pathlib import Path
import hashlib,json,os,time,gc
import numpy as np
import pandas as pd
from scipy.stats import norm
from lab02 import holm
from lab03f import load as load_f,profile_data,contiguous_segments
from lab03e_inference import noise_path,MECHANISMS


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(root,x):
    lock=json.loads((root/'data/lab03g/inputs_manifest.json').read_text())
    assert digest(root/'data/lab03g/plano_v1.json')==lock['plan_sha256']
    for name,h in (lock['source_pins']|lock['frozen_E_pins']).items():assert digest(root/name)==h,name
    assert digest(x)==lock['x_sha256']
    fp,mats,samples=load_f(root,x)
    return json.loads((root/'data/lab03g/plano_v1.json').read_text()),fp,mats,samples


def block_counts(N,L,B,rng):
    """Identical noncircular MBB row multiplicities to F, including last truncation."""
    full,tail=divmod(N,L)
    if L>N:raise ValueError('Block longer than stratum')
    starts=rng.integers(0,N-L+1,size=(B,full+(tail>0)));out=np.zeros((B,N))
    for k in range(0,B,128):
        a=starts[k:k+128];ids=(a[:,:,None]+np.arange(L)).reshape(len(a),-1)[:,:N]
        np.add.at(out[k:k+len(a)],(np.arange(len(a))[:,None],ids),1.)
    assert np.all(out.sum(1)==N)
    return out


def segment_counts(index,L,B,seed):
    out=np.zeros((B,len(index)));rng=np.random.default_rng(seed)
    for ix in [np.flatnonzero(index.year<2021),np.flatnonzero(index.year>=2021)]:
        if len(ix):out[:,ix]=block_counts(len(ix),L,B,rng)
    return out


def f_counts(fp,mats,L):
    B=fp['bootstrap']['replications'];seed=fp['bootstrap']['seed'];before=mats['decada'].loc[:'2020-12-31'];recent=mats['recente']
    late=block_counts(len(recent),L,B,np.random.default_rng(np.random.SeedSequence([seed,L,1])))
    out={'recent':late}
    for i,p in enumerate(['daily','exclude_2020_03','exclude_2020_H1']):
        early=np.zeros((B,len(before)));rng=np.random.default_rng(np.random.SeedSequence([seed,L,2,i]))
        for ix in contiguous_segments(before.index,p):early[:,ix]=block_counts(len(ix),L,B,rng)
        if p=='daily':out['early']=early
        out[p]=np.column_stack([early,late])
    return out


def _weights(M,regime,valid,counts):
    """Contrast row for weighted separate-intercept regime regression."""
    W=np.zeros_like(counts);invalid=np.zeros(len(counts),bool)
    for sign,mult in [(True,1.),(False,-1.)]:
        on=valid&(regime==sign);a=counts*on[None,:];n=a.sum(1);safe=np.maximum(n,1.)
        means=(a@M)/safe[:,None]
        gram=np.einsum('bt,ti,tj->bij',a,M,M,optimize=True)-safe[:,None,None]*means[:,:,None]*means[:,None,:]
        bad=(n<60)|(np.diagonal(gram,axis1=1,axis2=2).min(1)/np.maximum(n-1,1)<1e-12)
        bad|=~np.isfinite(gram).all((1,2))
        good=np.flatnonzero(~bad)
        if len(good):
            cond=np.linalg.cond(gram[good]);bad[good[cond>1e12]]=True;good=np.flatnonzero(~bad)
        u=np.zeros((len(counts),M.shape[1]))
        if len(good):u[good]=np.linalg.solve(gram[good],np.ones((len(good),M.shape[1],1)))[:,:,0]
        W+=mult*a*(u@M.T-np.sum(u*means,axis=1)[:,None]);invalid|=bad
    return W,invalid


class PanelOperator:
    def __init__(self,frame,tickers,counts,keep=None,offsets=(0,)):
        self.tickers=tickers;self.index=frame.index;self.N=len(frame);self.J=len(tickers)
        m=frame['^BVSP'].to_numpy();M=np.column_stack([frame['^BVSP'].shift(k) for k in offsets]);keep=np.ones(len(frame),bool) if keep is None else keep
        eligible=keep&np.isfinite(M).all(1)&(m!=0);M=np.where(np.isfinite(M),M,0.)
        self.groups=[];self.invalid=np.zeros(len(counts),bool)
        Y=frame[tickers].to_numpy();groups={}
        for j in range(self.J):
            valid=eligible&np.isfinite(Y[:,j]);groups.setdefault(valid.tobytes(),[valid,[]])[1].append(j)
        for valid,members in groups.values():
            w0,bad0=_weights(M,m>0,valid,np.ones((1,len(frame))))
            W,bad=_weights(M,m>0,valid,counts)
            n=counts@valid;denom=counts@eligible
            bad|=(n<200)|(n/np.maximum(denom,1)<.95)
            assert not bad0.any() and valid.sum()>=200 and valid.sum()/eligible.sum()>=.95
            self.groups.append(dict(members=np.array(members),valid=valid,w0=w0[0],W=W))
            self.invalid|=bad
        self.Y=Y;self.B=len(counts)

    def evaluate(self,Y=None):
        if Y is None:Y=self.Y
        if Y.ndim==2:Y=Y[:,None,:]
        assert Y.shape[0]==self.N and Y.shape[2]==self.J
        R=Y.shape[1];boot=np.empty((self.B,R,self.J));point=np.empty((R,self.J))
        for g in self.groups:
            members=g['members'];values=np.where(g['valid'][:,None,None],Y[:,:,members],0.)
            values=values.reshape(self.N,-1)
            boot[:,:,members]=(g['W']@values).reshape(self.B,R,len(members))
            point[:,members]=(g['w0']@values).reshape(R,len(members))
        boot[self.invalid]=np.nan
        return point,boot


def statistics(point,boot):
    """All outputs retain incomplete draws; no redraw or selective omission."""
    ans={}
    for stat,fun in [('mean',np.mean),('median',np.median)]:
        t=fun(point,axis=-1);b=fun(boot,axis=-1);error=b-t[None,:]
        invalid=~np.isfinite(error).all(0);lo,hi=np.quantile(error,[.025,.975],axis=0)
        p=(1+(abs(error)>=abs(t)[None,:]).sum(0))/(len(boot)+1)
        p=np.where(invalid,np.nan,p)
        ans[stat]=dict(estimate=t,bootstrap_mean=b.mean(0),bootstrap_bias=b.mean(0)-t,bootstrap_se=b.std(0,ddof=1),
            ci_low=t-hi,ci_high=t-lo,p_centered=p,invalid_draws=(~np.isfinite(error)).sum(0),draws=b)
    return ans


def add_rows(rows,draws,stats,family,profile,scenario,L,assets):
    for stat,q in stats.items():
        row=dict(family=family,profile=profile,scenario=scenario,statistic=stat,block=L,assets=assets,B=len(q['draws']))
        row.update({k:float(v[0]) for k,v in q.items() if k!='draws'});row['status']='estimated' if row['invalid_draws']==0 else 'incomplete_bootstrap_inference_withheld'
        rows.append(row);draws[f'{profile}_{scenario}_{stat}_L{L}']=q['draws'][:,0]


def f_operators(fp,mats,samples,L):
    counts=f_counts(fp,mats,L);tickers={s:list(samples[s].ticker) for s in samples}
    panels={};recent=mats['recente'];long=mats['decada'];before=long.loc[:'2020-12-31']
    panels['recent']=PanelOperator(recent,tickers['recente'],counts['recent'])
    panels['early']=PanelOperator(before,tickers['decada'],counts['early'])
    for profile in ['daily','exclude_2020_03','exclude_2020_H1']:
        _,keep=profile_data(long,profile);panels[profile]=PanelOperator(long,tickers['decada'],counts[profile],keep)
    return panels


def family_values(ops,common,Ylong=None,Yrecent=None,Yearly=None):
    """Four temporal and all ten original F targets from jointly simulated panels."""
    out={};rp,rb=ops['recent'].evaluate(Yrecent)
    out[('F','daily','recente')]=statistics(rp,rb)
    out[('F','daily','decada_periodo_comum')]=statistics(rp[:,common],rb[:,:,common])
    earlyp,earlyb=ops['early'].evaluate(Yearly)
    out[('temporal','early','decada')]=statistics(earlyp,earlyb)
    out[('temporal','theta','decada')]=statistics(rp[:,common]-earlyp,rb[:,:,common]-earlyb)
    del earlyb,rb;gc.collect()
    for profile in ['daily','exclude_2020_03','exclude_2020_H1']:
        p,b=ops[profile].evaluate(Ylong);out[('F',profile,'decada')]=statistics(p,b);del b
    return out


def observed(root,plan,fp,mats,samples,output):
    rows=[];draws={};ids=list(samples['recente'].papel_id);common=np.array([ids.index(p) for p in samples['decada'].papel_id])
    frozen=pd.read_csv(root/'results/tables/lab03f_pos_parecer_20261024/aggregate.csv.gz',float_precision='round_trip')
    for L in plan['observed_bootstrap']['daily_blocks']:
        ops=f_operators(fp,mats,samples,L);values=family_values(ops,common)
        for (family,profile,scenario),stats in values.items():
            if family=='F':
                for stat,q in stats.items():
                    r=frozen[(frozen.profile==profile)&(frozen.scenario==scenario)&(frozen.statistic==stat)&(frozen.block==L)].iloc[0]
                    np.testing.assert_allclose([q['estimate'][0],q['ci_low'][0],q['ci_high'][0],q['p_centered'][0]],[r.estimate,r.ci_low,r.ci_high,r.p_centered],atol=1e-10,rtol=1e-9)
            else:add_rows(rows,draws,stats,'temporal4',profile,scenario,L,80)
        if L==21:
            ep,_=ops['early'].evaluate();lp,_=ops['recent'].evaluate()
            points=samples['decada'][['papel_id','ticker','setor_economico']].copy();points['delta_early']=ep[0];points['delta_late']=lp[0,common];points['theta']=lp[0,common]-ep[0];points.to_csv(output/'temporal_asset_points.csv',index=False)
        del ops,values;gc.collect();print(f'G temporal L={L}; F10 reproduced',flush=True)
    for pi,profile in enumerate(plan['observed_bootstrap']['microstructure']):
        for bi,L in enumerate(plan['observed_bootstrap']['weekly_blocks'] if profile=='weekly' else plan['observed_bootstrap']['daily_blocks']):
            ops={}
            for si,scenario in enumerate(['decada','recente']):
                frame,_=profile_data(mats[scenario],profile);counts=segment_counts(frame.index,L,4999,np.random.SeedSequence([plan['observed_bootstrap']['seed'],700,pi,si,L]))
                offsets=(0,1) if profile=='lag1' else ((-1,0,1) if profile=='leadlag1' else (0,))
                ops[scenario]=PanelOperator(frame,list(samples[scenario].ticker),counts,offsets=offsets)
            p,b=ops['decada'].evaluate();add_rows(rows,draws,statistics(p,b),'micro18',profile,'decada',L,80);del b
            p,b=ops['recente'].evaluate();add_rows(rows,draws,statistics(p,b),'micro18',profile,'recente',L,117)
            add_rows(rows,draws,statistics(p[:,common],b[:,:,common]),'micro18',profile,'decada_periodo_comum',L,80)
            for r in rows:
                if r['family']=='micro18' and r['profile']==profile and r['block']==L:r['block_choice']=bi
            del ops,b;gc.collect();print(f'G {profile}, block{L} complete',flush=True)
    f=pd.DataFrame(rows)
    for L,g in f[f.family.eq('temporal4')].groupby('block'):f.loc[g.index,'p_adjusted']=holm(g.p_centered,4)
    for choice,g in f[f.family.eq('micro18')].groupby('block_choice'):
        assert len(g)==18;f.loc[g.index,'p_adjusted']=holm(g.p_centered,18)
    assert len(f)==66
    f.to_csv(output/'observed_aggregate.csv.gz',index=False,compression={'method':'gzip','mtime':0});np.savez_compressed(output/'observed_draws.npz',**draws)
    return f


def rate(events):
    R=len(events);p=float(np.mean(events));z=norm.ppf(.975);c=(p+z*z/(2*R))/(1+z*z/R);r=z*np.sqrt(p*(1-p)/R+z*z/(4*R*R))/(1+z*z/R)
    return dict(rate=p,mcse=np.sqrt(p*(1-p)/R),wilson_low=max(0,c-r),wilson_high=min(1,c+r))


def calibration(root,plan,fp,mats,samples,output):
    cfg=plan['calibration'];R=cfg['outer_R'];B=cfg['inner_B'];assert B==4999
    ops=f_operators(fp,mats,samples,21);assert not any(p.invalid.any() for p in ops.values())
    market=mats['decada']['^BVSP'].to_numpy();scale=np.sqrt(.5+.5*np.r_[market[0],market[:-1]]**2/np.mean(market**2));scale/=np.sqrt(np.mean(scale**2))
    nuisance=pd.read_csv(root/'results/tables/lab03e_colab_20261023/asset_nuisance.csv.gz');assert list(nuisance.papel_id)==list(samples['recente'].papel_id)
    generator=dict(market=market,scale=scale,dates=mats['decada'].index,nuisance=nuisance,plan_e={'seed_entropy':plan['observed_bootstrap']['seed']})
    ids=list(samples['recente'].papel_id);common=np.array([ids.index(p) for p in samples['decada'].papel_id]);Npre=(mats['decada'].index.year<2021).sum()
    rows=[];summaries=[];family_rows=[];start=time.monotonic()
    for mi,name in enumerate(cfg['mechanisms']):
        assert name==MECHANISMS[mi];mechanism=[]
        for first in range(0,R,10):
            noise=np.stack([noise_path(generator,mi,i,purpose=410) for i in range(first,min(first+10,R))],axis=1)
            values=family_values(ops,common,noise[:,:,common],noise[Npre:],noise[:Npre,:,common])
            for (family,profile,scenario),stats in values.items():
                for stat,q in stats.items():
                    assert not q['invalid_draws'].any()
                    for j in range(len(q['estimate'])):
                        row=dict(mechanism=name,replication=first+j,family=family,profile=profile,scenario=scenario,statistic=stat)
                        row.update({k:float(v[j]) for k,v in q.items() if k!='draws'});mechanism.append(row)
            if (first+10)%50==0:print(f'G calibration {name}: {first+10}/{R}; {time.monotonic()-start:.1f}s elapsed',flush=True)
        f=pd.DataFrame(mechanism);assert len(f)==R*14
        for (rep,family),g in f.groupby(['replication','family']):
            size=10 if family=='F' else 4;assert len(g)==size;f.loc[g.index,'p_adjusted']=holm(g.p_centered,size)
        for keys,g in f.groupby(['family','profile','scenario','statistic']):
            identity=dict(mechanism=name,family=keys[0],profile=keys[1],scenario=keys[2],statistic=keys[3],R=R,B=B)
            for event,ev in [('raw_rejection',g.p_centered<.05),('adjusted_rejection',g.p_adjusted<.05),('coverage',(g.ci_low<=0)&(g.ci_high>=0))]:summaries.append(dict(**identity,event=event,**rate(ev)))
        for family,g in f.groupby('family'):
            for adjusted,pcol in [(False,'p_centered'),(True,'p_adjusted')]:family_rows.append(dict(mechanism=name,family=family,adjusted=adjusted,R=R,**rate(g.assign(reject=g[pcol]<.05).groupby('replication').reject.any())))
        rows.append(f);print(f'G calibration {name} complete',flush=True)
        pd.concat(rows).to_csv(output/'calibration_replications.csv.gz',index=False,compression={'method':'gzip','mtime':0})
        pd.DataFrame(summaries).to_csv(output/'calibration_cases.csv',index=False);pd.DataFrame(family_rows).to_csv(output/'calibration_families.csv',index=False)
    return pd.concat(rows)

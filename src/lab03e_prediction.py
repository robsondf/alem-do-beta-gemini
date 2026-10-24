"""Conditional-market predictive-risk calibration with repeated asset estimation.

The exact oracle is used only to evaluate coverage in declared simulations. It
never enters a forecast. Market uncertainty/vintages/universe bias remain outside.
"""
import numpy as np,pandas as pd
from scipy import sparse
from scipy.signal import lfilter
from lab03c import probability,panel_rate


def forecast_weights(m,valid,train,targets):
    """Two fixed-past OLS forecast operators; inputs contain no asset outcomes."""
    mt=m[train];on=valid[train]&(mt!=0);n=on.sum();pos=on&(mt>0);neg=on&(mt<0);W=len(train)
    if n==0:raise ArithmeticError('No historical pairs; no invented forecast')
    eligible=n>=200 and n/W>=.95 and pos.sum()>=60 and neg.sum()>=60
    if eligible:eligible=min(np.var(mt[on],ddof=1),np.var(mt[pos],ddof=1),np.var(mt[neg],ddof=1))>=1e-12
    if not eligible:
        mean=np.full((len(targets),n),1/n);return train[on],mean,mean.copy(),dict(n_pairs=n,n_plus=pos.sum(),n_minus=neg.sum(),status='historical_mean_fallback')
    arX=np.column_stack([np.ones(W-1),mt[:-1]]);ar=np.linalg.lstsq(arX,mt[1:],rcond=None)[0];eps=mt[1:]-arX@ar;eps-=eps.mean();ms=ar[0]+ar[1]*m[targets-1,None]+eps[None,:]
    scale=np.std(mt[on],ddof=1);X=np.column_stack([np.ones(n),(mt[on]>0),mt[on]/scale,mt[on]*(mt[on]>0)/scale]);P=np.linalg.pinv(X);PT=np.linalg.pinv(X[:,[0,2]])
    F=np.column_stack([np.ones(len(targets)),(ms>0).mean(1),ms.mean(1)/scale,(ms*(ms>0)).mean(1)/scale]);Ftr=F[:,[0,2]]
    tr=Ftr@PT;co=F@P;zero=(ms==0).mean(1)
    if zero.any():co+=zero[:,None]*(PT[0]-P[0])
    return train[on],tr,co,dict(n_pairs=n,n_plus=pos.sum(),n_minus=neg.sum(),status='estimated')


def panel_operators(d,W,pi):
    panel=d['panels'][pi];sample=panel['sample'];mat=d['matrices']['referencia_n'][panel['scenario']];master=d['dates'];m=d['market'];N=len(m);year=2019 if pi==0 else 2024;targets=np.flatnonzero((master.year>=year)&(master.year<=2025));dates=master[targets];month=dates.to_period('M');Y=np.full((N,len(sample)),np.nan);Y[master.get_indexer(mat.index)]=mat[sample.ticker].to_numpy();valid=np.isfinite(Y)
    # Deduplication key is computational only; each monthly operator reads prior mask only.
    begin=targets[0]-W;keys={}
    for j in range(len(sample)):keys.setdefault(valid[begin:targets[-1]+1,j].tobytes(),[]).append(j)
    ops=[];audit=[]
    for members in keys.values():
        mask=valid[:,members[0]];ri=[];ci=[];trdata=[];codata=[]
        for period in month.unique():
            loc=np.flatnonzero(month==period);tt=targets[loc];origin=tt[0]-1;train=np.arange(origin-W+1,origin+1);used,tr,co,stats=forecast_weights(m,mask,train,tt);assert used.max()<tt.min()
            ri.append(np.repeat(loc,len(used)));ci.append(np.tile(used,len(loc)));trdata.append(tr.ravel());codata.append(co.ravel())
            for j in members:audit.append(dict(window=W,scenario=panel['scenario'],papel_id=sample.iloc[j].papel_id,origin=str(master[origin].date()),max_train_date=str(master[used.max()].date()),target_start=str(master[tt.min()].date()),target_end=str(master[tt.max()].date()),**stats))
        rr=np.concatenate(ri);cc=np.concatenate(ci);shape=(len(targets),N);tr=sparse.csr_matrix((np.concatenate(trdata),(rr,cc)),shape=shape);co=sparse.csr_matrix((np.concatenate(codata),(rr,cc)),shape=shape);ops.append(dict(members=np.array(members),traditional=tr,conditional=co))
    return dict(window=W,panel_index=pi,scenario=panel['scenario'],sample=sample,assets=panel['asset_index'],targets=targets,dates=dates,valid=valid[targets],operators=ops,audit=audit)


def covariance_variance(A,targets,phi):
    if not phi:return np.asarray(A.multiply(A).sum(axis=1)).ravel()
    dense=A.toarray();forward=lfilter([1.],[1.,-phi],dense,axis=1);backward=lfilter([1.],[1.,-phi],dense[:,::-1],axis=1)[:,::-1];convolved=forward+backward-dense
    # Difference in full MSE later cancels Var(current error)=1, but keeps covariance.
    return np.sum(dense*convolved,axis=1)-2*convolved[np.arange(len(targets)),targets]


def oracle_risk(d,p,phi,delta):
    """Exact E(loss gap | complete fixed market path, covariance law, nuisance)."""
    m=d['market'];dm=m*(m>0);target=p['targets'];beta=d['nuisance'].beta_base.to_numpy()[p['assets']];sigma=d['nuisance'].sigma.to_numpy()[p['assets']];out=np.empty(len(p['sample']))
    for op in p['operators']:
        ids=op['members'];tr=op['traditional'];co=op['conditional'];true=m[target,None]*beta[ids]+delta*dm[target,None];meantr=(tr@m)[:,None]*beta[ids]+delta*(tr@dm)[:,None];meanco=(co@m)[:,None]*beta[ids]+delta*(co@dm)[:,None];bias=(true-meantr)**2-(true-meanco)**2
        v=covariance_variance(tr,target,phi)-covariance_variance(co,target,phi);risk=bias+v[:,None]*sigma[ids]**2;mask=p['valid'][:,ids];out[ids]=np.where(mask,risk,0).sum(0)/mask.sum(0)
    return out


def predict(p,Y):
    """OLS is re-estimated for each path via its exact fixed-design linear map."""
    # Y: sessions x replications x117; coefs/forecasts depend on past outcomes only.
    T=len(p['targets']);R=Y.shape[1];A=len(p['sample']);tr=np.empty((T,R,A));co=np.empty_like(tr)
    for op in p['operators']:
        ids=op['members'];assets=p['assets'][ids];values=Y[:,:,assets].reshape(len(Y),R*len(ids));tr[:,:,ids]=(op['traditional']@values).reshape(T,R,len(ids));co[:,:,ids]=(op['conditional']@values).reshape(T,R,len(ids))
    actual=Y[p['targets']][:,:,p['assets']];loss=(actual-tr)**2-(actual-co)**2;loss=np.where(p['valid'][:,None,:],loss,0.);gain=loss.sum(0)/p['valid'].sum(0);return loss,gain,tr,co


def bootstrap_bank(p,block,seed,B=1999):
    T=len(p['targets']);K=int(np.ceil(T/block));full=T//block;remainder=T%block;rng=np.random.default_rng(np.random.SeedSequence([seed,701,p['window'],p['panel_index'],block]));starts=rng.integers(0,T-block+1,size=(B,K));rows=np.repeat(np.arange(B),full);cols=starts[:,:full].ravel();counts=sparse.csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(B,T-block+1));last=starts[:,-1] if remainder else None
    bank=dict(block=block,remainder=remainder,counts=counts,last=last,B=B,T=T);bank['denominator']=resample_sums(p['valid'].astype(float),bank)
    if (bank['denominator']==0).any():raise ArithmeticError('Empty bootstrap asset; no redraw')
    return bank


def resample_sums(value,bank):
    # Exact same noncircular moving-block draws as the original direct-index algorithm.
    L=bank['block'];c=np.vstack([np.zeros((1,value.shape[1])),np.cumsum(value,axis=0)]);total=bank['counts']@(c[L:]-c[:-L])
    r=bank['remainder']
    if r:total+=(c[r:]-c[:-r])[bank['last']]
    return total


def intervals(loss,gain,bank):
    T,R,A=loss.shape;draw=resample_sums(loss.reshape(T,R*A),bank).reshape(bank['B'],R,A)/bank['denominator'][:,None,:];lo,hi=np.quantile(draw,[.025,.975],axis=0);se=np.std(draw,axis=0,ddof=1)
    if np.any(se<=0):raise ArithmeticError('Degenerate predictive loss uncertainty')
    maximum=np.max(abs(draw-gain[None,:,:])/se[None,:,:],axis=2);critical=np.quantile(maximum,.9875,axis=0);width=critical[:,None]*se
    return lo,hi,width,se,critical


def draw_noise(d,mi,ri):
    p=d['plan_e'];rng=np.random.default_rng(np.random.SeedSequence([p['seed_entropy'],300,mi,ri]));N=len(d['market']);burn=1024 if mi==1 else 256;z=rng.standard_normal((N+burn,118));v=np.sqrt(.3)*z[:,:1]+np.sqrt(.7)*z[:,1:]
    if mi==1:
        variance=np.ones(117);last=np.zeros(117);noise=np.empty_like(v)
        for t in range(len(v)):
            if t:variance=.03+.05*last**2+.92*variance
            last=np.sqrt(variance)*v[t];noise[t]=last
        noise=noise[burn:]
    else:
        phi=.3 if mi==2 else 0.;noise=lfilter([np.sqrt(1-phi*phi)],[1,-phi],v,axis=0)[burn:]
    return noise*d['nuisance'].sigma.to_numpy()[None,:]


def run(d,output,progress=print):
    plan=d['plan_e'];R=plan['predictive']['validation_per_scenario'];previous_seed=d['previous_plan_seed'];panels=[panel_operators(d,W,pi) for W in [252,504] for pi in [0,1]];offset=np.cumsum([0]+[len(p['sample']) for p in panels]);assert offset[-1]==394
    banks={(i,L):bootstrap_bank(p,L,previous_seed) for i,p in enumerate(panels) for L in [21,42,63]};case=[]
    for i,p in enumerate(panels):
        for row in p['sample'].to_dict('records'):case.append({**row,'window':p['window'],'scenario':p['scenario']})
    pd.DataFrame(case).to_csv(output/'predictive_design.csv',index=False);pd.DataFrame([r for p in panels for r in p['audit']]).to_csv(output/'predictive_fold_design.csv',index=False)
    beta=d['nuisance'].beta_base.to_numpy();base=d['market'][:,None]*beta;dm=d['market']*(d['market']>0);families=[];asset_summaries=[]
    for mi,name in enumerate(['gaussian_iid','gaussian_garch','gaussian_ar03']):
        phi=.3 if mi==2 else 0.;truth={delta:np.concatenate([oracle_risk(d,p,phi,delta) for p in panels]) for delta in [0.,.25]}
        saved={delta:dict(gain=np.empty((R,394)),truth=truth[delta],marginal_low=np.empty((R,394,3)),marginal_high=np.empty((R,394,3)),simultaneous_width=np.empty((R,394,3)),bootstrap_se=np.empty((R,394,3)),critical=np.empty((R,4,3))) for delta in [0.,.25]}
        for start in range(0,R,8):
            count=min(8,R-start);noise=np.stack([draw_noise(d,mi,ri) for ri in range(start,start+count)],axis=1)
            for delta in [0.,.25]:
                Y=base[:,None,:]+noise+delta*dm[:,None,None];a=saved[delta]
                for pi,p in enumerate(panels):
                    ix=slice(offset[pi],offset[pi+1]);loss,gain,_,_=predict(p,Y);a['gain'][start:start+count,ix]=gain
                    for li,L in enumerate([21,42,63]):
                        lo,hi,width,se,critical=intervals(loss,gain,banks[pi,L]);a['marginal_low'][start:start+count,ix,li]=lo;a['marginal_high'][start:start+count,ix,li]=hi;a['simultaneous_width'][start:start+count,ix,li]=width;a['bootstrap_se'][start:start+count,ix,li]=se;a['critical'][start:start+count,pi,li]=critical
            if start%80==0:progress(f'Predictive risk validation {name}: {start+count}/{R}; all394 cases,2effects,3block lengths',flush=True)
        for delta,a in saved.items():
            np.savez_compressed(output/(f'predictive_{name}_delta{delta:.2f}.npz'),**a)
            for li,L in enumerate([21,42,63]):
                for method in ['marginal_percentile','simultaneous_max_deviation']:
                    if method=='marginal_percentile':lo=a['marginal_low'][:,:,li];hi=a['marginal_high'][:,:,li]
                    else:lo=a['gain']-a['simultaneous_width'][:,:,li];hi=a['gain']+a['simultaneous_width'][:,:,li]
                    covered=(lo<=a['truth'])&(hi>=a['truth']);rj=(lo>0);null=a['truth']<=0;alt=~null;rate=probability(covered.all(1));false=probability(rj[:,null].any(1)) if null.any() else [np.nan]*4;mean,mc=panel_rate(covered);pr,prse=panel_rate(rj[:,alt]);families.append(dict(mechanism=name,delta=delta,block_length=L,method=method,nominal_marginal=.95,nominal_family=.95 if method.startswith('simultaneous') else np.nan,mean_coverage=mean,mean_coverage_mcse=mc,joint_coverage=rate[0],joint_coverage_mcse=rate[1],joint_mc_low=rate[2],joint_mc_high=rate[3],fwer_gain_positive=false[0],fwer_gain_positive_mc_low=false[2],fwer_gain_positive_mc_high=false[3],power=pr,power_mcse=prse,mc_conditional_on_fixed_bootstrap_bank=True))
                    cv=probability(covered)
                    for j,row in enumerate(case):asset_summaries.append(dict(mechanism=name,delta=delta,block_length=L,method=method,window=row['window'],scenario=row['scenario'],papel_id=row['papel_id'],ticker=row['ticker'],true_conditional_risk_gap=a['truth'][j],mean_estimated_gain=a['gain'][:,j].mean(),coverage=cv[0][j],coverage_mcse=cv[1][j],coverage_mc_low=cv[2][j],coverage_mc_high=cv[3][j],mean_interval_width=(hi[:,j]-lo[:,j]).mean()))
        progress(f'Predictive risk validation {name}: {R}/{R} complete',flush=True)
    # Observed N forecasts are unchanged; reproduce old marginal intervals and add max-deviation CIs.
    Y=np.full((len(d['market']),117),np.nan)
    for p in d['panels']:Y[np.ix_(p['time_index'],p['asset_index'])]=d['matrices']['referencia_n'][p['scenario']][p['sample'].ticker].to_numpy()
    observed=[]
    for pi,p in enumerate(panels):
        # Sparse operators have zero entries on missing training positions; zeros below are only algebraic masking.
        loss,gain,tr,co=predict(p,np.where(np.isfinite(Y),Y,0.)[:,None,:]);n=p['valid'].sum(0)
        for li,L in enumerate([21,42,63]):
            lo,hi,width,se,critical=intervals(loss,gain,banks[pi,L])
            for j,row in enumerate(p['sample'].to_dict('records')):
                observed.append(dict(window=p['window'],scenario=p['scenario'],papel_id=row['papel_id'],ticker=row['ticker'],block_length=L,n=int(n[j]),loss_gain=gain[0,j],marginal_low=lo[0,j],marginal_high=hi[0,j],simultaneous_low=gain[0,j]-width[0,j],simultaneous_high=gain[0,j]+width[0,j],bootstrap_se=se[0,j],group_critical=critical[0],family_size=394,common_reused=False))
    obs=pd.DataFrame(observed);long_ids=set(d['panels'][0]['sample'].papel_id);common=obs[obs.scenario.eq('recente')&obs.papel_id.isin(long_ids)].copy();common['scenario']='decada_periodo_comum';common['common_reused']=True;obs=pd.concat([obs,common],ignore_index=True)
    return dict(predictive_family=pd.DataFrame(families),predictive_calibration=pd.DataFrame(asset_summaries),observed_predictive_intervals=obs)

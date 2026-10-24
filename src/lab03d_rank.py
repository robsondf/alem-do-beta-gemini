"""Design-equivalent marginal MC banks and finite-model rank-envelope tests.

Location/scale invariance removes redundant asset simulation in calibration only.
Joint validation retains117 distinct paths. No distribution-free market guarantee.
"""
import numpy as np,pandas as pd
from scipy.signal import lfilter
from lab03c import kernel,draw_errors,holm_rows,probability,panel_rate,patterns
from lab03d_inference import details,hac_variance,temporal_project,temporal_truth,family_performance
from lab03d_envelope import precalculate,statistic


def designs(d):
    tasks=[];maps={};catalog=[]
    def add(kind,k,ti,j):
        key=(kind,ti.tobytes(),k['valid'][:,j].tobytes())
        if key in maps:return maps[key]
        index=len(tasks);kk=kernel(k['m'],k['valid'][:,[j]]);tasks.append(dict(kind=kind,kernel=kk,time_index=ti))
        catalog.append(dict(bank_index=index,kind=kind,n_sessions=len(ti),conditional_n=int(kk['valid'].sum()),n_plus=int(kk['plus'][1][0]),n_minus=int(kk['minus'][1][0]),first_session=str(d['dates'][ti[0]].date()),last_session=str(d['dates'][ti[-1]].date())))
        maps[key]=index;return index
    static=[]
    for p in d['panels']:
        for j in range(len(p['asset_index'])):static.append(add('static',p['kernel'],p['time_index'],j))
    annual=[]
    for p in d['annual_groups']:
        for j in range(len(p['asset_index'])):annual.append(add('annual',p['kernel'],p['time_index'],j))
    theta=[];early,late=d['theta_panels']
    for j in range(80):
        key=('theta',early['kernel']['valid'][:,j].tobytes(),late['kernel']['valid'][:,j].tobytes())
        if key not in maps:
            index=len(tasks);ek=kernel(early['kernel']['m'],early['kernel']['valid'][:,[j]]);lk=kernel(late['kernel']['m'],late['kernel']['valid'][:,[j]])
            tasks.append(dict(kind='theta',early=ek,late=lk,early_time=early['time_index'],late_time=late['time_index']))
            catalog.append(dict(bank_index=index,kind='theta',n_sessions=len(d['dates']),conditional_n=int(ek['valid'].sum()+lk['valid'].sum()),n_plus=int(ek['plus'][1][0]+lk['plus'][1][0]),n_minus=int(ek['minus'][1][0]+lk['minus'][1][0]),first_session=str(d['dates'][0].date()),last_session=str(d['dates'][-1].date())))
            maps[key]=index
        theta.append(maps[key])
    return dict(tasks=tasks,static=np.asarray(static),annual=np.asarray(annual),theta=np.asarray(theta),catalog=pd.DataFrame(catalog))


def bank_statistic(noise,design):
    out=np.empty(len(design['tasks']))
    for i,p in enumerate(design['tasks']):
        if p['kind']!='theta':
            k=p['kernel'];e,s,_,_=details(noise[p['time_index'],None],k);se=np.sqrt(hac_variance(s[1])*k['correction']);out[i]=e[0]/se[0]
        else:
            ek,lk=p['early'],p['late'];ee,es,_,_=details(noise[p['early_time'],None],ek);le,ls,_,_=details(noise[p['late_time'],None],lk)
            score=np.concatenate([-es[1],ls[1]],axis=0);n=ek['valid'].sum()+lk['valid'].sum();se=np.sqrt(hac_variance(score)*n/(n-8));out[i]=(le[0]-ee[0])/se[0]
    return out


def unit_path(d,plan,entropy,mi,ri):
    rng=np.random.default_rng(np.random.SeedSequence([entropy,mi,ri]));shape=(len(d['market'])+256,2)
    z=rng.standard_normal(shape) if mi==0 else rng.standard_t(5,shape)*np.sqrt(.6)
    innovation=np.sqrt(.3)*z[:,0]+np.sqrt(.7)*z[:,1];phi=plan['mechanisms'][mi]['phi'];u=lfilter([np.sqrt(1-phi*phi)],[1,-phi],innovation)[256:]
    return u*(d['scale'] if mi else 1.)


def equivalence_check(d,dd):
    # A common path with differing positive scales must reproduce every mapped statistic.
    rng=np.random.default_rng(832);u=rng.normal(0,.02,len(d['market']));scale=np.linspace(.5,2,117);noise=u[:,None]*scale[None,:]
    precalculate(d);e,s=statistic(d,noise);ae,ase,te,tse=temporal_project(d,noise);bank=bank_statistic(u,dd)
    differences=[]
    for name,value in [('static',e/s),('annual',ae/ase[1]),('theta',te/tse[1])]:
        ref=bank[dd[name]];np.testing.assert_allclose(value,ref,rtol=1e-10,atol=1e-12);differences.append(float(np.max(np.abs(value-ref))))
    return max(differences)


def generate(d,dd,plan,add):
    B=9999;R=1000;G=len(dd['tasks']);bank=np.empty((3,B,G));out={kind+'_'+part:np.empty((3,R,n)) for kind,n in [('static',197),('annual',985),('theta',80)] for part in ['error','se']}
    for mi,spec in enumerate(plan['mechanisms']):
        for ri in range(B):
            bank[mi,ri]=bank_statistic(unit_path(d,plan,add['calibration_seed_entropy'],mi,ri),dd)
            if ri%1000==999:print(f'Equivalent-design bank {spec["name"]}: {ri+1}/{B}',flush=True)
        print(f'Equivalent-design bank {spec["name"]}: {B}/{B} complete',flush=True)
    precalculate(d);p=dict(plan,seed_entropy=add['validation_seed_entropy'])
    for mi,spec in enumerate(plan['mechanisms']):
        for ri in range(R):
            noise=draw_errors(d,mi,ri,p);e,s=statistic(d,noise);ae,ase,te,tse=temporal_project(d,noise)
            for kind,ee,ss in [('static',e,s),('annual',ae,ase[1]),('theta',te,tse[1])]:out[kind+'_error'][mi,ri]=ee;out[kind+'_se'][mi,ri]=ss
            if ri%100==99:print(f'Independent joint validation {spec["name"]}: {ri+1}/{R}',flush=True)
    if not np.isfinite(bank).all() or any(not np.isfinite(a).all() for a in out.values()):raise ArithmeticError('Nonfinite rank simulation')
    return bank,out


def rank_p(stat,sorted_signed,sorted_abs,mapping,tail='two'):
    a=np.atleast_2d(stat);B=sorted_signed.shape[1];out=np.zeros_like(a)
    for m in range(3):
        for j,g in enumerate(mapping):
            if tail=='two':count=B-np.searchsorted(sorted_abs[m,:,g],np.abs(a[:,j]),side='left')
            elif tail=='positive':count=B-np.searchsorted(sorted_signed[m,:,g],a[:,j],side='left')
            elif tail=='negative':count=np.searchsorted(sorted_signed[m,:,g],a[:,j],side='right')
            else:raise ValueError(tail)
            out[:,j]=np.maximum(out[:,j],(1+count)/(B+1))
    return out


def annual_maps(d):return [row[row>=0] for row in d['annual_map']]

def temporal_p(d,bank,dd,ae,ase,te,tse):
    signed,ab=bank;ap=rank_p(ae/ase,signed,ab,dd['annual'],'positive');an=rank_p(ae/ase,signed,ab,dd['annual'],'negative')
    pp=np.column_stack([ap[:,ix].max(1) for ix in annual_maps(d)]);pn=np.column_stack([an[:,ix].max(1) for ix in annual_maps(d)])
    tp=rank_p(te/tse,signed,ab,dd['theta'])
    return np.column_stack([tp,pp,pn])


def summarize(d,dd,plan,cal,a):
    signed=np.sort(cal,axis=1);ab=np.sort(np.abs(cal),axis=1);bank=(signed,ab);marg=np.max(ab[:,9500,:],axis=0);sim=np.max(ab[:,9997,:],axis=0)
    sc=[];sf=[];sr=[];sp=[];tc=[];tf=[];th=[]
    pp=dict(effect_patterns=dict(dense_delta=[-.5,-.25,-.1,0,.1,.25,.5],sparse_delta=[-.25,.25]))
    for mi,spec in enumerate(plan['mechanisms']):
        e=a['static_error'][mi];s=a['static_se'][mi];cv=np.abs(e)<=marg[dd['static']]*s;simcv=np.abs(e)<=sim[dd['static']]*s;cp=probability(cv)
        for j,row in enumerate(d['design'].to_dict('records')):sc.append(dict(**row,mechanism=spec['name'],coverage=cp[0][j],coverage_mcse=cp[1][j],coverage_mc_low=cp[2][j],coverage_mc_high=cp[3][j],marginal_critical=marg[dd['static'][j]],bonferroni_critical=sim[dd['static'][j]]))
        for pattern,truth in patterns(d['design'],d['nuisance'],pp):
            p=rank_p((e+truth)/s,signed,ab,dd['static']);raw=p<.05;adj=holm_rows(p)<.05;null=truth==0;f=family_performance(raw,adj,null);f.update(mechanism=spec['name'],method='MC_envelope_Holm',pattern=pattern,simultaneous_coverage=float(simcv.all(1).mean()),simultaneous_coverage_mcse=float(simcv.all(1).std(ddof=1)/np.sqrt(len(e))),validation_conditioned_on_generated_bank=True);sf.append(f);pr=probability(adj)
            for j,row in enumerate(d['design'].itertuples()):sr.append(dict(mechanism=spec['name'],pattern=pattern,scenario=row.scenario,papel_id=row.papel_id,true_delta=truth[j],adjusted_rejection=pr[0][j],adjusted_mcse=pr[1][j],adjusted_mc_low=pr[2][j],adjusted_mc_high=pr[3][j]))
            for scenario in ['decada','recente']:
                ix=d['design'].scenario.eq(scenario).to_numpy();q=dict(mechanism=spec['name'],method='MC_envelope_Holm',pattern=pattern,scenario=scenario)
                for key,ev,mask in [('coverage',cv,ix),('power_adjusted',adj,ix&~null)]:q[key],q[key+'_mcse']=panel_rate(ev[:,mask])
                sp.append(q)
        ae=a['annual_error'][mi];ase=a['annual_se'][mi];te=a['theta_error'][mi];tse=a['theta_se'][mi]
        for kind,design,err,se in [('annual',d['annual_design'],ae,ase),('theta',d['design'].iloc[:80],te,tse)]:
            covered=np.abs(err)<=marg[dd[kind]]*se;cp=probability(covered)
            for j,row in enumerate(design.to_dict('records')):tc.append(dict(**row,kind=kind,mechanism=spec['name'],coverage=cp[0][j],coverage_mcse=cp[1][j],coverage_mc_low=cp[2][j],coverage_mc_high=cp[3][j]))
        for pattern in plan['temporal']['patterns']:
            ta,tt,null=temporal_truth(d,pattern);p=temporal_p(d,bank,dd,ae+ta,ase,te+tt,tse);raw=p<.05;adj=holm_rows(p)<.05;f=family_performance(raw,adj,null);f.update(mechanism=spec['name'],method='MC_envelope_Holm',pattern=pattern);tf.append(f);pr=probability(adj)
            for j in range(474):
                case=j if j<80 else (j-80 if j<277 else j-277);row=d['design'].iloc[case];th.append(dict(mechanism=spec['name'],pattern=pattern,kind='theta' if j<80 else ('positive_IUT' if j<277 else 'negative_IUT'),scenario=row.scenario,papel_id=row.papel_id,is_true_null=bool(null[j]),adjusted_rejection=pr[0][j],adjusted_mcse=pr[1][j],adjusted_mc_low=pr[2][j],adjusted_mc_high=pr[3][j]))
    return dict(envelope_calibration=pd.DataFrame(sc),envelope_family=pd.DataFrame(sf),envelope_rejection=pd.DataFrame(sr),envelope_panels=pd.DataFrame(sp),envelope_temporal_calibration=pd.DataFrame(tc),envelope_temporal_family=pd.DataFrame(tf),envelope_temporal_hypotheses=pd.DataFrame(th))


def observed(d,dd,cal):
    y=np.zeros((len(d['market']),117))
    for p in d['panels']:y[np.ix_(p['time_index'],p['asset_index'])]=d['matrices']['referencia_n'][p['scenario']][p['sample'].ticker].to_numpy()
    precalculate(d);e,s=statistic(d,y);ae,ase,te,tse=temporal_project(d,y);signed=np.sort(cal,axis=1);ab=np.sort(np.abs(cal),axis=1);crit=np.max(ab[:,9500,:],axis=0);bonf=np.max(ab[:,9997,:],axis=0)
    p=rank_p(e[None,:]/s[None,:],signed,ab,dd['static'])[0];adj=holm_rows(p[None,:])[0];rows=[]
    for j,row in enumerate(d['design'].to_dict('records')):rows.append(dict(**row,method='MC_envelope_Holm',delta=e[j],se_delta=s[j],p_envelope=p[j],p_envelope_holm_197=adj[j],ci_marginal_low=e[j]-crit[dd['static'][j]]*s[j],ci_marginal_high=e[j]+crit[dd['static'][j]]*s[j],ci_bonferroni_low=e[j]-bonf[dd['static'][j]]*s[j],ci_bonferroni_high=e[j]+bonf[dd['static'][j]]*s[j]))
    p=temporal_p(d,(signed,ab),dd,ae[None,:],ase[1,None,:],te[None,:],tse[1,None,:])[0];adj=holm_rows(p[None,:])[0];temp=[]
    for j in range(474):
        case=j if j<80 else (j-80 if j<277 else j-277);row=d['design'].iloc[case];temp.append(dict(method='MC_envelope_Holm',kind='theta' if j<80 else ('positive_IUT' if j<277 else 'negative_IUT'),scenario=row.scenario,papel_id=row.papel_id,p_envelope=p[j],p_envelope_holm_474=adj[j]))
    intervals=[]
    for kind,design,value,se in [('annual',d['annual_design'],ae,ase[1]),('theta',d['design'].iloc[:80],te,tse[1])]:
        for j,row in enumerate(design.to_dict('records')):intervals.append(dict(**row,kind=kind,estimate=value[j],se=se[j],ci_marginal_low=value[j]-crit[dd[kind][j]]*se[j],ci_marginal_high=value[j]+crit[dd[kind][j]]*se[j]))
    return dict(observed_envelope=pd.DataFrame(rows),observed_envelope_temporal=pd.DataFrame(temp),observed_envelope_intervals=pd.DataFrame(intervals))


def tail_precision(d,dd,cal,observed_tables):
    """Pointwise MC tail uncertainty, not an interval for randomization p."""
    static=observed_tables['observed_envelope'];intervals=observed_tables['observed_envelope_intervals'];rows=[];B=cal.shape[1]
    for kind in ['static','annual','theta']:
        q=static if kind=='static' else intervals[intervals.kind.eq(kind)]
        value=q.delta.to_numpy()/q.se_delta.to_numpy() if kind=='static' else q.estimate.to_numpy()/q.se.to_numpy()
        for j,(row,t) in enumerate(zip(q.to_dict('records'),value)):
            for mi,name in enumerate(['gaussian_iid','student_hetero','student_ar']):
                simulated=cal[mi,:,dd[kind][j]]
                for tail in (['positive','negative'] if kind=='annual' else ['two']):
                    k=int((np.abs(simulated)>=abs(t)).sum()) if tail=='two' else int((simulated>=t).sum()) if tail=='positive' else int((simulated<=t).sum())
                    rate=k/B;z=1.959963984540054;den=1+z*z/B;center=(rate+z*z/(2*B))/den;half=z*np.sqrt(rate*(1-rate)/B+z*z/(4*B*B))/den
                    rows.append(dict(kind=kind,scenario=('decada' if row['year']<2021 else 'recente') if kind=='annual' else row['scenario'],papel_id=row['papel_id'],year=row.get('year'),mechanism=name,tail=tail,t_observed=t,exceedances=k,bank_size=B,rank_p=(k+1)/(B+1),mc_tail_rate=rate,mc_tail_wilson_low=max(0,center-half),mc_tail_wilson_high=min(1,center+half)))
    return pd.DataFrame(rows)

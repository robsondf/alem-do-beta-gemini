"""Independent fresh MC precision bank and declared out-of-class stress tests."""
import numpy as np,pandas as pd
from scipy.signal import lfilter
from scipy.stats import beta
from lab03c import holm_rows,probability,panel_rate
from lab03d_rank import designs,rank_p,temporal_p,annual_maps
from lab03d_inference import family_performance

KINDS=('static','annual','theta')
MECHANISMS=('gaussian_iid','student_hetero','student_ar','garch_t5','variance_break_t5','ar06_t5')

def part(k):
    m=k['m'];N=len(m);X=np.zeros((N,4));P=np.zeros((4,N));lev=np.zeros(N)
    for j,(mask,n,mean,w) in enumerate([k['plus'],k['minus']]):
        mask=mask[:,0];weight=w[:,0];mu=float(mean[0]);nn=int(n[0]);X[:,2*j]=mask;X[:,2*j+1]=mask*m;P[2*j]=mask/nn-mu*weight;P[2*j+1]=weight
        ss=np.sum(np.where(mask,m-mu,0)**2);lev+=np.where(mask,1/nn+(m-mu)**2/ss,0)
    return X,P,lev,k['weights'][:,0],int(k['valid'].sum())

def operators(d):
    dd=designs(d);ops=[]
    for task in dd['tasks']:
        if task['kind']!='theta':
            X,P,h,w,n=part(task['kernel']);ti=task['time_index'];k=4
        else:
            ex,ep,eh,ew,en=part(task['early']);lx,lp,lh,lw,ln=part(task['late']);N=len(ex)+len(lx);X=np.zeros((N,8));P=np.zeros((8,N));X[:len(ex),:4]=ex;X[len(ex):,4:]=lx;P[:4,:len(ex)]=ep;P[4:,len(ex):]=lp;h=np.r_[eh,lh];w=np.r_[-ew,lw];ti=np.r_[task['early_time'],task['late_time']];n=en+ln;k=8
        assert np.max(h)<1-1e-10
        ops.append(dict(time=ti,X=X,P=P,weight=w,score_weight=w/(1-h)*np.sqrt(n/(n-k)),kind=task['kind']))
    # All case-to-asset mappings are inherited; no correlated assets treated as independent.
    ids={pid:i for i,pid in enumerate(d['nuisance'].papel_id)};case_assets=dict(static=d['design'].master_asset_index.to_numpy(int),annual=np.array([ids[pid] for pid in d['annual_design'].papel_id]),theta=d['design'].iloc[:80].master_asset_index.to_numpy(int))
    groups=[]
    for g,op in enumerate(ops):
        kind=op['kind'];case=np.flatnonzero(dd[kind]==g);groups.append((kind,case,case_assets[kind][case]))
    dd['operators']=ops;dd['groups']=groups;return dd

def project(Y,op):
    # Y contains only the declared valid design; NaN positions have exactly zero design weights.
    Y=np.asarray(Y);Y=Y[:,None] if Y.ndim==1 else Y
    if np.isnan(Y).any():
        bad=np.isnan(Y);assert not np.any(bad & (op['weight'][:,None]!=0));Y=np.where(bad,0.,Y)
    coef=op['P']@Y;res=Y-op['X']@coef;score=op['score_weight'][:,None]*res;v=np.sum(score*score,axis=0)
    for lag in range(1,6):v+=2*(1-lag/6)*np.sum(score[lag:]*score[:-lag],axis=0)
    if np.any(v<=1e-28):raise ArithmeticError('Degenerate contrast; no clipping or dropped replicate')
    return op['weight']@Y,np.sqrt(v)

def project_all(noise,dd):
    result={k:(np.empty(n),np.empty(n)) for k,n in [('static',197),('annual',985),('theta',80)]}
    for op,(kind,case,assets) in zip(dd['operators'],dd['groups']):
        e,se=project(noise[np.ix_(op['time'],assets)],op);result[kind][0][case]=e;result[kind][1][case]=se
    return result

def bank_paths(d,mi,rng,count):
    N=len(d['market']);z=rng.standard_normal((count,N+256,2)) if mi==0 else rng.standard_t(5,(count,N+256,2))*np.sqrt(.6)
    v=np.sqrt(.3)*z[:,:,0]+np.sqrt(.7)*z[:,:,1];phi=.3 if mi==2 else 0.;u=lfilter([np.sqrt(1-phi*phi)],[1,-phi],v,axis=1)[:,256:]
    return (u*(d['scale'] if mi else 1.)).T

def calibration(d,dd,output,progress=print):
    plan=d['plan_e'];B=plan['precision']['calibration_per_mechanism'];S=plan['precision']['replications_per_stream'];bank=np.empty((3,B,len(dd['operators'])))
    for mi in range(3):
        for stream in range(3):
            rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],100,mi,stream]));offset=stream*S
            for start in range(0,S,128):
                n=min(128,S-start);paths=bank_paths(d,mi,rng,n)
                for g,op in enumerate(dd['operators']):
                    e,se=project(paths[op['time']],op);bank[mi,offset+start:offset+start+n,g]=e/se
                if (start//128)%25==0:progress(f'MC bank {MECHANISMS[mi]}, stream{stream+1}: {start+n}/{S}',flush=True)
            progress(f'MC bank {MECHANISMS[mi]}, stream{stream+1}: {S}/{S}',flush=True)
    assert np.isfinite(bank).all();np.savez_compressed(output/'calibration_bank.npz',calibration_t=bank,static_map=dd['static'],annual_map=dd['annual'],theta_map=dd['theta']);return bank

def noise_path(d,mi,ri,purpose=200):
    p=d['plan_e'];rng=np.random.default_rng(np.random.SeedSequence([p['seed_entropy'],purpose,mi,ri]));N=len(d['market']);burn=1024 if mi==3 else 256
    z=rng.standard_normal((N+burn,118)) if mi==0 else rng.standard_t(5,(N+burn,118))*np.sqrt(.6);v=np.sqrt(.3)*z[:,:1]+np.sqrt(.7)*z[:,1:]
    if mi==3:
        variance=np.ones(117);last=np.zeros(117);out=np.empty_like(v)
        for t in range(len(v)):
            if t:variance=.03+.05*last**2+.92*variance
            last=np.sqrt(variance)*v[t];out[t]=last
        u=out[burn:]
    else:
        phi=0. if mi<2 else (.6 if mi==5 else .3);u=lfilter([np.sqrt(1-phi*phi)],[1,-phi],v,axis=0)[burn:]
        if mi in [1,2,4,5]:u*=d['scale'][:,None]
        if mi==4:
            h=np.where(d['dates']>=pd.Timestamp('2020-01-01'),2.,1.);h/=np.sqrt(np.mean(h*h));u*=h[:,None]
    return u*d['nuisance'].sigma.to_numpy()[None,:]

def validation(d,dd,output,progress=print):
    R=d['plan_e']['inference']['validation_per_mechanism'];allvalues={}
    for mi,name in enumerate(MECHANISMS):
        values={kind+'_'+part:np.empty((R,n)) for kind,n in [('static',197),('annual',985),('theta',80)] for part in ['error','se']}
        for ri in range(R):
            v=project_all(noise_path(d,mi,ri),dd)
            for kind,(e,se) in v.items():values[kind+'_error'][ri]=e;values[kind+'_se'][ri]=se
            if ri%100==99:progress(f'Joint inference validation {name}: {ri+1}/{R}; all197/985/80 cases',flush=True)
        np.savez_compressed(output/('validation_'+name+'.npz'),**values);allvalues[name]=values
    return allvalues

def truth_patterns(d):
    annual=d['annual_design'];out=[('zero',np.zeros(985))]
    for value in d['plan_e']['inference']['temporal_constant_delta']:out.append((f'constant_{value:+.2f}',np.full(985,value)))
    for value in d['plan_e']['inference']['temporal_flip_magnitude']:out.append((f'flip_{value:.2f}',np.where(annual.year<2021,-value,value)))
    return out

def summaries(d,dd,bank,values):
    signed=np.sort(bank,axis=1);ab=np.sort(abs(bank),axis=1);marg=np.max(ab[:,int(np.ceil(len(bank[0])*.95)),:],axis=0);rows=[];power=[];coverage=[];patterns=truth_patterns(d);maps=annual_maps(d)
    for name,a in values.items():
        E=a['static_error'];S=a['static_se']
        for delta in d['plan_e']['inference']['static_dense_delta']:
            p=rank_p((E+delta)/S,signed,ab,dd['static']);rej=holm_rows(p)<.05;f=family_performance(p<.05,rej,np.full(197,delta==0));rows.append(dict(kind='static',mechanism=name,pattern=f'dense_{delta:+.2f}',**f))
            for scenario in ['decada','recente']:
                ix=d['design'].scenario.eq(scenario).to_numpy();pr,se=panel_rate(rej[:,ix]);power.append(dict(kind='static',mechanism=name,pattern=f'dense_{delta:+.2f}',scenario=scenario,true_effect=delta,rejection=pr,rejection_mcse=se,is_power=delta!=0))
        for kind,design in [('static',d['design']),('annual',d['annual_design']),('theta',d['design'].iloc[:80])]:
            covered=abs(a[kind+'_error'])<=marg[dd[kind]]*a[kind+'_se'];rate=probability(covered)
            for j,r in enumerate(design.to_dict('records')):coverage.append(dict(kind=kind,mechanism=name,**r,coverage=rate[0][j],coverage_mcse=rate[1][j],mc_low=rate[2][j],mc_high=rate[3][j]))
        for pattern,ta in patterns:
            tt=np.full(80,float(pattern.split('_')[1])*2 if pattern.startswith('flip_') else 0.);positive=np.array([np.all(ta[ix]>0) for ix in maps]);negative=np.array([np.all(ta[ix]<0) for ix in maps]);null=np.r_[tt==0,~positive,~negative]
            p=temporal_p(d,(signed,ab),dd,a['annual_error']+ta,a['annual_se'],a['theta_error']+tt,a['theta_se']);rej=holm_rows(p)<.05;rows.append(dict(kind='temporal',mechanism=name,pattern=pattern,**family_performance(p<.05,rej,null)))
            for kind,ix,truth in [('theta',np.arange(80),np.full(80,tt[0])),('positive_IUT',np.arange(80,277),positive.astype(float)),('negative_IUT',np.arange(277,474),-negative.astype(float))]:
                nonnull=~null[ix];rate,se=panel_rate(rej[:,ix][:,nonnull]);power.append(dict(kind=kind,mechanism=name,pattern=pattern,scenario='all',true_effect=float(ta.max()) if pattern.startswith('flip_') else float(ta[0]),rejection=rate,rejection_mcse=se,is_power=bool(nonnull.any()),true_alternatives=int(nonnull.sum())))
    return dict(inference_family=pd.DataFrame(rows),inference_power=pd.DataFrame(power),inference_coverage=pd.DataFrame(coverage))

def observed(d,dd,bank):
    Y=np.full((len(d['market']),117),np.nan)
    for p in d['panels']:Y[np.ix_(p['time_index'],p['asset_index'])]=d['matrices']['referencia_n'][p['scenario']][p['sample'].ticker].to_numpy()
    values=project_all(Y,dd);rows=[];tails=[];temps=[];S=d['plan_e']['precision']['replications_per_stream'];B=bank.shape[1]
    selections=[('pooled',bank)]+[(f'stream{s+1}',bank[:,s*S:(s+1)*S]) for s in range(3)]
    for label,cal in selections:
        signed=np.sort(cal,axis=1);ab=np.sort(abs(cal),axis=1);e,se=values['static'];p=rank_p((e/se)[None,:],signed,ab,dd['static'])[0];adj=holm_rows(p[None,:])[0]
        for j,r in enumerate(d['design'].to_dict('records')):rows.append(dict(bank=label,**r,delta=e[j],se_delta=se[j],p_rank=p[j],p_holm_197=adj[j],bank_size=cal.shape[1]))
        p=temporal_p(d,(signed,ab),dd,values['annual'][0][None,:],values['annual'][1][None,:],values['theta'][0][None,:],values['theta'][1][None,:])[0];adj=holm_rows(p[None,:])[0]
        for j in range(474):temps.append(dict(bank=label,kind='theta' if j<80 else 'positive_IUT' if j<277 else 'negative_IUT',case_index=j if j<80 else (j-80 if j<277 else j-277),p_rank=p[j],p_holm_474=adj[j],bank_size=cal.shape[1]))
    # Exact pointwise binomial intervals for the ideal tail probability, not CI for discrete rank p.
    for kind,design in [('static',d['design']),('annual',d['annual_design']),('theta',d['design'].iloc[:80])]:
        t=values[kind][0]/values[kind][1]
        for j,r in enumerate(design.to_dict('records')):
            for mi,name in enumerate(MECHANISMS[:3]):
                a=bank[mi,:,dd[kind][j]]
                for tail in (['positive','negative'] if kind=='annual' else ['two']):
                    k=int((abs(a)>=abs(t[j])).sum()) if tail=='two' else int((a>=t[j]).sum()) if tail=='positive' else int((a<=t[j]).sum());lo=0. if k==0 else float(beta.ppf(.025,k,B-k+1));hi=1. if k==B else float(beta.ppf(.975,k+1,B-k));tails.append(dict(kind=kind,papel_id=r['papel_id'],year=r.get('year'),scenario=r.get('scenario','decada' if r.get('year',0)<2021 else 'recente'),mechanism=name,tail=tail,t_observed=t[j],exceedances=k,bank_size=B,p_rank=(k+1)/(B+1),ideal_tail_lower=lo,ideal_tail_upper=hi,interval_scope='pointwise exact binomial ideal-tail probability; not adjusted-decision CI'))
    return dict(observed_static_precision=pd.DataFrame(rows),observed_temporal_precision=pd.DataFrame(temps),observed_tail_precision=pd.DataFrame(tails))

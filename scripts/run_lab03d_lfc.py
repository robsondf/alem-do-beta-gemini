#!/usr/bin/env python3
"""Exploratory least-favorable annual-direction stress, theta slots reserved."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03c import holm_rows,probability,panel_rate
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();o=a.output
 lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text());ap=ROOT/'data/lab03d/adendo_temporal_lfc_v1.json';assert hashlib.sha256(ap.read_bytes()).hexdigest()==lock['temporal_lfc_addendum_sha256']
 plan=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text());ad=json.loads(ap.read_text());dd=pd.read_csv(o/'design.csv');aa=pd.read_csv(o/'annual_design.csv');z=np.load(o/'replicates.npz');errors=z['annual_error'];ses=z['annual_se'];index={(r.papel_id,r.year):j for j,r in enumerate(aa.itertuples())};maps=[[index[(r.papel_id,y)] for y in range(2016 if r.scenario=='decada' else 2021,2026)] for r in dd.itertuples()];family=[];hyp=[]
 for year in ad['zero_years']:
  for delta in ad['other_year_delta']:
   truth=np.where(aa.year.eq(year),0.,delta);pos=np.array([np.all(truth[ix]>0) for ix in maps]);neg=np.array([np.all(truth[ix]<0) for ix in maps]);null=np.r_[np.zeros(80,bool),~pos,~neg];alt=np.r_[np.zeros(80,bool),pos,neg]
   for mi,spec in enumerate(plan['mechanisms']):
    for method,mi2 in [('HAC5_Holm',0),('HC3_HAC5_Holm',1)]:
     E=errors[mi]+truth;S=ses[mi,mi2];pp=np.column_stack([norm.sf(E[:,ix]/S[:,ix]).max(1) for ix in maps]);pn=np.column_stack([norm.cdf(E[:,ix]/S[:,ix]).max(1) for ix in maps]);p=np.column_stack([np.ones((1000,80)),pp,pn]);adjusted=holm_rows(p)<.05
     row=dict(zero_year=year,other_year_delta=delta,mechanism=spec['name'],method=method,tested=394,reserved_theta=80,family_size=474,true_null_tested=int(null.sum()),true_alternative_tested=int(alt.sum()))
     for prefix,ev in [('fwer_raw',p<.05),('fwer_adjusted',adjusted)]:
      values=probability(ev[:,null].any(1));row.update(zip([prefix,prefix+'_mcse',prefix+'_mc_low',prefix+'_mc_high'],[float(v) for v in values]))
     row['power'],row['power_mcse']=panel_rate(adjusted[:,alt]);family.append(row);rates=probability(adjusted[:,80:])
     for j in range(394):
      case=j if j<197 else j-197;r=dd.iloc[case];hyp.append(dict(zero_year=year,other_year_delta=delta,mechanism=spec['name'],method=method,kind='positive_IUT' if j<197 else 'negative_IUT',scenario=r.scenario,papel_id=r.papel_id,is_true_null=bool(null[80+j]),adjusted_rejection=rates[0][j],adjusted_mcse=rates[1][j]))
 pd.DataFrame(family).to_csv(o/'temporal_lfc_family.csv',index=False);pd.DataFrame(hyp).to_csv(o/'temporal_lfc_hypotheses.csv',index=False);print('IUT LFC stress:24 family summaries,9456 tested-hypothesis rows; theta not assessed in this diagnostic')
 # Analytic IUT boundary: other-year slopes tend to signed infinity; theta not assessed.
 rp=o/'envelope_replicates.npz'
 if rp.exists():
  rz=np.load(rp);bank=rz['calibration_t'];rank_errors=rz['annual_error'];rank_ses=rz['annual_se'];mapping=rz['annual_map']
  from lab03d_rank import rank_p
  signed=np.sort(bank,axis=1);ab=np.sort(np.abs(bank),axis=1);limit=[]
  for mi,spec in enumerate(plan['mechanisms']):
   for method in ['HAC5_Holm','HC3_HAC5_Holm','MC_envelope_Holm']:
    if method=='MC_envelope_Holm':
     E=rank_errors[mi];S=rank_ses[mi];pa=rank_p(E/S,signed,ab,mapping,'positive');na=rank_p(E/S,signed,ab,mapping,'negative');minimum=.0001;stream='independent envelope validation'
    else:
     E=errors[mi];S=ses[mi,0 if method=='HAC5_Holm' else 1];pa=norm.sf(E/S);na=norm.cdf(E/S);minimum=0.;stream='original Lab03D validation'
    for year in ad['zero_years']:
     present=np.array([year in range(2016 if r.scenario=='decada' else 2021,2026) for r in dd.itertuples()])
     for sign in [-1,1]:
      positive=np.ones((1000,197));negative=np.ones((1000,197));fav=positive if sign>0 else negative;source=pa if sign>0 else na
      for j,row in enumerate(dd.itertuples()):fav[:,j]=source[:,index[(row.papel_id,year)]] if present[j] else minimum
      p=np.column_stack([np.ones((1000,80)),positive,negative]);adj=holm_rows(p)<.05
      null=np.r_[np.zeros(80,bool),present if sign>0 else np.ones(197,bool),present if sign<0 else np.ones(197,bool)];alt=np.r_[np.zeros(80,bool),~present if sign>0 else np.zeros(197,bool),~present if sign<0 else np.zeros(197,bool)]
      row=dict(zero_year=year,other_year_effect_sign=sign,other_year_effect_limit='infinite',mechanism=spec['name'],method=method,stream=stream,tested=394,reserved_theta=80,family_size=474,true_null_tested=int(null.sum()),true_alternative_tested=int(alt.sum()))
      for prefix,ev in [('fwer_raw',p<.05),('fwer_adjusted',adj)]:
       values=probability(ev[:,null].any(1));row.update(zip([prefix,prefix+'_mcse',prefix+'_mc_low',prefix+'_mc_high'],[float(v) for v in values]))
      row['power'],row['power_mcse']=panel_rate(adj[:,alt]);limit.append(row)
  pd.DataFrame(limit).to_csv(o/'temporal_iut_limit_family.csv',index=False);print('Analytic IUT limiting-null diagnostic:36 summaries;80 theta slots reserved; finite-bank minimum p retained')

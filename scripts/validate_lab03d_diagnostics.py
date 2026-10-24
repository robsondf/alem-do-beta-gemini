#!/usr/bin/env python3
"""Independent reconstruction of IUT-boundary and finite-bank tail diagnostics."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import norm

def validate(o):
 d=pd.read_csv(o/'design.csv');aa=pd.read_csv(o/'annual_design.csv');lookup={(r.papel_id,r.year):j for j,r in enumerate(aa.itertuples())};maps=[[lookup[(r.papel_id,y)] for y in range(2016 if r.scenario=='decada' else 2021,2026)] for r in d.itertuples()]
 with np.load(o/'replicates.npz') as z:old={k:z[k] for k in ['annual_error','annual_se']}
 with np.load(o/'envelope_replicates.npz') as z:new={k:z[k] for k in ['annual_error','annual_se','calibration_t','annual_map','static_map','theta_map']}
 names=['gaussian_iid','student_hetero','student_ar'];bank=new['calibration_t'];signed=np.sort(bank,axis=1);ab=np.sort(abs(bank),axis=1)
 def rank(t,tail):
  result=np.zeros(t.shape)
  for mi in range(3):
   for j,g in enumerate(new['annual_map']):
    counts=9999-np.searchsorted(signed[mi,:,g],t[:,j],side='left') if tail=='positive' else np.searchsorted(signed[mi,:,g],t[:,j],side='right')
    result[:,j]=np.maximum(result[:,j],(1+counts)/10000)
  return result
 def check(row,p,null,alt):
  order=np.argsort(p,axis=1);q=np.take_along_axis(p,order,axis=1)*(474-np.arange(474));q=np.minimum(1,np.maximum.accumulate(q,axis=1));adj=np.empty_like(q);np.put_along_axis(adj,order,q,axis=1)
  for key,event in [('fwer_raw',p<.05),('fwer_adjusted',adj<.05)]:
   ev=event[:,null].any(1);rate=ev.mean();se=np.sqrt(rate*(1-rate)/1000);z=norm.ppf(.975);den=1+z*z/1000;c=(rate+z*z/2000)/den;h=z*np.sqrt(rate*(1-rate)/1000+z*z/4000000)/den
   np.testing.assert_allclose([row[key],row[key+'_mcse'],row[key+'_mc_low'],row[key+'_mc_high']],[rate,se,max(0,c-h),min(1,c+h)],atol=1e-14)
  if alt.any():np.testing.assert_allclose(row['power'],(adj[:,alt]<.05).mean(),atol=1e-14)
 limiting=pd.read_csv(o/'temporal_iut_limit_family.csv');finite=pd.read_csv(o/'temporal_lfc_family.csv')
 for row in limiting.to_dict('records'):
  mi=names.index(row['mechanism']);method=row['method'];isrank=method=='MC_envelope_Holm';err=new['annual_error'][mi] if isrank else old['annual_error'][mi];se=new['annual_se'][mi] if isrank else old['annual_se'][mi,0 if method=='HAC5_Holm' else 1];t=err/se;source=rank(t,'positive' if row['other_year_effect_sign']>0 else 'negative') if isrank else (norm.sf(t) if row['other_year_effect_sign']>0 else norm.cdf(t));present=np.array([row['zero_year'] in range(2016 if r.scenario=='decada' else 2021,2026) for r in d.itertuples()]);fav=np.full((1000,197),.0001 if isrank else 0.)
  for j,r in enumerate(d.itertuples()):
   if present[j]:fav[:,j]=source[:,lookup[(r.papel_id,row['zero_year'])]]
  p=np.column_stack([np.ones((1000,80)),fav if row['other_year_effect_sign']>0 else np.ones_like(fav),fav if row['other_year_effect_sign']<0 else np.ones_like(fav)]);null=np.r_[np.zeros(80,bool),present if row['other_year_effect_sign']>0 else np.ones(197,bool),present if row['other_year_effect_sign']<0 else np.ones(197,bool)];alt=np.r_[np.zeros(80,bool),~present if row['other_year_effect_sign']>0 else np.zeros(197,bool),~present if row['other_year_effect_sign']<0 else np.zeros(197,bool)];check(row,p,null,alt)
 for row in finite.to_dict('records'):
  mi=names.index(row['mechanism']);truth=np.where(aa.year.eq(row['zero_year']),0.,row['other_year_delta']);t=(old['annual_error'][mi]+truth)/old['annual_se'][mi,0 if row['method']=='HAC5_Holm' else 1];positive=np.array([np.all(truth[ix]>0) for ix in maps]);negative=np.array([np.all(truth[ix]<0) for ix in maps]);p=np.column_stack([np.ones((1000,80)),np.column_stack([norm.sf(t[:,ix]).max(1) for ix in maps]),np.column_stack([norm.cdf(t[:,ix]).max(1) for ix in maps])]);check(row,p,np.r_[np.zeros(80,bool),~positive,~negative],np.r_[np.zeros(80,bool),positive,negative])
 tail=pd.read_csv(o/'observed_envelope_tail_mc.csv');counters={'static':0,'annual':0,'theta':0};mapping={kind:{} for kind in counters}
 for kind,rows in [('static',d),('annual',aa),('theta',d.iloc[:80])]:
  for j,r in enumerate(rows.itertuples()):mapping[kind][(('decada' if r.year<2021 else 'recente') if kind=='annual' else r.scenario,r.papel_id,int(r.year) if kind=='annual' else None)]=int(new[kind+'_map'][j])
 for row in tail.to_dict('records'):
  g=mapping[row['kind']][(row['scenario'],row['papel_id'],int(row['year']) if row['kind']=='annual' else None)];sample=bank[names.index(row['mechanism']),:,g];t=row['t_observed'];k=int((abs(sample)>=abs(t)).sum()) if row['tail']=='two' else int((sample>=t).sum()) if row['tail']=='positive' else int((sample<=t).sum());assert k==row['exceedances'];assert row['rank_p']==(k+1)/10000;counters[row['kind']]+=1
 receipt=dict(status='passed',independent_production_imports=True,limiting_iut_families=len(limiting),finite_iut_families=len(finite),tail_count_rows=len(tail),theta_reserved_not_validated_by_boundary_diagnostic=80,tail_intervals_pointwise_not_simultaneous=True)
 (o/'validacao_diagnosticos_independente.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();validate(a.output)

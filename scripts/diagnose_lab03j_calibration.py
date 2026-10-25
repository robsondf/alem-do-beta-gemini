#!/usr/bin/env python3
"""Observed-versus-simulated bootstrap SE for all existing84G calibration cases."""
from pathlib import Path
import argparse,json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def run(output):
 root=ROOT/'results/tables';gdir=root/'lab03g_pos_parecer_v3_20261024';r=pd.read_csv(gdir/'calibration_replications.csv.gz');g=pd.read_csv(gdir/'observed_aggregate.csv.gz');f=pd.read_csv(root/'lab03f_pos_parecer_20261024/aggregate.csv.gz');cases=pd.read_csv(gdir/'calibration_cases.csv');rows=[]
 for (mechanism,family,profile,scenario,statistic),d in r.groupby(['mechanism','family','profile','scenario','statistic'],sort=True):
  actual=f if family=='F' else g;a=actual.query('profile==@profile and scenario==@scenario and statistic==@statistic and block==21');assert len(a)==1 and len(d)==1000;se=float(a.iloc[0].bootstrap_se);n=int(d.bootstrap_se.le(se).sum());z=1.959963984540054;ph=n/1000;den=1+z*z/1000;center=(ph+z*z/2000)/den;half=z*np.sqrt(ph*(1-ph)/1000+z*z/(4*1000**2))/den;q=d.bootstrap_se.quantile([.025,.5,.975]).to_numpy();c=cases.query('mechanism==@mechanism and family==@family and profile==@profile and scenario==@scenario and statistic==@statistic and event=="coverage"');assert len(c)==1
  rows.append(dict(mechanism=mechanism,family=family,profile=profile,scenario=scenario,statistic=statistic,observed_se=se,R=1000,count_at_or_below_observed=n,observed_SE_empirical_percentile=n/1000,percentile_wilson_low=center-half,percentile_wilson_high=center+half,simulated_SE_p025=q[0],simulated_SE_median=q[1],simulated_SE_p975=q[2],coverage=c.iloc[0].rate,coverage_wilson_low=c.iloc[0].wilson_low,coverage_wilson_high=c.iloc[0].wilson_high))
 d=pd.DataFrame(rows);assert len(d)==84;output.mkdir(parents=True,exist_ok=True);d.to_csv(output/'calibration_SE_diagnostic.csv',index=False)
 (output/'calibration_SE_scope.json').write_text(json.dumps(dict(cases=84,saved_replication_rows=84000,new_generators=0,mechanisms_excluded=0,formal_fit_test=False,new_design_coverage_validated=False,scope='One-dimensional descriptive SE comparison;not model rejection or observed-interval coverage certification'),indent=2)+'\n');return d
def dependence(i_output,output):
 r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True);m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index).to_numpy();inv=pd.read_csv(ROOT/'results/tables/resposta_pareceres_20261024/inventario_117.csv');ids=inv[inv.in_decade_80].papel_id;r=r.reindex(columns=ids);res=r.copy()
 for name in r:
  y=r[name].to_numpy();ok=np.isfinite(y);X=np.column_stack([np.ones(len(m)),m>0,m,m*(m>0)]);b=np.linalg.lstsq(X[ok],y[ok],rcond=None)[0];res[name]=y-X@b
 C=res.corr().to_numpy();pairs=C[np.triu_indices(len(ids),1)];record=dict(residual_pair_correlations=len(pairs),mean_pair_correlation=float(np.nanmean(pairs)),median_pair_correlation=float(np.nanmedian(pairs)),generator_fixed_common_innovation_correlation=.3,scope='Descriptive residual comparison,not latent innovation identification or formal model fit');(output/'dependence_realism.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--i-output',type=Path);a=p.parse_args();run(a.output)
 if a.i_output:dependence(a.i_output,a.output)

#!/usr/bin/env python3
"""Build manuscript tables directly from the K outputs, without editing old J."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]
from lab03k import design

def build(source,paper):
 tables=paper/'tables';figs=paper/'figures/lab02';tables.mkdir(parents=True,exist_ok=True);figs.mkdir(parents=True,exist_ok=True)
 c=pd.read_csv(source/'coefficients.csv');t=pd.read_csv(source/'joint_tests.csv');a=pd.read_csv(source/'eligibility.csv');cov=pd.read_csv(source/'covariates.csv',index_col=0)
 f=lambda x:f'{x:.4f}'.replace('.',',')
 ci=lambda r:f'{f(r.estimate)} [{f(r.ci_low)}; {f(r.ci_high)}]'
 cohorts={'original80':'Originais','union118':'União'};models={'reference':'Porte/setor','beta2015':r'+ $\beta_{2015}$','exclude_unmatched':'Sem ativos sinalizados','Amihud2015':'Amihud/porte/setor'}
 for L in [21,5,63]:
  for reference in [True,False]:
   lines=[r'\begin{tabular}{llrrr}',r'\toprule',r'Coorte/modelo & $N$ & $\widehat\lambda$ [IC 95\%] & $\widehat\gamma$ [IC 95\%] & $p^*$ conjunto\\',r'\midrule']
   # Four numeric columns plus descriptive label; N belongs in column2.
   for row in t[t.block.eq(L)&t.model.eq('reference').eq(reference)].itertuples():
    q=c.query('cohort==@row.cohort and model==@row.model and block==@L');ll=q[q.parameter.eq('liquidity')].iloc[0];gg=q[q.parameter.eq('size')].iloc[0]
    lines.append(f'{cohorts[row.cohort]}: {models[row.model]} & {row.N} & {ci(ll)} & {ci(gg)} & {f(row.p_holm_family)}'+r'\\')
   lines += [r'\bottomrule',r'\end{tabular}'];(tables/f'lab03k_{"reference" if reference else "sensitivity"}_{L}.tex').write_text('\n'.join(lines)+'\n')
 diag=[]
 for cohort in cohorts:
  ids=a.query('cohort==@cohort and model=="reference" and included').papel_id;cc=cov.loc[ids];X,_=design(cc.log_liquidity_2015.to_numpy(),cc.log_size.to_numpy(),cc.sector.to_numpy());x=X[:,1];Z=np.delete(X,1,axis=1);res=x-Z@np.linalg.lstsq(Z,x,rcond=None)[0];rho=np.corrcoef(X[:,1:3].T)[0,1]
  diag.append(dict(cohort=cohort,N=len(cc),correlation_volume_size=rho,simple_pair_VIF=1/(1-rho*rho),full_volume_VIF=np.sum((x-x.mean())**2)/sum(res*res)))
 pd.DataFrame(diag).to_csv(source/'design_diagnostics.csv',index=False)
 cal=pd.read_csv(source/'calibration_summary.csv');lines=[r'\begin{tabular}{lrrr}',r'\toprule',r'Mecanismo / $\rho$ & FWER (Wilson 95\%) & Cobertura mín. & máx.\\',r'\midrule']
 laws={'normal_iid':'Normal iid','t5_deterministic_volatility':'t5, escala determinística','t5_GARCH':'GARCH t5'}
 for (law,rho),g in cal.groupby(['generator','rho'],sort=False):
  row=g[g.target.eq('joint_Holm2_FWER')].iloc[0];cv=g[~g.target.eq('joint_Holm2_FWER')]
  pct=lambda x:f'{100*x:.1f}'.replace('.',',')
  lines.append(f'{laws[law]} / {rho:.2f} & {pct(row.rate)} [{pct(row.wilson_low)}; {pct(row.wilson_high)}] & {pct(cv.rate.min())} & {pct(cv.rate.max())}'+r'\\')
 lines += [r'\bottomrule',r'\end{tabular}'];(tables/'lab03k_calibration.tex').write_text('\n'.join(lines)+'\n')
 fig,axes=plt.subplots(1,2,figsize=(9,3.9),sharey=True)
 for ax,param,label in zip(axes,['liquidity','size'],['Coeficiente de log-volume','Coeficiente de log-capitalização']):
  for cohort,color,offset in [('original80','#0072B2',-.10),('union118','#D55E00',.10)]:
   for j,model in enumerate(['reference','beta2015','exclude_unmatched']):
    rr=c.query('cohort==@cohort and model==@model and block==21 and parameter==@param').iloc[0]
    ax.plot([rr.ci_low,rr.ci_high],[j+offset,j+offset],color=color,lw=2);ax.scatter(rr.estimate,j+offset,color=color,s=23,label=cohorts[cohort] if j==0 else None)
  ax.axvline(0,color='.6',ls='--',lw=.8);ax.set_xlabel(label);ax.grid(axis='x',alpha=.2)
 axes[0].set_yticks(range(3),['Porte e setor','+ beta de 2015','Exclusão de ativos']);axes[0].invert_yaxis();axes[1].legend(frameon=False,fontsize=9);fig.suptitle('Sensibilidades do volume: ICs básicos nominais 95%, bloco 21',fontsize=11);fig.tight_layout()
 for ext in ['pdf','png']:fig.savefig(figs/f'lab03k_controls.{ext}',dpi=180,bbox_inches='tight')
 plt.close(fig)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--paper',type=Path,required=True);a=p.parse_args();build(a.source,a.paper)

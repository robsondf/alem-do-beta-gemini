#!/usr/bin/env python3
"""Build J tables and two descriptive main figures from versioned aggregate outputs."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def run(source,paper):
 tables=paper/'tables';figs=paper/'figures/lab02';tables.mkdir(parents=True,exist_ok=True);figs.mkdir(parents=True,exist_ok=True)
 def f(v,n=3):return f'{v:.{n}f}'.replace('.',',')
 def write(name,cols,head,rows):
  (tables/name).write_text('\\begin{tabular}{'+cols+'}\n\\toprule\n'+head+r'\\'+'\n\\midrule\n'+'\n'.join(' & '.join(row)+r'\\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n')
 c=pd.read_csv(source/'controlled_regressions.csv');labels={'none':'Nenhum','beta':r'$\beta$','sector':'Setor','sector+beta':r'Setor, $\beta$','size':'Porte','size+beta':r'Porte, $\beta$','size+sector':'Porte, setor','size+sector+beta':r'Porte, setor, $\beta$'}
 for L in [21,5,63]:
  rows=[]
  for controls,label in labels.items():
   vals=[]
   for cohort in ['original80','union118']:
    q=c.query('cohort==@cohort and controls==@controls and block==@L').iloc[0];vals.extend([f(q.estimate)+r' ['+f(q.ci_low)+';'+f(q.ci_high)+']',f(q.p_holm16,4)])
   rows.append([label,*vals])
  write(f'lab03j_controls_{L}.tex','lrrrr',r' & \multicolumn{2}{c}{Originais ($N=62$)} & \multicolumn{2}{c}{União ($N=76$)}\\ Controles & $\lambda$ [IC95\%] & $p^*$ & $\lambda$ [IC95\%] & $p^*$',rows)
 a=pd.read_csv(source/'liquidity_change.csv');rows=[]
 for q in a.query('block==21').itertuples():rows.append(['Originais' if q.cohort=='original80' else 'União','Nível2015' if q.liquidity_target=='initial_level' else 'Mudança',str(q.N),f(q.estimate),f(q.bootstrap_bias),f(q.p,4),f(q.p_holm4,4)])
 write('lab03j_change.tex','llrrrrr',r'Coorte & Liquidez & $N$ & $\rho_S$ & Desloc. & $p$ & $p^*$',rows)
 e=pd.read_csv(source/'calibration_SE_diagnostic.csv');rows=[]
 mech={'gaussian_iid':'Normal iid','student_hetero':'t5 heteroc.','student_ar':'t5/AR0,3','garch_t5':'GARCH t5','variance_break_t5':'Quebra t5','ar06_t5':'t5/AR0,6'}
 for name,label in mech.items():
  q=e.query('mechanism==@name and family=="F" and scenario=="decada" and statistic=="mean"').iloc[0];rows.append([label,f(q.observed_se,5),f(q.simulated_SE_p025,4),f(q.simulated_SE_median,4),f(q.simulated_SE_p975,4),str(q.count_at_or_below_observed)+'/1000',f(100*q.coverage,1)+r'\%'])
 write('lab03j_se.tex','lrrrrrr',r'Mecanismo & EP obs. & $q_{.025}$ & Mediana & $q_{.975}$ & $k/R$ & Cob.',rows)
 s=pd.read_csv(source/'succession_sensitivity.csv');rows=[]
 for q in s.query('block==21').itertuples():rows.append(['2015' if q.cohort=='universe2015' else 'União',r'Média $\Delta$' if q.target=='early_mean' else r'$\rho_S$',str(q.N),f(q.estimate),f(q.ci_low),f(q.ci_high),f(q.p_holm4,4)])
 write('lab03j_successions.tex','llrrrrr',r'Coorte & Alvo & $N$ & Ponto & IC inf. & IC sup. & $p^*$',rows)
 ann=pd.read_csv(ROOT/'results/tables/lab03h_pos_parecer_v4_20261024/annual_overview.csv');plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
 fig,ax=plt.subplots(figsize=(7.4,2.6),layout='constrained')
 for scenario,label,color in [('decada','80 ativos fixos','#21618c'),('recente','117 ativos fixos','#c05b18')]:
  q=ann[ann.scenario.eq(scenario)];ax.plot(q.year,q.delta_median,'o-',label=label,color=color,ms=4);ax.fill_between(q.year,q.delta_q25,q.delta_q75,color=color,alpha=.12)
 ax.axhline(0,color='#555555',lw=.7);ax.set(xticks=range(2016,2026),ylabel=r'$\widehat\Delta$: mediana e IQR',xlabel='Ano');ax.legend(frameon=False,ncol=2,loc='lower left');ax.grid(axis='y',alpha=.15)
 fig.savefig(figs/'lab03j_assimetria_anual.pdf');fig.savefig(figs/'lab03j_assimetria_anual.png',dpi=180);plt.close(fig)
 d=pd.read_csv(ROOT/'results/tables/lab03i_parecer_v4_20261024/asset_liquidity.csv');d=d[d.ok_early];fig,ax=plt.subplots(figsize=(7.4,2.7),layout='constrained')
 for group,label,color,marker in [('Comuns','Ambas seleções','#21618c','o'),('Só originais','Só seleção 2025','#c05b18','s'),('Só universo 2015','Só seleção 2015','#527a3b','^')]:
  q=d[d.group.eq(group)];ax.scatter(np.log(q.adtv_2015),q.d_early,label=f'{label} (N={len(q)})',color=color,marker=marker,s=22,alpha=.8,linewidths=.2,edgecolors='white')
 ax.axhline(0,color='#555555',lw=.7);ax.set(xlabel='Log do volume financeiro médio diário em 2015 (R$)',ylabel=r'$\widehat\Delta_{2016-2020}$');ax.legend(frameon=False,ncol=3,fontsize=8,loc='upper left');ax.grid(alpha=.12)
 fig.savefig(figs/'lab03j_liquidez_inicial.pdf');fig.savefig(figs/'lab03j_liquidez_inicial.png',dpi=180);plt.close(fig)
 print('J paper:6tables,2figures')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'results/tables/lab03j_pareceres_20261024');p.add_argument('--paper',type=Path,default=ROOT/'paper');a=p.parse_args();run(a.source,a.paper)

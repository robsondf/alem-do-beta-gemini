#!/usr/bin/env python3
"""Tables and static scientific plots from completed G exports only."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build(out):
    f=pd.read_csv(out/'observed_aggregate.csv.gz');c=pd.read_csv(out/'calibration_families.csv');cases=pd.read_csv(out/'calibration_cases.csv');assert len(c)==24 and len(cases)==252, 'Wait for all six mechanisms before plotting';figdir=out/'figures';figdir.mkdir(exist_ok=True)
    def num(x,n=4):return f'{x:.{n}f}'.replace('.',',')
    lines=[r'\begin{tabular}{llrrrr}',r'\toprule',r'Alvo & Resumo & Estimativa & IC95\% marginal & $p$ & $p_{Holm4}$\\',r'\midrule']
    for r in f[f.family.eq('temporal4')&f.block.eq(21)].itertuples():lines.append(f"{'2016--2020' if r.profile=='early' else '$\\theta$: recente $-$ inicial'} & {'Média' if r.statistic=='mean' else 'Mediana'} & {num(r.estimate)} & [{num(r.ci_low)};{num(r.ci_high)}] & {num(r.p_centered)} & {num(r.p_adjusted)}\\\\")
    (out/'temporal.tex').write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    lines=[r'\begin{tabular}{llrrr}',r'\toprule',r'Especificação & Resumo & Estimativa & IC95\% marginal & $p_{Holm18}$\\',r'\midrule']
    for r in f[f.family.eq('micro18')&f.scenario.eq('decada')&f.block_choice.eq(0)].itertuples():lines.append(f"{dict(lag1='Defasada',leadlag1='Avanço/defasagem',weekly='Semanal')[r.profile]} & {'Média' if r.statistic=='mean' else 'Mediana'} & {num(r.estimate)} & [{num(r.ci_low)};{num(r.ci_high)}] & {num(r.p_adjusted)}\\\\")
    (out/'microstructure.tex').write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    mechanisms=list(c.mechanism.unique());labels=['Normal iid','t5 heteroc.','t5 AR0,3','GARCH t5','Quebra t5','t5 AR0,6']
    lines=[r'\begin{tabular}{lrrrr}',r'\toprule',r'Mecanismo & FWER10 (\%) & Wilson95\% & FWER4 (\%) & Wilson95\%\\',r'\midrule']
    for mech,label in zip(mechanisms,labels):
        a=c[(c.mechanism==mech)&c.adjusted&c.family.eq('F')].iloc[0];b=c[(c.mechanism==mech)&c.adjusted&c.family.eq('temporal')].iloc[0]
        lines.append(f'{label} & {num(100*a.rate,1)} & [{num(100*a.wilson_low,2)};{num(100*a.wilson_high,2)}] & {num(100*b.rate,1)} & [{num(100*b.wilson_low,2)};{num(100*b.wilson_high,2)}]\\\\')
    (out/'calibration.tex').write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,4.0),sharex=True)
    for ax,profile,title in zip(axes,['early','theta'],['Assimetria em 2016–2020','Mudança: 2021–2025 menos 2016–2020']):
        for j,stat in enumerate(['mean','median']):
            for shift,L,color in [(-.15,5,'#5d9fb4'),(0,21,'#193c66'),(.15,63,'#d88f32')]:
                r=f[(f.profile==profile)&(f.statistic==stat)&f.block.eq(L)].iloc[0];ax.errorbar(r.estimate,j+shift,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt='o',color=color,capsize=3,label=f'{L} sessões' if j==0 else None)
        ax.axvline(0,color='0.5',lw=1);ax.set_yticks([0,1],['Média','Mediana']);ax.set_title(title,fontsize=10);ax.set_xlabel('Contraste de inclinações');ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    handles,leglabels=axes[0].get_legend_handles_labels();fig.legend(handles,leglabels,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,-.02),fontsize=9);fig.suptitle('80 ativos fixos · ICs básicos nominais de 95% · 4.999 sorteios',fontsize=11);fig.tight_layout(rect=(0,.08,1,1))
    for ext in ['pdf','png']:fig.savefig(figdir/f'lab03g_temporal.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,family,title in zip(axes,['F','temporal'],['Família agregada original: 10 testes','Mudança temporal: 4 testes']):
        a=c[c.family.eq(family)&c.adjusted].set_index('mechanism').loc[mechanisms];y=np.arange(6);ax.errorbar(100*a.rate,y,xerr=[100*(a.rate-a.wilson_low),100*(a.wilson_high-a.rate)],fmt='o',color='#193c66',capsize=3)
        ax.axvline(5,color='#a84a38',ls='--');ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('FWER ajustada (%) e Wilson95%');ax.set_title(title,fontsize=10);ax.grid(axis='x',alpha=.2)
    fig.suptitle('Nulidade global · 1.000 réplicas por mecanismo · bloco 21',fontsize=11);fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(figdir/f'lab03g_calibracao.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    result={'FWER10_range':list(c[c.family.eq('F')&c.adjusted].rate.agg(['min','max'])),'FWER4_range':list(c[c.family.eq('temporal')&c.adjusted].rate.agg(['min','max'])),'coverage_range_all_84_cases':list(cases[cases.event.eq('coverage')].rate.agg(['min','max']))}
    (out/'plot_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output)

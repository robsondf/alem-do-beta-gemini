#!/usr/bin/env python3
"""Publication figures/tables from the complete post-review exports."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def produce(output):
    figures=output/'figures';figures.mkdir(exist_ok=True)
    a=pd.read_csv(output/'aggregate.csv.gz');f=pd.read_csv(output/'individual.csv.gz')
    labels={'decada':'80 ativos · 2016–2025','decada_periodo_comum':'80 ativos · 2021–2025','recente':'117 ativos · 2021–2025'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
    fig,axes=plt.subplots(1,2,figsize=(10,3.6),sharex=True)
    for ax,stat,title in zip(axes,['mean','median'],['Média por ativo','Mediana entre ativos']):
        for j,s in enumerate(labels):
            for k,L in enumerate([5,21,63]):
                r=a[(a.profile=='daily')&(a.scenario==s)&(a.statistic==stat)&(a.block==L)].iloc[0]
                color=['#8295a1','#176b87','#bb6239'][k];y=j+(k-1)*.16
                ax.plot([r.ci_low,r.ci_high],[y,y],color=color,lw=1.7)
                ax.scatter(r.estimate,y,s=24,color=color,label=f'Bloco {L}' if j==0 else None,zorder=3)
        ax.axvline(0,c='.5',ls='--',lw=1);ax.set_yticks(range(3),labels.values());ax.invert_yaxis()
        ax.set_title(title);ax.set_xlabel(r'Contraste $\Delta=\beta^+-\beta^-$')
    handles,legend_labels=axes[1].get_legend_handles_labels()
    fig.legend(handles,legend_labels,loc='upper center',bbox_to_anchor=(.5,1.08),frameon=False,ncol=3,fontsize=9)
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(figures/f'lab03f_agregado.{ext}',dpi=180)
    plt.close(fig)
    profiles=['daily','exclude_2020_03','exclude_2020_H1','continuous','lag1','leadlag1','weekly']
    names=['Diário integral','Sem março/2020','Sem 2020-S1','Contínuo (g=0)','Atual e defasagem 1','Avanço e defasagem 1','Semanal']
    fig,axes=plt.subplots(1,2,figsize=(10,4.7),sharey=True)
    for ax,ticker in zip(axes,['VULC3.SA','BBDC4.SA']):
        for j,profile in enumerate(profiles):
            r=f[(f.profile==profile)&(f.scenario=='decada')&(f.ticker==ticker)].iloc[0]
            ax.plot([r.delta_ci_low,r.delta_ci_high],[j,j],c='#176b87',lw=1.8)
            ax.scatter(r.delta,j,c='#176b87',s=32)
        ax.axvline(0,c='.5',ls='--',lw=1);ax.set_title(ticker.removesuffix('.SA'))
        ax.set_yticks(range(7),names);ax.set_xlabel('Contraste estimado e IC marginal HAC5')
    axes[0].invert_yaxis()
    fig.tight_layout()
    for ext in ['pdf','png']:fig.savefig(figures/f'lab03f_criticos.{ext}',dpi=180)
    plt.close(fig)
    lines=[r'\begin{tabular}{llrrrl}',r'\toprule',r'Recorte & Estatística & Estimativa & $p_{10}$ & $p_{30}$ & IC marginal\\',r'\midrule']
    for profile,s,label in [('daily','decada','80 década'),('daily','decada_periodo_comum','80 comuns'),('daily','recente','117 recentes'),('exclude_2020_03','decada','80 sem mar./20'),('exclude_2020_H1','decada','80 sem 2020-S1')]:
        for stat,lab in [('mean','Média'),('median','Mediana')]:
            r=a[(a.profile==profile)&(a.scenario==s)&(a.statistic==stat)&(a.block==21)].iloc[0]
            lines.append(f'{label} & {lab} & {r.estimate:.3f} & {r.p_holm10:.4f} & {r.p_holm30:.4f} & [{r.ci_low:.3f}; {r.ci_high:.3f}]'+r'\\')
    lines.extend([r'\bottomrule',r'\end{tabular}']);(output/'aggregate.tex').write_text('\n'.join(lines)+'\n')
    summary=pd.read_csv(output/'profile_summary.csv')
    lines=[r'\begin{tabular}{lrrrrrr}',r'\toprule',r'& \multicolumn{3}{c}{80 década} & \multicolumn{3}{c}{117 recentes}\\',r'Especificação & Média & Mediana & Rej. & Média & Mediana & Rej.\\',r'\midrule']
    for p,label in zip(profiles,['Diário integral','Sem março/2020','Sem 2020-S1','Contínuo','Defasagem 1','Avanço/defasagem 1','Semanal']):
        d=summary[(summary.profile==p)&(summary.scenario=='decada')].iloc[0]
        r=summary[(summary.profile==p)&(summary.scenario=='recente')].iloc[0]
        lines.append(f'{label} & {d.mean_delta:.3f} & {d.median_delta:.3f} & {int(d.holm197)} & {r.mean_delta:.3f} & {r.median_delta:.3f} & {int(r.holm197)}'+r'\\')
    lines.extend([r'\bottomrule',r'\end{tabular}']);(output/'profiles.tex').write_text('\n'.join(lines)+'\n')
    g=pd.read_csv(output/'existing_sensitivity_holm.csv.gz')
    lines=[r'\begin{tabular}{llrrl}',r'\toprule',r'Ativo & Diagnóstico & $\widehat\Delta$ & $p_{Holm197}$ & IC marginal\\',r'\midrule']
    for ticker in ['VULC3.SA','BBDC4.SA']:
        for policy,label in [('unmasked','Completa'),('remove1_largest_absolute_observation_influence','Retira 1'),('remove5_largest_absolute_observation_influence','Retira 5')]:
            r=g[(g.ticker==ticker)&(g.scenario=='decada')&(g.reference=='referencia_n')&(g.diagnostic==policy)].iloc[0]
            lines.append(f'{ticker.removesuffix(".SA")} & {label} & {r.delta:.3f} & {r.p_holm197:.4f} & [{r.ci_low:.3f}; {r.ci_high:.3f}]'+r'\\')
    lines.extend([r'\bottomrule',r'\end{tabular}']);(output/'critical.tex').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);produce(p.parse_args().output)

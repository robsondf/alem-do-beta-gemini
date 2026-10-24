#!/usr/bin/env python3
"""Prespecified scientific plots; observed return figures are unaffected."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LABELS={'gaussian_iid':'Normal independente','student_hetero':'t5 + heterocedasticidade','student_ar':'t5 + heterocedasticidade + AR(0,3)'}
COLORS={'HAC0':'#999999','HAC5':'#15648b','HAC20':'#c26432'}
def plot(output):
    f=pd.read_csv(output/'family.csv'); p=pd.read_csv(output/'panel_summary.csv')
    folder=output/'figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight','pdf.fonttype':42})
    def save(fig,name):
        fig.savefig(folder/(name+'.png'),dpi=170);fig.savefig(folder/(name+'.pdf'));plt.close(fig)
    fig,ax=plt.subplots(1,3,figsize=(11,3.6),layout='constrained')
    for ai,scenario in enumerate(['decada','recente']):
        q=p[p.pattern.eq('dense_+0.00') & p.scenario.eq(scenario)]
        for off,(method,color) in enumerate(COLORS.items()):
            a=q[q.method.eq(method)].set_index('mechanism').loc[list(LABELS)]
            ax[ai].errorbar(np.arange(3)+(off-1)*.13,100*a.coverage,yerr=196*a.coverage_mcse,fmt='o',color=color,label=method,capsize=3)
        ax[ai].axhline(95,color='black',ls=':',lw=1);ax[ai].set_title('Cobertura: '+('80, 2016–2025' if ai==0 else '117, 2021–2025'));ax[ai].set_ylabel('Cobertura marginal média (%)')
    q=f[f.pattern.eq('dense_+0.00')]
    for off,(method,color) in enumerate(COLORS.items()):
        a=q[q.method.eq(method)].set_index('mechanism').loc[list(LABELS)]
        ax[2].errorbar(np.arange(3)+(off-1)*.13,100*a.fwer_holm,yerr=np.array([100*(a.fwer_holm-a.fwer_holm_mc_low),100*(a.fwer_holm_mc_high-a.fwer_holm)]),fmt='o',color=color,label=method,capsize=3)
    ax[2].axhline(5,color='black',ls=':',lw=1);ax[2].set_ylabel('FWER Holm197 (%)');ax[2].set_title('Pelo menos uma falsa rejeição');ax[2].set_ylim(bottom=0)
    for a in ax:a.set_xticks(range(3),['Normal','t5 + h','t5 + h + AR']);a.grid(axis='y',alpha=.2)
    ax[0].set_ylim(83,96);ax[1].set_ylim(83,96)
    ax[0].legend(frameon=False);save(fig,'lab03c_calibracao')
    fig,ax=plt.subplots(3,2,figsize=(10,9),sharex=True,sharey=True,layout='constrained')
    for mi,mechanism in enumerate(LABELS):
        for si,scenario in enumerate(['decada','recente']):
            a=ax[mi,si];q=p[p.mechanism.eq(mechanism)&p.method.eq('HAC5')&p.scenario.eq(scenario)&p.pattern.str.startswith('dense_')].copy();q['delta']=q.pattern.str.removeprefix('dense_').astype(float);q=q.sort_values('delta');xx=q.delta.to_numpy()
            for name,label,color in [('raw','Sem ajuste','#b66724'),('holm','Holm197','#15648b')]:
                yy=np.where(xx==0,q['type1_'+name],q['power_'+name]);mc=np.where(xx==0,q['type1_'+name+'_mcse'],q['power_'+name+'_mcse'])
                a.plot(xx,100*yy,'o-',label=label,color=color);a.fill_between(xx,100*np.maximum(0,yy-1.96*mc),100*np.minimum(1,yy+1.96*mc),color=color,alpha=.15)
            a.axvline(0,color='black',ls=':',lw=1);a.set_ylim(0,100);a.grid(alpha=.2);a.set_title(LABELS[mechanism]+(' | 80 década' if si==0 else ' | 117 recentes'))
            if si==0:a.set_ylabel('Taxa de rejeição (%)')
            if mi==2:a.set_xlabel('Assimetria verdadeira δ (beta)')
    ax[0,0].legend(frameon=False);save(fig,'lab03c_rejeicao')
    fig,ax=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    q=f[f.method.eq('HAC5') & (f.pattern.str.startswith('sparse_')|f.pattern.eq('dense_+0.00'))].copy()
    q['label']=[LABELS[m]+' | '+('δ = 0' if p=='dense_+0.00' else p.replace('sparse_','12 ativos δ = ')) for m,p in zip(q.mechanism,q.pattern)]
    yy=np.arange(len(q))
    ax[0].errorbar(100*q.fwer_holm,yy,xerr=np.array([100*(q.fwer_holm-q.fwer_holm_mc_low),100*(q.fwer_holm_mc_high-q.fwer_holm)]),fmt='o',color=COLORS['HAC5'],capsize=3);ax[0].set_yticks(yy,q.label,fontsize=8);ax[0].axvline(5,color='black',ls=':');ax[0].set_xlabel('FWER Holm197 (%)');ax[0].set_xlim(left=0)
    a=q[q.nonnull_cases>0];ax[1].errorbar(100*a.power_holm,a.index.map(lambda v:list(q.index).index(v)),xerr=196*a.power_holm_mcse,fmt='o',color=COLORS['HAC5'],capsize=3);ax[1].set_yticks(yy,[]);ax[1].set_xlabel('Poder médio nos não nulos (%)');ax[1].set_xlim(0,100)
    for a in ax:a.invert_yaxis();a.grid(axis='x',alpha=.2)
    save(fig,'lab03c_esparso')
    # Single compact primary-method table, all mechanisms retained.
    lines=[r'\begin{tabular}{lrrr}',r'\toprule',r'Mecanismo & Cob. 80 (\%) & Cob. 117 (\%) & FWER (\%)\\',r'\midrule']
    for m,label in LABELS.items():
        sub=p[p.mechanism.eq(m)&p.method.eq('HAC5')&p.pattern.eq('dense_+0.00')].set_index('scenario')
        row=f[f.mechanism.eq(m)&f.method.eq('HAC5')&f.pattern.eq('dense_+0.00')].iloc[0]
        short={'gaussian_iid':'Normal','student_hetero':'t5 + h','student_ar':'t5 + h + AR'}[m]
        lines.append(short+' & '+f'{100*sub.loc["decada","coverage"]:.2f} & {100*sub.loc["recente","coverage"]:.2f} & {100*row.fwer_holm:.2f}'.replace('.',',')+r'\\')
    lines += [r'\bottomrule',r'\end{tabular}']
    (output/'lab03c_resumo.tex').write_text('\n'.join(lines)+'\n')
    print('3 PNGs, 3 PDFs and primary calibration table saved')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();plot(a.output)

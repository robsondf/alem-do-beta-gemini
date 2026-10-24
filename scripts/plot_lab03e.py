#!/usr/bin/env python3
"""Scientific summaries; all mechanisms/lengths retained, no preferred winner."""
import argparse,io,json
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import fitz
LABELS={'gaussian_iid':'Normal iid','student_hetero':'t5 hetero','student_ar':'t5 AR .3','garch_t5':'t5 GARCH','variance_break_t5':'t5 quebra','ar06_t5':'t5 AR .6','gaussian_garch':'Normal GARCH','gaussian_ar03':'Normal AR .3'}
COLORS=['#255c99','#a14720','#3b7862','#754a9a','#ae8a22','#b03c65']
def save(fig,folder,name):
    fig.tight_layout();folder.mkdir(exist_ok=True)
    for ext in ['png','pdf']:
        b=io.BytesIO();fig.savefig(b,format=ext,dpi=160,bbox_inches='tight');raw=b.getvalue()
        if ext=='png':im=Image.open(io.BytesIO(raw));im.load()
        else:
            doc=fitz.open(stream=raw,filetype='pdf');assert len(doc)==1;doc[0].get_pixmap();doc.close()
        p=folder/(name+'.'+ext);stage=p.with_suffix('.'+ext+'.stage');stage.write_bytes(raw);stage.replace(p)
    plt.close(fig)
def run(folder):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.17,'pdf.fonttype':42});figures=folder/'figures';f=pd.read_csv(folder/'inference_family.csv');power=pd.read_csv(folder/'inference_power.csv');obs=pd.read_csv(folder/'observed_static_precision.csv');pred=pd.read_csv(folder/'predictive_family.csv');eco=pd.read_csv(folder/'economic_ledger.csv')
    names=list(LABELS)[:6];fig,axes=plt.subplots(1,2,figsize=(10,3.9))
    for ai,kind in enumerate(['static','temporal']):
        q=f[(f.kind==kind)&f.pattern.eq('dense_+0.00' if kind=='static' else 'zero')].set_index('mechanism').loc[names];v=100*q.fwer_adjusted.to_numpy();lo=100*q.fwer_adjusted_mc_low.to_numpy();hi=100*q.fwer_adjusted_mc_high.to_numpy();axes[ai].errorbar(np.arange(6),v,yerr=[v-lo,hi-v],fmt='o',color='#255c99',capsize=3);axes[ai].axhline(5,color='#a14720',ls='--',lw=1);axes[ai].axvline(2.5,color='.5',ls=':',lw=1);axes[ai].set(xticks=np.arange(6),xticklabels=[LABELS[n] for n in names],ylabel='FWER (%)',title=('Estática: 197 hipóteses' if ai==0 else 'Temporal: 474 hipóteses'),ylim=(0,7));axes[ai].tick_params(axis='x',rotation=35)
    save(fig,figures,'lab03e_inferencia')
    fig,axes=plt.subplots(1,3,figsize=(12,3.8))
    for mi,name in enumerate(names):
        q=power[(power.kind=='theta')&power.mechanism.eq(name)&power.pattern.str.startswith('flip')];axes[0].plot(q.true_effect*2,100*q.rejection,'o-',label=LABELS[name],color=COLORS[mi]);q=power[power.kind.isin(['positive_IUT','negative_IUT'])&power.mechanism.eq(name)&power.pattern.str.startswith('constant')&power.is_power];q=q.assign(effect=abs(q.true_effect)).groupby('effect',as_index=False).rejection.mean();axes[1].plot(q.effect,100*q.rejection,'o-',color=COLORS[mi])
    for ax in axes[:2]:ax.axhline(80,color='.4',ls='--',lw=1);ax.set(ylim=(-2,103),ylabel='Potência média (%)')
    axes[0].set(xlabel='Mudança verdadeira θ = 2δ',title='Inversão entre metades');axes[1].set(xlabel='|δ| constante por ano',title='IUT: média dos dois sinais');axes[0].legend(fontsize=7,loc='lower right')
    for i,ticker in enumerate(['VULC3.SA','BBDC4.SA']):
        q=obs[(obs.ticker==ticker)&obs.scenario.eq('decada')].set_index('bank').loc[['pooled','stream1','stream2','stream3']];axes[2].plot(np.arange(4),q.p_holm_197,'o-',label=ticker.replace('.SA',''),color=COLORS[i])
    axes[2].axhline(.05,color='.4',ls='--');axes[2].set(xticks=np.arange(4),xticklabels=['Conjunto','Fluxo 1','Fluxo 2','Fluxo 3'],ylabel='p ajustado Holm197',title='Precisão Monte Carlo');axes[2].tick_params(axis='x',rotation=30);axes[2].legend(fontsize=8)
    save(fig,figures,'lab03e_potencia_precisao')
    fig,axes=plt.subplots(1,2,figsize=(8,4.3));sn=[(n,delta) for n in ['gaussian_iid','gaussian_garch','gaussian_ar03'] for delta in [0.,.25]]
    for j,(name,delta) in enumerate(sn):
        for ai,(method,col,title) in enumerate([('marginal_percentile','mean_coverage','IC marginal: cobertura média'),('simultaneous_max_deviation','joint_coverage','IC conjunto: cobertura dos 394')]):
            q=pred[pred.mechanism.eq(name)&pred.delta.eq(delta)&pred.method.eq(method)].sort_values('block_length');axes[ai].plot(q.block_length,100*q[col],'o-',color=COLORS[j],label=LABELS[name]+f'; δ={delta:g}');axes[ai].set(xlabel='Comprimento do bloco (sessões)',ylabel='Frequência (%)',title=title,xticks=[21,42,63])
    for ax in axes[:2]:ax.axhline(95,color='.4',ls='--',lw=1)
    handles,labels=axes[1].get_legend_handles_labels();fig.legend(handles,labels,fontsize=9.2,loc='lower center',bbox_to_anchor=(.5,-.23),ncol=2);save(fig,figures,'lab03e_cobertura_previsao')
    q=pd.read_csv(folder/'observed_predictive_intervals.csv');fig,axes=plt.subplots(2,2,figsize=(11,7))
    for ai,(W,s) in enumerate([(252,'decada'),(252,'recente'),(504,'decada'),(504,'recente')]):
        ax=axes.flat[ai];a=q[q.window.eq(W)&q.scenario.eq(s)&q.block_length.eq(21)].sort_values('loss_gain');x=np.arange(len(a));ax.vlines(x,a.simultaneous_low*1e6,a.simultaneous_high*1e6,color='#c6cfdb',lw=.8);ax.vlines(x,a.marginal_low*1e6,a.marginal_high*1e6,color='#255c99',lw=.9);ax.scatter(x,a.loss_gain*1e6,s=5,c='#a14720');ax.axhline(0,color='.3',lw=.7);ax.set(title=f'{s}, W={W}; L=21',xlabel='Ativos ordenados pelo ganho observado',ylabel='Ganho de MSE × 10⁶')
    save(fig,figures,'lab03e_intervalos_observados')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,s in zip(axes,['decada','recente']):
        a=eco[eco.scenario.eq(s)];ax.scatter(a.delta,a.max_absolute_diagnostic_shift,s=16,color='#255c99',alpha=.7);ax.set(xlabel='Δ na referência observada',ylabel='Maior |mudança em Δ| nos diagnósticos',title=s)
        for _,r in a.nlargest(3,'max_absolute_diagnostic_shift').iterrows():ax.annotate(r.ticker.replace('.SA',''),(r.delta,r.max_absolute_diagnostic_shift),fontsize=7,xytext=(3,3),textcoords='offset points')
    save(fig,figures,'lab03e_impacto_economico')
    grid=[]
    for (kind,mechanism,scenario),g in power[power.is_power].groupby(['kind','mechanism','scenario']):
        for family,gg in g.groupby(g.pattern.str.split('_').str[0]):
            q=gg[gg.rejection>=.8];effect=float(abs(q.true_effect).min()) if len(q) else np.nan;grid.append(dict(kind=kind,mechanism=mechanism,scenario=scenario,pattern_family=family,first_absolute_grid_effect_reaching_80pct=effect,theta_change_at_first_grid=2*effect if family=='flip' and kind=='theta' else np.nan,not_general_MDE=True))
    pd.DataFrame(grid).to_csv(folder/'power_grid_summary.csv',index=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);run(p.parse_args().output)

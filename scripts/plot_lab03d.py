#!/usr/bin/env python3
"""Scientific comparisons, complete predictive horizons and all-asset uncertainty."""
import argparse,io
from PIL import Image
import fitz
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

MECHANISMS=['gaussian_iid','student_hetero','student_ar']
LABELS=['Normal','t5 + h','t5 + h + AR']
METHODS=['HAC5_Holm','HC3_HAC5_Holm','HC3_HAC5_maxT','MC_envelope_Holm']
COLORS=['#777777','#c06b28','#8256a4','#126d8a']
NAMES=['HAC5 + Holm','HC3-HAC5 + Holm','HC3-HAC5 + maxT','Envelope MC + Holm']
SCENARIOS=['decada','decada_periodo_comum','recente']
SLABELS=['80 | 2019–2025','80 comuns | 2024–2025','117 | 2024–2025']

def plot(output):
    folder=output/'figures';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight','pdf.fonttype':42})
    def save(fig,name):
        for suffix in ['png','pdf']:
            buffer=io.BytesIO();fig.savefig(buffer,format=suffix,dpi=165);data=buffer.getvalue()
            if suffix=='png':Image.open(io.BytesIO(data)).load()
            else:assert fitz.open(stream=data,filetype='pdf').page_count==1
            target=folder/(name+'.'+suffix);temporary=target.with_suffix('.stage');temporary.write_bytes(data);temporary.replace(target)
        plt.close(fig)
    sf=pd.concat([pd.read_csv(output/'static_family.csv'),pd.read_csv(output/'envelope_family.csv')],ignore_index=True)
    panels=pd.concat([pd.read_csv(output/'static_panels.csv'),pd.read_csv(output/'envelope_panels.csv')],ignore_index=True)
    fig,ax=plt.subplots(2,2,figsize=(9,6.4),layout='constrained')
    for i,scenario in enumerate(['decada','recente']):
        for mi in [0,1,3]:
            method=METHODS[mi];q=panels[panels.method.eq(method)&panels.pattern.eq('dense_+0.00')&panels.scenario.eq(scenario)].set_index('mechanism').loc[MECHANISMS]
            ax[0,i].errorbar(np.arange(3)+(mi-1)*.1,100*q.coverage,yerr=196*q.coverage_mcse,fmt='o',color=COLORS[mi],capsize=3,label=NAMES[mi])
        ax[0,i].axhline(95,color='black',ls=':',lw=1);ax[0,i].set_title('Cobertura marginal: '+('80 década' if i==0 else '117 recentes'));ax[0,i].set_ylim(85,100.5);ax[0,i].set_ylabel('%')
    for mi,method in enumerate(METHODS):
        q=sf[sf.method.eq(method)&sf.pattern.eq('dense_+0.00')].set_index('mechanism').loc[MECHANISMS]
        ax[1,0].errorbar(np.arange(3)+(mi-1.5)*.1,100*q.fwer_adjusted,yerr=np.maximum(0,np.vstack([100*(q.fwer_adjusted-q.fwer_adjusted_mc_low),100*(q.fwer_adjusted_mc_high-q.fwer_adjusted)])),fmt='o',capsize=3,color=COLORS[mi],label=NAMES[mi])
    ax[1,0].axhline(5,color='black',ls=':');ax[1,0].set_title('FWER estática | nulidade global');ax[1,0].set_ylabel('%');ax[1,0].set_ylim(bottom=0)
    tf=pd.concat([pd.read_csv(output/'temporal_family.csv'),pd.read_csv(output/'envelope_temporal_family.csv')],ignore_index=True)
    for mi in [0,1,3]:
        q=tf[tf.method.eq(METHODS[mi])&tf.pattern.eq('zero')].set_index('mechanism').loc[MECHANISMS]
        ax[1,1].errorbar(np.arange(3)+(mi-1)*.1,100*q.fwer_adjusted,yerr=np.maximum(0,np.vstack([100*(q.fwer_adjusted-q.fwer_adjusted_mc_low),100*(q.fwer_adjusted_mc_high-q.fwer_adjusted)])),fmt='o',capsize=3,color=COLORS[mi])
    ax[1,1].axhline(5,color='black',ls=':');ax[1,1].set_title('FWER temporal474 | nulidade global');ax[1,1].set_ylabel('%');ax[1,1].set_ylim(bottom=0)
    for a in ax.ravel():a.set_xticks(range(3),LABELS);a.grid(axis='y',alpha=.2)
    handles,labels=ax[1,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False,fontsize=9)
    save(fig,'lab03d_calibracao')
    metrics=pd.read_csv(output/'prediction_metrics.csv');gains=pd.read_csv(output/'prediction_gains.csv');intervals=pd.read_csv(output/'prediction_intervals.csv')
    fig,ax=plt.subplots(2,3,figsize=(10,6),layout='constrained')
    for si,(scenario,label) in enumerate(zip(SCENARIOS,SLABELS)):
        for model,color,name in [('traditional_market','#b87432','Tradicional'),('conditional_market','#126d8a','Condicional')]:
            q=metrics[metrics.configuration.eq('N252')&metrics.scenario.eq(scenario)&~metrics.period.eq('full')&metrics.model.eq(model)&metrics.regime.eq('all')].copy();q['year']=q.period.astype(int);gr=q.groupby('year').r2_vs_mean;median=gr.median();lo=gr.quantile(.25);hi=gr.quantile(.75)
            ax[0,si].plot(median.index,100*median,'o-',color=color,label=name);ax[0,si].fill_between(median.index,100*lo,100*hi,color=color,alpha=.14)
        q=gains[gains.configuration.eq('N252')&gains.scenario.eq(scenario)&~gains.period.eq('full')&gains.regime.eq('all')].copy();q['year']=q.period.astype(int);gr=q.groupby('year').relative_mse_gain;median=gr.median();ax[1,si].plot(median.index,100*median,'o-',color='#126d8a');ax[1,si].fill_between(median.index,100*gr.quantile(.25),100*gr.quantile(.75),color='#126d8a',alpha=.15)
        for a in ax[:,si]:a.axhline(0,color='black',ls=':',lw=1);a.grid(alpha=.2);a.set_xticks(median.index,median.index,rotation=35)
        ax[0,si].set_title(label);ax[0,si].set_ylabel('R² fora da amostra vs média (%)' if si==0 else '')
        ax[1,si].set_ylabel('Redução relativa de MSE (%)' if si==0 else '')
    for row in range(2):
        bounds=np.array([a.get_ylim() for a in ax[row]]);limits=(bounds[:,0].min(),bounds[:,1].max())
        for a in ax[row]:a.set_ylim(*limits)
    ax[0,0].legend(frameon=False,fontsize=9);save(fig,'lab03d_previsao_anual')
    fig,ax=plt.subplots(figsize=(8.4,5),layout='constrained');configs=['N252','N504','gap_guard252','LightQ4252','jcp_duas_celulas_documentadas252','jcp_condicional252','jcp_rendimento_caixa_baixo252','jcp_rendimento_caixa_alto252'];labels=['N,252 (primário)','N,504','Proteção causal de lacunas','Light: exclusão2024Q4','JCP duas células','JCP condicional','JCP + caixa baixo','JCP + caixa alto']
    q=gains[gains.period.eq('full')&gains.regime.eq('all')];table=q.groupby(['configuration','scenario']).relative_mse_gain.median().unstack().loc[configs,SCENARIOS]*100
    bound=max(abs(table.to_numpy()).max(),1e-6);im=ax.imshow(table.to_numpy(),cmap='RdBu',vmin=-bound,vmax=bound,aspect='auto');ax.set_yticks(range(8),labels);ax.set_xticks(range(3),SLABELS,fontsize=9)
    for i in range(8):
        for j in range(3):ax.text(j,i,f'{table.iloc[i,j]:+.5f}%',ha='center',va='center',fontsize=10,color='white' if abs(table.iloc[i,j])>.6*bound else 'black')
    fig.colorbar(im,ax=ax,label='Mediana da redução relativa de MSE (%)');save(fig,'lab03d_sensibilidades_previsao')
    fig,axes=plt.subplots(1,3,figsize=(12,18),layout='constrained')
    for si,scenario in enumerate(SCENARIOS):
        q=intervals[intervals.configuration.eq('N252')&intervals.scenario.eq(scenario)&intervals.block_length.eq(21)].merge(gains[gains.configuration.eq('N252')&gains.scenario.eq(scenario)&gains.period.eq('full')&gains.regime.eq('all')][['papel_id','ticker']],on='papel_id',validate='one_to_one').sort_values('ticker');yy=np.arange(len(q));axes[si].hlines(yy,q.ci_low*1e6,q.ci_high*1e6,color='#8a9ba4',lw=.65);axes[si].scatter(q.loss_gain*1e6,yy,s=7,color='#126d8a');axes[si].axvline(0,color='black',ls=':',lw=.8);axes[si].set_yticks(yy,q.ticker.str.removesuffix('.SA'),fontsize=6.2);axes[si].invert_yaxis();axes[si].set_title(SLABELS[si]);axes[si].set_xlabel('Redução de MSE (×10⁻⁶)');axes[si].grid(axis='x',alpha=.2)
    save(fig,'lab03d_intervalos_ativos')
    if (output/'temporal_iut_limit_family.csv').exists():
        q=pd.read_csv(output/'temporal_iut_limit_family.csv');fig,axes=plt.subplots(1,2,figsize=(9,4.5),sharey=True,layout='constrained')
        for yi,year in enumerate([2020,2024]):
            for mi in [0,1,3]:
                sub=q[q.zero_year.eq(year)&q.other_year_effect_sign.eq(1)&q.method.eq(METHODS[mi])].set_index('mechanism').loc[MECHANISMS]
                axes[yi].errorbar(np.arange(3)+(mi-1)*.1,100*sub.fwer_adjusted,yerr=np.maximum(0,np.vstack([100*(sub.fwer_adjusted-sub.fwer_adjusted_mc_low),100*(sub.fwer_adjusted_mc_high-sub.fwer_adjusted)])),fmt='o',capsize=3,color=COLORS[mi],label=NAMES[mi])
            axes[yi].axhline(5,color='black',ls=':');axes[yi].set_xticks(range(3),LABELS);axes[yi].set_title('Ano nulo: '+str(year));axes[yi].grid(axis='y',alpha=.2)
        axes[0].set_ylabel('FWER entre IUTs nulos (%)');axes[0].set_ylim(bottom=0);axes[0].legend(frameon=False,fontsize=8);save(fig,'lab03d_iut_limite')
    # Machine-derived compact article tables, with no selected mechanism omitted.
    def latex_num(v,digits=2):return f'{v:.{digits}f}'.replace('.',',')
    lines=[r'\begin{tabular}{lrrrr}',r'\toprule',r'Mecanismo & HAC5 & HC3 & maxT & Envelope MC\\',r'\midrule']
    for mechanism,label in zip(MECHANISMS,LABELS):
        row=sf[sf.mechanism.eq(mechanism)&sf.pattern.eq('dense_+0.00')].set_index('method');lines.append(label+' & '+' & '.join(latex_num(100*row.loc[m,'fwer_adjusted']) for m in METHODS)+r'\\')
    lines += [r'\bottomrule',r'\end{tabular}'];(output/'lab03d_inferencia.tex').write_text('\n'.join(lines)+'\n')
    lines=[r'\begin{tabular}{lrrr}',r'\toprule',r'Recorte & Ativos & Ganho MSE (\%) & $R^2_{OS}$ vs zero (\%)\\',r'\midrule']
    for scenario,label in zip(SCENARIOS,['80, 2019--2025','80 comuns, 2024--2025','117, 2024--2025']):
        g=gains[gains.configuration.eq('N252')&gains.scenario.eq(scenario)&gains.period.eq('full')&gains.regime.eq('all')];m=metrics[metrics.configuration.eq('N252')&metrics.scenario.eq(scenario)&metrics.period.eq('full')&metrics.regime.eq('all')&metrics.model.eq('conditional_market')];lines.append(label+' & '+str(len(g))+' & '+latex_num(100*g.relative_mse_gain.median(),5)+' & '+latex_num(100*m.r2_vs_zero.median(),4)+r'\\')
    lines += [r'\bottomrule',r'\end{tabular}'];(output/'lab03d_previsao.tex').write_text('\n'.join(lines)+'\n')
    print('Scientific figures and2 article tables saved')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();plot(a.output)

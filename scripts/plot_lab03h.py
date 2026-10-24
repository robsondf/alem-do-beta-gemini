#!/usr/bin/env python3
"""Publication tables/figures from completed H outputs; no re-estimation."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def build(out):
    H=pd.read_csv(out/'crisis_aggregate.csv.gz');G=pd.read_csv(ROOT/'results/tables/lab03g_pos_parecer_v3_20261024/observed_aggregate.csv.gz');F=pd.read_csv(ROOT/'results/tables/lab03f_pos_parecer_20261024/aggregate.csv.gz');figs=out/'figures';figs.mkdir(exist_ok=True)
    def n(x,k=4):return f'{x:.{k}f}'.replace('.',',')
    labels={'daily':'Integral','exclude_2020_03':'Sem março/2020','exclude_2020_H1':'Sem 2020-S1'}
    def row(profile,stat,L):
        if profile=='daily':return G[G.profile.eq('theta')&G.block.eq(L)&G.statistic.eq(stat)].iloc[0]
        return H[H.profile.eq(profile)&H.block.eq(L)&H.statistic.eq(stat)].iloc[0]
    def adj(q):return q.p_adjusted if 'p_adjusted' in q else q.p_holm4
    text=[r'\begin{tabular}{llrrrrr}',r'\toprule',r'Primeira metade & Resumo & $\widehat\theta$ & $p_{21}$ & $p^*_{21}$ & $p^*_{5}$ & $p^*_{63}$\\',r'\midrule']
    for profile in labels:
        for stat in ['mean','median']:
            q=row(profile,stat,21);text.append(f"{labels[profile]} & {'Média' if stat=='mean' else 'Mediana'} & {n(q.estimate)} & {n(q.p_centered)} & {n(adj(q))} & {n(adj(row(profile,stat,5)))} & {n(adj(row(profile,stat,63)))}\\\\")
    (out/'crisis.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    meta=pd.read_csv(ROOT/'results/tables/lab03b_colab_20261023/asset_betas.csv.gz');text=[r'\begin{tabular}{lrrrrrrr}',r'\toprule',r'Recorte & $N$ & Média$\Delta$ & Mediana & $\Delta<0$ & $p^*_{m}$ & $p^*_{q}$ & Rej.$_i$\\',r'\midrule']
    for s,label in [('decada','2016--2025'),('decada_periodo_comum','80 comuns, 2021--2025'),('recente','117, 2021--2025')]:
        a=meta[meta.scenario.eq(s)];mean=F[F.profile.eq('daily')&F.scenario.eq(s)&F.statistic.eq('mean')&F.block.eq(21)].iloc[0];med=F[F.profile.eq('daily')&F.scenario.eq(s)&F.statistic.eq('median')&F.block.eq(21)].iloc[0];text.append(f'{label} & {len(a)} & {n(mean.estimate)} & {n(med.estimate)} & {int((a.delta<0).sum())} & {n(mean.p_holm10)} & {n(med.p_holm10)} & {2 if s=="decada" else 0}\\\\')
    (out/'levels.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    micro=pd.read_csv(out/'microstructure_raw_and_adjusted.csv');text=[r'\begin{tabular}{lrrrrr}',r'\toprule',r'Média na década & $N_t$ & $p_{5/1}$ & $p_{21/4}$ & $p_{63/13}$ & $p^*_{21/4}$\\',r'\midrule']
    for profile,label,blocks in [('lag1','Defasagem 1',[5,21,63]),('leadlag1','Avanço/defasagem',[5,21,63]),('weekly','Semanal',[1,4,13])]:
        a=micro[micro.profile.eq(profile)&micro.scenario.eq('decada')&micro.statistic.eq('mean')];q=a[a.block.eq(blocks[1])].iloc[0];text.append(f'{label} & {int(q.n_median)} & '+ ' & '.join(n(a[a.block.eq(L)].iloc[0].p_centered) for L in blocks)+f' & {n(q.p_adjusted)}\\\\')
    (out/'microstructure.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    scale=pd.read_csv(out/'scale_diagnostics.csv');cov=pd.read_csv(out/'coverage_by_target.csv');text=[r'\begin{tabular}{lrrrrr}',r'\toprule',r'Mecanismo & DP$\bar\Delta$ & EP$_{boot}$ & Cob.$\bar\Delta$(\%) & Cob.$\bar\theta$(\%) & DP/EP\\',r'\midrule']
    mechlabels=dict(gaussian_iid='Normal iid',student_hetero='t5 heteroc.',student_ar='t5 AR0,3',garch_t5='GARCH t5',variance_break_t5='Quebra t5',ar06_t5='t5 AR0,6')
    for q in scale.itertuples():
        c=cov[cov.mechanism.eq(q.mechanism)&cov.family.eq('temporal')&cov.profile.eq('theta')&cov.statistic.eq('mean')].iloc[0];text.append(f'{mechlabels[q.mechanism]} & {n(q.sd_estimator,3)} & {n(q.mean_bootstrap_se,3)} & {n(100*q.coverage,1)} & {n(100*c.coverage,1)} & {n(q.sd_over_mean_se,2)}\\\\')
    (out/'scale.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    cdf=pd.read_csv(out/'cdf_diagnostics.csv');text=[r'\begin{tabular}{lrr}',r'\toprule',r'Alvo & $p$ original ajustado & Faixa CDF/Holm por mecanismo\\',r'\midrule']
    for profile,s,stat,label,p in [('daily','decada','mean','Média da década',.0234),('early','decada','mean','Média inicial',.0096),('theta','decada','mean','Mudança média',.0252),('theta','decada','median','Mudança mediana',.0508)]:
        a=cdf[cdf.profile.eq(profile)&cdf.scenario.eq(s)&cdf.statistic.eq(stat)];text.append(f'{label} & {n(p)} & [{n(a.p_calibrated_Holm_diagnostic.min())};{n(a.p_calibrated_Holm_diagnostic.max())}]\\\\')
    (out/'cdf.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    sector=pd.read_csv(out/'sector_summary.csv');text=[r'\begin{tabular}{p{.31\textwidth}rrrrr}',r'\toprule',r'Setor & $N_{80}$ & Med.$\Delta_{10a}$ & Med.$\Delta_{com}$ & $N_{117}$ & Med.$\Delta_{5a}$\\',r'\midrule']
    for s in sorted(sector.setor_economico.unique()):
        a=sector[sector.setor_economico.eq(s)].set_index('scenario');x=a.loc['decada'];c=a.loc['decada_periodo_comum'];v=a.loc['recente'];text.append(f'{s} & {int(x.assets)} & {n(x.delta_median,3)} & {n(c.delta_median,3)} & {int(v.assets)} & {n(v.delta_median,3)}\\\\')
    (out/'sectors.tex').write_text('\n'.join(text+[r'\bottomrule',r'\end{tabular}'])+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(10,4.4),sharex=True)
    for ax,stat,title in zip(axes,['mean','median'],['Mudança média pareada','Mediana das mudanças pareadas']):
        for j,profile in enumerate(labels):
            for L,shift,color in [(5,-.17,'#5d9fb4'),(21,0,'#193c66'),(63,.17,'#d88f32')]:
                q=row(profile,stat,L);ax.errorbar(q.estimate,j+shift,xerr=[[q.estimate-q.ci_low],[q.ci_high-q.estimate]],fmt='o',capsize=3,color=color,label=f'{L} sessões' if j==0 else None)
        ax.axvline(0,color='0.5',lw=1);ax.set_yticks(range(3),list(labels.values()));ax.invert_yaxis();ax.set_title(title,fontsize=10);ax.set_xlabel('2021–2025 menos primeira metade');ax.grid(axis='x',alpha=.2)
    handles,leg=axes[0].get_legend_handles_labels();fig.legend(handles,leg,ncol=3,loc='lower center',frameon=False);fig.suptitle('80 ativos fixos · ICs básicos nominais · cobertura das novas máscaras não validada',fontsize=10);fig.tight_layout(rect=(0,.08,1,.96))
    for ext in ['pdf','png']:fig.savefig(figs/f'lab03h_crise.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    annual=pd.read_csv(out/'annual_overview.csv');fig,axes=plt.subplots(1,2,figsize=(10,4.0))
    for s,label,color in [('decada','80 ativos fixos','#193c66'),('recente','117 ativos fixos','#c47b28')]:
        a=annual[annual.scenario.eq(s)]
        for ax,name,scale in zip(axes,['delta','es95'],[1,100]):
            ax.plot(a.year,scale*a[name+'_median'],marker='o',markersize=3,color=color,label=label);ax.fill_between(a.year,scale*a[name+'_q25'],scale*a[name+'_q75'],color=color,alpha=.13)
    axes[0].axhline(0,color='0.5',lw=1);axes[0].set_ylabel('Δ = β⁺ − β⁻');axes[0].set_title('Assimetria anual entre ativos',fontsize=10);axes[1].set_ylabel('ES95 histórico diário (%)');axes[1].set_title('Cauda das perdas simples por ativo',fontsize=10)
    for ax in axes:ax.set_xticks(range(2016,2026));ax.tick_params(axis='x',rotation=45);ax.grid(alpha=.2)
    handles,leg=axes[0].get_legend_handles_labels();fig.legend(handles,leg,ncol=2,loc='lower center',frameon=False);fig.suptitle('Mediana e IQR entre ativos · faixas descritivas, não intervalos de confiança',fontsize=10);fig.tight_layout(rect=(0,.1,1,.96))
    for ext in ['pdf','png']:fig.savefig(figs/f'lab03h_periodo_completo.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print('H: six tables and two scientific figures generated from completed exports')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();build(a.output)

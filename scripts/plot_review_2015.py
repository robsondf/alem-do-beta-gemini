#!/usr/bin/env python3
"""Tables and scientific figure from completed I outputs; no re-estimation."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build(out):
    g=out/'gaps_preserved';a=pd.read_csv(g/'aggregate_reproduced.csv');assoc=pd.read_csv(out/'liquidity_all_variants.csv');orig=pd.read_csv(g/'assets_originais_COTAHIST.csv').set_index('papel_id');new=pd.read_csv(g/'assets_universo_2015.csv').set_index('papel_id');l=pd.read_csv(out/'liquidity_2015_full.csv.gz').groupby('papel_id').agg(volume_total_2015=('volume_financeiro','sum'),days_2015=('data','nunique'));l['adtv_2015']=l.volume_total_2015/246;l['presence_2015']=l.days_2015/246;union=pd.concat([orig,new.loc[new.index.difference(orig.index)]]);union=union.join(l);union['group']=np.where(union.index.isin(orig.index.intersection(new.index)),'Comuns',np.where(union.index.isin(orig.index),'Só originais','Só universo 2015'));union['theta']=union.d_late-union.d_early;union.to_csv(out/'asset_liquidity.csv')
    n=lambda v,k=4:f'{v:.{k}f}'.replace('.',',');lines=[r'\begin{tabular}{llrrrr}',r'\toprule',r'Universo & Alvo & $N$ & Estimativa & $p$ & $p^*$\\',r'\midrule']
    for name,label in [('originais_COTAHIST','Originais'),('universo_2015','Seleção 2015')]:
        for target,t in [('early',r'Média$\Delta_{16-20}$'),('theta',r'Média$\theta$'),('decada',r'Média$\Delta_{16-25}$')]:
            row=a[a.universo.eq(name)&a.alvo.eq(target)&a.resumo.eq('media')&a.bloco.eq(21)].iloc[0];lines.append(f'{label} & {t} & {row.N} & {n(row.est)} & {n(row.p)} & {n(row.p_holm)}\\\\')
    (out/'selection.tex').write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    lines=[r'\begin{tabular}{llrrrrrr}',r'\toprule',r'Variante/coorte & Alvo & $N$ & $\rho$ & Viés$_{boot,21}$ & $p^*_{5}$ & $p^*_{21}$ & $p^*_{63}$\\',r'\midrule']
    for (variant,cohort,target),rows in assoc.groupby(['variant','cohort','target'],sort=False):
        q=rows[rows.block.eq(21)].iloc[0];label=('Externo' if variant=='external_diagnostic' else 'Lacunas')+('/orig.' if cohort=='original80' else '/união');lines.append(f'{label} & '+(r'$\Delta$' if target=='early' else r'$\theta$')+f' & {q.N} & {n(q.estimate,3)} & {n(q.bootstrap_bias,3)} & '+' & '.join(n(rows[rows.block.eq(b)].iloc[0].p_holm8) for b in [5,21,63])+r'\\')
    (out/'associations.tex').write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    groups=[]
    for name,sub in union.groupby('group'):
        early=sub[sub.ok_early];pair=sub[sub.ok_early&sub.ok_late];groups.append(dict(group=name,universe=len(sub),N_early=len(early),mean_early=early.d_early.mean(),N_theta=len(pair),mean_theta=pair.theta.mean()))
    pd.DataFrame(groups).to_csv(out/'composition_groups.csv',index=False)
    figdir=out/'figures';figdir.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42});fig,axes=plt.subplots(1,2,figsize=(10,4.2))
    colors={'Comuns':'#607d8b','Só originais':'#ad5b26','Só universo 2015':'#287e9d'}
    for ax,target,title in [(axes[0],'early','Assimetria em 2016–2020'),(axes[1],'theta','Mudança entre quinquênios')]:
        use=union[union.ok_early] if target=='early' else union[union.ok_early&union.ok_late];field='d_early' if target=='early' else 'theta'
        for label,color in colors.items():
            p=use[use.group.eq(label)];ax.scatter(np.log10(p.adtv_2015),p[field],s=19,color=color,alpha=.8,label=label)
        q=assoc[assoc.variant.eq('gaps_preserved')&assoc.cohort.eq('union118')&assoc.target.eq(target)&assoc.block.eq(21)].iloc[0];ax.set_title(f'{title} · N={len(use)}',fontsize=10);ax.text(.03,.96,f'ρ = {n(q.estimate,3)}',transform=ax.transAxes,ha='left',va='top');ax.axhline(0,color='.6',lw=.8);ax.set_xlabel('log10(volume financeiro médio por sessão em 2015)');ax.set_ylabel('Δ = β⁺ − β⁻' if target=='early' else 'θ = Δ recente − Δ inicial');ax.grid(alpha=.17)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,ncol=3,loc='lower center',frameon=False);fig.suptitle('Retornos COTAHIST · lacunas documentadas preservadas · associação descritiva',fontsize=10);fig.tight_layout(rect=(0,.09,1,.95))
    for ext in ['pdf','png']:fig.savefig(figdir/('lab03i_liquidez.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig);print('I: selection/association tables,composition and liquidity figure generated')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);build(p.parse_args().output)

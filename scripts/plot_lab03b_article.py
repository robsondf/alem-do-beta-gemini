#!/usr/bin/env python3
"""Compact paper layouts, same complete estimates; full notebook plots remain separate."""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def plot(source,target):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    b=pd.read_csv(source/'asset_betas.csv');a=pd.read_csv(source/'annual_sector.csv');r=pd.read_csv(source/'risk_full.csv');r=r[r.cash_variant.eq('referencia_n')]
    ar=pd.read_csv(source/'risk_annual.csv');ci=pd.read_csv(source/'sector_bootstrap.csv');ci=ci[ci.block_length.eq(10)]
    scenarios=['decada','decada_periodo_comum','recente'];labels=['80 · 2016–2025','80 comuns · 2021–2025','117 · 2021–2025']
    def save(fig,name):
        final=target/('lab03b_artigo_'+name+'.pdf');temp=final.with_suffix('.staging.pdf')
        fig.savefig(temp,bbox_inches='tight');plt.close(fig)
        assert temp.read_bytes().startswith(b'%PDF') and temp.read_bytes().rstrip().endswith(b'%%EOF')
        temp.replace(final)
    fig,axes=plt.subplots(1,3,figsize=(8.6,3.1),constrained_layout=True)
    low=min(b.beta_minus.min(),b.beta_plus.min())-.08;high=max(b.beta_minus.max(),b.beta_plus.max())+.08
    for ax,s,label in zip(axes,scenarios,labels):
        g=b[b.scenario.eq(s)];ax.scatter(g.beta_minus,g.beta_plus,s=12,color='#176287',alpha=.8);ax.plot([low,high],[low,high],'--',color='gray',lw=.8)
        ax.set(xlim=(low,high),ylim=(low,high),title=label,xlabel='β⁻',ylabel='β⁺');ax.grid(alpha=.15)
    save(fig,'betas')
    sectors=sorted(b.setor_economico.unique());fig,axes=plt.subplots(5,2,figsize=(8.5,9.7),sharex=True,sharey=True,constrained_layout=True)
    for ax,sector in zip(axes.flat,sectors):
        for s,col,style in [('decada','#145a86','-'),('recente','#cc6b25','--')]:
            g=a[a.scenario.eq(s)&a.setor_economico.eq(sector)].sort_values('year');ax.plot(g.year,g.delta_median,style,color=col,marker='o',ms=2.5);ax.fill_between(g.year,g.delta_q25,g.delta_q75,color=col,alpha=.12)
        ax.axhline(0,color='gray',lw=.7);ax.set(title=sector,xticks=[2016,2019,2022,2025],xlim=(2015.8,2025.2),ylabel='Mediana Δβ');ax.grid(alpha=.16)
    save(fig,'setores')
    fig,axes=plt.subplots(1,3,figsize=(9.5,4.6),sharey=True,constrained_layout=True);extent=1.08*np.abs(ci[['point','ci_low','ci_high']].to_numpy()).max()
    short={'Petróleo, Gás e Biocombustíveis':'Petróleo/Gás/Biocomb.','Tecnologia da Informação':'Tecnologia Informação'}
    for ax,s,label in zip(axes,scenarios,labels):
        g=ci[ci.scenario.eq(s)].set_index('setor_economico').loc[sectors]
        for i,row in enumerate(g.itertuples()):
            ax.plot([row.ci_low,row.ci_high],[i,i],color='#176287',lw=1.4);ax.scatter(row.point,i,color='#176287',s=17)
            ax.annotate('n='+str(row.assets_sector),(row.point,i),xytext=(3,4),textcoords='offset points',fontsize=7)
        ax.axvline(0,ls='--',color='gray',lw=.7);ax.set(title=label,xlim=(-extent,extent),yticks=range(10),yticklabels=[short.get(z,z) for z in sectors],xlabel='Mediana setor − demais');ax.grid(axis='x',alpha=.15)
    axes[0].invert_yaxis();save(fig,'contrastes')
    merged=r.merge(b[['scenario','papel_id','beta_minus']],on=['scenario','papel_id'],validate='one_to_one')
    fig,axes=plt.subplots(2,3,figsize=(8.7,5.1),constrained_layout=True)
    for j,(s,label) in enumerate(zip(scenarios,labels)):
        g=merged[merged.scenario.eq(s)]
        for i,x,y,xlabel,ylabel in [(0,'beta_market_model','log_std_daily','β tradicional','Vol. diária log (%)'),(1,'beta_minus','es95_simple_loss','β⁻','ES95 diário (%)')]:
            ax=axes[i,j];ax.scatter(g[x],100*g[y],s=12,color='#176287',alpha=.8);ax.set(xlabel=xlabel,ylabel=ylabel,title=label if i==0 else '',xlim=(merged[x].min()-.08,merged[x].max()+.08),ylim=(0,merged[y].max()*108));ax.grid(alpha=.15)
    save(fig,'risco')
    fig,axes=plt.subplots(2,3,figsize=(8.6,5.1),constrained_layout=True)
    for j,(s,label) in enumerate(zip(scenarios,labels)):
        g=ar[ar.scenario.eq(s)]
        for i,measure,scale,ylabel in [(0,'log_std_daily',100,'Vol. diária log (%)'),(1,'r2_market_model',1,'R²')]:
            gg=g.groupby('year')[measure];med=gg.median();lo=gg.quantile(.25);hi=gg.quantile(.75);ax=axes[i,j]
            ax.plot(med.index,med*scale,marker='o',ms=3,color='#145a86');ax.fill_between(med.index,lo*scale,hi*scale,color='#145a86',alpha=.18)
            ax.set(title=label if i==0 else '',ylabel=ylabel,xticks=med.index[::2],ylim=(0,float(ar.groupby(['scenario','year'])[measure].quantile(.75).max())*scale*1.07) if i==0 else (0,1));ax.grid(alpha=.15)
    save(fig,'risco_anual')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--target',type=Path,required=True);a=p.parse_args();plot(a.source,a.target)

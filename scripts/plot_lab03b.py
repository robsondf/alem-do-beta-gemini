#!/usr/bin/env python3
"""Scientific figures: every asset and year, no display clipping/winsorisation."""
from pathlib import Path
import argparse,json,zipfile,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03b import sha
from lab02 import BENCHMARK
LABELS=['80 ativos · 2016–2025','80 comuns · 2021–2025','117 ativos · 2021–2025']
SCENARIOS=['decada','decada_periodo_comum','recente']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})

def plot(output,archive):
    lock=json.loads((ROOT/'data/lab03b/inputs_manifest.json').read_text());assert sha(archive)==lock['lab03_sha256']
    b=pd.read_csv(output/'asset_betas.csv');a=pd.read_csv(output/'annual_sector.csv')
    r=pd.read_csv(output/'risk_full.csv');r=r[r.cash_variant.eq('referencia_n')]
    ar=pd.read_csv(output/'risk_annual.csv');ci=pd.read_csv(output/'sector_bootstrap.csv');ci=ci[ci.block_length.eq(10)]
    with zipfile.ZipFile(archive) as z:rolling=pd.read_csv(z.open('rolling.csv'))
    sectors=sorted(b.setor_economico.unique());colors={s:plt.get_cmap('tab10')(i) for i,s in enumerate(sectors)}
    folder=output/'figures';folder.mkdir(exist_ok=True)
    def save(fig,name,note):
        fig.text(.01,.012,note,fontsize=8,color='#444',va='bottom',wrap=True)
        fig.savefig(folder/(name+'.png'),dpi=160,bbox_inches='tight');fig.savefig(folder/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(17,6));fig.subplots_adjust(bottom=.24,wspace=.22)
    limits=[min(b.beta_minus.min(),b.beta_plus.min())-.1,max(b.beta_minus.max(),b.beta_plus.max())+.1]
    for ax,scenario,label in zip(axes,SCENARIOS,LABELS):
        g=b[b.scenario.eq(scenario)]
        for s in sectors:
            q=g[g.setor_economico.eq(s)];ax.scatter(q.beta_minus,q.beta_plus,s=20,color=colors[s],alpha=.8)
        ax.plot(limits,limits,'--',color='gray',lw=1);ax.set(xlim=limits,ylim=limits,title=label,xlabel='β⁻ · mercado em queda',ylabel='β⁺ · mercado em alta');ax.grid(alpha=.17)
    fig.legend([Line2D([],[],marker='o',ls='',color=colors[s]) for s in sectors],sectors,loc='lower center',bbox_to_anchor=(.5,.07),ncol=5,fontsize=8)
    save(fig,'lab03b_betas','Cada ponto é um ativo/classe. Abaixo da diagonal: Δβ=β⁺−β⁻<0. Estimativas condicionais N/log/HAC5; não são carteiras ou retornos esperados. Os 80 comuns reutilizam os 117.')
    fig,axes=plt.subplots(5,2,figsize=(15,16),sharex=True,sharey=True);fig.subplots_adjust(hspace=.32,bottom=.09,top=.94)
    for ax,sector in zip(axes.flat,sectors):
        for scenario,col,style in [('decada','#145a86','-'),('recente','#cc6b25','--')]:
            g=a[a.scenario.eq(scenario)&a.setor_economico.eq(sector)].sort_values('year')
            ax.plot(g.year,g.delta_median,style,marker='o',ms=3,color=col)
            ax.fill_between(g.year,g.delta_q25,g.delta_q75,color=col,alpha=.12)
        ax.axhline(0,color='gray',lw=.8);ax.set(title=sector,xlim=(2015.8,2025.2),xticks=[2016,2018,2020,2022,2024,2025],ylabel='Mediana de Δβ');ax.grid(alpha=.15)
    fig.suptitle('Assimetria anual por setor · pares diários, todos os anos',fontsize=17)
    fig.legend([Line2D([],[],color='#145a86',marker='o'),Line2D([],[],color='#cc6b25',ls='--',marker='o')],['80 fixos, 2016–2025','117 fixos, 2021–2025'],loc='lower center',bbox_to_anchor=(.5,.043),ncol=2)
    save(fig,'lab03b_setores_anuais','Faixas = IQR ENTRE ATIVOS, não ICs; n=1 descreve só o ativo. Pares diários por ano; linhas não interpolam retornos. Common80 coincide com os mesmos ativos da década em 2021–2025.')
    fig,axes=plt.subplots(1,3,figsize=(17,7));fig.subplots_adjust(left=.20,wspace=.12,bottom=.16)
    order=sectors
    extent=1.08*float(np.nanmax(np.abs(ci[['point','ci_low','ci_high']].to_numpy())))
    for j,(ax,scenario,label) in enumerate(zip(axes,SCENARIOS,LABELS)):
        g=ci[ci.scenario.eq(scenario)].set_index('setor_economico').loc[order]
        for i,(s,row) in enumerate(g.iterrows()):
            ax.plot([row.ci_low,row.ci_high],[i,i],color=colors[s],lw=2)
            ax.scatter(row.point,i,color=colors[s],s=30)
            ax.annotate('n='+str(row.assets_sector),(row.point,i),xytext=(4,5),textcoords='offset points',fontsize=7)
        ax.axvline(0,color='gray',ls='--');ax.set(title=label,yticks=range(10),yticklabels=order if j==0 else [],xlabel='Mediana do setor − mediana dos demais',xlim=(-extent,extent));ax.grid(axis='x',alpha=.2);ax.invert_yaxis()
    save(fig,'lab03b_contrastes_setoriais','ICs marginais exploratórios, 999 blocos síncronos de 10 pregões; aproximação estacionária, sem teste Holm ou efeito causal. n=1 descreve só o ativo. Escala comum; sensibilidades L5/L20 nos CSVs.')
    # Full calendar axis explicitly includes the unestimable initial 252-session warm-up.
    fig,axes=plt.subplots(2,1,figsize=(17,20));fig.subplots_adjust(left=.10,right=.91,hspace=.17,bottom=.065)
    rolled=rolling[rolling.width.eq(252)&rolling.scenario.isin(['decada','recente'])]
    vmax=float(rolled.delta.abs().max());norm=TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax)
    for ax,scenario,label,start in zip(axes,['decada','recente'],[LABELS[0],LABELS[2]],['2016-01-01','2021-01-01']):
        g=rolled[rolled.scenario.eq(scenario)]
        meta=g[['ticker','setor_economico']].drop_duplicates().sort_values(['setor_economico','ticker']);tickers=meta.ticker.tolist()
        dates=sorted(g.window_end.unique());values=g.pivot(index='ticker',columns='window_end',values='delta').loc[tickers,dates].to_numpy()
        import matplotlib.dates as md
        centers=md.date2num(pd.to_datetime(dates));edges=np.r_[centers[0]-(centers[1]-centers[0])/2,(centers[:-1]+centers[1:])/2,centers[-1]+(centers[-1]-centers[-2])/2]
        im=ax.pcolormesh(edges,np.arange(len(tickers)+1)-.5,values,cmap='RdBu_r',norm=norm,rasterized=True)
        ax.set_facecolor('#dedede');ax.set_xlim(pd.Timestamp(start),pd.Timestamp('2025-12-31'));ax.xaxis_date();ax.xaxis.set_major_locator(md.YearLocator());ax.xaxis.set_major_formatter(md.DateFormatter('%Y'))
        ax.set(yticks=range(len(tickers)),yticklabels=[t.replace('.SA','') for t in tickers],title=label+' · Δβ, 252 pregões/passo 21');ax.tick_params(axis='y',labelsize=5);ax.invert_yaxis()
    fig.colorbar(im,ax=axes.ravel().tolist(),fraction=.018,pad=.025,label='Δβ · escala comum sem corte de valores')
    save(fig,'lab03b_mapa_movel','Todos os ativos; ordenação setor/ticker. Cinza inicial = janela ainda não contém 252 pregões, sem preencher 2016/2021. Sobreposição não cria testes independentes; common80 reutiliza os 117. Escala cobre todos os valores, sem winsorização.')
    fig,axes=plt.subplots(2,3,figsize=(17,10));fig.subplots_adjust(hspace=.35,bottom=.17)
    merged=r.merge(b[['scenario','papel_id','beta_minus']],on=['scenario','papel_id'],validate='one_to_one')
    xranges=[(merged.beta_market_model.min()-.08,merged.beta_market_model.max()+.08),(merged.beta_minus.min()-.08,merged.beta_minus.max()+.08)]
    yranges=[(0,merged.log_std_daily.max()*108),(0,merged.es95_simple_loss.max()*108)]
    for j,(scenario,label) in enumerate(zip(SCENARIOS,LABELS)):
        g=merged[merged.scenario.eq(scenario)]
        for sector in sectors:
            q=g[g.setor_economico.eq(sector)]
            axes[0,j].scatter(q.beta_market_model,100*q.log_std_daily,color=colors[sector],s=20,alpha=.8)
            axes[1,j].scatter(q.beta_minus,100*q.es95_simple_loss,color=colors[sector],s=20,alpha=.8)
        axes[0,j].set(title=label,xlabel='β tradicional',ylabel='Desvio padrão diário log (%)')
        axes[1,j].set(xlabel='β⁻ · exposição ao mercado em queda',ylabel='ES95 histórico · perda simples diária (%)')
        for k,ax in enumerate(axes[:,j]):ax.grid(alpha=.18);ax.set(xlim=xranges[k],ylim=yranges[k])
    fig.legend([Line2D([],[],marker='o',ls='',color=colors[s]) for s in sectors],sectors,loc='lower center',bbox_to_anchor=(.5,.05),ncol=5,fontsize=8)
    save(fig,'lab03b_risco','Risco total, exposição ao mercado e perdas de cauda são conceitos distintos. ES95 é média dos piores 5% de perdas simples diárias com massa fracionária; não é previsão. Dados N observados, sem taxa livre de risco ou alfa de Jensen.')
    fig,axes=plt.subplots(2,3,figsize=(16,9));fig.subplots_adjust(hspace=.32,bottom=.13)
    for j,(scenario,label) in enumerate(zip(SCENARIOS,LABELS)):
        g=ar[ar.scenario.eq(scenario)]
        for row,measure,scale,ylabel in [(0,'log_std_daily',100,'Desvio padrão diário log (%)'),(1,'r2_market_model',1,'R² do modelo de mercado')]:
            gg=g.groupby('year')[measure];med=gg.median();lo=gg.quantile(.25);hi=gg.quantile(.75)
            ax=axes[row,j];ax.plot(med.index,med*scale,marker='o',color='#145a86');ax.fill_between(med.index,lo*scale,hi*scale,color='#145a86',alpha=.18)
            ylim=(0,float(ar.groupby(['scenario','year'])[measure].quantile(.75).max())*scale*1.07) if row==0 else (0,1)
            # Compare cohort medians on common scales; no asset's plotted IQR is clipped.
            ax.set(title=label if row==0 else '',ylabel=ylabel,xticks=med.index[::2],ylim=ylim);ax.grid(alpha=.2)
    save(fig,'lab03b_risco_anual','Pontos = mediana entre ativos; faixas = IQR entre ativos, não ICs. Cada ano usa retornos diários observados. R² mede associação no modelo, não fração causal de risco. Sem anualização automática, projeção ou atribuição causal a eventos.')
    print('Seis figuras completas exportadas em PNG e PDF vetorial.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--lab03-archive',type=Path,required=True);a=p.parse_args();plot(a.output,a.lab03_archive)

#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot(output):
    annual,halves,families,rolling=[pd.read_csv(output/(name+'.csv')) for name in ['annual','halves','temporal_family','rolling']]
    figures=output/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    def save(fig,name):
        for suffix in ['png','pdf']:fig.savefig(figures/(name+'.'+suffix),dpi=170,bbox_inches='tight',facecolor='white')
        plt.close(fig)
    h=halves[halves.configuration.eq('N_log_HAC5')].sort_values('theta')
    assert len(h)==80
    fig,ax=plt.subplots(figsize=(10,15))
    pos=np.arange(len(h))
    ax.errorbar(h.theta,pos,xerr=np.vstack([h.theta-h.theta_ci_low,h.theta_ci_high-h.theta]),fmt='o',
                ms=3,color='#4C78A8',ecolor='#9AB3CB',elinewidth=.8,capsize=2)
    ax.set_yticks(pos,h.ticker.str.replace('.SA','',regex=False),fontsize=8)
    ax.axvline(0,color='#555',linestyle='--',lw=1)
    ax.grid(axis='x',alpha=.2)
    ax.set_xlabel('θ = Δβ de 2021–2025 − Δβ de 2016–2020 · IC95% marginal HAC5 conjunto')
    ax.set_title('Mudança de magnitude: os mesmos 80 ativos\nReferência N · modelo com oito parâmetros',pad=16,fontweight='bold')
    fig.text(.02,.003,'Todos os ativos, ordenados apenas para exibição. ICs marginais não incorporam Holm474.\n'
             'Não rejeitar θ=0 não demonstra equivalência ou estabilidade; nenhuma quebra causal é identificada.',fontsize=9,color='#555')
    fig.tight_layout(rect=[0,.04,1,.99]);save(fig,'lab03_theta80')
    a=annual[annual.configuration.eq('N_log_HAC5')]
    limit=float(a.delta.abs().max())
    for scenario,size,years in [('decada',80,range(2016,2026)),('recente',117,range(2021,2026))]:
        data=a[a.scenario.eq(scenario)]
        identities=data[['papel_id','ticker','setor_economico']].drop_duplicates().sort_values(['setor_economico','ticker'])
        table=data.pivot(index='papel_id',columns='year',values='delta').loc[identities.papel_id,list(years)]
        assert len(table)==size
        fig,ax=plt.subplots(figsize=(10,14 if size==80 else 18))
        cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#eeeeee')
        im=ax.imshow(np.ma.masked_invalid(table.to_numpy()),aspect='auto',cmap=cmap,vmin=-limit,vmax=limit)
        ax.set_yticks(range(size),identities.ticker.str.replace('.SA','',regex=False),fontsize=7)
        ax.set_xticks(range(len(years)),list(years))
        previous=None
        for i,sector in enumerate(identities.setor_economico):
            if previous is not None and sector!=previous:ax.axhline(i-.5,color='#333',lw=.6)
            previous=sector
        if scenario=='decada':ax.axvline(4.5,color='black',lw=1.3)
        ax.set_title(f'Δβ anual dos {size} ativos · {min(years)}–{max(years)}\nRetornos diários observados · referência N / HAC5',fontweight='bold',pad=16)
        fig.colorbar(im,ax=ax,shrink=.45,label='Δβ estimado com os pares diários de cada ano')
        fig.text(.02,.004,'Todos os ativos, por setor/ticker; cores com a mesma escala nas duas amostras, sem winsorização.\n'
                 'Cada célula usa observações diárias do ano, não um único retorno anual. Cor não testa persistência; usa-se IUT/Holm474.',fontsize=9,color='#555')
        fig.tight_layout(rect=[0,.04,1,.99]);save(fig,'lab03_anual_'+scenario)
    # WEGE3 was already the inspection asset in the earlier analysis notebook.
    fig,axs=plt.subplots(2,3,figsize=(15,9),sharey=True)
    labels={'decada':'80 ativos · janela de dados 2016–2025',
            'decada_periodo_comum':'80 comuns · janela de dados 2021–2025',
            'recente':'117 ativos · janela de dados 2021–2025'}
    for col,scenario in enumerate(labels):
        for row,width in enumerate([252,504]):
            ax=axs[row,col]
            g=rolling[rolling.scenario.eq(scenario)&rolling.ticker.eq('WEGE3.SA')&rolling.width.eq(width)].copy()
            x=pd.to_datetime(g.window_end)
            ax.fill_between(x,g.delta_ci_low,g.delta_ci_high,color='#4C78A8',alpha=.18,label='IC95% marginal')
            ax.plot(x,g.delta,color='#28618D',lw=1.3,label='Δβ')
            ax.set_xlim(x.min(),x.max())
            ax.axhline(0,color='#777',lw=.8,linestyle='--')
            ax.set_title(labels[scenario]+'\n'+str(width)+' pregões, passo 21',fontsize=10)
            ax.tick_params(axis='x',rotation=35);ax.grid(alpha=.18)
            if col==0:ax.set_ylabel('WEGE3 · Δβ / HAC5')
    axs[0,0].legend(loc='best',fontsize=8)
    fig.suptitle('Janelas móveis de WEGE3: diagnóstico, sem teste por sobreposição de ICs',fontweight='bold',fontsize=14)
    fig.text(.02,.004,'Exemplo já escolhido no Lab02; todos os ativos/32.708 linhas estão no CSV. Cada ponto utiliza somente sua janela até a data mostrada.\n'
             'Janelas sobrepostas compartilham retornos; os dois painéis comuns repetem o mesmo ativo/dados, sem novas evidências independentes.',fontsize=9,color='#555')
    fig.tight_layout(rect=[0,.06,1,.94]);save(fig,'lab03_rolling_wege3')
    fig,ax=plt.subplots(figsize=(8,3.7))
    colors={252:'#28618D',504:'#C57F16'}
    for width in [252,504]:
        g=rolling[rolling.scenario.eq('decada')&rolling.ticker.eq('WEGE3.SA')&rolling.width.eq(width)]
        x=pd.to_datetime(g.window_end)
        ax.fill_between(x,g.delta_ci_low,g.delta_ci_high,color=colors[width],alpha=.10)
        ax.plot(x,g.delta,color=colors[width],lw=1.3,label=str(width)+' pregões')
    g=rolling[rolling.scenario.eq('decada')&rolling.ticker.eq('WEGE3.SA')]
    ax.set_xlim(pd.to_datetime(g.window_end).min(),pd.to_datetime(g.window_end).max())
    ax.axhline(0,color='#666',ls='--',lw=.8)
    ax.set(xlabel='Fim da janela · dados de 2016–2025',ylabel='Δβ · HAC5',title='WEGE3: 252 e 504 pregões, passo de 21')
    ax.grid(alpha=.18);ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(figures/'lab03_rolling_artigo.pdf',bbox_inches='tight')
    plt.close(fig)
    rows=[]
    for configuration,g in families.groupby('configuration',sort=False):
        rows.append(dict(configuration=configuration,
                         magnitude_rejections=int(g[g.test.eq('magnitude_late_minus_early')].reject_005_conditional.sum()),
                         positive_rejections=int(g[g.direction.eq('positive')].reject_005_conditional.sum()),
                         negative_rejections=int(g[g.direction.eq('negative')].reject_005_conditional.sum()),
                         nonestimable=int(g.p_raw.isna().sum()),family_size=len(g)))
    pd.DataFrame(rows).to_csv(output/'resumo_publicacao.csv',index=False)
    (output/'manifesto_exports.json').write_text(json.dumps({str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file() and p.name!='manifesto_exports.json'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);plot(p.parse_args().output)

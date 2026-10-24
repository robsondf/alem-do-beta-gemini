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

LABELS = {'decada': '80 ativos · 2016–2025', 'decada_periodo_comum': '80 comuns · 2021–2025',
          'recente': '117 ativos · 2021–2025'}


def plot(output):
    hac, boot, events, simple = (pd.read_csv(output / (n + '.csv')) for n in ['hac', 'bootstrap', 'events', 'simple'])
    ref = hac[hac.cash_variant.eq('referencia_n')]
    figs = output / 'figures'
    figs.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'savefig.facecolor': 'white'})
    def save(fig, name):
        for suffix in ['png', 'pdf']:
            fig.savefig(figs / (name + '.' + suffix), dpi=180, bbox_inches='tight')
        plt.close(fig)
    fig, axs = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    for ax, s in zip(axs, LABELS):
        g = ref[ref.scenario.eq(s)]
        base = g[g.treatment.eq('HAC5')].set_index('papel_id').delta_se
        values = [(g[g.treatment.eq('HAC' + str(k))].set_index('papel_id').delta_se / base).to_numpy()
                  for k in [0, 10, 20]]
        values += [(boot[boot.scenario.eq(s) & boot.block_length.eq(k)].bootstrap_se /
                    boot[boot.scenario.eq(s) & boot.block_length.eq(k)].hac_se).to_numpy() for k in [5, 10, 20]]
        boxes = ax.boxplot(values, tick_labels=['HAC0', 'HAC10', 'HAC20', 'B5', 'B10', 'B20'],
                           patch_artist=True, showfliers=False)
        for i, box in enumerate(boxes['boxes']):
            box.set_facecolor('#4C78A8' if i < 3 else '#E0A02F')
            box.set_alpha(.6)
        ax.axhline(1, color='#444', lw=1, linestyle='--')
        ax.set_title(LABELS[s], fontsize=11)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=.2)
    axs[0].set_ylabel('Erro padrão de Δβ / erro padrão HAC5')
    fig.suptitle('Sensibilidade da incerteza na referência N', fontsize=15, fontweight='bold')
    fig.text(.02, -.04, 'Caixas: mediana e quartis; bigodes 1,5 IQR; pontos extremos omitidos apenas do desenho. Todos os ativos estão nos CSVs.\n'
             'B5/B10/B20: 999 réplicas em blocos, referência N; os 80 comuns reutilizam os 117. Não é teste de persistência.', fontsize=9, color='#555')
    fig.tight_layout(rect=[0, .03, 1, .94])
    save(fig, 'lab02y_incerteza')
    e = events[events.cash_variant.eq('referencia_n')].copy()
    e['row'] = e.ticker.str.replace('.SA', '', regex=False) + ' | ' + e.treatment
    piv = e.pivot(index='row', columns='scenario', values='delta_change').reindex(columns=LABELS)
    names = []
    for name in piv.index:
        for a, b in [('without_', 'sem '), ('_plusminus5', ' ±5 pregões'), ('_year', ' ano '),
                     ('preferencia', 'preferência'), ('preference_Q4_2024', '4º trimestre/2024'),
                     ('regime_before_assai', 'pré-Assaí (2021)'), ('regime_between_assai_exito', 'entre Assaí/Éxito'),
                     ('regime_after_exito', 'pós-Éxito')]:
            name = name.replace(a, b)
        names.append(name)
    fig, ax = plt.subplots(figsize=(11, 8))
    limit = max(abs(piv.min().min()), abs(piv.max().max()))
    cmap = plt.get_cmap('RdBu_r').copy(); cmap.set_bad('#eeeeee')
    im = ax.imshow(np.ma.masked_invalid(piv.to_numpy()), cmap=cmap, vmin=-limit, vmax=limit, aspect='auto')
    ax.set_yticks(range(len(piv)), names)
    ax.set_xticks(range(3), list(LABELS.values()))
    for i, row in enumerate(piv.index):
        for j, s in enumerate(LABELS):
            value = piv.loc[row, s]
            text = f'{value:+.4f}' if np.isfinite(value) else '—'
            if row.startswith('PCAR3') and row.endswith('regime_before_assai') and s == 'recente':
                text = '37 pares: insuficiente'
            ax.text(j, i, text, ha='center', va='center', fontsize=9,
                    color='white' if np.isfinite(value) and abs(value) > .65 * limit else '#222')
    ax.set_title('Eventos e recortes: mudança de Δβ frente à mesma referência N', pad=16, fontweight='bold')
    fig.colorbar(im, ax=ax, shrink=.65, label='Δβ do recorte − Δβ da janela completa')
    fig.text(.02, -.01, 'Traço: ativo fora da amostra ou janela não aplicável. A retirada de dias também muda a amostra temporal.\n'
             'Nenhum NaN foi preenchido; máscaras não identificam efeito causal do evento. Demais quatro cenários de caixa estão nos CSVs.', fontsize=9, color='#555')
    fig.tight_layout()
    save(fig, 'lab02y_eventos')
    a = simple[simple.cash_variant.eq('referencia_n')]
    lo = min(a.delta.min(), a.delta_same_cash_log_reference.min())
    hi = max(a.delta.max(), a.delta_same_cash_log_reference.max())
    margin = (hi - lo) * .08
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.8), sharex=True, sharey=True)
    for ax, s in zip(axs, LABELS):
        g = a[a.scenario.eq(s)]
        ax.scatter(g.delta_same_cash_log_reference, g.delta, s=22, color='#4C78A8', alpha=.7)
        ax.plot([lo - margin, hi + margin], [lo - margin, hi + margin], '--', color='#777', lw=1)
        ax.set(xlim=(lo - margin, hi + margin), ylim=(lo - margin, hi + margin),
               title=LABELS[s], xlabel='Δβ com log-retornos')
        ax.grid(alpha=.15)
    axs[0].set_ylabel('Δβ com retornos simples')
    fig.suptitle('Sensibilidade à definição do retorno · referência N', fontweight='bold', fontsize=14)
    fig.text(.02, -.01, 'Transformação exp(r)−1 aplicada ao ativo e ao mercado nos mesmos pares. Linha tracejada: igualdade.\n'
             'Coeficientes são estimandos distintos; a diferença não identifica erro dos dados nem mudança temporal.', fontsize=9, color='#555')
    fig.tight_layout(rect=[0, .04, 1, .92])
    save(fig, 'lab02y_simples_log')
    manifest = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'manifesto_exports.json'}
    (output / 'manifesto_exports.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    plot(p.parse_args().output)

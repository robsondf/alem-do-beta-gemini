#!/usr/bin/env python3
"""Expose already verified Colab diagnostics; no estimation or new tests of H1/H2."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PINS = {
 'results/tables/lab03e_colab_20261023/economic_sensitivities.csv.gz': '90ebc8dc0a71f65f0a41ebff6afe2d9deea6ffe9d18d57d7e86df4ba0a54fb11',
 'results/tables/lab03e_colab_20261023/economic_removed_observations.csv.gz': 'a0ac47f356cf6f98a5cfc9246320f616bdc54c900f69da60a803364533264fbd',
 'results/tables/lab03e_colab_20261023/economic_ledger.csv.gz': 'd095b6be7330ce8f5dc28b425a30b90ab70d1f90c1d63e80d424ab81e634e56e',
 'results/tables/lab03e_colab_20261023/observed_static_precision.csv.gz': '374c396f18c52c6e1e1d2295411808af8c824d4dfafe97537c00f883814faa94',
 'results/tables/lab03e_colab_20261023/bank_designs.csv.gz': 'd0fe48ee6d20975ca37b6c8fdb39cbbf1face241c65b96735dcfcc868d92212d',
 'results/tables/lab03b_colab_20261023/asset_betas.csv.gz': '0c2c54fc1f212d914cf083300757e2706a94d32ae762e64b8814e1a837192275',
}


def summarize(output):
    tables = {}
    for name, expected in PINS.items():
        raw = (ROOT / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Changed input: ' + name)
        tables[Path(name).name] = pd.read_csv(ROOT / name, float_precision='round_trip')
    output.mkdir(parents=True, exist_ok=False)
    sensitivities = tables['economic_sensitivities.csv.gz']
    ledger = tables['economic_ledger.csv.gz']
    metadata = tables['asset_betas.csv.gz']
    assert len(ledger) == 197 and len(sensitivities) == 1970 and len(metadata) == 277
    assert metadata.groupby('scenario').size().to_dict() == {'decada': 80, 'decada_periodo_comum': 80, 'recente': 117}
    assert metadata.papel_id.nunique() == 117
    keys = ['scenario', 'papel_id']
    primary = metadata[metadata.scenario.ne('decada_periodo_comum')].copy()
    assert len(primary) == 197 and not primary.duplicated(keys).any()
    recent = metadata[metadata.scenario.eq('recente')].set_index('papel_id')
    common = metadata[metadata.scenario.eq('decada_periodo_comum')].set_index('papel_id')
    for column in ['ticker', 'company_id', 'beta', 'beta_minus', 'beta_plus', 'delta', 'n_pairs', 'delta_p_holm_197']:
        pd.testing.assert_series_equal(common[column].sort_index(), recent.loc[common.index, column].sort_index(), check_names=False)
    fields = ['scenario','papel_id','ticker','company_id','setor_economico','n_pairs','n_plus','n_minus','n_missing','beta','beta_minus','beta_plus','delta','delta_se','delta_ci_low','delta_ci_high','delta_p','delta_p_holm_197','alpha_minus','alpha_plus']
    primary = primary[fields].sort_values(keys).reset_index(drop=True)
    primary['intercept_jump'] = primary.alpha_plus - primary.alpha_minus
    primary['intercept_jump_se_status'] = 'not_exported_by_frozen_run'
    rank = tables['observed_static_precision.csv.gz']
    rank = rank[rank.bank.eq('pooled')][keys + ['p_rank', 'p_holm_197']].rename(columns={'p_rank':'complement_p_rank','p_holm_197':'complement_p_holm_197'})
    primary = primary.merge(rank, on=keys, validate='one_to_one')
    primary.to_csv(output/'estimativas_197.csv', index=False)
    inventory = recent.reset_index()[['papel_id','ticker','company_id','setor_economico']].sort_values('papel_id')
    long_ids = set(metadata.loc[metadata.scenario.eq('decada'), 'papel_id'])
    inventory['in_decade_80'] = inventory.papel_id.isin(long_ids)
    inventory['in_recent_117'] = True
    inventory.to_csv(output/'inventario_117.csv', index=False)
    diagnostics = ['unmasked','remove1_largest_absolute_observation_influence','remove5_largest_absolute_observation_influence']
    critical = sensitivities[sensitivities.scenario.eq('decada') & sensitivities.ticker.isin(['VULC3.SA','BBDC4.SA']) & sensitivities.reference.eq('referencia_n') & sensitivities.diagnostic.isin(diagnostics)].copy()
    assert len(critical) == 6 and not critical.duplicated(['papel_id','diagnostic']).any()
    critical['adjusted_decision_after_mask'] = 'not_recalibrated_not_claimed'
    critical.to_csv(output/'casos_criticos.csv', index=False)
    removed = tables['economic_removed_observations.csv.gz']
    removed = removed[removed.scenario.eq('decada') & removed.ticker.isin(['VULC3.SA','BBDC4.SA'])]
    removed.to_csv(output/'datas_influentes.csv', index=False)
    # Maxima are located in the full ledger, not attributed to a highlighted asset.
    maxima = ledger.loc[ledger.groupby('scenario').max_absolute_diagnostic_shift.idxmax(), ['scenario','ticker','max_absolute_diagnostic_shift']]
    maxima.to_csv(output/'maximos_amostra.csv', index=False)
    designs = tables['bank_designs.csv.gz']
    lines = [r'\begin{tabular}{llrrl}', r'\toprule',
             r'Ativo & Diagnóstico & $\widehat\Delta$ & Mudança & IC marginal\\', r'\midrule']
    labels = dict(unmasked='Completa', remove1_largest_absolute_observation_influence='Retira 1', remove5_largest_absolute_observation_influence='Retira 5')
    for ticker in ['VULC3.SA','BBDC4.SA']:
        for diagnostic in diagnostics:
            row = critical[critical.ticker.eq(ticker) & critical.diagnostic.eq(diagnostic)].iloc[0]
            lines.append(f"{ticker.removesuffix('.SA')} & {labels[diagnostic]} & {row.delta:.3f} & {row.delta_shift:.3f} & [{row.ci_low:.3f}; {row.ci_high:.3f}]" + r'\\')
    lines.extend([r'\bottomrule', r'\end{tabular}'])
    (output/'casos_criticos.tex').write_text('\n'.join(lines)+'\n')
    report = dict(passed=True, scope='Read-only summaries of authenticated outputs; no re-estimation, no new financial observations, no redefinition of families.',
                  input_sha256=PINS, input_rows=dict(ledger=197,sensitivities=1970,metadata=277),
                  samples=dict(decade_assets=80,recent_assets=117,decade_issuers=76,recent_issuers=112),
                  copied_critical_rows=6, copied_primary_rows=197,
                  MC_designs=designs.groupby('kind').size().to_dict(),
                  MC_designs_total=len(designs),
                  post_mask_adjusted_significance='not_computed_not_claimed')
    (output/'verificacao.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(summarize(parser.parse_args().output), indent=2, ensure_ascii=False))

"""Same-input exploratory robustness suite; never a global data certification."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from lab02 import BENCHMARK, Config, GAPS, event_masks, fit_panel, holm
from lab02_analysis import block_diagnostic

VARIANTS = ('referencia_n', 'jcp_duas_celulas_documentadas', 'jcp_condicional',
            'jcp_rendimento_caixa_baixo', 'jcp_rendimento_caixa_alto')
SCENARIOS = ('decada', 'decada_periodo_comum', 'recente')
IDENTITY = ['ticker', 'papel_id', 'company_id', 'setor_economico']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_x(archive, lock):
    if sha(archive) != lock['x_results_sha256']:
        raise ValueError('X archive hash mismatch')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or any(n.startswith('/') or '..' in Path(n).parts for n in names):
            raise ValueError('Unsafe or duplicate archive entry')
        manifest = json.loads(z.read('manifesto_exports.json'))
        if set(names) != set(manifest) | {'manifesto_exports.json'}:
            raise ValueError('Unmanifested X entry')
        for rel, digest in manifest.items():
            if hashlib.sha256(z.read(rel)).hexdigest() != digest:
                raise ValueError('X output hash mismatch: ' + rel)
        record = json.loads(z.read('registro_execucao.json'))
        if record['environment'] != 'Colab' or not record['tests_successful'] or record['tests_run'] != 15:
            raise ValueError('Require the verified X Colab run')
        estimates = pd.read_csv(z.open('estimativas_1385.csv'))
        matrices = {v: {s: pd.read_csv(z.open(f'matrices/{v}/{s}/retornos_logaritmicos.csv.gz'),
                                     compression='gzip', index_col=0, parse_dates=True,
                                     float_precision='round_trip') for s in SCENARIOS} for v in VARIANTS}
    samples = {s: estimates.loc[estimates.variant.eq('referencia_n') & estimates.scenario.eq(s), IDENTITY]
               .rename(columns={'ticker': 'ticker_yahoo'}) for s in SCENARIOS}
    for v in VARIANTS:
        m = matrices[v]
        pd.testing.assert_frame_equal(m['decada'].loc['2021':'2025'], m['decada_periodo_comum'], check_exact=True)
        pd.testing.assert_frame_equal(m['decada_periodo_comum'], m['recente'][m['decada_periodo_comum'].columns], check_exact=True)
        for s, size in zip(SCENARIOS, (80, 80, 117)):
            x = m[s]
            if x.index.has_duplicates or not x.index.is_monotonic_increasing or x.columns.has_duplicates:
                raise ValueError('Invalid session/security grid')
            if samples[s].papel_id.nunique() != size or samples[s].setor_economico.nunique() != 10:
                raise ValueError('Changed fixed sample')
            if not x.isna().equals(matrices['referencia_n'][s].isna()):
                raise ValueError('Changed missing daily returns')
            pd.testing.assert_series_equal(x[BENCHMARK], matrices['referencia_n'][s][BENCHMARK], check_exact=True)
            for ticker, dates in GAPS.items():
                if ticker in x:
                    assert x.loc[x.index.intersection(pd.to_datetime(dates)), ticker].isna().all()
            assert x.loc['2024-10-30', 'LIGT3.SA'] == matrices['referencia_n'][s].loc['2024-10-30', 'LIGT3.SA']
    return matrices, samples, estimates


def add_families(table):
    """Each predeclared configuration has 197 exploratory slots, never 277."""
    table = table.copy()
    table['delta_p_holm_197'] = np.nan
    for _, group in table.groupby(['cash_variant', 'treatment'], sort=False):
        primary = group[group.scenario.ne('decada_periodo_comum')]
        if len(primary) != 197:
            raise ValueError('Expected 197 fixed primary hypotheses')
        adjusted = holm(primary.delta_p, family_size=197)
        table.loc[primary.index, 'delta_p_holm_197'] = adjusted
        recent = table.loc[primary.index][lambda x: x.scenario.eq('recente')].set_index('papel_id')
        common = group[group.scenario.eq('decada_periodo_comum')]
        if len(common) != 80:
            raise ValueError('Expected 80 common estimates')
        table.loc[common.index, 'delta_p_holm_197'] = common.papel_id.map(recent.delta_p_holm_197).to_numpy()
    return table


def check_common(table, keys):
    """Shared assets reuse the same data; check results and counts, not only IDs."""
    for _, group in table.groupby(keys, sort=False):
        a = group[group.scenario.eq('decada_periodo_comum')].set_index('papel_id').sort_index()
        b = group[group.scenario.eq('recente')].set_index('papel_id').loc[a.index]
        for col in ['beta', 'beta_plus', 'beta_minus', 'delta', 'delta_se', 'n_pairs', 'n_plus', 'n_minus']:
            np.testing.assert_allclose(a[col], b[col], rtol=0, atol=0, equal_nan=True)


def relative_changes(table, reference):
    names = ['beta', 'beta_plus', 'beta_minus', 'delta']
    ref = reference[['scenario', 'ticker'] + names].rename(columns={n: n + '_same_cash_log_reference' for n in names})
    out = table.merge(ref, on=['scenario', 'ticker'], validate='many_to_one')
    for name in names:
        out[name + '_change'] = out[name] - out[name + '_same_cash_log_reference']
    return out


def run(archive, lock, repetitions=999):
    matrices, samples, x = load_x(archive, lock)
    hac, simple, events, excluded = [], [], [], []
    for v in VARIANTS:
        reference = x[x.variant.eq(v)]
        for s in SCENARIOS:
            m, sample = matrices[v][s], samples[s]
            for lag in (0, 5, 10, 20):
                t = fit_panel(m, sample, s, replace(Config(), hac_lags=lag))
                t['cash_variant'], t['treatment'] = v, f'HAC{lag}'
                hac.append(t)
            transformed = np.expm1(m)
            assert transformed.isna().equals(m.isna())
            assert np.array_equal(np.sign(transformed[BENCHMARK]), np.sign(m[BENCHMARK]))
            t = fit_panel(transformed, sample, s)
            t['cash_variant'], t['treatment'] = v, 'simple_asset_and_market'
            simple.append(relative_changes(t, reference))
            for asset in sample.itertuples():
                for name, mask in event_masks(m.index, asset.ticker_yahoo).items():
                    subset = sample[sample.papel_id.eq(asset.papel_id)]
                    t = fit_panel(m, subset, s, masks={asset.ticker_yahoo: mask})
                    t['cash_variant'], t['treatment'] = v, name
                    events.append(relative_changes(t, reference))
                    if v == VARIANTS[0]:
                        excluded.extend(dict(scenario=s, ticker=asset.ticker_yahoo, treatment=name, date=str(date.date()))
                                        for date in m.index[~mask])
    hac, simple = add_families(pd.concat(hac, ignore_index=True)), add_families(pd.concat(simple, ignore_index=True))
    events = pd.concat(events, ignore_index=True)
    check_common(hac, ['cash_variant', 'treatment'])
    check_common(simple, ['cash_variant', 'treatment'])
    check_common(events, ['cash_variant', 'treatment', 'ticker'])
    for v in VARIANTS:
        for s in SCENARIOS:
            group = hac[hac.cash_variant.eq(v) & hac.scenario.eq(s)]
            ref = x[x.variant.eq(v) & x.scenario.eq(s)].set_index('ticker')
            for _, row in group.iterrows():
                for name in ['beta', 'beta_plus', 'beta_minus', 'delta']:
                    assert abs(row[name] - ref.loc[row.ticker, name]) < 1e-10
    panels = {s: {'sample': samples[s], 'log': matrices['referencia_n'][s]} for s in SCENARIOS}
    bootstrap = block_diagnostic(panels, x[x.variant.eq('referencia_n')], repetitions=repetitions,
                                 lengths=(5, 10, 20), seed=20261011)
    bootstrap['cash_variant'] = 'referencia_n'
    # Historical weekly/bootstrap results have different inputs. Do not relabel them as current.
    summaries = []
    for (v, treatment, s), g in hac.groupby(['cash_variant', 'treatment', 'scenario'], sort=False):
        summaries.append(dict(kind='HAC', cash_variant=v, treatment=treatment, scenario=s, assets=len(g),
                              eligible=int(g.status_conditional.eq('ok').sum()),
                              delta_median=float(g.delta.median()), delta_se_median=float(g.delta_se.median()),
                              holm_below_005=int((g.delta_p_holm_197 < .05).sum())))
    for kind, t in [('simple', simple), ('event', events)]:
        for (v, treatment, s), g in t.groupby(['cash_variant', 'treatment', 'scenario'], sort=False):
            summaries.append(dict(kind=kind, cash_variant=v, treatment=treatment, scenario=s, assets=len(g),
                                  eligible=int(g.status_conditional.eq('ok').sum()),
                                  max_absolute_delta_change=float(g.delta_change.abs().max()) if g.delta_change.notna().any() else np.nan))
    for (s, length), g in bootstrap.groupby(['scenario', 'block_length']):
        summaries.append(dict(kind='bootstrap', cash_variant='referencia_n', treatment=f'block{length}',
                              scenario=s, assets=len(g), eligible=int(g.status.eq('ok').sum()),
                              median_se_ratio=float((g.bootstrap_se / g.hac_se).median()),
                              minimum_accepted=int(g.accepted.min()), maximum_rejected=int(g.rejected.max())))
    metrics = dict(stage='Lab02Y', x_colab_verified=True, cash_variants=5, fixed_primary_cases=197,
                   common_cases_reused=80, hac_rows=len(hac), simple_rows=len(simple), event_rows=len(events),
                   bootstrap_rows=len(bootstrap), repetitions=repetitions, seed=20261011,
                   bootstrap_cash_variant='referencia_n',
                   event_insufficient=int(events.status_conditional.ne('ok').sum()),
                   source_archive_sha256=sha(archive), same_inputs_across_hac=True,
                   missing_values_filled=False, new_confirmatory_families=False,
                   weekly_reconstructed_from_daily=False, global_homologated=0, persistence_tested=False)
    return dict(hac=hac, simple=simple, events=events, bootstrap=bootstrap,
                exclusions=pd.DataFrame(excluded), summary=pd.DataFrame(summaries), metrics=metrics)

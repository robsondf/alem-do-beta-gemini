#!/usr/bin/env python3
"""Independent OLS/HAC and complete block bootstrap recalculation, no production imports."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd


def direct(y, m, include, lag):
    valid = include & np.isfinite(y) & np.isfinite(m)
    up, down = valid & (m > 0), valid & (m < 0)
    out = dict(n_pairs=int(valid.sum()), n_plus=int(up.sum()), n_minus=int(down.sum()))
    enough = (valid.sum() >= 200 and valid.sum() / include.sum() >= .95
              and up.sum() >= 60 and down.sum() >= 60)
    if not enough:
        return out, False
    def fit(x, mask):
        a = x[mask]
        b = np.linalg.lstsq(a, y[mask], rcond=None)[0]
        score = np.zeros_like(x)
        score[mask] = a * (y[mask] - a @ b)[:, None]
        meat = score.T @ score
        for k in range(1, lag + 1):
            cross = score[k:].T @ score[:-k]
            meat += (1 - k / (lag + 1)) * (cross + cross.T)
        bread = np.linalg.inv(a.T @ a)
        return b, (mask.sum() / (mask.sum() - a.shape[1])) * bread @ meat @ bread
    x = np.nan_to_num(m)
    b, c = fit(np.column_stack([np.ones(len(m)), x]), valid)
    d = (m > 0).astype(float)
    bc, cc = fit(np.column_stack([np.ones(len(m)), d, x, d * x]), up | down)
    for name, value, cov, contrast in [('beta', b[1], c, [0, 1]),
        ('beta_minus', bc[2], cc, [0, 0, 1, 0]), ('beta_plus', bc[2] + bc[3], cc, [0, 0, 1, 1]),
        ('delta', bc[3], cc, [0, 0, 0, 1])]:
        contrast = np.array(contrast)
        se = math.sqrt(float(contrast @ cov @ contrast))
        out.update({name: value, name + '_se': se, name + '_ci_low': value - 1.959963984540054 * se,
                    name + '_ci_high': value + 1.959963984540054 * se,
                    name + '_p': math.erfc(abs(value / se) / math.sqrt(2))})
    return out, True


def mask_for(index, ticker, treatment):
    if treatment.startswith('regime_'):
        lo, hi = {'regime_before_assai': ('2021-01-01', '2021-03-01'),
                  'regime_between_assai_exito': ('2021-03-01', '2023-08-23'),
                  'regime_after_exito': ('2023-08-23', '2026-01-01')}[treatment]
        return (index >= lo) & (index < hi)
    if treatment == 'without_preference_Q4_2024':
        return ~((index >= '2024-10-01') & (index <= '2024-12-31'))
    if '_year' in treatment:
        return index.year != int(treatment.rsplit('_year', 1)[1])
    event = treatment.removeprefix('without_').removesuffix('_plusminus5')
    lo, hi = {'direitos': ('2016-01-04', '2016-01-05'), 'extrafarma': ('2021-06-28', '2021-06-30'),
              'preferencia': ('2024-10-30', '2024-10-30'), 'assai': ('2021-03-01', '2021-03-01'),
              'exito': ('2023-08-23', '2023-08-23')}[event]
    mask = np.ones(len(index), bool)
    mask[max(0, index.searchsorted(lo) - 5):min(len(index), index.searchsorted(hi, side='right') + 5)] = False
    return mask


def batch_delta(y, m):
    valid = np.isfinite(y) & np.isfinite(m[:, None])
    total = valid.sum(axis=0)
    slopes = []
    for regime in [m > 0, m < 0]:
        ok = valid & regime[:, None]
        n = ok.sum(axis=0)
        count = np.maximum(n, 1)
        x, z = np.where(ok, m[:, None], 0.), np.where(ok, y, 0.)
        variance_sum = (x * x).sum(axis=0) - x.sum(axis=0) ** 2 / count
        covariance_sum = (x * z).sum(axis=0) - x.sum(axis=0) * z.sum(axis=0) / count
        enough = ((total >= 200) & (total / len(m) >= .95) & (n >= 60)
                  & (variance_sum / np.maximum(n - 1, 1) >= 1e-12))
        slopes.append(np.where(enough, covariance_sum / variance_sum, np.nan))
    return slopes[0] - slopes[1]


def validate(archive, output):
    with zipfile.ZipFile(archive) as z:
        matrices = {(v, s): pd.read_csv(z.open(n), compression='gzip', index_col=0,
                    parse_dates=True, float_precision='round_trip')
                    for n in z.namelist() if n.startswith('matrices/')
                    for _, v, s, _ in [n.split('/')]}
    table = {name: pd.read_csv(output / (name + '.csv')) for name in ['hac', 'simple', 'events', 'bootstrap']}
    maximum, fitted, insufficient = 0., 0, 0
    for kind in ['hac', 'simple', 'events']:
        for r in table[kind].itertuples():
            x = matrices[r.cash_variant, r.scenario]
            if kind == 'simple':
                x = np.expm1(x)
            include = mask_for(x.index, r.ticker, r.treatment) if kind == 'events' else np.ones(len(x), bool)
            values, enough = direct(x[r.ticker].to_numpy(), x['^BVSP'].to_numpy(), include, r.hac_lags)
            assert all(getattr(r, key) == value for key, value in values.items() if key.startswith('n_'))
            assert (r.status_conditional == 'ok') == enough
            if enough:
                fitted += 1
                for key, value in values.items():
                    if key.startswith('n_'):
                        continue
                    maximum = max(maximum, abs(getattr(r, key) - value))
                    assert np.isclose(getattr(r, key), value, rtol=1e-9, atol=1e-10), (kind, key)
            else:
                insufficient += 1
                assert np.isnan(r.delta) and np.isnan(r.delta_se)
        if kind != 'events':
            for _, g in table[kind].groupby(['cash_variant', 'treatment']):
                p = g[g.scenario.ne('decada_periodo_comum')]
                assert len(p) == 197
                order = np.argsort(p.delta_p, kind='stable')
                q = np.empty(197)
                q[order] = np.minimum(1, np.maximum.accumulate((197 - np.arange(197)) * p.delta_p.to_numpy()[order]))
                np.testing.assert_allclose(q, p.delta_p_holm_197, rtol=1e-10, atol=1e-12)
                recent = g[g.scenario.eq('recente')].set_index('papel_id')
                common = g[g.scenario.eq('decada_periodo_comum')].set_index('papel_id')
                for col in ['beta', 'delta', 'delta_se', 'delta_p_holm_197', 'n_pairs', 'n_plus', 'n_minus']:
                    np.testing.assert_allclose(common[col], recent.loc[common.index, col], atol=0, rtol=0)
    bootstrap_error = 0.
    repetitions = int(table['bootstrap'].repetitions.iloc[0])
    for s, offset in [('decada', 0), ('recente', 1)]:
        b = table['bootstrap'][table['bootstrap'].scenario.eq(s)]
        x = matrices['referencia_n', s]
        assets = b[b.block_length.eq(5)].sort_values('papel_id').ticker.tolist()
        y, m = x[assets].to_numpy(), x['^BVSP'].to_numpy()
        original = batch_delta(y, m)
        for length in [5, 10, 20]:
            rng = np.random.default_rng(np.random.SeedSequence([20261011, offset, length]))
            draws = np.empty((repetitions, len(assets)))
            for rep in range(repetitions):
                starts = rng.integers(0, len(m) - length + 1, size=math.ceil(len(m) / length))
                idx = (starts[:, None] + np.arange(length)).ravel()[:len(m)]
                draws[rep] = batch_delta(y[idx], m[idx])
            for j, ticker in enumerate(assets):
                row = b[b.block_length.eq(length) & b.ticker.eq(ticker)].iloc[0]
                values = draws[:, j][np.isfinite(draws[:, j])]
                assert len(values) == row.accepted and repetitions - len(values) == row.rejected
                assert len(values) >= max(99, math.ceil(.95 * repetitions))
                expected = dict(delta=original[j], bootstrap_se=values.std(ddof=1),
                                bootstrap_bias=values.mean() - original[j],
                                delta_percentile_low=np.quantile(values, .025),
                                delta_percentile_high=np.quantile(values, .975))
                for key, value in expected.items():
                    bootstrap_error = max(bootstrap_error, abs(row[key] - value))
                    assert np.isclose(row[key], value, rtol=1e-9, atol=1e-10), key
    b = table['bootstrap']
    a = b[b.scenario.eq('decada_periodo_comum')].set_index(['papel_id', 'block_length']).sort_index()
    c = b[b.scenario.eq('recente')].set_index(['papel_id', 'block_length']).loc[a.index]
    for col in ['delta', 'bootstrap_se', 'bootstrap_bias', 'delta_percentile_low', 'delta_percentile_high', 'accepted', 'rejected']:
        np.testing.assert_allclose(a[col], c[col], rtol=0, atol=0)
    return dict(direct_daily_rows=fitted, insufficient_rows_verified=insufficient,
                daily_max_absolute_difference=maximum, bootstrap_rows_verified=len(b),
                bootstrap_replicates_recomputed=2 * 3 * repetitions,
                bootstrap_max_absolute_difference=bootstrap_error,
                source_modules_imported=False, global_homologated=0, persistence_tested=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.archive, args.output), indent=2))

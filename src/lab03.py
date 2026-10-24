"""Conditional temporal tests on authenticated observed returns; no global certification."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import norm

from lab02 import BENCHMARK, Config, estimate_security, event_masks, holm, ols_hac, _uncertainty
from lab02_robustness_suite import load_x

SCENARIOS = ('decada', 'decada_periodo_comum', 'recente')
COEFFICIENTS = ('beta', 'beta_plus', 'beta_minus', 'delta')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs(root, x_archive, y_archive):
    lock = json.loads((root / 'data/lab03/inputs_manifest.json').read_text())
    for rel, digest in lock['repo_files'].items():
        if sha(root / rel) != digest:
            raise ValueError('Repository input hash mismatch: ' + rel)
    receipt = json.loads((root / 'data/lab02/validacao_lab02y_colab_20261023.json').read_text())
    if not receipt['colab_execution_verified'] or receipt['exceptions'] != 0 or receipt['tests'] != 8:
        raise ValueError('Y must have its own verified execution')
    if sha(y_archive) != lock['y_results_sha256']:
        raise ValueError('Y archive hash mismatch')
    with zipfile.ZipFile(y_archive) as z:
        manifest = json.loads(z.read('manifesto_exports.json'))
        if len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) != set(manifest) | {'manifesto_exports.json'}:
            raise ValueError('Unmanifested or duplicated Y entry')
        for name, digest in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError('Y output hash mismatch: ' + name)
        execution = json.loads(z.read('registro_execucao.json'))
        if execution['environment'] != 'Colab' or not execution['tests_successful'] or execution['tests_run'] != 8:
            raise ValueError('Require the saved Y Colab output')
    y_lock = json.loads((root / 'data/lab02/lab02y_inputs_manifest.json').read_text())
    matrices, samples, reference = load_x(x_archive, y_lock)
    if execution['input_x_sha256'] != sha(x_archive):
        raise ValueError('X/Y lineage mismatch')
    plan = json.loads((root / 'data/lab03/plano_execucao_v1.json').read_text())
    if plan['family_size'] != 474 or plan['annual_minimum'] != vars(Config()):
        raise ValueError('Frozen temporal inference changed')
    return matrices, samples, reference, plan


def combined_event_mask(index, ticker):
    """Union of previously defined ±5-session masks and Light Q4; no year deletion."""
    include = np.ones(len(index), bool)
    for name, mask in event_masks(index, ticker).items():
        if name.endswith('_plusminus5') or name == 'without_preference_Q4_2024':
            include &= np.asarray(mask)
    return include


def joint_halves(asset, market, config=Config(), include=None):
    pd.testing.assert_index_equal(asset.index, market.index)
    if not asset.index.is_monotonic_increasing or asset.index.has_duplicates:
        raise ValueError('Unsorted/duplicate calendar')
    y, m = asset.to_numpy(float), market.to_numpy(float)
    include = np.ones(len(m), bool) if include is None else np.asarray(include, bool)
    if include.shape != m.shape:
        raise ValueError('Invalid calendar mask')
    late = asset.index.year >= 2021
    result = dict(hac_lags=config.hac_lags, confidence=config.confidence, parameters=8)
    halves = []
    for name, mask in [('early', ~late), ('late', late)]:
        fit = estimate_security(asset, market, config, include & mask)
        halves.append(fit)
        result.update({name + '_' + key: value for key, value in fit.items()
                       if key in ['n_sessions', 'n_pairs', 'n_plus', 'n_minus', 'n_neutral', 'coverage',
                                  'status_conditional', 'delta', 'delta_se', 'beta_plus', 'beta_minus']})
    result.update(status='insufficient_segment', theta=np.nan, theta_se=np.nan, theta_p=np.nan,
                  theta_ci_low=np.nan, theta_ci_high=np.nan,
                  early_delta_joint=np.nan, late_delta_joint=np.nan,
                  cross_covariance_early_late=np.nan, covariance_identity_error=np.nan)
    if not all(h['status_conditional'] == 'ok' for h in halves):
        return result
    valid = include & np.isfinite(y) & np.isfinite(m) & (m != 0)
    d, q, x = (m > 0).astype(float), late.astype(float), np.nan_to_num(m)
    design = np.column_stack([np.ones(len(m)), d, x, d*x, q, q*d, q*x, q*d*x])
    coefficients, covariance = ols_hac(y, design, valid, config.hac_lags)
    early, late_delta = coefficients[3], coefficients[3] + coefficients[7]
    if not np.allclose([early, late_delta], [h['delta'] for h in halves], rtol=1e-9, atol=1e-10):
        raise ArithmeticError('Joint model differs from separate halves')
    early_contrast, late_contrast = np.eye(8)[3], np.eye(8)[3] + np.eye(8)[7]
    cross = float(early_contrast @ covariance @ late_contrast)
    identity = float(early_contrast @ covariance @ early_contrast + late_contrast @ covariance @ late_contrast - 2*cross)
    result.update(status='ok', n_model=int(valid.sum()), early_delta_joint=float(early), late_delta_joint=float(late_delta),
                  cross_covariance_early_late=cross, covariance_identity_error=abs(identity-covariance[7, 7]),
                  temporal_interpretation='conditional_difference_not_equivalence_or_causal_break')
    _uncertainty(result, 'theta', coefficients[7], covariance, np.eye(8)[7], config.confidence)
    return result


def direction_rows(annual, scenario, expected_years):
    rows = []
    group = annual[annual.scenario.eq(scenario)]
    for papel, asset in group.groupby('papel_id', sort=False):
        if sorted(asset.year.tolist()) != list(expected_years):
            raise ValueError('Do not discard an annual hypothesis')
        good = (asset.status_conditional.eq('ok') & np.isfinite(asset.delta) & np.isfinite(asset.delta_se)
                & asset.delta_se.gt(1e-14))
        z = asset.delta / asset.delta_se
        for direction, probabilities in [('positive', norm.sf(z)), ('negative', norm.cdf(z))]:
            rows.append(dict(scenario=scenario, ticker=asset.ticker.iloc[0], papel_id=papel,
                             company_id=asset.company_id.iloc[0], setor_economico=asset.setor_economico.iloc[0],
                             test='direction_all_years', direction=direction, years_required=len(expected_years),
                             years_eligible=int(good.sum()), status='ok' if good.all() else 'insufficient_annual_component',
                             p_raw=float(np.max(probabilities)) if good.all() else np.nan,
                             delta_min=float(asset.delta.min()), delta_max=float(asset.delta.max()),
                             annual_years=','.join(map(str, expected_years))))
    return rows


def temporal_family(annual, halves):
    rows = []
    for h in halves.itertuples():
        rows.append(dict(scenario='decada', ticker=h.ticker, papel_id=h.papel_id,
                         company_id=h.company_id, setor_economico=h.setor_economico,
                         test='magnitude_late_minus_early', direction='two_sided',
                         status=h.status, p_raw=h.theta_p, theta=h.theta, theta_se=h.theta_se,
                         theta_ci_low=h.theta_ci_low, theta_ci_high=h.theta_ci_high))
    rows += direction_rows(annual, 'decada', range(2016, 2026))
    rows += direction_rows(annual, 'recente', range(2021, 2026))
    result = pd.DataFrame(rows)
    if len(result) != 474 or len(halves) != 80:
        raise ValueError('Expected 80 + 2*(80+117) temporal hypotheses')
    result['p_holm_474'] = holm(result.p_raw, family_size=474)
    result['reject_005_conditional'] = result.p_holm_474.lt(.05) & result.p_holm_474.notna()
    result['scope'] = 'observed_reference_conditional_not_global_homologation_not_independent_preregistration'
    common_ids = set(annual.loc[annual.scenario.eq('decada_periodo_comum'), 'papel_id'])
    common = result[result.scenario.eq('recente') & result.papel_id.isin(common_ids)].copy()
    common['scenario'] = 'decada_periodo_comum'
    if len(common) != 160:
        raise ValueError('Expected reused directions for 80 common assets')
    return result, common


def annual_and_halves(matrices, samples, config_spec):
    cfg = replace(Config(), hac_lags=config_spec['hac_lags'])
    source = matrices[config_spec['cash_variant']]
    annual, halves = [], []
    for scenario in ['decada', 'recente']:
        matrix = source[scenario]
        if config_spec['return'] == 'simple':
            matrix = np.expm1(matrix)
        for asset in samples[scenario].itertuples():
            ticker = asset.ticker_yahoo
            identity = dict(ticker=ticker, papel_id=asset.papel_id, company_id=asset.company_id,
                            setor_economico=asset.setor_economico)
            mask = combined_event_mask(matrix.index, ticker) if config_spec['events'] else np.ones(len(matrix), bool)
            for year in range(2016 if scenario == 'decada' else 2021, 2026):
                selected = matrix.index.year == year
                fit = estimate_security(matrix.loc[selected, ticker], matrix.loc[selected, BENCHMARK], cfg, mask[selected])
                annual.append(dict(fit, **identity, scenario=scenario, year=year))
            if scenario == 'decada':
                fit = joint_halves(matrix[ticker], matrix[BENCHMARK], cfg, mask)
                halves.append(dict(fit, **identity))
    annual = pd.DataFrame(annual)
    ids = set(samples['decada_periodo_comum'].papel_id)
    common = annual[annual.scenario.eq('recente') & annual.papel_id.isin(ids)].copy()
    common['scenario'] = 'decada_periodo_comum'
    annual = pd.concat([annual, common], ignore_index=True)
    for year in range(2021, 2026):
        a = annual[annual.scenario.eq('decada') & annual.year.eq(year)].set_index('papel_id').sort_index()
        b = common[common.year.eq(year)].set_index('papel_id').loc[a.index]
        for name in list(COEFFICIENTS) + ['delta_se', 'n_pairs', 'n_plus', 'n_minus']:
            np.testing.assert_allclose(a[name], b[name], rtol=0, atol=0, equal_nan=True)
    return annual, pd.DataFrame(halves)


def rolling(matrices, samples, progress=print):
    rows = []
    for scenario in ['decada', 'recente']:
        m = matrices['referencia_n'][scenario]
        for width in [252, 504]:
            for number, start in enumerate(range(0, len(m)-width+1, 21)):
                window = m.iloc[start:start+width]
                for asset in samples[scenario].itertuples():
                    fit = estimate_security(window[asset.ticker_yahoo], window[BENCHMARK])
                    rows.append(dict(fit, scenario=scenario, ticker=asset.ticker_yahoo, papel_id=asset.papel_id,
                                     company_id=asset.company_id, setor_economico=asset.setor_economico,
                                     width=width, step=21, window_start=str(window.index[0].date()),
                                     window_end=str(window.index[-1].date()), scope='overlapping_exploratory_not_independent_tests'))
                if number % 20 == 0:
                    progress(f'Janelas móveis {scenario}, largura {width}: {number+1} janelas calculadas', flush=True)
    result = pd.DataFrame(rows)
    ids = set(samples['decada_periodo_comum'].papel_id)
    common = result[result.scenario.eq('recente') & result.papel_id.isin(ids)].copy()
    common['scenario'] = 'decada_periodo_comum'
    return pd.concat([result, common], ignore_index=True)


def run(root, x_archive, y_archive, progress=print):
    matrices, samples, reference, plan = load_inputs(root, x_archive, y_archive)
    annual_rows, half_rows, family_rows, common_rows = [], [], [], []
    for position, spec in enumerate(plan['configurations']):
        progress(f'Configuração temporal {position+1}/{len(plan["configurations"])}: {spec["name"]}', flush=True)
        annual, halves = annual_and_halves(matrices, samples, spec)
        family, common = temporal_family(annual, halves)
        for table, target in [(annual, annual_rows), (halves, half_rows), (family, family_rows), (common, common_rows)]:
            table['configuration'] = spec['name']
            target.append(table)
    annual, halves, families, common = [pd.concat(t, ignore_index=True) for t in [annual_rows, half_rows, family_rows, common_rows]]
    windows = rolling(matrices, samples, progress)
    summary = families.groupby(['configuration', 'test', 'scenario', 'direction'], sort=False).agg(
        hypotheses=('p_raw', 'size'), estimable=('p_raw', 'count'),
        holm_below_005=('reject_005_conditional', 'sum')).reset_index()
    metrics = dict(stage='Lab03', source_x_sha256=sha(x_archive), source_y_sha256=sha(y_archive),
                   configurations=len(plan['configurations']), annual_rows=len(annual), joint_half_rows=len(halves),
                   temporal_family_rows=len(families), family_size_per_configuration=474,
                   common_direction_rows_reused=len(common), rolling_rows=len(windows),
                   missing_values_filled=False, global_homologated=0,
                   temporal_tests_computed=True, temporal_interpretation='conditional_on_observed_reference',
                   independently_preregistered=False, equivalence_tested=False,
                   future_persistence_tested=False, confirmatory_global_data_gate_passed=False)
    return dict(annual=annual, halves=halves, temporal_family=families, common_directions=common,
                rolling=windows, summary=summary, metrics=metrics)

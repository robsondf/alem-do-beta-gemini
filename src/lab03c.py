"""Fixed-design Monte Carlo for static conditional-beta inference, not market data."""
from pathlib import Path
import hashlib, io, json, zipfile
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm

Z = norm.ppf(.975)
LAGS = (0, 5, 20)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def archive(path, digest):
    if sha(path) != digest:
        raise ValueError('Input archive SHA mismatch')
    z = zipfile.ZipFile(path)
    manifest = json.loads(z.read('manifesto_exports.json'))
    if len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) != set(manifest) | {'manifesto_exports.json'}:
        raise ValueError('Incomplete/duplicate archive')
    for name, value in manifest.items():
        if name.startswith('/') or '..' in Path(name).parts or hashlib.sha256(z.read(name)).hexdigest() != value:
            raise ValueError('Invalid export: ' + name)
    return z


def kernel(m, valid):
    """Contrast influence weights; scores remain on the original session grid."""
    masks = [valid & (m[:, None] > 0), valid & (m[:, None] < 0)]
    pieces = []
    for mask in masks:
        n = mask.sum(axis=0)
        mean = np.where(mask, m[:, None], 0).sum(axis=0) / n
        center = np.where(mask, m[:, None] - mean, 0)
        ss = (center * center).sum(axis=0)
        if (n < 60).any() or (ss / (n - 1) < 1e-12).any():
            raise ValueError('Insufficient regime')
        pieces.append((mask, n, mean, center / ss))
    count = masks[0].sum(axis=0) + masks[1].sum(axis=0)
    if (valid.sum(axis=0) < 200).any() or (valid.mean(axis=0) < .95).any():
        raise ValueError('Insufficient pair coverage')
    return dict(m=m, valid=masks[0] | masks[1], plus=pieces[0], minus=pieces[1],
                weights=pieces[0][3] - pieces[1][3], correction=count / (count - 4))


def project(noise, k, lags=LAGS):
    y = np.where(k['valid'], noise, 0)
    fitted = np.zeros_like(y)
    for mask, n, mean, weight in [k['plus'], k['minus']]:
        slope = (weight * y).sum(axis=0)
        intercept = np.where(mask, y, 0).sum(axis=0) / n - slope * mean
        fitted += np.where(mask, intercept + slope * k['m'][:, None], 0)
    residual = np.where(k['valid'], y - fitted, 0)
    score = k['weights'] * residual
    delta = (k['weights'] * y).sum(axis=0)
    zero = np.einsum('ij,ij->j', score, score)
    cross = [np.einsum('ij,ij->j', score[h:], score[:-h]) for h in range(1, max(lags) + 1)]
    variances = []
    for lag in lags:
        v = zero.copy()
        for h in range(1, lag + 1):
            v += 2 * (1 - h / (lag + 1)) * cross[h - 1]
        v *= k['correction']
        if (v < -1e-12).any():
            raise ArithmeticError('Negative HAC variance')
        variances.append(np.sqrt(np.maximum(v, 0)))
    return delta, np.asarray(variances)


def holm_rows(p):
    """Holm step-down on each full197 row, including dependent hypotheses."""
    order = np.argsort(p, axis=1, kind='stable')
    sorted_p = np.take_along_axis(p, order, axis=1)
    adjusted = np.minimum(1, np.maximum.accumulate(sorted_p * np.arange(p.shape[1], 0, -1), axis=1))
    return np.take_along_axis(adjusted, np.argsort(order, axis=1), axis=1)


def probability(events):
    """Bernoulli mean, Monte Carlo SE, Wilson95 bounds; works at zero/one."""
    r = len(events); p = np.asarray(events, float).mean(axis=0)
    se = np.sqrt(p * (1 - p) / r)
    center = (p + Z * Z / (2 * r)) / (1 + Z * Z / r)
    radius = Z * np.sqrt(p * (1 - p) / r + Z * Z / (4 * r * r)) / (1 + Z * Z / r)
    return p, se, np.maximum(0, center - radius), np.minimum(1, center + radius)


def panel_rate(events):
    if events.shape[1] == 0:
        return np.nan, np.nan
    rates = events.mean(axis=1)
    return float(rates.mean()), float(rates.std(ddof=1) / np.sqrt(len(rates)))


def prepare(x_archive, b_archive, lock):
    with archive(b_archive, lock['b_sha256']) as z:
        meta = pd.read_csv(z.open('asset_betas.csv'))
        if json.loads(z.read('registro_execucao.json'))['environment'] != 'Colab':
            raise ValueError('Require saved actual Colab')
    with archive(x_archive, lock['x_sha256']) as z:
        mats = {s: pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),
                              compression='gzip', index_col=0, parse_dates=True, float_precision='round_trip')
                for s in ['decada', 'recente']}
    dm, rm = mats['decada'], mats['recente']
    recent = meta[meta.scenario.eq('recente')].sort_values('papel_id').reset_index(drop=True)
    decade = meta[meta.scenario.eq('decada')].sort_values('papel_id').reset_index(drop=True)
    if (len(recent), len(decade), recent.setor_economico.nunique(), decade.setor_economico.nunique()) != (117, 80, 10, 10):
        raise ValueError('Fixed samples changed')
    pd.testing.assert_frame_equal(dm.loc[rm.index], rm[dm.columns], check_exact=True)
    if dm.index.has_duplicates or rm.index.has_duplicates or dm.isna().sum().sum() != 7 or rm.isna().sum().sum() != 7:
        raise ValueError('Calendar/missing mask changed')
    ids = list(recent.papel_id); long_ids = set(decade.papel_id); nuisance = []
    for row in recent.itertuples():
        s = 'decada' if row.papel_id in long_ids else 'recente'
        a = mats[s]; ok = a[row.ticker].notna() & a['^BVSP'].notna()
        y, m = a.loc[ok, row.ticker].to_numpy(), a.loc[ok, '^BVSP'].to_numpy()
        coef = np.linalg.lstsq(np.column_stack([np.ones(len(m)), m]), y, rcond=None)[0]
        sigma = np.sqrt(np.sum((y - coef[0] - coef[1] * m) ** 2) / (len(m) - 2))
        nuisance.append(dict(papel_id=row.papel_id, ticker=row.ticker, setor_economico=row.setor_economico,
                             calibration_period=s, beta_base=coef[1], sigma=sigma, n_calibration=len(m)))
    nuisance = pd.DataFrame(nuisance); panels = []; design = []
    for s, sample in [('decada', decade), ('recente', recent)]:
        a = mats[s]; m = a['^BVSP'].to_numpy(); valid = np.isfinite(a[sample.ticker].to_numpy()) & np.isfinite(m[:, None])
        k = kernel(m, valid); asset_index = np.array([ids.index(p) for p in sample.papel_id])
        time_index = dm.index.get_indexer(a.index)
        panels.append(dict(scenario=s, kernel=k, sample=sample, asset_index=asset_index, time_index=time_index))
        for j, row in enumerate(sample.itertuples()):
            counts = (int(valid[:, j].sum()), int(k['plus'][1][j]), int(k['minus'][1][j]))
            if counts != (row.n_pairs, row.n_plus, row.n_minus):
                raise ValueError('Counts differ from actual execution')
            design.append(dict(scenario=s, papel_id=row.papel_id, ticker=row.ticker,
                               setor_economico=row.setor_economico, master_asset_index=int(asset_index[j]),
                               n_sessions=len(m), n_pairs=counts[0], n_plus=counts[1], n_minus=counts[2],
                               n_missing=int((~valid[:, j]).sum()), conditional_n=int(k['valid'][:, j].sum()),
                               valid_mask_sha256=hashlib.sha256(valid[:, j].tobytes()).hexdigest()))
    market = dm['^BVSP'].to_numpy()
    h = np.sqrt(.5 + .5 * np.r_[market[0], market[:-1]] ** 2 / np.mean(market ** 2))
    h /= np.sqrt(np.mean(h ** 2))
    return dict(panels=panels, design=pd.DataFrame(design), nuisance=nuisance, market=market, scale=h)


def draw_errors(d, mechanism_index, replication_index, plan):
    spec = plan['mechanisms'][mechanism_index]
    rng = np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'], mechanism_index, replication_index]))
    shape = (len(d['market']) + 256, 118)
    z = rng.standard_normal(shape) if mechanism_index == 0 else rng.standard_t(5, shape) * np.sqrt(3 / 5)
    innovation = np.sqrt(.3) * z[:, :1] + np.sqrt(.7) * z[:, 1:]
    phi = spec['phi']
    u = lfilter([np.sqrt(1 - phi * phi)], [1, -phi], innovation, axis=0)[256:]
    h = d['scale'] if spec['heteroscedastic'] else np.ones(len(u))
    return u * h[:, None] * d['nuisance'].sigma.to_numpy()


def patterns(design, nuisance, plan):
    out = [(f'dense_{v:+.2f}', np.full(len(design), v)) for v in plan['effect_patterns']['dense_delta']]
    selected = set(nuisance.papel_id[:12])
    for v in plan['effect_patterns']['sparse_delta']:
        out.append((f'sparse_{v:+.2f}', np.where(design.papel_id.isin(selected), v, 0)))
    return out


def simulate(d, plan, progress=print):
    r = plan['replications']; error = np.empty((3, r, 197)); se = np.empty((3, 3, r, 197))
    for mi, spec in enumerate(plan['mechanisms']):
        for ri in range(r):
            noise = draw_errors(d, mi, ri, plan); offset = 0
            for panel in d['panels']:
                values = noise[np.ix_(panel['time_index'], panel['asset_index'])]
                delta, scale = project(values, panel['kernel'])
                c = len(delta); error[mi, ri, offset:offset+c] = delta
                se[mi, :, ri, offset:offset+c] = scale; offset += c
            if ri % 100 == 99:
                progress(f"{spec['name']}: {ri+1}/{r} réplicas, todos197 casos", flush=True)
    if not np.isfinite(error).all() or not np.isfinite(se).all() or (se <= 1e-14).any():
        raise ArithmeticError('Degenerate simulation; no rows discarded or redrawn')
    return error, se


def analyze(d, plan, error, se):
    design = d['design']; calibration = []; power = []; panels = []; families = []
    for mi, spec in enumerate(plan['mechanisms']):
        errors = error[mi]
        for li, lag in enumerate(LAGS):
            scales = se[mi, li]; covered = np.abs(errors) <= Z * scales
            cov = probability(covered)
            for j, row in enumerate(design.to_dict('records')):
                calibration.append(dict(**row, mechanism=spec['name'], method=f'HAC{lag}',
                    bias=float(errors[:, j].mean()), bias_mcse=float(errors[:, j].std(ddof=1)/np.sqrt(len(errors))),
                    rmse=float(np.sqrt(np.mean(errors[:, j] ** 2))), empirical_se=float(errors[:, j].std(ddof=1)),
                    mean_model_se=float(scales[:, j].mean()), coverage=cov[0][j],
                    coverage_mcse=cov[1][j], coverage_mc_low=cov[2][j], coverage_mc_high=cov[3][j]))
            for pattern, truth in patterns(design, d['nuisance'], plan):
                p = 2 * norm.sf(np.abs((errors + truth) / scales))
                raw = p < .05; adjusted = holm_rows(p) < .05
                a, b = probability(raw), probability(adjusted)
                null = truth == 0; nonnull = ~null
                for j, row in enumerate(design.to_dict('records')):
                    power.append(dict(scenario=row['scenario'], papel_id=row['papel_id'],
                        mechanism=spec['name'], method=f'HAC{lag}', pattern=pattern, true_delta=truth[j],
                        is_true_null=bool(null[j]), raw_rejection=a[0][j], raw_mcse=a[1][j],
                        raw_mc_low=a[2][j], raw_mc_high=a[3][j], holm_rejection=b[0][j],
                        holm_mcse=b[1][j], holm_mc_low=b[2][j], holm_mc_high=b[3][j]))
                f = dict(mechanism=spec['name'], method=f'HAC{lag}', pattern=pattern,
                         null_cases=int(null.sum()), nonnull_cases=int(nonnull.sum()))
                for name, events in [('fwer_raw', raw[:, null].any(axis=1)), ('fwer_holm', adjusted[:, null].any(axis=1))]:
                    vals = probability(events) if null.any() else [np.nan]*4
                    f.update(zip([name, name+'_mcse', name+'_mc_low', name+'_mc_high'], [float(x) for x in vals]))
                f['power_holm'], f['power_holm_mcse'] = panel_rate(adjusted[:, nonnull])
                families.append(f)
                for scenario in ['decada', 'recente']:
                    ix = design.scenario.eq(scenario).to_numpy()
                    item = dict(mechanism=spec['name'], method=f'HAC{lag}', pattern=pattern, scenario=scenario,
                                assets=int(ix.sum()), null_cases=int((ix & null).sum()), nonnull_cases=int((ix & nonnull).sum()))
                    for name, ev, mask in [('coverage', covered, ix), ('power_raw', raw, ix & nonnull),
                                          ('power_holm', adjusted, ix & nonnull), ('type1_raw', raw, ix & null),
                                          ('type1_holm', adjusted, ix & null)]:
                        item[name], item[name+'_mcse'] = panel_rate(ev[:, mask])
                    panels.append(item)
    return dict(calibration=pd.DataFrame(calibration), power=pd.DataFrame(power),
                panel_summary=pd.DataFrame(panels), family=pd.DataFrame(families))

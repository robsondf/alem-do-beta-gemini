"""Fixed-asset sector descriptions and observed-return risk; no CAPM pricing test."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

import numpy as np
import pandas as pd

from lab02 import BENCHMARK
from lab02_analysis import _batch_slopes, moving_block_indices
from lab02_robustness_suite import load_x
from lab02 import Config

SCENARIOS = ('decada', 'decada_periodo_comum', 'recente')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def authenticated_zip(path, expected):
    if sha(path) != expected:
        raise ValueError('Archive hash mismatch')
    z = zipfile.ZipFile(path)
    names = z.namelist()
    manifest = json.loads(z.read('manifesto_exports.json'))
    if len(names) != len(set(names)) or set(names) != set(manifest) | {'manifesto_exports.json'}:
        raise ValueError('Incomplete/duplicate manifest')
    for name, digest in manifest.items():
        if name.startswith('/') or '..' in Path(name).parts or hashlib.sha256(z.read(name)).hexdigest() != digest:
            raise ValueError('Invalid archive member')
    return z


def load(root, x, y, temporal):
    lock = json.loads((root/'data/lab03b/inputs_manifest.json').read_text())
    for name, digest in lock['repo_files'].items():
        if sha(root/name) != digest:
            raise ValueError('Changed repository input: '+name)
    receipt = json.loads((root/'data/lab03/validacao_colab_20261023.json').read_text())
    if not receipt['colab_execution_verified'] or receipt['tests'] != 14:
        raise ValueError('Require the verified Lab03 execution')
    matrices, samples, estimates = load_x(x, json.loads((root/'data/lab02/lab02y_inputs_manifest.json').read_text()))
    with authenticated_zip(y, lock['y_sha256']) as z:
        bootstrap = pd.read_csv(z.open('bootstrap.csv'))
        h = pd.read_csv(z.open('hac.csv'))
        baseline = h[h.cash_variant.eq('referencia_n') & h.treatment.eq('HAC5')].copy()
    with authenticated_zip(temporal, lock['lab03_sha256']) as z:
        annual = pd.read_csv(z.open('annual.csv'))
        annual = annual[annual.configuration.eq('N_log_HAC5')].copy()
        if json.loads(z.read('registro_execucao.json'))['environment'] != 'Colab':
            raise ValueError('Expected saved temporal Colab')
    if len(baseline) != 277 or len(annual) != 1785:
        raise ValueError('Changed fixed cases')
    return matrices, samples, baseline, annual, bootstrap


def empirical_loss_tail(log_returns, confidence=.95):
    """Signed simple losses, inverse-EDF VaR and fractional-mass upper-tail ES."""
    x = np.asarray(log_returns, float)
    x = x[np.isfinite(x)]
    if not len(x) or not 0 < confidence < 1:
        raise ValueError('Empty tail sample or invalid confidence')
    losses = -np.expm1(x)
    mass = (1-confidence)*len(x)
    k = int(np.floor(mass))
    ordered = np.sort(losses)[::-1]
    es = (ordered[:k].sum() + (mass-k)*ordered[min(k, len(x)-1)]) / mass
    return dict(var95_simple_loss=float(np.quantile(losses, confidence, method='inverted_cdf')),
                es95_simple_loss=float(es), tail_mass_observations=float(mass))


def risk(asset, market):
    pd.testing.assert_index_equal(asset.index, market.index)
    valid = np.isfinite(asset.to_numpy(float)) & np.isfinite(market.to_numpy(float))
    y, m = asset.to_numpy(float)[valid], market.to_numpy(float)[valid]
    out = dict(n_sessions=len(asset), n_pairs=len(y), n_missing=len(asset)-len(y),
               n_plus=int((m>0).sum()), n_minus=int((m<0).sum()), n_neutral=int((m==0).sum()),
               coverage=len(y)/len(asset), status='insufficient')
    if len(y) < 200 or out['coverage'] < .95 or np.var(m, ddof=1) < 1e-12:
        return out
    yc, mc = y-y.mean(), m-m.mean()
    beta = float(yc@mc/(mc@mc))
    residual = yc-beta*mc
    total = float(yc@yc/(len(y)-1))
    associated = float(beta**2*(mc@mc)/(len(y)-1))
    remaining = float(residual@residual/(len(y)-1))
    out.update(status='ok', beta_market_model=beta, intercept_market_model=float(y.mean()-beta*m.mean()),
               log_mean_daily=float(y.mean()), log_std_daily=float(np.sqrt(total)),
               market_log_std_paired=float(m.std(ddof=1)), residual_log_std_daily=float(np.sqrt(remaining)),
               total_log_variance=total, market_associated_log_variance=associated,
               residual_log_variance=remaining, variance_identity_error=abs(total-associated-remaining),
               r2_market_model=associated/total if total>0 else np.nan,
               downside_log_deviation_zero=float(np.sqrt(np.mean(np.minimum(y, 0)**2))),
               negative_asset_days=int((y<0).sum()),
               scope='descriptive_observed_returns_not_CAPM_pricing_or_risk_forecast', **empirical_loss_tail(y))
    return out


def eta_squared(delta, sectors):
    delta, sectors = np.asarray(delta, float), np.asarray(sectors)
    if not np.isfinite(delta).all():
        return np.nan
    total = float(np.sum((delta-delta.mean())**2))
    if total <= 1e-24:
        return np.nan
    between = sum(np.sum(sectors==s)*(delta[sectors==s].mean()-delta.mean())**2 for s in np.unique(sectors))
    return float(between/total)


def sector_descriptions(baseline):
    rows=[]
    for scenario, group in baseline.groupby('scenario', sort=False):
        for sector, g in group.groupby('setor_economico', sort=True):
            other=group[group.setor_economico.ne(sector)].delta
            rows.append(dict(scenario=scenario, setor_economico=sector, assets=len(g),
                delta_median=float(g.delta.median()), delta_q25=float(g.delta.quantile(.25)),
                delta_q75=float(g.delta.quantile(.75)), beta_median=float(g.beta.median()),
                beta_plus_median=float(g.beta_plus.median()), beta_minus_median=float(g.beta_minus.median()),
                negative_delta_assets=int(g.delta.lt(0).sum()), static_holm_below005=int(g.delta_p_holm_197.lt(.05).sum()),
                median_sector_minus_complement=float(g.delta.median()-other.median()),
                eta2_all_assets=eta_squared(group.delta, group.setor_economico),
                interpretation='asset_distribution_summary_not_sector_portfolio_or_population_effect'))
    return pd.DataFrame(rows)


def bootstrap_sectors(matrices, samples, baseline, y_bootstrap, repetitions=999, progress=print):
    """Reuse Y seeds/draws. Fixed assets; shared calendar blocks; marginal diagnostics."""
    intervals, eta_rows, checks=[], [], []
    cache={}
    for scenario, offset in [('decada',0), ('recente',1)]:
        matrix=matrices['referencia_n'][scenario]
        sample=samples[scenario].sort_values('papel_id').reset_index(drop=True)
        y=matrix[sample.ticker_yahoo].to_numpy(float); m=matrix[BENCHMARK].to_numpy(float)
        original=_batch_slopes(y,m,Config())
        ref=baseline[baseline.scenario.eq(scenario)].set_index('papel_id').loc[sample.papel_id]
        np.testing.assert_allclose(original,ref.delta,rtol=1e-10,atol=1e-12)
        for length in [5,10,20]:
            rng=np.random.default_rng(np.random.SeedSequence([20261011,offset,length]))
            draws=np.empty((repetitions,len(sample)))
            for rep in range(repetitions):
                idx=moving_block_indices(len(m),length,rng)
                draws[rep]=_batch_slopes(y[idx],m[idx],Config())
            cache[(scenario,length)]=(sample,original,draws)
            expected=y_bootstrap[y_bootstrap.scenario.eq(scenario) & y_bootstrap.block_length.eq(length)].set_index('papel_id').loc[sample.papel_id]
            for j,papel in enumerate(sample.papel_id):
                values=draws[:,j];values=values[np.isfinite(values)]
                se=float(values.std(ddof=1))
                np.testing.assert_allclose(se,expected.loc[papel,'bootstrap_se'],rtol=1e-10,atol=1e-12)
                checks.append(dict(scenario=scenario,papel_id=papel,block_length=length,accepted=len(values),
                                   reproduced_y_bootstrap_se=se, archived_y_bootstrap_se=expected.loc[papel,'bootstrap_se']))
            progress(f'Blocos setoriais: {scenario}, L={length}, {repetitions} sorteios',flush=True)
    common_ids=set(samples['decada_periodo_comum'].papel_id)
    for scenario in SCENARIOS:
        for length in [5,10,20]:
            sample,original,draws=cache[('recente' if scenario=='decada_periodo_comum' else scenario,length)]
            if scenario=='decada_periodo_comum':
                selected=sample.papel_id.isin(common_ids).to_numpy();sample=sample[selected];original=original[selected];draws=draws[:,selected]
            sectors=sample.setor_economico.to_numpy()
            # A replicate may not silently discard an asset or a sector member.
            complete=np.isfinite(draws).all(axis=1);good=draws[complete]
            enough=len(good)>=max(99,int(np.ceil(.95*repetitions)))
            for sector in sorted(set(sectors)):
                selected=sectors==sector
                values=np.median(good[:,selected],axis=1)-np.median(good[:,~selected],axis=1)
                lo,hi=np.quantile(values,[.025,.975]) if enough else (np.nan,np.nan)
                intervals.append(dict(scenario=scenario,setor_economico=sector,block_length=length,repetitions=repetitions,
                    assets_sector=int(selected.sum()),assets_complement=int((~selected).sum()),accepted=int(complete.sum()),
                    point=float(np.median(original[selected])-np.median(original[~selected])),ci_low=lo,ci_high=hi,
                    scope='exploratory_marginal_percentile_stationarity_assumption_not_Holm_or_sector_causality'))
            vals=np.array([eta_squared(v,sectors) for v in good]);vals=vals[np.isfinite(vals)]
            lo,hi=np.quantile(vals,[.025,.975]) if enough and len(vals)>=99 else (np.nan,np.nan)
            eta_rows.append(dict(scenario=scenario,block_length=length,point=eta_squared(original,sectors),
                ci_low=lo,ci_high=hi,accepted=len(vals),scope='descriptive_grouping_of_point_estimates_not_structural_variance_explained'))
    checks=pd.DataFrame(checks)
    reused=checks[checks.scenario.eq('recente') & checks.papel_id.isin(common_ids)].copy()
    reused['scenario']='decada_periodo_comum'
    return pd.DataFrame(intervals),pd.DataFrame(eta_rows),pd.concat([checks,reused],ignore_index=True)


def run(root,x,y,temporal,progress=print):
    matrices,samples,baseline,annual,yboot=load(root,x,y,temporal)
    full, yearly=[] , []
    for variant, panels in matrices.items():
        for scenario in ['decada','recente']:
            matrix=panels[scenario]
            for a in samples[scenario].itertuples():
                identity=dict(scenario=scenario,ticker=a.ticker_yahoo,papel_id=a.papel_id,setor_economico=a.setor_economico,cash_variant=variant)
                out=risk(matrix[a.ticker_yahoo],matrix[BENCHMARK]);full.append(dict(out,**identity))
                if variant=='referencia_n':
                    for year in sorted(set(matrix.index.year)):
                        window=matrix[matrix.index.year==year]
                        yearly.append(dict(risk(window[a.ticker_yahoo],window[BENCHMARK]),**identity,year=year))
    ids=set(samples['decada_periodo_comum'].papel_id)
    tables=[]
    for rows in [full,yearly]:
        t=pd.DataFrame(rows);common=t[t.scenario.eq('recente') & t.papel_id.isin(ids)].copy();common['scenario']='decada_periodo_comum'
        tables.append(pd.concat([t,common],ignore_index=True))
    full,yearly=tables
    primary=full[full.cash_variant.eq('referencia_n')].merge(baseline[['scenario','papel_id','beta']],on=['scenario','papel_id'],validate='one_to_one')
    np.testing.assert_allclose(primary.beta_market_model,primary.beta,rtol=1e-10,atol=1e-12)
    sectors=sector_descriptions(baseline)
    intervals,eta,checks=bootstrap_sectors(matrices,samples,baseline,yboot,progress=progress)
    annual_sectors=annual.groupby(['scenario','year','setor_economico'],sort=False).agg(
        assets=('papel_id','size'),delta_median=('delta','median'),delta_q25=('delta',lambda z:z.quantile(.25)),
        delta_q75=('delta',lambda z:z.quantile(.75))).reset_index()
    summaries=[]
    for scenario in SCENARIOS:
        b=baseline[baseline.scenario.eq(scenario)];p=full[full.scenario.eq(scenario)&full.cash_variant.eq('referencia_n')]
        summaries.append(dict(scenario=scenario,assets=len(b),negative_delta=int(b.delta.lt(0).sum()),
            static_holm_below005=int(b.delta_p_holm_197.lt(.05).sum()),median_delta=b.delta.median(),
            eta2=eta_squared(b.delta,b.setor_economico),median_daily_vol=p.log_std_daily.median(),
            median_model_r2=p.r2_market_model.median(),median_es95=p.es95_simple_loss.median()))
    metrics=dict(stage='Lab03B',risk_full_rows=len(full),risk_annual_rows=len(yearly),sector_point_rows=len(sectors),
        sector_bootstrap_rows=len(intervals),sector_eta_rows=len(eta),bootstrap_y_reproduced_rows=len(checks),
        annual_sector_rows=len(annual_sectors),risk_free_series_used=False,CAPM_pricing_tested=False,
        Jensen_alpha_estimated=False,assets_reselected=False,company_weights_used=False,
        missing_returns_filled=False,global_homologated=0,
        maximum_variance_identity_error=float(full.variance_identity_error.max()),
        bootstrap_inference='exploratory_marginal_conditional_percentile_no_new_rejection_claims')
    return dict(risk_full=full,risk_annual=yearly,asset_betas=baseline,sector_point=sectors,
        sector_bootstrap=intervals,sector_eta=eta,bootstrap_y_check=checks,annual_sector=annual_sectors,
        summary=pd.DataFrame(summaries),metrics=metrics)

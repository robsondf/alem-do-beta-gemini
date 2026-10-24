"""Fixed-security market betas. No network, selection, imputation or winsorization.

HAC scores stay on the input trading-session grid (missing/neutral scores = 0).
Only the estimating equations omit invalid pairs. Zero scores are NOT returns.
"""
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd
import scipy
from scipy.stats import norm

BENCHMARK = "^BVSP"
SCENARIOS = {"decada": ("decada", 2016, 2025, 80),
             "decada_periodo_comum": ("decada", 2021, 2025, 80),
             "recente": ("recente", 2021, 2025, 117)}
GAPS = {"ABCB4.SA": ["2016-01-04", "2016-01-05"],
        "UGPA3.SA": ["2021-06-28", "2021-06-29", "2021-06-30"]}
LAYERS = {"reconciliacao": "998c94f3c3e72bbec0f62e5062ac777d386b308c68ee0c2d7ea622d797302728",
          "camada_eventos": "86ad7d71498fef253c9e7863c30359d914f3c01aa2bce8dba17f7e83d34e93f5",
          "revisao_extremos": "f98d9ee05bd20810bdc957519dfdf5809de39441df4bf2ba0bb78861f96f50ff",
          "revisao_integral": "9f65d2e5be630fdca9810c10aaad282ee64b4316bfcc2703c8b5c9946f833ecd",
          "fechamento_lab01": "ef3d1c68c401bd6b508fab859c7e2dceb0bafa0c0d805eccf0ae7f5aef4dfd64"}


@dataclass(frozen=True)
class Config:
    min_pairs: int = 200
    min_regime: int = 60
    min_coverage: float = .95
    min_market_variance: float = 1e-12
    hac_lags: int = 5
    confidence: float = .95

    def __post_init__(self):
        if (self.min_pairs < 5 or self.min_regime < 3 or self.hac_lags < 0
                or not 0 < self.confidence < 1 or not 0 < self.min_coverage <= 1
                or self.min_market_variance <= 0):
            raise ValueError("Invalid inference configuration")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_matrix(path):
    frame = pd.read_csv(path, index_col=0, parse_dates=[0])
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans
            or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
            or frame.columns.has_duplicates):
        raise ValueError(f"Invalid calendar/columns: {path}")
    frame = frame.apply(pd.to_numeric, errors="raise")
    if np.isinf(frame.to_numpy()).any():
        raise ValueError(f"Infinite return/price: {path}")
    return frame


def load_inputs(root, lock_path, validation_path):
    """Fail closed: immutable Lab01 controls AND pinned matrices, before fitting."""
    root = Path(root)
    lock = json.loads(Path(lock_path).read_text())
    validation = json.loads(Path(validation_path).read_text())
    hashes = lock["sha256_arquivos"]
    for name, expected in validation["sha256_exportacoes"].items():
        if hashes.get(name) != expected:
            raise ValueError(f"Lock incompatible with Lab01 validation: {name}")
    required = {"fatores_ajuste_jcp_bruto.csv", "fatores_ajuste_jcp_liquido_diagnostico.csv"}
    required |= set(validation["sha256_exportacoes"])
    required |= {f"{s}/{n}" for s in SCENARIOS for n in
                 ["amostra_fixa.csv", "retornos_logaritmicos.csv.gz",
                  "retornos_simples.csv.gz", "precos_ajustados.csv.gz"]}
    if not required <= set(hashes):
        raise ValueError("Incomplete input lock")
    for name, expected in hashes.items():
        if sha256(root / name) != expected:
            raise ValueError(f"Input changed; explicit revalidation required: {name}")
    state = json.loads((root / "estado_reconciliacao.json").read_text())
    provenance = json.loads((root / "proveniencia.json").read_text())
    if (state.get("versao_notebook") != lock["versao_lab01"]
            or state.get("apto_iniciar_lab02") is not True
            or state.get("auditoria_global_completa") is not False
            or state.get("apto_betas_definitivos") is not False
            or state.get("n_extremos_em_investigacao") != 0
            or state.get("ajustes_pendentes") or state.get("eventos_criticos_pendentes")):
        raise ValueError("Lab01 controls incompatible with this pilot")
    for name, expected in LAYERS.items():
        if provenance.get(name, {}).get("sha_manifesto") != expected:
            raise ValueError(f"Layer mismatch: {name}")
    if (provenance["ano_volume"] != 2025
            or provenance["consulta_precos"]["auto_adjust"] is not True
            or provenance["consulta_precos"]["end"] != "2026-01-01"):
        raise ValueError("Return provenance mismatch")
    gaps = pd.read_csv(root / "exclusoes_retornos_direitos.csv")
    expected_gaps = {(t, d) for t, dates in GAPS.items() for d in dates}
    observed = set(zip(gaps.ticker, pd.to_datetime(gaps.data).dt.strftime("%Y-%m-%d")))
    if len(gaps) != 5 or observed != expected_gaps:
        raise ValueError("Daily rights gaps changed")
    samples = pd.read_csv(root / "amostras_paineis.csv")
    panels = {}
    for scenario, (panel, first, last, size) in SCENARIOS.items():
        sample = pd.read_csv(root / scenario / "amostra_fixa.csv")
        fixed = samples.loc[samples.painel.eq(panel)].sort_values("papel_id").reset_index(drop=True)
        pd.testing.assert_frame_equal(sample.sort_values("papel_id").reset_index(drop=True), fixed)
        if (len(sample) != size or sample.papel_id.nunique() != size
                or sample.ticker_yahoo.nunique() != size or sample.setor_economico.nunique() != 10):
            raise ValueError("Fixed sample composition changed")
        mats = {name: read_matrix(root / scenario / f"{file}.csv.gz") for name, file in
                [("log", "retornos_logaritmicos"), ("simple", "retornos_simples"),
                 ("prices", "precos_ajustados")]}
        for name, mat in mats.items():
            if (set(mat.columns) != set(sample.ticker_yahoo) | {BENCHMARK}
                    or set(mat.index.year) != set(range(first, last + 1))):
                raise ValueError(f"Matrix composition/period mismatch: {scenario}/{name}")
            pd.testing.assert_index_equal(mat.index, mats["log"].index)
        pd.testing.assert_frame_equal(np.log1p(mats["simple"]), mats["log"],
                                      check_exact=False, atol=1e-12, rtol=1e-10)
        for ticker, dates in GAPS.items():
            for date in dates:
                if pd.Timestamp(date) in mats["log"].index:
                    for name in ["log", "simple"]:
                        if pd.notna(mats[name].loc[date, ticker]):
                            raise ValueError("Unidentified daily return was filled")
        for name in ["log", "simple"]:
            if not np.isclose(mats[name].loc["2024-10-30", "LIGT3.SA"],
                              np.log1p(-.14328112) if name == "log" else -.14328112):
                raise ValueError("Reconciled Light return changed")
        panels[scenario] = dict(sample=sample, **mats)
    common = panels["decada_periodo_comum"]
    for name in ["log", "simple", "prices"]:
        pd.testing.assert_frame_equal(common[name], panels["decada"][name].loc[common[name].index])
        pd.testing.assert_frame_equal(common[name], panels["recente"][name][common[name].columns])
    if not set(common["sample"].papel_id) <= set(panels["recente"]["sample"].papel_id):
        raise ValueError("Fixed panels no longer nested")
    controls = pd.read_csv(root / "comparacao_paineis.csv")
    for row in controls.itertuples():
        pair = panels[row.cenario]["log"][[row.ticker, BENCHMARK]].dropna()
        counts = (len(pair), (pair[BENCHMARK] > 0).sum(),
                  (pair[BENCHMARK] < 0).sum(), (pair[BENCHMARK] == 0).sum())
        if counts != (row.n_pares, row.n_alta, row.n_baixa, row.n_neutros):
            raise ValueError("Pair counts differ from validated Lab01")
    return panels, dict(state=state, provenance=provenance, lock=lock)


def ols_hac(y, design, mask, lags):
    """OLS on valid rows; Bartlett covariance on uncompressed session scores."""
    x, target = design[mask], y[mask]
    n, k = x.shape
    if n <= k or np.linalg.matrix_rank(x) < k:
        raise ValueError("Unidentified OLS design")
    coef = np.linalg.lstsq(x, target, rcond=None)[0]
    scores = np.zeros_like(design)
    scores[mask] = x * (target - x @ coef)[:, None]
    meat = scores.T @ scores
    lags = min(lags, len(scores) - 1)
    for lag in range(1, lags + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (lags + 1)) * (cross + cross.T)
    bread = np.linalg.inv(x.T @ x)
    covariance = (n / (n - k)) * bread @ meat @ bread
    return coef, (covariance + covariance.T) / 2


def _uncertainty(result, name, estimate, covariance, contrast, confidence):
    variance = float(contrast @ covariance @ contrast)
    if variance < -1e-12:
        raise ArithmeticError("Nonpositive HAC covariance")
    se = np.sqrt(max(0., variance))
    critical = norm.ppf((1 + confidence) / 2)
    # A zero residual variance is degenerate; do not manufacture a p=0 claim.
    p = float(2 * norm.sf(abs(estimate / se))) if se > 1e-14 else np.nan
    result.update({name: float(estimate), f"{name}_se": float(se),
                   f"{name}_ci_low": float(estimate - critical * se),
                   f"{name}_ci_high": float(estimate + critical * se),
                   f"{name}_p": p})


def estimate_security(asset, market, config=Config(), include=None):
    """One asset; cov/var definitions with intercepts, delta = plus minus minus."""
    pd.testing.assert_index_equal(asset.index, market.index)
    if asset.index.has_duplicates or not asset.index.is_monotonic_increasing:
        raise ValueError("Unsorted/duplicate session grid")
    y, m = asset.to_numpy(float), market.to_numpy(float)
    eligible = np.ones(len(m), dtype=bool) if include is None else np.asarray(include, dtype=bool)
    if eligible.shape != m.shape:
        raise ValueError("Invalid scenario mask")
    valid = eligible & np.isfinite(y) & np.isfinite(m)
    positive, negative = valid & (m > 0), valid & (m < 0)
    n, nplus, nminus = int(valid.sum()), int(positive.sum()), int(negative.sum())
    result = dict(n_sessions=int(eligible.sum()), n_pairs=n, n_plus=nplus, n_minus=nminus,
                  n_neutral=int((valid & (m == 0)).sum()), n_missing=int((eligible & ~valid).sum()),
                  coverage=n / eligible.sum() if eligible.any() else 0.,
                  min_pairs=config.min_pairs, min_regime=config.min_regime,
                  min_coverage=config.min_coverage, hac_lags=config.hac_lags,
                  confidence=config.confidence, inference="HAC_Bartlett_calendar_normal",
                  first_pair=str(asset.index[valid][0].date()) if n else None,
                  last_pair=str(asset.index[valid][-1].date()) if n else None)
    for name, mask in [("all", valid), ("plus", positive), ("minus", negative)]:
        result[f"market_variance_{name}"] = float(np.var(m[mask], ddof=1)) if mask.sum() > 1 else np.nan
    for name in ["beta", "beta_plus", "beta_minus", "delta"]:
        for suffix in ["", "_se", "_ci_low", "_ci_high", "_p"]:
            result[name + suffix] = np.nan
    coverage_ok = result["coverage"] >= config.min_coverage
    total_ok = (n >= config.min_pairs and coverage_ok
                and result["market_variance_all"] >= config.min_market_variance)
    result["status_beta"] = "ok" if total_ok else "insufficient_pairs_coverage_or_variance"
    if total_ok:
        design = np.column_stack([np.ones(len(m)), np.nan_to_num(m)])
        coef, covariance = ols_hac(y, design, valid, config.hac_lags)
        result["alpha"] = float(coef[0])
        _uncertainty(result, "beta", coef[1], covariance, np.array([0., 1.]), config.confidence)
        direct = np.cov(y[valid], m[valid], ddof=1)[0, 1] / np.var(m[valid], ddof=1)
        if not np.isclose(coef[1], direct, atol=1e-10, rtol=1e-9):
            raise ArithmeticError("Traditional beta differs from cov/var")
    regimes_ok = (total_ok and nplus >= config.min_regime and nminus >= config.min_regime
                  and result["market_variance_plus"] >= config.min_market_variance
                  and result["market_variance_minus"] >= config.min_market_variance)
    result["status_conditional"] = "ok" if regimes_ok else "insufficient_regimes_coverage_or_variance"
    if regimes_ok:
        d = (m > 0).astype(float)
        x = np.nan_to_num(m)
        design = np.column_stack([np.ones(len(m)), d, x, d * x])
        coef, covariance = ols_hac(y, design, positive | negative, config.hac_lags)
        bp = np.cov(y[positive], m[positive], ddof=1)[0, 1] / np.var(m[positive], ddof=1)
        bm = np.cov(y[negative], m[negative], ddof=1)[0, 1] / np.var(m[negative], ddof=1)
        err = max(abs(coef[2] - bm), abs(coef[2] + coef[3] - bp), abs(coef[3] - (bp - bm)))
        if not np.isclose(err, 0., atol=1e-10):
            raise ArithmeticError("Conditional cov/var differs from interaction regression")
        result.update(alpha_minus=float(coef[0]), alpha_plus=float(coef[0] + coef[1]),
                      interaction_max_error=float(err),
                      cov_beta_plus_minus=float(covariance[2, 2] + covariance[2, 3]))
        _uncertainty(result, "beta_minus", bm, covariance, np.array([0., 0., 1., 0.]), config.confidence)
        _uncertainty(result, "beta_plus", bp, covariance, np.array([0., 0., 1., 1.]), config.confidence)
        _uncertainty(result, "delta", bp - bm, covariance, np.array([0., 0., 0., 1.]), config.confidence)
    return result


def holm(pvalues, family_size=None):
    """Missing tests reserve their family slots (equivalent to p=1)."""
    p = np.asarray(pvalues, dtype=float)
    output = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    order = valid[np.argsort(p[valid], kind="stable")]
    size = len(p) if family_size is None else family_size
    if size < len(valid):
        raise ValueError("Family smaller than test count")
    output[order] = np.minimum(1., np.maximum.accumulate((size - np.arange(len(order))) * p[order]))
    return output


def fit_panel(matrix, sample, scenario, config=Config(), variant="baseline", window="full", masks=None):
    rows = []
    for row in sample.itertuples():
        mask = None if masks is None else masks.get(row.ticker_yahoo)
        result = estimate_security(matrix[row.ticker_yahoo], matrix[BENCHMARK], config, mask)
        result.update(scenario=scenario, painel=SCENARIOS[scenario][0],
                      ticker=row.ticker_yahoo, papel_id=row.papel_id, company_id=row.company_id,
                      setor_economico=row.setor_economico, variant=variant, window=window)
        rows.append(result)
    return pd.DataFrame(rows)


def weekly_returns(prices):
    """Observed last B3 session per W-FRI; never select last NONmissing price."""
    last_dates = pd.Series(prices.index, index=prices.index).groupby(prices.index.to_period("W-FRI")).last()
    endpoints = prices.loc[pd.DatetimeIndex(last_dates)]
    if ((endpoints <= 0) & endpoints.notna()).any().any():
        raise ValueError("Nonpositive wealth endpoint")
    return np.log(endpoints / endpoints.shift(1))


def net_jcp_diagnostic(matrix, gross, net):
    """Local four-history diagnostic, not tax harmonization of all 117 securities."""
    keys = ["ticker", "data_ex", "eventos"]
    factors = gross.merge(net, on=keys, suffixes=("_gross", "_net"), validate="one_to_one")
    if len(factors) != len(gross) or len(factors) != len(net):
        raise ValueError("Incomplete JCP factor pairs")
    output = matrix.copy()
    for row in factors.itertuples():
        date = pd.Timestamp(row.data_ex)
        if not (row.fator_gross > 0 and row.fator_net > 0):
            raise ValueError("Invalid JCP factor")
        if row.ticker in output and date in output.index:
            # net return: gross wealth ratio times gross_factor/net_factor.
            # NaN remains NaN; no prices or missing daily marks reconstructed.
            output.loc[date, row.ticker] += np.log(row.fator_gross / row.fator_net)
    return output, sorted(set(factors.ticker) & set(matrix.columns))


def event_masks(index, ticker):
    """Predeclared dates; broad Light Q4 + year covers preference conservatively."""
    events = {"ABCB4.SA": [("direitos", "2016-01-04", "2016-01-05", 2016)],
              "UGPA3.SA": [("extrafarma", "2021-06-28", "2021-06-30", 2021)],
              "LIGT3.SA": [("preferencia", "2024-10-30", "2024-10-30", 2024)],
              "PCAR3.SA": [("assai", "2021-03-01", "2021-03-01", 2021),
                            ("exito", "2023-08-23", "2023-08-23", 2023)]}
    result = {}
    for label, start, end, year in events.get(ticker, []):
        if not ((index >= start) & (index <= end)).any():
            continue
        start_pos, end_pos = index.searchsorted(start), index.searchsorted(end, side="right")
        mask = np.ones(len(index), bool)
        mask[max(0, start_pos - 5):min(len(index), end_pos + 5)] = False
        result[f"without_{label}_plusminus5"] = mask
        result[f"without_{label}_year{year}"] = index.year != year
        if ticker == "LIGT3.SA":
            result["without_preference_Q4_2024"] = ~((index >= "2024-10-01") & (index <= "2024-12-31"))
    if ticker == "PCAR3.SA":
        for label, first, last in [("before_assai", "2021-01-01", "2021-03-01"),
                                   ("between_assai_exito", "2021-03-01", "2023-08-23"),
                                   ("after_exito", "2023-08-23", "2026-01-01")]:
            result[f"regime_{label}"] = (index >= first) & (index < last)
    return result


def compare_common(baseline):
    columns = ["beta", "beta_plus", "beta_minus", "delta"]
    old = baseline.loc[baseline.scenario.eq("decada_periodo_comum")]
    recent = baseline.loc[baseline.scenario.eq("recente")]
    shared = old.merge(recent, on="papel_id", suffixes=("_80", "_117"), validate="one_to_one")
    for col in columns + ["n_pairs", "n_plus", "n_minus", "n_neutral"]:
        if not np.allclose(shared[col + "_80"], shared[col + "_117"], equal_nan=True, atol=1e-12):
            raise ValueError("Shared assets differ in common-period fit")
    summaries = []
    added = recent.loc[~recent.papel_id.isin(old.papel_id)]
    for name, frame in [("shared_80", old), ("all_117", recent), ("additional_37", added)]:
        for sector, part in [("ALL", frame), *list(frame.groupby("setor_economico"))]:
            for col in columns:
                valid = part[col].dropna()
                summaries.append(dict(group=name, setor_economico=sector, measure=col,
                    n_assets=len(part), n_estimated=len(valid), n_issuers=part.company_id.nunique(),
                    mean=valid.mean(), median=valid.median(), q25=valid.quantile(.25), q75=valid.quantile(.75)))
    # Descriptive security distributions only: no independent-samples t-tests.
    return shared, pd.DataFrame(summaries)


def run_lab02(root, output, repo_root, config=Config()):
    repo_root, root, output = Path(repo_root), Path(root), Path(output)
    if output.resolve() == root.resolve() or root.resolve() in output.resolve().parents:
        raise ValueError("Keep Lab02 outputs outside immutable Lab01 inputs")
    panels, controls = load_inputs(root, repo_root / "data/lab02/entradas_validadas.json",
                                  repo_root / "data/fechamento_lab01/validacao_colab_20261010.json")
    baseline = pd.concat([fit_panel(p["log"], p["sample"], s, config) for s, p in panels.items()], ignore_index=True)
    family = baseline.loc[baseline.scenario.ne("decada_periodo_comum")].copy()
    family["delta_p_holm"] = holm(family.delta_p)
    # 197 asset-window hypotheses. The common-period 80 reuse the recent tests.
    mapping = family.set_index(["scenario", "papel_id"])["delta_p_holm"].to_dict()
    baseline["delta_p_holm"] = [mapping[("recente" if r.scenario == "decada_periodo_comum" else r.scenario, r.papel_id)]
                                for r in baseline.itertuples()]
    shared, summary = compare_common(baseline)
    sensitivity, exclusions = [], []
    gross = pd.read_csv(root / "fatores_ajuste_jcp_bruto.csv")
    net = pd.read_csv(root / "fatores_ajuste_jcp_liquido_diagnostico.csv")
    for scenario, panel in panels.items():
        sample, log = panel["sample"], panel["log"]
        sensitivity.append(fit_panel(panel["simple"], sample, scenario, config, "simple"))
        for lag in [0, 10, 20]:
            sensitivity.append(fit_panel(log, sample, scenario, replace(config, hac_lags=lag), f"HAC_lags{lag}"))
        for minimum in [40, 100]:
            sensitivity.append(fit_panel(log, sample, scenario, replace(config, min_regime=minimum), f"min_regime{minimum}"))
        sensitivity.append(fit_panel(weekly_returns(panel["prices"]), sample, scenario,
                                    replace(config, min_pairs=40, min_regime=20, hac_lags=4), "weekly_endpoints"))
        for year in sorted(set(log.index.year)):
            sensitivity.append(fit_panel(log.loc[log.index.year == year], sample, scenario,
                                         config, "annual", str(year)))
        for ticker in ["ABCB4.SA", "UGPA3.SA", "LIGT3.SA", "PCAR3.SA"]:
            for variant, mask in event_masks(log.index, ticker).items():
                sub = sample.loc[sample.ticker_yahoo.eq(ticker)]
                sensitivity.append(fit_panel(log, sub, scenario, config, variant, masks={ticker: mask}))
                for date in log.index[~mask]:
                    exclusions.append(dict(scenario=scenario, ticker=ticker, variant=variant, data=str(date.date())))
        diagnostic, tickers = net_jcp_diagnostic(log, gross, net)
        sensitivity.append(fit_panel(diagnostic, sample.loc[sample.ticker_yahoo.isin(tickers)],
                                    scenario, config, "net_JCP_four_histories_only"))
    sensitivity = pd.concat(sensitivity, ignore_index=True)
    reference = baseline[["scenario", "papel_id", "beta", "beta_plus", "beta_minus", "delta", "n_pairs"]]
    sensitivity = sensitivity.merge(reference, on=["scenario", "papel_id"], suffixes=("", "_baseline"), validate="many_to_one")
    for name in ["beta", "beta_plus", "beta_minus", "delta"]:
        sensitivity[name + "_change"] = sensitivity[name] - sensitivity[name + "_baseline"]
    # Exploratory sensitivity p-values are deliberately not declared confirmatory.
    output.mkdir(parents=True, exist_ok=False)
    tables = {"betas": baseline, "sensibilidades": sensitivity,
              "comparacao_ativos_compartilhados": shared, "comparacao_distribuicoes": summary,
              "mascaras_sensibilidade": pd.DataFrame(exclusions),
              "lacunas_preservadas": pd.read_csv(root / "exclusoes_retornos_direitos.csv")}
    for name, frame in tables.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    state = dict(schema=1, gerado_em=pd.Timestamp.now(tz="UTC").isoformat(), config=asdict(config),
                 lab01_version=controls["state"]["versao_notebook"], inputs=controls["lock"],
                 module_sha256=sha256(repo_root / "src/lab02.py"),
                 environment=dict(python=platform.python_version(), numpy=np.__version__,
                                  pandas=pd.__version__, scipy=scipy.__version__),
                 n_baseline_rows=len(baseline), n_sensitivity_rows=len(sensitivity), holm_family_size=len(family),
                 auditoria_global_completa=False, apto_betas_definitivos=False,
                 resultados_empiricos_executados=True, persistencia_testada=False,
                 limitations=["Amostras retrospectivas, sobrevivência e liquidez final de 2025",
                              "Cinco retornos diários não identificados preservados",
                              "Inferência HAC assintótica; pisos não garantem poder nem estabilidade",
                              "ICs marginais, Holm para 197 hipóteses; sensibilidades exploratórias",
                              "Distribuições entre ativos descritivas; classes compartilham emissores",
                              "JCP líquido é diagnóstico local de quatro históricos; harmonização global pendente",
                              "Frequência semanal usa patrimônio ajustado observado nas extremidades",
                              "Light Q4 é janela conservadora, não calendário contratual certificado"],
                 outputs={f.name: sha256(f) for f in output.glob("*.csv")})
    (output / "execucao.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return tables, state

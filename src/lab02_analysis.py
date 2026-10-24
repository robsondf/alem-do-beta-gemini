"""Exploratory diagnostics and figures for the fixed-asset Lab02.

Never changes the estimator, the input matrices, the sample, or the main tests.
Block intervals, model fit and temporal plots are diagnostics, not predictions.
"""
from dataclasses import asdict
from pathlib import Path
import json
import platform

import numpy as np
import pandas as pd
import scipy
from scipy import stats
import matplotlib
import matplotlib.pyplot as plt

from lab02 import BENCHMARK, Config, SCENARIOS, holm, load_inputs, sha256

LABELS = {"decada": "80 ativos · 2016–2025",
          "decada_periodo_comum": "80 ativos · 2021–2025",
          "recente": "117 ativos · 2021–2025"}
MEASURES = ["beta", "beta_plus", "beta_minus", "delta"]


def verify_run(folder, repo_root):
    """Read all six outputs only after authenticating their source/configuration."""
    folder, repo_root = Path(folder), Path(repo_root)
    state = json.loads((folder / "execucao.json").read_text())
    lock = json.loads((repo_root / "data/lab02/entradas_validadas.json").read_text())
    if (state["inputs"] != lock or state["module_sha256"] != sha256(repo_root / "src/lab02.py")
            or state["config"] != asdict(Config())
            or state["auditoria_global_completa"] is not False
            or state["apto_betas_definitivos"] is not False):
        raise ValueError("Incompatible Lab02 provenance/configuration")
    names = {"betas", "sensibilidades", "comparacao_ativos_compartilhados",
             "comparacao_distribuicoes", "mascaras_sensibilidade", "lacunas_preservadas"}
    if set(state["outputs"]) != {n + ".csv" for n in names}:
        raise ValueError("Incomplete Lab02 output manifest")
    for f, expected in state["outputs"].items():
        if sha256(folder / f) != expected:
            raise ValueError("Changed Lab02 output: " + f)
    tables = {n: pd.read_csv(folder / (n + ".csv")) for n in names}
    b = tables["betas"]
    if (b.groupby("scenario").size().to_dict() != {s: x[3] for s, x in SCENARIOS.items()}
            or b.duplicated(["scenario", "papel_id"]).any()
            or len(tables["lacunas_preservadas"]) != 5):
        raise ValueError("Fixed sample/output composition changed")
    return tables, state


def calendar_correlation(values, lag=1):
    """Pairwise finite lag correlation on the ORIGINAL session grid; no compression."""
    x = np.asarray(values, float)
    a, b = x[lag:], x[:-lag]
    valid = np.isfinite(a) & np.isfinite(b)
    n = int(valid.sum())
    if n < 3 or np.std(a[valid]) == 0 or np.std(b[valid]) == 0:
        return np.nan, n
    return float(np.corrcoef(a[valid], b[valid])[0, 1]), n


def moments(values):
    x = np.asarray(values, float)
    x = x[np.isfinite(x)]
    result = {"n": len(x)}
    keys = ["mean", "median", "std_daily", "variance_daily", "mad_mean", "skew_corrected",
            "excess_kurtosis_corrected", "q01", "q05", "q95", "q99", "jb_statistic", "jb_p_nominal"]
    result.update({k: np.nan for k in keys})
    if len(x) < 4 or np.std(x) == 0:
        return result
    jb = stats.jarque_bera(x)
    result.update(mean=float(x.mean()), median=float(np.median(x)),
                  std_daily=float(x.std(ddof=1)), variance_daily=float(x.var(ddof=1)),
                  mad_mean=float(np.abs(x - x.mean()).mean()),
                  skew_corrected=float(stats.skew(x, bias=False)),
                  excess_kurtosis_corrected=float(stats.kurtosis(x, fisher=True, bias=False)),
                  q01=float(np.quantile(x, .01)), q05=float(np.quantile(x, .05)),
                  q95=float(np.quantile(x, .95)), q99=float(np.quantile(x, .99)),
                  jb_statistic=float(jb.statistic), jb_p_nominal=float(jb.pvalue))
    return result


def diagnostic_asset(asset, market):
    """Moments on paired returns; fit and residual diagnostics with distinct regimes."""
    pd.testing.assert_index_equal(asset.index, market.index)
    y, m = asset.to_numpy(float), market.to_numpy(float)
    valid = np.isfinite(y) & np.isfinite(m)
    masks = {"all": valid, "plus": valid & (m > 0), "minus": valid & (m < 0)}
    descriptive, fit = [], []
    for regime, mask in masks.items():
        yy, xx = y[mask], m[mask]
        a, z = moments(yy), moments(xx)
        a.update(regime=regime, market_std_daily=z["std_daily"],
                 vol_annual_scale_proxy=a["std_daily"] * np.sqrt(252),
                 market_variance=z["variance_daily"],
                 pearson=float(np.corrcoef(yy, xx)[0, 1]) if len(yy) > 3 and np.std(xx) and np.std(yy) else np.nan,
                 spearman=float(stats.spearmanr(yy, xx).statistic) if len(yy) > 3 and np.std(xx) and np.std(yy) else np.nan,
                 jb_large_sample_n_gt_2000=len(yy) > 2000,
                 jb_calibration="nominal_iid_asymptotic_not_confirmatory")
        descriptive.append(a)
    designs = {k: np.column_stack([np.ones(len(m)), np.nan_to_num(m)]) for k in masks}
    masks["interaction"] = valid & (m != 0)
    d, x = (m > 0).astype(float), np.nan_to_num(m)
    designs["interaction"] = np.column_stack([np.ones(len(m)), d, x, d * x])
    for model, mask in masks.items():
        target, design = y[mask], designs[model][mask]
        n, k = design.shape
        if n <= k or np.linalg.matrix_rank(design) < k:
            fit.append(dict(model=model, n=n, status="insufficient_design"))
            continue
        coef = np.linalg.lstsq(design, target, rcond=None)[0]
        residual = target - design @ coef
        sse, tss = float(residual @ residual), float(((target - target.mean()) ** 2).sum())
        r2 = 1 - sse / tss if tss > 0 else np.nan
        grid = np.full(len(m), np.nan)
        grid[mask] = residual
        row = dict(model=model, n=n, k=k, status="ok", r2=r2,
                   r2_adjusted=1 - (1 - r2) * (n - 1) / (n - k),
                   rmse=float(np.sqrt(sse / n)), residual_std=float(np.sqrt(sse / (n - k))),
                   sse=sse, tss=tss, residual_mean=float(residual.mean()),
                   residual_skew=float(stats.skew(residual, bias=False)),
                   residual_excess_kurtosis=float(stats.kurtosis(residual, bias=False)),
                   jb_p_nominal=float(stats.jarque_bera(residual).pvalue),
                   jb_large_sample_n_gt_2000=n > 2000)
        for lag in [1, 5, 20]:
            row[f"residual_acf_lag{lag}"], row[f"residual_acf_n_lag{lag}"] = calendar_correlation(grid, lag)
        row["squared_residual_acf_lag1"], row["squared_residual_acf_n_lag1"] = calendar_correlation(grid ** 2)
        fit.append(row)
    return descriptive, fit


def diagnostics(panels):
    desc, fit = [], []
    for scenario, panel in panels.items():
        for asset in panel["sample"].itertuples():
            a, b = diagnostic_asset(panel["log"][asset.ticker_yahoo], panel["log"][BENCHMARK])
            identity = dict(scenario=scenario, ticker=asset.ticker_yahoo, papel_id=asset.papel_id,
                            company_id=asset.company_id, setor_economico=asset.setor_economico)
            desc += [{**identity, **r} for r in a]
            fit += [{**identity, **r} for r in b]
    return pd.DataFrame(desc), pd.DataFrame(fit)


def moving_block_indices(n, length, rng):
    """Overlapping non-circular blocks; draw full sessions before selecting regimes."""
    if not 1 <= length <= n:
        raise ValueError("Invalid block length")
    starts = rng.integers(0, n - length + 1, size=(n + length - 1) // length)
    return (starts[:, None] + np.arange(length)).ravel()[:n]


def _batch_slopes(y, m, config):
    valid = np.isfinite(y) & np.isfinite(m[:, None])
    total = valid.sum(axis=0)
    slopes = []
    for mask in [valid & (m[:, None] > 0), valid & (m[:, None] < 0)]:
        count = mask.sum(axis=0)
        yy, xx = np.where(mask, y, 0.), np.where(mask, m[:, None], 0.)
        safe = np.maximum(count, 1)
        xx = np.where(mask, xx - xx.sum(axis=0) / safe, 0.)
        yy = np.where(mask, yy - yy.sum(axis=0) / safe, 0.)
        denominator = (xx ** 2).sum(axis=0)
        enough = ((total >= config.min_pairs) & (total / len(m) >= config.min_coverage)
                  & (count >= config.min_regime)
                  & (denominator / np.maximum(count - 1, 1) >= config.min_market_variance))
        with np.errstate(divide="ignore", invalid="ignore"):
            slopes.append(np.where(enough, (xx * yy).sum(axis=0) / denominator, np.nan))
    return slopes[0] - slopes[1]


def block_diagnostic(panels, baseline, repetitions=999, lengths=(5, 10, 20), seed=20261011, config=Config()):
    """Percentile intervals for delta, exploratory and conditional on stationarity.

    Each replicate shares the SAME calendar draw across all assets in a panel,
    retaining market pairs and cross-asset dependence. Original NaNs remain NaNs.
    Recent estimates are reused for the overlapping 80, not independently drawn.
    """
    if repetitions < 99:
        raise ValueError("At least 99 repetitions required for diagnostic quantiles")
    rows = []
    for scenario, offset in [("decada", 0), ("recente", 1)]:
        p = panels[scenario]
        sample = p["sample"].sort_values("papel_id")
        tickers = sample.ticker_yahoo.tolist()
        y, m = p["log"][tickers].to_numpy(float), p["log"][BENCHMARK].to_numpy(float)
        original = _batch_slopes(y, m, config)
        reference = baseline.loc[baseline.scenario.eq(scenario)].set_index("ticker").loc[tickers]
        if not np.allclose(original, reference.delta, atol=1e-10, rtol=1e-10, equal_nan=True):
            raise ValueError("Bootstrap statistic differs from baseline")
        for length in lengths:
            rng = np.random.default_rng(np.random.SeedSequence([seed, offset, int(length)]))
            replicas = np.empty((repetitions, len(tickers)))
            for rep in range(repetitions):
                idx = moving_block_indices(len(m), length, rng)
                replicas[rep] = _batch_slopes(y[idx], m[idx], config)
            for j, asset in enumerate(sample.itertuples()):
                values = replicas[:, j]
                values = values[np.isfinite(values)]
                accepted = len(values)
                enough = accepted >= max(99, int(np.ceil(.95 * repetitions)))
                lo, hi = np.quantile(values, [.025, .975]) if enough else (np.nan, np.nan)
                rows.append(dict(scenario=scenario, ticker=asset.ticker_yahoo, papel_id=asset.papel_id,
                    block_length=length, repetitions=repetitions, accepted=accepted,
                    rejected=repetitions - accepted, seed=seed, delta=original[j],
                    bootstrap_se=float(values.std(ddof=1)) if enough else np.nan,
                    bootstrap_bias=float(values.mean() - original[j]) if enough else np.nan,
                    delta_percentile_low=lo, delta_percentile_high=hi,
                    hac_se=float(reference.iloc[j].delta_se),
                    status="ok" if enough else "insufficient_valid_replicates",
                    inference="exploratory_percentile_not_Holm_not_stationarity_certificate"))
    result = pd.DataFrame(rows)
    shared_ids = set(panels["decada_periodo_comum"]["sample"].papel_id)
    common = result.loc[result.scenario.eq("recente") & result.papel_id.isin(shared_ids)].copy()
    common["scenario"] = "decada_periodo_comum"
    return pd.concat([result, common], ignore_index=True)


def descriptive_betas(baseline):
    rows = []
    for scenario, frame in baseline.groupby("scenario", sort=False):
        for measure in MEASURES:
            z = frame[measure].dropna()
            rows.append(dict(scenario=scenario, measure=measure, n_assets=len(frame), n_estimated=len(z),
                median=z.median(), mean=z.mean(), q25=z.quantile(.25), q75=z.quantile(.75),
                minimum=z.min(), maximum=z.max(),
                n_delta_negative=int(frame.delta.lt(0).sum()),
                n_delta_p_holm_lt_005=int(frame.delta_p_holm.lt(.05).sum())))
    return pd.DataFrame(rows)


def sensitivity_summary(baseline, sensitivity):
    rows, hac_rows = [], []
    for (scenario, variant), group in sensitivity.groupby(["scenario", "variant"], sort=False):
        g = group.loc[group.delta.notna() & group.delta_baseline.notna()]
        diff = g.delta_change.abs()
        rows.append(dict(scenario=scenario, variant=variant, n_rows=len(group), n_estimated=len(g),
            n_insufficient=int(group.status_conditional.ne("ok").sum()),
            median_abs_delta_change=diff.median(), max_abs_delta_change=diff.max(),
            n_sign_changes=int(((g.delta * g.delta_baseline < 0)
                               & (g.delta.abs() > 1e-12) & (g.delta_baseline.abs() > 1e-12)).sum())))
    for lag in [0, 5, 10, 20]:
        g = (baseline if lag == 5 else sensitivity.loc[sensitivity.variant.eq(f"HAC_lags{lag}")]).copy()
        primary = g.loc[g.scenario.ne("decada_periodo_comum")].copy()
        if len(primary) != 197:
            raise ValueError("HAC exploratory comparison requires the same 197 hypotheses")
        primary["delta_p_holm_diagnostic"] = holm(primary.delta_p)
        primary["hac_lags"] = lag
        hac_rows.append(primary[["scenario", "ticker", "papel_id", "hac_lags", "delta", "delta_se",
                                 "delta_p", "delta_p_holm_diagnostic"]])
    return pd.DataFrame(rows), pd.concat(hac_rows, ignore_index=True)


def _save(fig, folder, name):
    folder = Path(folder)
    for extension in ["png", "pdf"]:
        fig.savefig(folder / f"{name}.{extension}", dpi=170, bbox_inches="tight",
                    metadata={"Creator": "Além do Beta — análise exploratória"} if extension == "pdf" else None)
    plt.close(fig)


def make_figures(panels, baseline, sensitivity, hac, bootstrap, output, ticker="WEGE3.SA"):
    """All-asset plots; the selected example is explicit, never ranked by significance."""
    output = Path(output)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    files = []
    def save(fig, name):
        _save(fig, output, name)
        files.append(name)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    for ax, scenario in zip(axes, SCENARIOS):
        g = baseline.loc[baseline.scenario.eq(scenario)]
        ax.errorbar(g.beta_minus, g.beta_plus,
                    xerr=1.959963984540054 * g.beta_minus_se,
                    yerr=1.959963984540054 * g.beta_plus_se,
                    fmt="o", ms=3, alpha=.3, color="#24658d", elinewidth=.5)
        low = min((g.beta_minus - 1.96*g.beta_minus_se).min(), (g.beta_plus - 1.96*g.beta_plus_se).min())
        high = max((g.beta_minus + 1.96*g.beta_minus_se).max(), (g.beta_plus + 1.96*g.beta_plus_se).max())
        ax.plot([low, high], [low, high], "--", color="gray", lw=1)
        ax.set(title=LABELS[scenario], xlabel="Beta de baixa", ylabel="Beta de alta")
    fig.suptitle("Betas condicionais · ICs marginais de 95% · todos os ativos", fontsize=12)
    save(fig, "betas_condicionais")

    for scenario in ["decada", "recente"]:
        g = baseline.loc[baseline.scenario.eq(scenario)]
        sectors = sorted(g.setor_economico.unique())
        heights = [max(2.1, max(int(g.setor_economico.eq(s).sum()) for s in sectors[i:i+2])*.16)
                   for i in range(0, 10, 2)]
        fig, axes = plt.subplots(5, 2, figsize=(11, sum(heights)+1.2),
                                 gridspec_kw={"height_ratios": heights}, constrained_layout=True)
        low, high = (g.delta - 1.96*g.delta_se).min(), (g.delta + 1.96*g.delta_se).max()
        padding = .05*(high-low)
        for ax, sector in zip(axes.ravel(), sectors):
            part = g.loc[g.setor_economico.eq(sector)].sort_values("ticker")
            y = np.arange(len(part))
            ax.errorbar(part.delta, y, xerr=1.959963984540054*part.delta_se,
                        fmt="o", ms=3, color="#24658d", ecolor="#9aa9b0", capsize=1)
            ax.axvline(0, ls="--", color="gray", lw=.8)
            ax.set(yticks=y, yticklabels=part.ticker.str.replace(".SA", "", regex=False),
                   title=f"{sector} (n={len(part)})", xlabel="Δβ = alta − baixa",
                   xlim=(low-padding, high+padding))
            ax.tick_params(axis="y", labelsize=7)
        fig.suptitle(LABELS[scenario] + " · Δβ e IC HAC marginal de 95%", fontsize=12)
        save(fig, "intervalos_" + scenario)

    fig, axes = plt.subplots(1, 4, figsize=(13, 4), constrained_layout=True)
    recent = baseline.loc[baseline.scenario.eq("recente")]
    common = baseline.loc[baseline.scenario.eq("decada_periodo_comum")]
    added = recent.loc[~recent.papel_id.isin(common.papel_id)]
    for ax, measure in zip(axes, MEASURES):
        ax.boxplot([common[measure].dropna(), added[measure].dropna(), recent[measure].dropna()],
                   tick_labels=["80 comuns", "37 adicionais", "117 totais"], widths=.55)
        ax.tick_params(axis="x", rotation=25)
        ax.set_title(measure)
        ax.axhline(0 if measure == "delta" else 1, ls="--", color="gray", lw=.8)
    fig.suptitle("Composição em 2021–2025 · distribuições por ativo · grupos sobrepostos", fontsize=12)
    save(fig, "composicao_periodo_comum")

    years = sensitivity.loc[sensitivity.scenario.eq("decada") & sensitivity.variant.eq("annual")].copy()
    years["year"] = pd.to_numeric(years.window).astype(int)
    order = baseline.loc[baseline.scenario.eq("decada")].sort_values(["setor_economico", "ticker"]).ticker
    heat = years.pivot(index="ticker", columns="year", values="delta").reindex(order)
    fig, ax = plt.subplots(figsize=(9, 14), constrained_layout=True)
    limit = float(np.nanmax(np.abs(heat)))
    plot = ax.imshow(heat, aspect="auto", cmap="RdBu_r", vmin=-limit, vmax=limit)
    ax.set(xticks=np.arange(10), xticklabels=heat.columns, yticks=np.arange(len(heat)),
           yticklabels=heat.index.str.replace(".SA", "", regex=False),
           title="80 ativos fixos · Δβ anual · 2016–2025\nEstimativas exploratórias; cores não indicam significância")
    ax.tick_params(axis="y", labelsize=6)
    fig.colorbar(plot, ax=ax, label="Δβ (escala completa, sem corte dos valores)", shrink=.4)
    save(fig, "delta_anual_decada")

    p = panels["decada"]
    if ticker not in p["log"]:
        raise ValueError("Inspection ticker must belong to the fixed decade sample")
    pair = p["log"][[ticker, BENCHMARK]].dropna()
    selected = baseline.loc[baseline.scenario.eq("decada") & baseline.ticker.eq(ticker)].iloc[0]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    ax = axes[0, 0]
    for positive, label, color in [(True, "Alta", "#24658d"), (False, "Baixa", "#a84437")]:
        q = pair.loc[pair[BENCHMARK].gt(0) if positive else pair[BENCHMARK].lt(0)]
        ax.scatter(100*q[BENCHMARK], 100*q[ticker], s=6, alpha=.25, color=color, rasterized=True)
        x = np.linspace(q[BENCHMARK].min(), q[BENCHMARK].max(), 100)
        beta, alpha = (selected.beta_plus, selected.alpha_plus) if positive else (selected.beta_minus, selected.alpha_minus)
        ax.plot(100*x, 100*(alpha + beta*x), color=color, label=f"{label}: β={beta:.3f}")
    x = np.linspace(pair[BENCHMARK].min(), pair[BENCHMARK].max(), 100)
    ax.plot(100*x, 100*(selected.alpha + selected.beta*x), "--", color="black", label=f"Tradicional: β={selected.beta:.3f}")
    ax.set(xlabel="Ibovespa · retorno log diário (%)", ylabel="Ativo · retorno log diário (%)")
    ax.legend(fontsize=8)
    residual = pair[ticker] - (selected.alpha + selected.beta * pair[BENCHMARK])
    axes[0, 1].scatter(100*pair[BENCHMARK], 100*residual, s=6, alpha=.25, rasterized=True)
    axes[0, 1].axhline(0, color="gray", lw=.8)
    axes[0, 1].set(xlabel="Ibovespa (%)", ylabel="Resíduo tradicional (%)")
    stats.probplot(residual, dist="norm", plot=axes[1, 0])
    axes[1, 0].set(title="Q–Q dos resíduos · diagnóstico", xlabel="Quantis normais teóricos", ylabel="Resíduo log diário")
    grid = pd.Series(np.nan, index=p["log"].index)
    grid.loc[residual.index] = residual
    lags = range(1, 21)
    axes[1, 1].plot(list(lags), [calendar_correlation(grid, k)[0] for k in lags], "o-", ms=3, label="Resíduos")
    axes[1, 1].plot(list(lags), [calendar_correlation(grid**2, k)[0] for k in lags], "o-", ms=3, label="Resíduos²")
    axes[1, 1].axhline(0, color="gray", lw=.8)
    axes[1, 1].set(xlabel="Defasagem em pregões (grade original)", ylabel="Correlação descritiva")
    axes[1, 1].legend(fontsize=8)
    fig.suptitle(f"{ticker} · 2016–2025 · exemplo escolhido explicitamente", fontsize=12)
    save(fig, "diagnostico_ativo")

    g = years.loc[years.ticker.eq(ticker)].sort_values("year")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    for name, label, color in [("beta_plus", "Alta", "#24658d"), ("beta_minus", "Baixa", "#a84437")]:
        axes[0].errorbar(g.year, g[name], yerr=1.959963984540054*g[name+"_se"], fmt="o-", color=color, label=label)
    axes[0].legend()
    axes[0].set_ylabel("Beta condicional e IC marginal")
    axes[1].errorbar(g.year, g.delta, yerr=1.959963984540054*g.delta_se, fmt="o-", color="#24658d")
    axes[1].axhline(0, ls="--", color="gray")
    axes[1].set(xlabel="Ano", ylabel="Δβ e IC marginal", xticks=g.year)
    fig.suptitle(f"{ticker} · estimativas anuais · não é teste de persistência", fontsize=12)
    save(fig, "evolucao_anual_ativo")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, scenario in zip(axes, ["decada", "recente"]):
        parts = []
        for lag in [0, 10, 20]:
            g = hac.loc[hac.scenario.eq(scenario) & hac.hac_lags.eq(lag)]
            ref = hac.loc[hac.scenario.eq(scenario) & hac.hac_lags.eq(5)].set_index("papel_id")
            parts.append((g.set_index("papel_id").delta_se / ref.delta_se).dropna())
        ax.boxplot(parts, tick_labels=["HAC 0 / 5", "HAC 10 / 5", "HAC 20 / 5"])
        ax.axhline(1, ls="--", color="gray")
        ax.set(title=LABELS[scenario], ylabel="Razão dos erros padrão de Δβ")
    fig.suptitle("Sensibilidade da incerteza · coeficientes permanecem iguais", fontsize=12)
    save(fig, "sensibilidade_HAC")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, scenario in zip(axes, ["decada", "recente"]):
        parts = [bootstrap.loc[bootstrap.scenario.eq(scenario) & bootstrap.block_length.eq(k)] for k in [5, 10, 20]]
        ax.boxplot([(g.bootstrap_se / g.hac_se).dropna() for g in parts], tick_labels=["5 pregões", "10 pregões", "20 pregões"])
        ax.axhline(1, ls="--", color="gray")
        ax.set(title=LABELS[scenario], ylabel="EP bootstrap / EP HAC 5")
    fig.suptitle(f"Bootstrap em blocos · diagnóstico de incerteza · {int(bootstrap.repetitions.iloc[0])} réplicas", fontsize=12)
    save(fig, "bootstrap_blocos")

    for scenario in ["decada", "recente"]:
        fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
        for ax, asset in zip(axes.ravel(), ["ABCB4.SA", "UGPA3.SA", "LIGT3.SA", "PCAR3.SA"]):
            ref = baseline.loc[baseline.scenario.eq(scenario) & baseline.ticker.eq(asset)]
            if ref.empty:
                ax.axis("off")
                ax.text(.5, .5, asset + " fora desta amostra fixa", ha="center", va="center", transform=ax.transAxes)
                continue
            variants = sensitivity.loc[sensitivity.scenario.eq(scenario) & sensitivity.ticker.eq(asset)
                & (sensitivity.variant.str.startswith("without_") | sensitivity.variant.str.startswith("regime_"))]
            g = pd.concat([ref.assign(variant="baseline"), variants], ignore_index=True)
            y = np.arange(len(g))
            good = g.delta.notna()
            ax.errorbar(g.loc[good, "delta"], y[good], xerr=1.959963984540054*g.loc[good, "delta_se"], fmt="o", color="#24658d", ms=3)
            ax.axvline(0, ls="--", color="gray", lw=.8)
            labels = [str(r.variant).replace("without_", "sem_") + (" · insuficiente" if pd.isna(r.delta) else "") for r in g.itertuples()]
            ax.set(yticks=y, yticklabels=labels, title=asset, xlabel="Δβ e IC marginal de 95%")
            ax.tick_params(axis="y", labelsize=7)
        fig.suptitle(LABELS[scenario] + " · reservas de eventos e lacunas", fontsize=12)
        save(fig, "eventos_" + scenario)
    return files


def run_analysis(input_root, run_folder, repo_root, output, repetitions=999, seed=20261011, ticker="WEGE3.SA"):
    repo_root, output = Path(repo_root), Path(output)
    if output.exists():
        raise ValueError("Analysis output must be a new directory")
    for source in [input_root, run_folder]:
        source = Path(source).resolve()
        if source == output.resolve() or source in output.resolve().parents:
            raise ValueError("Do not place analysis inside audited inputs or Lab02 run")
    tables, run = verify_run(run_folder, repo_root)
    panels, _ = load_inputs(input_root, repo_root / "data/lab02/entradas_validadas.json",
                            repo_root / "data/fechamento_lab01/validacao_colab_20261010.json")
    # Authenticate labels and pair counts against matrices; do not trust a display head.
    for scenario, p in panels.items():
        b = tables["betas"].loc[tables["betas"].scenario.eq(scenario)]
        ids = p["sample"].set_index("papel_id")
        if set(b.papel_id) != set(ids.index):
            raise ValueError("Asset identity changed")
        for row in b.itertuples():
            original = ids.loc[row.papel_id]
            if row.ticker != original.ticker_yahoo or row.setor_economico != original.setor_economico:
                raise ValueError("Asset label changed")
            pair = p["log"][[row.ticker, BENCHMARK]].dropna()
            if (len(pair), int(pair[BENCHMARK].gt(0).sum()), int(pair[BENCHMARK].lt(0).sum())) != (row.n_pairs, row.n_plus, row.n_minus):
                raise ValueError("Pair counts changed")
    desc, fit = diagnostics(panels)
    summary, hac = sensitivity_summary(tables["betas"], tables["sensibilidades"])
    block = block_diagnostic(panels, tables["betas"], repetitions=repetitions, seed=seed)
    output.mkdir(parents=True)
    figure_dir = output / "figures"
    figure_dir.mkdir()
    exports = {"momentos_retornos_pareados": desc, "diagnosticos_regressao": fit,
               "resumo_betas": descriptive_betas(tables["betas"]),
               "resumo_sensibilidades": summary, "HAC_familias_exploratorias": hac,
               "bootstrap_blocos": block}
    for name, frame in exports.items():
        frame.to_csv(output / (name + ".csv"), index=False)
    figures = make_figures(panels, tables["betas"], tables["sensibilidades"], hac, block, figure_dir, ticker)
    state = dict(schema=1, gerado_em=pd.Timestamp.now(tz="UTC").isoformat(),
        origem_execucao_sha256=sha256(Path(run_folder) / "execucao.json"),
        origem_outputs=run["outputs"], inputs=run["inputs"],
        module_sha256=sha256(repo_root / "src/lab02_analysis.py"),
        environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                         scipy=scipy.__version__, matplotlib=matplotlib.__version__),
        bootstrap=dict(repetitions=repetitions, lengths=[5, 10, 20], seed=seed,
            method="non_circular_overlapping_moving_blocks_shared_calendar",
            confidence=.95, min_accepted_fraction=.95, exploratory=True),
        selected_example=ticker, rows={n: len(t) for n,t in exports.items()}, figures=figures,
        auditoria_global_completa=False, apto_betas_definitivos=False, persistencia_testada=False,
        limitations=run["limitations"] + [
            "Momentos e correlações condicionados aos mesmos pares válidos de cada ativo",
            "Jarque–Bera: calibração nominal iid assintótica; não é teste confirmatório em série dependente",
            "R², RMSE e comparações de modelos são dentro da amostra, não previsão",
            "Bootstrap requer regularidade e estacionariedade; não corrige quebras, seleção ou lacunas informativas",
            "ICs percentile são marginais exploratórios, sem Holm; não substituir o teste principal",
            "Grupos de composição se sobrepõem; anos e ICs sobrepostos não estabelecem persistência"],
        outputs={str(p.relative_to(output)): sha256(p) for p in output.rglob("*") if p.is_file()})
    (output / "analise.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return exports, state

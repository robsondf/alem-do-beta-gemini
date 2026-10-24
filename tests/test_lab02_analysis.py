import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lab02 import Config, estimate_security
from lab02_analysis import (calendar_correlation, diagnostic_asset, moments,
                            moving_block_indices, _batch_slopes, block_diagnostic, verify_run)


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(711)
        self.index = pd.bdate_range("2019-01-01", periods=600)
        self.m = pd.Series(rng.normal(0, .02, 600), index=self.index)
        self.y = pd.Series(.003 + 1.2*self.m + rng.normal(0, .01, 600), index=self.index)

    def test_simple_ols_r2_equals_pearson_squared_with_intercept(self):
        self.y.iloc[[10, 44]] = np.nan
        desc, fit = diagnostic_asset(self.y, self.m)
        self.assertEqual(desc[0]["n"], 598)
        self.assertAlmostEqual(fit[0]["r2"], desc[0]["pearson"]**2, places=12)
        pair = pd.concat([self.y, self.m], axis=1).dropna()
        model = stats.linregress(pair.iloc[:, 1], pair.iloc[:, 0])
        residual = pair.iloc[:, 0] - model.intercept - model.slope*pair.iloc[:, 1]
        self.assertAlmostEqual(fit[0]["rmse"], np.sqrt(np.mean(residual**2)), places=12)

    def test_acf_preserves_calendar_gaps_and_pair_counts(self):
        z = np.array([1., np.nan, 2., 4., 3., 6., np.nan, 5., 8.])
        value, n = calendar_correlation(z, 1)
        self.assertEqual(n, 4)
        self.assertAlmostEqual(value, np.corrcoef([4, 3, 6, 8], [2, 4, 3, 5])[0, 1])
        self.assertNotAlmostEqual(value, calendar_correlation(z[np.isfinite(z)], 1)[0])

    def test_moments_explicit_unbiased_shape_and_excess_convention(self):
        z = np.array([-.04, -.01, 0., .001, .005, .08, np.nan])
        result = moments(z)
        z = z[np.isfinite(z)]
        self.assertEqual(result["n"], 6)
        self.assertAlmostEqual(result["skew_corrected"], stats.skew(z, bias=False))
        self.assertAlmostEqual(result["excess_kurtosis_corrected"], stats.kurtosis(z, fisher=True, bias=False))
        self.assertAlmostEqual(result["std_daily"]**2, result["variance_daily"])

    def test_blocks_are_contiguous_without_wrapping_or_dropping_sessions(self):
        idx = moving_block_indices(103, 5, np.random.default_rng(11))
        self.assertEqual(len(idx), 103)
        self.assertTrue(((idx >= 0) & (idx < 103)).all())
        self.assertTrue((np.diff(idx[:100].reshape(-1, 5), axis=1) == 1).all())
        with self.assertRaises(ValueError):
            moving_block_indices(10, 11, np.random.default_rng(1))

    def test_bootstrap_delta_agrees_with_conditional_interaction_and_keeps_nan(self):
        self.y.iloc[[5, 20, 41]] = np.nan
        result = _batch_slopes(self.y.to_numpy()[:, None], self.m.to_numpy(), Config())
        self.assertAlmostEqual(result[0], estimate_security(self.y, self.m)["delta"], places=12)
        before = self.y.copy()
        _batch_slopes(self.y.to_numpy()[:, None], self.m.to_numpy(), Config())
        pd.testing.assert_series_equal(before, self.y)

    def test_shared_assets_reuse_bootstrap_draws_and_reproducibility(self):
        sample = pd.DataFrame({"papel_id": [1, 2], "ticker_yahoo": ["A", "B"]})
        matrix = pd.DataFrame({"A": self.y, "B": self.y * 2, "^BVSP": self.m})
        panels = {s: {"log": matrix, "sample": sample} for s in ["decada", "recente", "decada_periodo_comum"]}
        baseline = pd.DataFrame([{"scenario": s, "ticker": a, **estimate_security(matrix[a], self.m)}
                                for s in ["decada", "recente"] for a in ["A", "B"]])
        first = block_diagnostic(panels, baseline, repetitions=99, lengths=(5,), seed=3)
        second = block_diagnostic(panels, baseline, repetitions=99, lengths=(5,), seed=3)
        pd.testing.assert_frame_equal(first, second)
        a = first[first.scenario.eq("recente")].drop(columns="scenario").reset_index(drop=True)
        b = first[first.scenario.eq("decada_periodo_comum")].drop(columns="scenario").reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)
        self.assertAlmostEqual(a.iloc[1].bootstrap_se, 2*a.iloc[0].bootstrap_se, places=12)

    def test_insufficient_regime_retained_as_nan(self):
        m = np.ones(300) * .01
        delta = _batch_slopes(np.linspace(-1, 1, 300)[:, None], m, Config())
        self.assertTrue(np.isnan(delta).all())

    def test_run_authentication_rejects_incompatible_source(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            state = json.loads((repo / "data/lab02/execucao_colab_20261010.json").read_text())
            state["module_sha256"] = "changed"
            Path(folder, "execucao.json").write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, "provenance"):
                verify_run(folder, repo)


if __name__ == "__main__":
    unittest.main()

"""Numerical contracts and fail-closed provenance; unittest, no network."""
import json
import tempfile
import unittest
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import linregress

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.lab02 import (Config, estimate_security, ols_hac, holm, weekly_returns,
                      net_jcp_diagnostic, event_masks, load_inputs)


class BetaTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(20261010)
        self.index = pd.bdate_range("2021-01-01", periods=700)
        self.m = pd.Series(rng.normal(0, .02, len(self.index)), index=self.index)
        self.y = pd.Series(np.where(self.m > 0, .007 + 1.4 * self.m, -.004 + .6 * self.m)
                           + rng.normal(0, .002, len(self.index)), index=self.index)

    def test_matches_independent_regressions_with_separate_intercepts(self):
        self.y.iloc[80:84] = np.nan
        self.m.iloc[160] = 0
        r = estimate_security(self.y, self.m)
        for sign, key in [(self.m > 0, "beta_plus"), (self.m < 0, "beta_minus")]:
            valid = sign & self.y.notna()
            slope = linregress(self.m[valid], self.y[valid]).slope
            self.assertAlmostEqual(r[key], slope, places=12)
        valid = self.y.notna()
        self.assertAlmostEqual(r['beta'], linregress(self.m[valid], self.y[valid]).slope, places=12)
        self.assertAlmostEqual(r['delta'], r['beta_plus'] - r['beta_minus'], places=12)
        self.assertEqual(r['n_neutral'], 1)
        self.assertEqual(r['n_pairs'], 696)
        self.assertLess(r['interaction_max_error'], 1e-10)
        self.assertGreater(r['delta_se'], 0)
        self.assertAlmostEqual(r['delta_se'] ** 2, r['beta_plus_se'] ** 2 +
                               r['beta_minus_se'] ** 2 - 2 * r['cov_beta_plus_minus'], places=12)

    def test_hac_matches_direct_double_sum_on_session_grid(self):
        x = np.column_stack([np.ones(7), [-3., -2., -1., 0., 1., 2., 3.]])
        y = np.array([1., 3., 2., 5., 7., 4., 8.])
        mask = np.array([True, True, False, True, False, True, True])
        beta, cov = ols_hac(y, x, mask, 2)
        meat = np.zeros((2, 2))
        residual = y - x @ beta
        for i in np.flatnonzero(mask):
            for j in np.flatnonzero(mask):
                if abs(i-j) <= 2:
                    meat += (1 - abs(i-j)/3) * np.outer(x[i]*residual[i], x[j]*residual[j])
        bread = np.linalg.inv(x[mask].T @ x[mask])
        np.testing.assert_allclose(cov, (5/3)*bread@meat@bread, atol=1e-12)
        _, compressed = ols_hac(y[mask], x[mask], np.ones(5, bool), 2)
        self.assertFalse(np.allclose(cov, compressed))

    def test_hac_zero_lag_equals_hc1(self):
        x = np.column_stack([np.ones(700), self.m])
        coef, cov = ols_hac(self.y.to_numpy(), x, np.ones(700, bool), 0)
        residual = self.y.to_numpy() - x@coef
        bread = np.linalg.inv(x.T@x)
        hc1 = (700/698)*bread@(x.T@(x*residual[:,None]**2))@bread
        np.testing.assert_allclose(cov, hc1, atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(cov).min(), -1e-12)

    def test_hac_covariance_includes_cross_regime_dependence(self):
        r = estimate_security(self.y, self.m)
        naive = r['beta_plus_se']**2 + r['beta_minus_se']**2
        self.assertNotAlmostEqual(r['delta_se']**2, naive, places=9)

    def test_no_interpolation_and_insufficient_regime_retains_row(self):
        y = self.y.copy(); y.iloc[:40] = np.nan
        r = estimate_security(y, self.m)
        self.assertEqual(r['status_beta'], 'insufficient_pairs_coverage_or_variance')
        self.assertTrue(np.isnan(r['beta']))
        r = estimate_security(self.y, abs(self.m))
        self.assertEqual(r['status_beta'], 'ok')
        self.assertTrue(np.isnan(r['delta']))

    def test_constant_market_is_unidentified(self):
        r = estimate_security(self.y, self.m*0 + .01)
        self.assertTrue(np.isnan(r['beta']))

    def test_neutral_days_change_traditional_only(self):
        self.m.iloc[0:20] = 0
        r = estimate_security(self.y, self.m)
        changed = self.y.copy(); changed.iloc[:20] += 1
        s = estimate_security(changed, self.m)
        self.assertEqual(r['delta'], s['delta'])
        self.assertNotEqual(r['beta'], s['beta'])

    def test_holm_arbitrary_dependence_and_missing_slots(self):
        np.testing.assert_allclose(holm([.01, .04, .03, np.nan]), [.04, .09, .09, np.nan])

    def test_weekly_uses_actual_last_session_even_if_missing(self):
        index = pd.bdate_range('2021-06-14', '2021-07-09')
        prices = pd.DataFrame({'A':np.arange(len(index))+100.}, index=index)
        prices.loc['2021-06-25','A'] = np.nan
        r = weekly_returns(prices)
        self.assertTrue(pd.isna(r.loc['2021-06-25','A']))
        self.assertTrue(pd.isna(r.loc['2021-07-02','A']))
        self.assertAlmostEqual(r.loc['2021-07-09','A'], np.log(119/114))

    def test_weekly_can_bridge_missing_interior_without_daily_fill(self):
        prices = pd.DataFrame({'A':[100.,101.,np.nan,np.nan,104.,105.,106.,107.,108.,110.]},
                              index=pd.bdate_range('2021-06-21',periods=10))
        self.assertAlmostEqual(weekly_returns(prices).iloc[-1,0], np.log(110/104))
        self.assertEqual(prices.A.isna().sum(), 2)

    def test_net_jcp_sign_and_nan_preservation(self):
        matrix = pd.DataFrame({'A':[.1,np.nan]}, index=pd.to_datetime(['2021-01-04','2021-01-05']))
        gross = pd.DataFrame({'ticker':['A','A'], 'data_ex':['2021-01-04','2021-01-05'],
                              'eventos':['e1','e2'], 'fator':[.9,.9]})
        net = gross.copy(); net['fator'] = .915
        output, tickers = net_jcp_diagnostic(matrix,gross,net)
        self.assertLess(output.iloc[0,0],matrix.iloc[0,0])
        self.assertTrue(pd.isna(output.iloc[1,0]))
        self.assertEqual(tickers,['A'])

    def test_event_masks_keep_grid_and_cover_light_preference(self):
        index = pd.bdate_range('2024-01-01','2025-12-31')
        masks = event_masks(index,'LIGT3.SA')
        self.assertFalse(masks['without_preference_Q4_2024'][index.get_loc('2024-11-20')])
        self.assertEqual(len(masks['without_preferencia_plusminus5']),len(index))
        self.assertFalse(masks['without_preferencia_year2024'][index.get_loc('2024-10-30')])

    def test_lock_rejects_unvalidated_replacement(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p/'lock.json').write_text(json.dumps({'sha256_arquivos':{'state':'wrong'}}))
            (p/'validation.json').write_text(json.dumps({'sha256_exportacoes':{'state':'expected'}}))
            with self.assertRaisesRegex(ValueError,'incompatible'):
                load_inputs(p,p/'lock.json',p/'validation.json')

    def test_notebook_embeds_exact_versioned_code_and_lock(self):
        root = Path(__file__).resolve().parents[1]
        notebook = json.loads((root/'notebooks/02_betas.ipynb').read_text())
        import ast
        assignments = {}
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                for node in ast.parse(''.join(cell['source'])).body:
                    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
                        if node.targets[0].id in ['MODULE_SOURCE','LOCK','VALIDACAO_LAB01']:
                            assignments[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(assignments['MODULE_SOURCE'],(root/'src/lab02.py').read_text())
        self.assertEqual(assignments['LOCK'],json.loads((root/'data/lab02/entradas_validadas.json').read_text()))
        self.assertEqual(assignments['VALIDACAO_LAB01'],json.loads(
            (root/'data/fechamento_lab01/validacao_colab_20261010.json').read_text()))

    def test_duplicate_or_unsorted_calendar_rejected(self):
        with self.assertRaises(ValueError):
            estimate_security(self.y.iloc[::-1],self.m.iloc[::-1])
        y, m = self.y.copy(),self.m.copy()
        y.index = m.index = pd.DatetimeIndex([self.index[0]]*len(m))
        with self.assertRaises(ValueError):
            estimate_security(y,m)


if __name__ == '__main__':
    unittest.main()

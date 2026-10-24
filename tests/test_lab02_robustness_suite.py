import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from lab02 import Config, estimate_security, event_masks
from lab02_robustness_suite import add_families, check_common, load_x


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = Path(os.environ['LAB02Y_X_ARCHIVE'])
        cls.lock = json.loads((ROOT / 'data/lab02/lab02y_inputs_manifest.json').read_text())
        cls.matrices, cls.samples, cls.estimates = load_x(cls.archive, cls.lock)

    def test_wrong_archive_hash_stops_before_use(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            load_x(self.archive, dict(self.lock, x_results_sha256='0' * 64))

    def test_fixed_assets_and_common_input_identity(self):
        self.assertEqual([len(self.samples[s]) for s in ['decada', 'decada_periodo_comum', 'recente']], [80, 80, 117])
        for m in self.matrices.values():
            pd.testing.assert_frame_equal(m['decada_periodo_comum'], m['recente'][m['decada_periodo_comum'].columns], check_exact=True)

    def test_daily_missing_values_are_not_filled(self):
        for m in self.matrices.values():
            self.assertTrue(m['decada'].isna().equals(self.matrices['referencia_n']['decada'].isna()))
            self.assertTrue(m['decada'].loc[['2016-01-04', '2016-01-05'], 'ABCB4.SA'].isna().all())
            self.assertTrue(m['recente'].loc[['2021-06-28', '2021-06-29', '2021-06-30'], 'UGPA3.SA'].isna().all())

    def test_simple_estimator_transforms_asset_and_market(self):
        m = self.matrices['referencia_n']['recente']
        y, x = np.expm1(m['BBAS3.SA']), np.expm1(m['^BVSP'])
        fitted = estimate_security(y, x)
        valid = y.notna() & x.notna()
        direct = np.cov(y[valid], x[valid], ddof=1)[0, 1] / np.var(x[valid], ddof=1)
        self.assertAlmostEqual(fitted['beta'], direct, places=12)
        self.assertGreater(abs(fitted['beta'] - estimate_security(y, m['^BVSP'])['beta']), 1e-6)

    def test_hac_changes_uncertainty_not_point_estimates(self):
        m = self.matrices['referencia_n']['decada']
        a = estimate_security(m['BBAS3.SA'], m['^BVSP'], Config(hac_lags=0))
        b = estimate_security(m['BBAS3.SA'], m['^BVSP'], Config(hac_lags=20))
        self.assertEqual(a['delta'], b['delta'])
        self.assertNotEqual(a['delta_se'], b['delta_se'])

    def test_insufficient_pcar_regime_remains_unestimated(self):
        m = self.matrices['referencia_n']['recente']
        mask = event_masks(m.index, 'PCAR3.SA')['regime_before_assai']
        result = estimate_security(m['PCAR3.SA'], m['^BVSP'], include=mask)
        self.assertEqual(result['n_pairs'], 37)
        self.assertNotEqual(result['status_conditional'], 'ok')
        self.assertTrue(np.isnan(result['delta']))

    def test_common_reuses_197_family_slots(self):
        rows = []
        for s, size in [('decada', 80), ('recente', 117), ('decada_periodo_comum', 80)]:
            for i in range(size):
                rows.append(dict(scenario=s, papel_id=i, cash_variant='reference', treatment='HAC5',
                                 delta_p=.0001 if s != 'decada' and i == 0 else 1.))
        t = add_families(pd.DataFrame(rows))
        selected = t[t.papel_id.eq(0) & t.scenario.ne('decada')]
        np.testing.assert_allclose(selected.delta_p_holm_197, [.0197, .0197])
        with self.assertRaisesRegex(ValueError, '197'):
            add_families(pd.DataFrame(rows).iloc[1:])

    def test_common_check_detects_different_counts(self):
        a = self.estimates[self.estimates.variant.eq('referencia_n')].copy()
        a['cash_variant'], a['treatment'] = 'reference', 'HAC5'
        check_common(a, ['cash_variant', 'treatment'])
        a.loc[a.scenario.eq('decada_periodo_comum'), 'n_plus'] += 1
        with self.assertRaises(AssertionError):
            check_common(a, ['cash_variant', 'treatment'])


if __name__ == '__main__':
    unittest.main()

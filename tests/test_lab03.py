import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from lab02 import Config, estimate_security, holm, ols_hac
from lab03 import joint_halves, direction_rows, temporal_family, load_inputs, rolling


class TemporalTests(unittest.TestCase):
    def synthetic(self):
        index = pd.bdate_range('2019-01-01','2022-12-30')
        rng = np.random.default_rng(20261023)
        m = rng.normal(0,.012,len(index))
        q, d = (index.year>=2021).astype(float), (m>0).astype(float)
        y = .0002 + .7*m + .2*d*m + q*(.0001+.35*d*m) + rng.normal(0,.002,len(index))
        return pd.Series(y,index=index),pd.Series(m,index=index)

    def test_joint_point_contrast_matches_separate_models(self):
        y,m=self.synthetic();r=joint_halves(y,m)
        early=estimate_security(y,m,include=y.index.year<2021)
        late=estimate_security(y,m,include=y.index.year>=2021)
        self.assertEqual(r['status'],'ok')
        self.assertAlmostEqual(r['theta'],late['delta']-early['delta'],places=12)
        self.assertAlmostEqual(r['theta'],.35,delta=.08)

    def test_joint_covariance_retains_cross_half_boundary(self):
        y,m=self.synthetic();r=joint_halves(y,m)
        self.assertLess(r['covariance_identity_error'],1e-14)
        self.assertGreater(abs(r['cross_covariance_early_late']),1e-15)
        self.assertNotEqual(r['theta_se']**2,r['early_delta_se']**2+r['late_delta_se']**2)

    def test_exact_joint_design_and_n_over_n_minus_eight(self):
        y,m=self.synthetic();d=(m.to_numpy()>0).astype(float);q=(m.index.year>=2021).astype(float);x=m.to_numpy()
        design=np.column_stack([np.ones(len(x)),d,x,d*x,q,q*d,q*x,q*d*x])
        b,c=ols_hac(y.to_numpy(),design,np.ones(len(x),bool),5);r=joint_halves(y,m)
        self.assertAlmostEqual(r['theta'],b[7],places=13)
        self.assertAlmostEqual(r['theta_se']**2,c[7,7],places=13)

    def test_missing_and_neutral_scores_not_concatenated(self):
        y,m=self.synthetic();m.iloc[400]=0;y.iloc[[399,401]]=np.nan;r=joint_halves(y,m)
        valid=y.notna()&m.ne(0);yc=y[valid];mc=m[valid];compressed=joint_halves(yc,mc)
        self.assertAlmostEqual(r['theta'],compressed['theta'],places=12)
        self.assertGreater(abs(r['theta_se']-compressed['theta_se']),1e-9)
        self.assertTrue(y.iloc[[399,401]].isna().all())

    def test_bad_half_never_lowered_to_get_estimate(self):
        y,m=self.synthetic();mask=(y.index.year>=2021)|(np.arange(len(y))<30);r=joint_halves(y,m,include=mask)
        self.assertEqual(r['status'],'insufficient_segment');self.assertTrue(np.isnan(r['theta']))

    def annual_fixture(self):
        return pd.DataFrame([dict(scenario='recente',ticker='TEST',papel_id='TEST',company_id='X',setor_economico='setor',
            year=year,delta=value,delta_se=.1,status_conditional='ok')
            for year,value in zip(range(2021,2026),[.4,.3,.2,.5,.1])])

    def test_iut_requires_worst_year_in_both_directions(self):
        table=self.annual_fixture();rows=direction_rows(table,'recente',range(2021,2026));p={r['direction']:r['p_raw'] for r in rows}
        self.assertAlmostEqual(p['positive'],norm.sf(1.))
        self.assertAlmostEqual(p['negative'],norm.cdf(5.))
        self.assertGreater(p['positive'],.05)

    def test_one_insufficient_year_blocks_both_directions(self):
        table=self.annual_fixture();table.loc[2,'status_conditional']='insufficient_regimes_coverage_or_variance'
        for row in direction_rows(table,'recente',range(2021,2026)):
            self.assertTrue(np.isnan(row['p_raw']));self.assertEqual(row['years_required'],5);self.assertEqual(row['years_eligible'],4)
        with self.assertRaisesRegex(ValueError,'discard'):
            direction_rows(table.iloc[:-1],'recente',range(2021,2026))

    def test_zero_standard_error_does_not_manufacture_persistence(self):
        table=self.annual_fixture();table.loc[0,'delta_se']=0
        self.assertTrue(all(np.isnan(r['p_raw']) for r in direction_rows(table,'recente',range(2021,2026))))

    def test_family_474_reserves_missing_hypotheses(self):
        values=np.ones(474);values[0]=.0001;values[1]=np.nan
        adjusted=holm(values,family_size=474)
        self.assertAlmostEqual(adjusted[0],.0474);self.assertTrue(np.isnan(adjusted[1]))

    def test_joint_hac_changes_uncertainty_not_theta(self):
        y,m=self.synthetic();a=joint_halves(y,m,Config(hac_lags=0));b=joint_halves(y,m,Config(hac_lags=20))
        self.assertEqual(a['theta'],b['theta']);self.assertNotEqual(a['theta_se'],b['theta_se'])

    def test_authenticated_data_keeps_all_seven_missing_decade_cells(self):
        matrices,samples,reference,plan=load_inputs(ROOT,Path(os.environ['LAB03_X_ARCHIVE']),Path(os.environ['LAB03_Y_ARCHIVE']))
        self.assertEqual(plan['family_size'],474)
        for m in matrices.values():
            self.assertEqual(int(m['decada'].isna().sum().sum()),7)
            self.assertEqual(m['decada'].loc['2024-10-30','LIGT3.SA'],matrices['referencia_n']['decada'].loc['2024-10-30','LIGT3.SA'])
        self.assertEqual([len(samples[s]) for s in ['decada','decada_periodo_comum','recente']],[80,80,117])

    def test_family_composition_and_common_reuse(self):
        rows=[]
        for scenario,size,years in [('decada',80,range(2016,2026)),('recente',117,range(2021,2026)),('decada_periodo_comum',80,range(2021,2026))]:
            for i in range(size):
                rows += [dict(scenario=scenario,ticker=str(i),papel_id=i,company_id=str(i),setor_economico='S',year=year,
                              delta=.5,delta_se=.1,status_conditional='ok') for year in years]
        annual=pd.DataFrame(rows)
        halves=pd.DataFrame([dict(ticker=str(i),papel_id=i,company_id=str(i),setor_economico='S',status='ok',
                                 theta=.1,theta_se=.2,theta_p=.6,theta_ci_low=-.3,theta_ci_high=.5) for i in range(80)])
        family,common=temporal_family(annual,halves)
        self.assertEqual(len(family),474);self.assertEqual(len(common),160)
        self.assertEqual(family.test.eq('magnitude_late_minus_early').sum(),80)
        a=common.set_index(['papel_id','direction']);b=family[family.scenario.eq('recente')].set_index(['papel_id','direction']).loc[a.index]
        np.testing.assert_array_equal(a.p_holm_474,b.p_holm_474)
        annual.loc[annual.scenario.eq('decada')&annual.papel_id.eq(0)&annual.year.eq(2017),'status_conditional']='insufficient'
        family,_=temporal_family(annual,halves)
        self.assertEqual(family.p_raw.isna().sum(),2);self.assertEqual(len(family),474)

    def test_rolling_uses_calendar_width_step_and_shared_results(self):
        y,m=self.synthetic();matrix=pd.DataFrame({'TEST':y.iloc[:300],'^BVSP':m.iloc[:300]})
        sample=pd.DataFrame([dict(ticker_yahoo='TEST',papel_id=1,company_id='X',setor_economico='S')])
        matrices={'referencia_n':{'decada':matrix,'recente':matrix}}
        samples={s:sample for s in ['decada','recente','decada_periodo_comum']}
        out=rolling(matrices,samples,lambda *args,**kw:None)
        a=out[out.scenario.eq('decada')]
        self.assertEqual(a.width.tolist(),[252,252,252])
        self.assertEqual(a.window_start.tolist(),[str(matrix.index[i].date()) for i in [0,21,42]])
        self.assertTrue(a.n_sessions.eq(252).all())
        np.testing.assert_array_equal(out[out.scenario.eq('recente')].delta,out[out.scenario.eq('decada_periodo_comum')].delta)

    def test_wrong_y_archive_rejected(self):
        with self.assertRaisesRegex(ValueError,'Y archive hash mismatch'):
            load_inputs(ROOT,Path(os.environ['LAB03_X_ARCHIVE']),Path(os.environ['LAB03_X_ARCHIVE']))


if __name__=='__main__':unittest.main()

import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03b import risk,empirical_loss_tail,eta_squared,sector_descriptions

class ScientificTests(unittest.TestCase):
    def setUp(self):
        self.index=pd.bdate_range('2020-01-01',periods=300)
        self.market=pd.Series(np.random.default_rng(42).normal(0,.01,300),index=self.index)
    def test_perfect_market_model(self):
        r=risk(2*self.market+.001,self.market)
        self.assertAlmostEqual(r['beta_market_model'],2)
        self.assertAlmostEqual(r['r2_market_model'],1)
        self.assertLess(r['residual_log_variance'],1e-25)
    def test_negative_beta_positive_variance(self):
        r=risk(-self.market,self.market)
        self.assertAlmostEqual(r['beta_market_model'],-1)
        self.assertGreater(r['market_associated_log_variance'],0)
    def test_residual_orthogonality_identity(self):
        y=pd.Series(np.random.default_rng(10).normal(0,.02,300),index=self.index)
        r=risk(y,self.market)
        self.assertLess(r['variance_identity_error'],1e-17)
        self.assertAlmostEqual(r['r2_market_model'],np.corrcoef(y,self.market)[0,1]**2)
    def test_missing_pairs_preserved(self):
        a=self.market.copy();a.iloc[[1,4]]=np.nan;r=risk(a,self.market)
        self.assertEqual(r['n_missing'],2);self.assertEqual(r['n_pairs'],298)
        self.assertEqual(int(a.isna().sum()),2)
    def test_calendar_mismatch_rejected(self):
        with self.assertRaises(AssertionError):risk(self.market,self.market.shift(1).iloc[1:])
    def test_insufficient_unchanged_floor(self):
        self.assertEqual(risk(self.market.iloc[:190],self.market.iloc[:190])['status'],'insufficient')
    def test_fractional_tail(self):
        losses=np.array([-.1,0,.05,.1,.2]);r=empirical_loss_tail(np.log1p(-losses),.7)
        self.assertAlmostEqual(r['var95_simple_loss'],.1)
        self.assertAlmostEqual(r['es95_simple_loss'],(.2+.5*.1)/1.5)
    def test_tail_ties(self):
        r=empirical_loss_tail(np.full(250,np.log(.9)))
        self.assertAlmostEqual(r['var95_simple_loss'],.1);self.assertAlmostEqual(r['es95_simple_loss'],.1)
    def test_signed_losses_not_clipped(self):
        self.assertLess(empirical_loss_tail(np.full(250,np.log(1.1)))['es95_simple_loss'],0)
    def test_downside_target_zero_not_market_regime(self):
        a=abs(self.market)+.001;r=risk(a,self.market)
        self.assertEqual(r['downside_log_deviation_zero'],0);self.assertGreater(r['n_minus'],0)
    def test_eta_grouping_and_undefined_constant(self):
        self.assertAlmostEqual(eta_squared([0,0,2,2],['a','a','b','b']),1)
        self.assertTrue(np.isnan(eta_squared([1,1],['a','b'])))
    def test_eta_rejects_silent_missing_asset(self):
        self.assertTrue(np.isnan(eta_squared([0,np.nan,2],['a','a','b'])))

if __name__=='__main__':unittest.main()

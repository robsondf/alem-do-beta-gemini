import sys,unittest
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03h import period_fits,cdf_family,conditional_variance,economic_rows


class HOracleTests(unittest.TestCase):
    def test_period_fit_matches_joint_OLS_with_gap_and_missing(self):
        rng=np.random.default_rng(301);m=rng.normal(0,.02,850);y=.001+.8*m-.2*m*(m>0)+rng.normal(0,.01,850);y[19]=np.nan;frame=pd.DataFrame({'^BVSP':m,'A':y});keep=np.ones(850,bool);keep[250:275]=False
        r=period_fits(frame,['A'],keep).iloc[0];on=keep&np.isfinite(y);D=m>0;X=np.column_stack([np.ones(850),D,m,D*m]);coef=np.linalg.lstsq(X[on],y[on],rcond=None)[0]
        self.assertAlmostEqual(r.delta,coef[3],places=11);self.assertAlmostEqual(r.intercept_jump,coef[1],places=11);self.assertEqual(r.n_missing,1);self.assertEqual(r.n_pairs,824)

    def test_AR_variance_matches_explicit_covariance(self):
        rng=np.random.default_rng(302);A=rng.normal(size=(15,4));h=np.linspace(.6,1.6,15);phi=.3;K=phi**abs(np.arange(15)[:,None]-np.arange(15));B=A*h[:,None];C=B.sum(1);expected=.3*C@K@C+.7*sum(B[:,i]@K@B[:,i] for i in range(4));self.assertAlmostEqual(conditional_variance(A,h,phi),expected,places=10)

    def test_CDF_reorders_before_Holm_and_counts_ties(self):
        obs=pd.DataFrame([dict(profile='A',scenario='d',statistic='mean',p_centered=.01),dict(profile='B',scenario='d',statistic='mean',p_centered=.03)]);null=pd.DataFrame([dict(profile=p,scenario='d',statistic='mean',p_centered=v) for p,values in [('A',[.001,.01,.4,.8]),('B',[.1,.2,.5,.9])] for v in values]);r=cdf_family(obs,null)
        np.testing.assert_allclose([x['p_calibrated_diagnostic'] for x in r],[.6,.2]);np.testing.assert_allclose([x['p_calibrated_Holm_diagnostic'] for x in r],[.6,.4]);self.assertEqual(r[0]['null_tail_count'],2)

    def test_scale_uses_log_of_simple_shock_and_keeps_intercept(self):
        point=pd.DataFrame([dict(profile='daily',papel_id='X',ticker='A',delta_early=-.2,delta_late=-.1,intercept_jump_early=.002,intercept_jump_late=.001)]);r=economic_rows(point,[-.05]);self.assertAlmostEqual(r.iloc[0].down_minus_up_linear_log,.2*np.log(.95));self.assertAlmostEqual(r.iloc[0].down_minus_up_full_projection_log,.2*np.log(.95)-.002);self.assertNotAlmostEqual(r.iloc[0].log_market,-.05)


if __name__=='__main__':unittest.main()

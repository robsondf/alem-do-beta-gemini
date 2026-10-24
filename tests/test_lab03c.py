import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03c import kernel,project,holm_rows,probability,panel_rate,draw_errors
from lab02 import ols_hac,holm


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.rng=np.random.default_rng(71);self.m=self.rng.normal(0,.02,300)
        self.m[[6,81]]=0;self.valid=np.ones((300,2),bool);self.valid[[21,22,90],0]=False
        self.k=kernel(self.m,self.valid)
        self.y=self.rng.normal(0,.03,(300,2))

    def test_joint_production_covariance(self):
        e,s=project(self.y,self.k)
        x=np.column_stack([np.ones(300),self.m>0,self.m,(self.m>0)*self.m])
        for j in range(2):
            for h,lag in enumerate([0,5,20]):
                b,c=ols_hac(self.y[:,j],x,self.valid[:,j]&(self.m!=0),lag)
                np.testing.assert_allclose(e[j],b[3],atol=1e-12)
                np.testing.assert_allclose(s[h,j],np.sqrt(c[3,3]),rtol=1e-11,atol=1e-12)

    def test_injection_and_intercepts(self):
        a,s=project(self.y,self.k);plus=self.m>0
        shifted=self.y+1.7+.8*plus[:,None]+.4*self.m[:,None]+.25*(self.m*plus)[:,None]
        b,t=project(shifted,self.k)
        np.testing.assert_allclose(b,a+.25,atol=1e-12)
        np.testing.assert_allclose(s,t,atol=1e-12)

    def test_missing_scores_and_neutrals(self):
        a,s=project(self.y,self.k);y=self.y.copy()
        y[~self.k['valid']]=1e9;b,t=project(y,self.k)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(s,t)

    def test_holm_reference(self):
        p=np.array([[.0001,.03,.2,.9],[.01,.01,.04,.08]])
        got=holm_rows(p)
        for i in range(2):
            np.testing.assert_allclose(got[i],np.asarray(holm(pd.Series(p[i]),family_size=4)))

    def test_wilson_endpoints(self):
        p,se,lo,hi=probability(np.zeros((1000,2),bool))
        np.testing.assert_array_equal(p,[0,0]);self.assertTrue((hi>0).all())
        self.assertTrue((hi<.004).all())
        p,se,lo,hi=probability(np.ones((1000,2),bool));self.assertTrue((lo<1).all())

    def test_mcse_respects_cross_dependence(self):
        event=np.arange(1000)%2==0;a=np.column_stack([event,event])
        p,se=panel_rate(a);self.assertAlmostEqual(p,.5)
        self.assertAlmostEqual(se,event.std(ddof=1)/np.sqrt(1000))
        self.assertTrue(np.isnan(panel_rate(np.empty((1000,0)))[0]))

    def test_floors(self):
        with self.assertRaises(ValueError):kernel(self.m[:190],self.valid[:190])

    def test_rng_repetition_and_order(self):
        d=dict(market=self.m,scale=np.ones(300),nuisance=pd.DataFrame({'sigma':np.ones(117)}))
        plan=dict(seed_entropy=20261023,mechanisms=[{'phi':0.,'heteroscedastic':False}])
        a=draw_errors(d,0,3,plan);b=draw_errors(d,0,4,plan);c=draw_errors(d,0,3,plan)
        np.testing.assert_array_equal(a,c);self.assertFalse(np.array_equal(a,b))

    def test_point_estimates_do_not_depend_on_hac(self):
        a,s=project(self.y,self.k,lags=(0,))
        b,t=project(self.y,self.k,lags=(5,20))
        np.testing.assert_array_equal(a,b);self.assertEqual(t.shape,(2,2))

    def test_contrast_weights(self):
        w=self.k['weights'];np.testing.assert_allclose(w.sum(axis=0),0,atol=1e-12)
        np.testing.assert_allclose((w*self.m[:,None]).sum(axis=0),0,atol=1e-12)
        np.testing.assert_allclose((w*(self.m*(self.m>0))[:,None]).sum(axis=0),1,atol=1e-12)


if __name__=='__main__':unittest.main()

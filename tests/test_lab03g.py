import sys,unittest
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03g import PanelOperator,block_counts,statistics


class BootstrapOperatorOracleTests(unittest.TestCase):
    def test_operator_equals_explicit_weighted_full_OLS(self):
        rng=np.random.default_rng(130);N=650;m=rng.normal(0,.02,N);Y=rng.normal(0,.03,(N,3));Y[17,1]=np.nan
        frame=pd.DataFrame(Y,columns=list('ABC'));frame['^BVSP']=m;counts=block_counts(N,21,9,np.random.default_rng(9));op=PanelOperator(frame,list('ABC'),counts,offsets=(-1,0,1));point,boot=op.evaluate()
        M=np.column_stack([frame['^BVSP'].shift(k) for k in [-1,0,1]]);D=m>0;X=np.column_stack([np.ones(N),D,M,M*D[:,None]])
        for b in range(9):
            ids=np.repeat(np.arange(N),counts[b].astype(int))
            for j in range(3):
                on=np.isfinite(X[ids]).all(1)&np.isfinite(Y[ids,j]);coef=np.linalg.lstsq(X[ids][on],Y[ids,j][on],rcond=None)[0]
                self.assertAlmostEqual(boot[b,0,j],coef[5:].sum(),places=10)

    def test_null_linear_component_annihilates_for_every_draw(self):
        rng=np.random.default_rng(131);N=700;m=rng.normal(0,.02,N);frame=pd.DataFrame({'A':rng.normal(0,.03,N),'^BVSP':m});counts=block_counts(N,21,21,np.random.default_rng(3));op=PanelOperator(frame,['A'],counts)
        p,b=op.evaluate();pp,bb=op.evaluate(frame[['A']].to_numpy()*3+.002+.8*m[:,None]);np.testing.assert_allclose(pp,p*3,atol=1e-11);np.testing.assert_allclose(bb,b*3,atol=1e-11)

    def test_counts_preserve_original_lag_rows(self):
        N=650;rng=np.random.default_rng(132);m=rng.normal(0,.02,N);y=np.r_[0,m[:-1]]+rng.normal(0,.001,N);a=pd.DataFrame({'A':y,'^BVSP':m});c=block_counts(N,21,3,np.random.default_rng(4));op=PanelOperator(a,['A'],c,offsets=(0,1));p,b=op.evaluate()
        X=np.column_stack([np.ones(N),m>0,m,np.r_[np.nan,m[:-1]],m*(m>0),np.r_[np.nan,m[:-1]]*(m>0)])
        for i in range(3):
            ids=np.repeat(np.arange(N),c[i].astype(int));ok=ids>0;coef=np.linalg.lstsq(X[ids[ok]],y[ids[ok]],rcond=None)[0];self.assertAlmostEqual(b[i,0,0],coef[4:].sum(),places=10)

    def test_statistics_do_not_drop_invalid_draws(self):
        p=np.array([[.1,.2,.3]]);b=np.tile(p,(20,1,1));b[3]=np.nan;s=statistics(p,b)
        for v in s.values():self.assertTrue(np.isnan(v['p_centered'][0]));self.assertEqual(v['invalid_draws'][0],1)


if __name__=='__main__':unittest.main()

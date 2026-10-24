import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.linalg import toeplitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03f import fit,sufficient,deltas,resample_moments,profile_data,contiguous_segments


class PostReviewOracleTests(unittest.TestCase):
    def test_joint_hac_against_dense_calendar_sandwich(self):
        rng=np.random.default_rng(21);m=rng.normal(0,.02,650);y=rng.normal(0,.03,650);y[[17,18]]=np.nan
        keep=np.ones(650,bool);keep[200:210]=False;f,terms,score=fit(y,m,keep)
        on=keep&np.isfinite(y);D=(m>0).astype(float);X=np.column_stack([np.ones(650),D,m,D*m]);x=X[on]
        coef=np.linalg.lstsq(x,y[on],rcond=None)[0];bread=np.linalg.inv(x.T@x)
        u=np.zeros((650,4));u[on]=x*(y[on]-x@coef)[:,None]
        K=toeplitz(np.r_[1-np.arange(6)/6,np.zeros(644)])
        V=bread@u.T@K@u@bread*on.sum()/(on.sum()-4)
        self.assertAlmostEqual(f['delta'],coef[3],places=11)
        self.assertAlmostEqual(f['delta_se_hac5'],np.sqrt(V[3,3]),places=11)
        self.assertAlmostEqual(f['intercept_jump_se_hac5'],np.sqrt(V[1,1]),places=11)
        self.assertEqual(score[205],0.)

    def test_dynamic_sum_contrast_has_joint_covariance(self):
        rng=np.random.default_rng(22);m=rng.normal(0,.02,650);y=rng.normal(0,.03,650)
        f,_,_=fit(y,m,offsets=(-1,0,1));D=(m[1:-1]>0).astype(float)
        M=np.column_stack([m[2:],m[1:-1],m[:-2]]);X=np.column_stack([np.ones(648),D,M,M*D[:,None]])
        coef=np.linalg.lstsq(X,y[1:-1],rcond=None)[0]
        self.assertAlmostEqual(f['delta'],sum(coef[5:]),places=11)
        self.assertEqual(f['n_eligible'],648)

    def test_sufficient_refit_matches_all_ols_and_ignores_nan(self):
        rng=np.random.default_rng(23);m=rng.normal(0,.02,650);Y=rng.normal(0,.03,(650,4));Y[17,1]=np.nan
        frame=pd.DataFrame(Y,columns=list('ABCD'));frame['^BVSP']=m
        actual=deltas(sufficient(frame,list('ABCD')).sum(0),4)[0]
        for j,n in enumerate('ABCD'):self.assertAlmostEqual(actual[j],fit(frame[n],m)[0]['delta'],places=11)

    def test_block_sums_equal_explicit_shared_indices(self):
        a=np.arange(73*6,dtype=float).reshape(73,6);L=11;B=17;seed=24
        actual=resample_moments(a,L,B,np.random.default_rng(seed));rng=np.random.default_rng(seed)
        starts=rng.integers(0,73-L+1,size=(B,7))
        for i,row in enumerate(starts):
            ids=np.concatenate([np.arange(v,v+L) for v in row])[:73]
            np.testing.assert_array_equal(actual[i],a[ids].sum(0))

    def test_missing_daily_return_makes_whole_week_missing(self):
        index=pd.bdate_range('2021-01-04',periods=40);a=pd.DataFrame({'A':.01,'^BVSP':.02},index=index)
        a.iloc[12,0]=np.nan;weekly,_=profile_data(a,'weekly')
        self.assertTrue(np.isnan(weekly.loc['2021-01-22','A']))
        self.assertAlmostEqual(weekly.loc['2021-01-15','A'],.05)
        self.assertAlmostEqual(weekly.loc['2021-01-22','^BVSP'],.10)

    def test_exclusion_blocks_never_cross_crisis_gap(self):
        index=pd.bdate_range('2019-01-01','2020-12-31');parts=contiguous_segments(index,'exclude_2020_03')
        self.assertEqual(len(parts),2)
        self.assertTrue((index[parts[0]]<'2020-03-01').all())
        self.assertTrue((index[parts[1]]>'2020-03-31').all())
        for x in parts:self.assertTrue((np.diff(x)==1).all())


if __name__=='__main__':unittest.main()

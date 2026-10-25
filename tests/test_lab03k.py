import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03k import joint,delta_weights,coefficients,floors

class JointContrasts(unittest.TestCase):
 def test_joint_invariance_to_turnover_coordinates(self):
  rng=np.random.default_rng(40);point=np.array([.04,.06]);draws=rng.multivariate_normal(point,[[.001,.0004],[.0004,.002]],size=4999);T=np.array([[1,0],[1,1]])
  a=joint(point,draws);b=joint(T@point,draws@T.T)
  self.assertEqual(a['p'],b['p']);self.assertAlmostEqual(a['statistic'],b['statistic'],places=10)
 def test_rank_singular_is_reported(self):
  d=np.arange(100,dtype=float);self.assertEqual(joint([1,1],np.column_stack([d,d]))['status'],'singular_covariance')
 def test_masked_temporal_functional_matches_weighted_regressions(self):
  rng=np.random.default_rng(1);m=rng.normal(0,.02,300);y=.001+.8*m+.3*m*(m>0)+rng.normal(0,.03,300);v=np.ones(300,bool);v[[2,6,78]]=False
  W=rng.integers(0,4,size=(4,300)).astype(float);Q=delta_weights(v,m,W)
  for b in range(4):
   slopes=[]
   for mask in [m>0,m<0]:
    use=v&mask&(W[b]>0);x=np.column_stack([np.ones(use.sum()),m[use]]);s=np.sqrt(W[b,use]);slopes.append(np.linalg.lstsq(x*s[:,None],y[use]*s,rcond=None)[0][1])
   self.assertAlmostEqual(Q[b]@y,slopes[0]-slopes[1],places=11)
  self.assertTrue(np.all(Q[:,~v]==0))
 def test_reestimated_preperiod_control_matches_dense_OLS(self):
  rng=np.random.default_rng(3);X=np.column_stack([np.ones(62),rng.normal(size=(62,2))]);b=rng.normal(size=(8,62));y=rng.normal(size=(8,62));fast=coefficients(y,X,b)
  for i in range(8):np.testing.assert_allclose(fast[i],np.linalg.lstsq(np.column_stack([X,b[i]]),y[i],rcond=None)[0],rtol=1e-10,atol=1e-12)
 def test_no_relaxation_of_temporal_floors(self):
  m=np.tile([-.01,.01],125);r=np.ones((250,3));r[:14,1]=np.nan;r[m>0,2]=np.nan
  self.assertEqual(floors(r,m).tolist(),[True,False,False])

if __name__=='__main__':unittest.main()

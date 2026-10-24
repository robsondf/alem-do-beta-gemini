import sys,unittest
from pathlib import Path
import numpy as np
from scipy.linalg import toeplitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03c import kernel
from lab03e_inference import part,project,bank_paths

class InferenceOracleTests(unittest.TestCase):
 def test_full_ols_sandwich_with_calendar_gaps(self):
  rng=np.random.default_rng(74);m=rng.normal(0,.02,700);m[10]=0;valid=np.ones((700,1),bool);valid[[5,35,98]]=False;k=kernel(m,valid);X,P,h,w,n=part(k);op=dict(X=X,P=P,weight=w,score_weight=w/(1-h)*np.sqrt(n/(n-4)));Y=rng.normal(0,.03,(700,7));e,s=project(Y,op);D=(m>0).astype(float);design=np.column_stack([np.ones(700),D,m,D*m]);on=k['valid'][:,0];xx=design[on];bread=np.linalg.inv(xx.T@xx);lev=np.sum((xx@bread)*xx,1);K=toeplitz(np.r_[1-np.arange(6)/6,np.zeros(694)])
  for j in range(7):
   coef=np.linalg.lstsq(xx,Y[on,j],rcond=None)[0];res=(Y[on,j]-xx@coef)/(1-lev);scores=np.zeros((700,4));scores[on]=xx*res[:,None];cov=bread@scores.T@K@scores@bread*n/(n-4);self.assertAlmostEqual(e[j],coef[3],places=11);self.assertAlmostEqual(s[j],np.sqrt(cov[3,3]),places=11)
 def test_batch_generator_is_chunk_invariant(self):
  d=dict(market=np.ones(600),scale=np.linspace(.7,1.2,600))
  for mi in range(3):
   a=bank_paths(d,mi,np.random.default_rng(9),4);rng=np.random.default_rng(9);b=np.column_stack([bank_paths(d,mi,rng,1),bank_paths(d,mi,rng,3)]);np.testing.assert_array_equal(a,b)
 def test_null_contrast_is_location_scale_invariant(self):
  rng=np.random.default_rng(15);m=rng.normal(0,.02,600);k=kernel(m,np.ones((600,1),bool));X,P,h,w,n=part(k);op=dict(X=X,P=P,weight=w,score_weight=w/(1-h)*np.sqrt(n/(n-4)));y=rng.normal(0,.02,(600,2));e,s=project(y,op);z=y*3+np.where(m[:,None]>0,.03,.02)+.5*m[:,None];ee,ss=project(z,op);np.testing.assert_allclose(e/s,ee/ss,atol=1e-12)
 def test_partial_contrast_never_uses_missing_cells(self):
  rng=np.random.default_rng(2);m=rng.normal(0,.02,600);valid=np.ones((600,1),bool);valid[17]=False;k=kernel(m,valid);X,P,h,w,n=part(k);op=dict(X=X,P=P,weight=w,score_weight=w/(1-h)*np.sqrt(n/(n-4)));y=rng.normal(0,.02,(600,2));a=project(y,op);y[17]=np.nan;b=project(y,op)
  for x,z in zip(a,b):np.testing.assert_allclose(x,z,atol=1e-12)
class PredictiveOracleTests(unittest.TestCase):
 def test_operator_matches_full_past_only_forecast(self):
  import pandas as pd
  from lab03e_prediction import forecast_weights
  from lab03d_prediction import forecast_fold
  rng=np.random.default_rng(845);m=rng.normal(0,.02,800);Y=rng.normal(0,.03,(800,2));Y[550,0]=np.nan;frame=pd.DataFrame({'A':Y[:,0],'B':Y[:,1],'^BVSP':m});targets=np.arange(701,710);old,_=forecast_fold(frame,['A','B'],700,252,targets)
  for j in range(2):
   used,tr,co,_=forecast_weights(m,np.isfinite(Y[:,j]),np.arange(449,701),targets);np.testing.assert_allclose(tr@Y[used,j],old[:,j,2],atol=1e-12);np.testing.assert_allclose(co@Y[used,j],old[:,j,3],atol=1e-12)
 def test_future_masks_do_not_change_prior_operator(self):
  from lab03e_prediction import forecast_weights
  rng=np.random.default_rng(5);m=rng.normal(0,.02,900);mask=np.ones(900,bool);a=forecast_weights(m,mask,np.arange(449,701),np.arange(701,710));mask[710:]=False;b=forecast_weights(m,mask,np.arange(449,701),np.arange(701,710))
  for x,z in zip(a[:3],b[:3]):np.testing.assert_array_equal(x,z)
 def test_sparse_bootstrap_equals_direct_resampled_indices(self):
  from lab03e_prediction import bootstrap_bank,resample_sums
  rng=np.random.default_rng(711);Y=rng.normal(size=(73,4));valid=np.ones((73,2),bool);valid[17,0]=False;p=dict(targets=np.arange(73),window=252,panel_index=0,valid=valid);bank=bootstrap_bank(p,21,19,B=31);actual=resample_sums(Y,bank);rng=np.random.default_rng(np.random.SeedSequence([19,701,252,0,21]));starts=rng.integers(0,53,size=(31,4))
  for b,row in enumerate(starts):
   ids=np.concatenate([np.arange(x,x+21) for x in row])[:73];np.testing.assert_allclose(actual[b],Y[ids].sum(0),atol=1e-12);np.testing.assert_array_equal(bank['denominator'][b],valid[ids].sum(0))
 def test_exact_risk_includes_train_target_ar_covariance(self):
  import pandas as pd
  from scipy import sparse
  from lab03e_prediction import oracle_risk
  rng=np.random.default_rng(8);N=600;m=rng.normal(0,.02,N);targets=np.arange(550,560);tr=np.zeros((10,N));co=np.zeros_like(tr)
  for j,t in enumerate(targets):
   tr[j,t-50:t]=1/50;co[j,t-30:t]=1/30
  pp=dict(targets=targets,assets=np.array([0,1]),sample=[0,1],valid=np.ones((10,2),bool),operators=[dict(members=np.array([0,1]),traditional=sparse.csr_matrix(tr),conditional=sparse.csr_matrix(co))]);d=dict(market=m,nuisance=pd.DataFrame({'beta_base':[.8,1.2],'sigma':[.02,.03]}))
  for phi in [0.,.3]:
   observed=oracle_risk(d,pp,phi,.25);Sigma=toeplitz(phi**np.arange(N));E=np.eye(N)[targets];qt=E-tr;qc=E-co
   for j,(b,sd) in enumerate(zip([.8,1.2],[.02,.03])):
    mu=b*m+.25*m*(m>0);truth=np.mean((qt@mu)**2-(qc@mu)**2+sd**2*np.diag(qt@Sigma@qt.T-qc@Sigma@qc.T));self.assertAlmostEqual(observed[j],truth,places=13)

class EconomicOracleTests(unittest.TestCase):
 def test_exact_delete_one_contrast_identity(self):
  from lab03e_economic import fit
  rng=np.random.default_rng(512);m=rng.normal(0,.02,700);y=.002+.8*m+.3*m*(m>0)+rng.normal(0,.02,700);a,inf=fit(m,y);j=np.argmax(abs(inf));keep=np.ones(700,bool);keep[j]=False;b,_=fit(m,y,keep);self.assertAlmostEqual(b['delta']-a['delta'],-inf[j],places=11)
 def test_diagnostic_keeps_original_coverage_denominator(self):
  from lab03e_economic import fit
  rng=np.random.default_rng(154);m=rng.normal(0,.02,700);y=rng.normal(0,.03,700);keep=np.ones(700,bool);keep[:36]=False;b,_=fit(m,y,keep);self.assertEqual(b['status'],'insufficient');self.assertEqual(b['n_pairs'],664);self.assertAlmostEqual(b['coverage'],664/700);self.assertNotIn('delta',b)
 def test_neighborhood_masks_preserve_data_and_use_sessions(self):
  import pandas as pd
  from lab03e_economic import fit,masks
  rng=np.random.default_rng(411);m=rng.normal(0,.02,700);y=rng.normal(0,.03,700);y[4]=np.nan;original=y.copy();a,inf=fit(m,y);out=masks(m,y,pd.bdate_range('2020-01-01',periods=700),inf,'ABCB4.SA');np.testing.assert_array_equal(np.flatnonzero(~out['neighbor1_known_missing_returns']),[3,4,5]);np.testing.assert_array_equal(np.flatnonzero(~out['neighbor5_known_missing_returns']),np.arange(10));np.testing.assert_array_equal(original,y)

if __name__=='__main__':unittest.main()

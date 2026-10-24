import sys,unittest,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.linalg import toeplitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lab03c import kernel
from lab03d_inference import details,hac_variance,multiplier_maxima,temporal_pvalues
from lab03d_prediction import forecast_fold,forecast_panel,masked_matrix,MODELS

class InferenceTests(unittest.TestCase):
 def test_fast_envelope_statistic_matches_full_score_projection(self):
  from lab03d_inference import static_project
  from lab03d_envelope import precalculate,statistic
  rng=np.random.default_rng(9);m=rng.normal(0,.02,600);noise=rng.normal(0,.03,(600,117))
  panels=[dict(kernel=kernel(m,np.ones((600,80),bool)),time_index=np.arange(600),asset_index=np.arange(80)),dict(kernel=kernel(m[300:],np.ones((300,117),bool)),time_index=np.arange(300,600),asset_index=np.arange(117))]
  d=dict(market=m,panels=panels);precalculate(d);e,se=statistic(d,noise);a,s,_=static_project(d,noise);np.testing.assert_allclose(e,a,atol=1e-12);np.testing.assert_allclose(se,s[1],atol=1e-12)
 def test_rank_envelope_keeps_ties_and_nonzero_pvalues(self):
  from lab03d_rank import rank_p
  bank=np.stack([np.tile(np.arange(9)[:,None],(1,2)),np.tile(np.arange(1,10)[:,None],(1,2)),np.tile(np.arange(9)[:,None],(1,2))]);p=rank_p(np.array([[8.,100.],[0.,0.]]),bank,bank,np.array([0,1]))
  np.testing.assert_allclose(p,[[.3,.1],[1.,1.]])
 def test_frozen_protocol_is_accepted_by_static_analysis(self):
  from lab03d_inference import analyze_static
  root=Path(__file__).resolve().parents[1];plan=json.loads((root/'data/lab03d/plano_v1.json').read_text())
  ids=np.r_[np.arange(80),np.arange(117)];d=dict(design=pd.DataFrame({'papel_id':ids,'scenario':['decada']*80+['recente']*117}),nuisance=pd.DataFrame({'papel_id':np.arange(117)}))
  a=dict(error=np.zeros((3,2,197)),se=np.ones((3,2,2,197)),critical=np.full((3,2),4.))
  result=analyze_static(d,plan,a);self.assertEqual(len(result['static_family']),81)
 def test_full_design_hac_and_hc3(self):
  rng=np.random.default_rng(91);m=rng.normal(0,.02,600);m[11]=0;valid=np.ones((600,2),bool);valid[[7,80],0]=False;k=kernel(m,valid);y=rng.normal(0,.03,(600,2));delta,s,_,lev=details(y,k)
  X=np.column_stack([np.ones(600),m>0,m,m*(m>0)])
  for j in range(2):
   on=k['valid'][:,j];xx=X[on];b=np.linalg.lstsq(xx,y[on,j],rcond=None)[0];bread=np.linalg.inv(xx.T@xx);h=np.einsum('ij,jk,ik->i',xx,bread,xx)
   np.testing.assert_allclose(lev[on,j],h,atol=1e-12);self.assertAlmostEqual(delta[j],b[3])
   for method in range(2):
    scores=np.zeros((600,4));e=y[on,j]-xx@b
    if method:e/=1-h
    scores[on]=xx*e[:,None];meat=scores.T@scores
    for lag in range(1,6):
     cross=scores[lag:].T@scores[:-lag];meat+=(1-lag/6)*(cross+cross.T)
    oracle=(bread@meat@bread)[3,3]*on.sum()/(on.sum()-4)
    got=hac_variance(s)[method,j]*k['correction'][j];self.assertAlmostEqual(got,oracle,places=12)
 def test_bartlett_factor_and_rank_boundary(self):
  score=np.random.default_rng(4).normal(size=(31,6));c,maxima,cov=multiplier_maxima(score,np.random.default_rng(8))
  weights=np.maximum(0,1-np.arange(31)/6);expected=score.T@toeplitz(weights)@score
  np.testing.assert_allclose(cov,expected,rtol=1e-12,atol=1e-12)
  self.assertEqual(c,np.sort(maxima)[950]);values=np.array([c-.001,c,c+.001]);p=(1+(maxima[:,None]>=values).sum(0))/1000
  np.testing.assert_array_equal(p<.05,values>c)
 def test_injection_keeps_both_covariances(self):
  rng=np.random.default_rng(4);m=rng.normal(0,.02,300);k=kernel(m,np.ones((300,3),bool));y=rng.normal(0,.02,(300,3));a,s,_,_=details(y,k);b,t,_,_=details(y+.3*(m*(m>0))[:,None]+2+3*(m>0)[:,None],k)
  np.testing.assert_allclose(b,a+.3,atol=1e-12);np.testing.assert_allclose(s,t,atol=1e-12)
 def test_iut_never_drops_an_annual_component(self):
  d=dict(annual_map=np.array([[0,1,2],[1,2,-1]]));a=np.array([[5.,-1.,5.]]);se=np.ones_like(a)
  p=temporal_pvalues(d,a,se,np.zeros((1,1)),np.ones((1,1)))
  self.assertGreater(p[0,1],.8);self.assertGreater(p[0,2],.8);self.assertEqual(p.shape,(1,5))

class ForecastTests(unittest.TestCase):
 def setUp(self):
  rng=np.random.default_rng(72);self.m=rng.normal(0,.02,1300);self.m[50]=0;self.y=.001+1.2*self.m+.3*self.m*(self.m>0)+rng.normal(0,.02,1300)
  self.a=pd.DataFrame({'A':self.y,'B':self.y*.5+rng.normal(0,.01,1300),'^BVSP':self.m},index=pd.bdate_range('2016-01-01',periods=1300));self.a.iloc[700,0]=np.nan
 def test_future_data_cannot_change_earlier_forecasts(self):
  idx=np.arange(801,821);base,_=forecast_fold(self.a,['A','B'],800,252,idx);changed=self.a.copy();changed.iloc[815:,:]=123.45
  got,_=forecast_fold(changed,['A','B'],800,252,idx)
  np.testing.assert_array_equal(base[idx<=815],got[idx<=815])
 def test_old_data_outside_rolling_window_cannot_change_forecast(self):
  idx=np.arange(801,810);a,_=forecast_fold(self.a,['A','B'],800,252,idx);b=self.a.copy();b.iloc[:549,:]=100
  got,_=forecast_fold(b,['A','B'],800,252,idx);np.testing.assert_array_equal(a,got)
 def test_full_ols_and_brute_force_market_integration(self):
  idx=np.arange(801,810);f,_=forecast_fold(self.a,['A','B'],800,252,idx);train=self.a.iloc[549:801];m=train['^BVSP'].to_numpy();xx=np.column_stack([np.ones(252),m>0,m,m*(m>0)])
  arx=np.column_stack([np.ones(251),m[:-1]]);ar=np.linalg.lstsq(arx,m[1:],rcond=None)[0];e=m[1:]-arx@ar;e-=e.mean()
  for j,col in enumerate(['A','B']):
   y=train[col].to_numpy();ok=np.isfinite(y)&(m!=0);b=np.linalg.lstsq(xx[ok],y[ok],rcond=None)[0];bt=np.linalg.lstsq(xx[ok][:,[0,2]],y[ok],rcond=None)[0]
   for t,k in enumerate(idx):
    ms=ar[0]+ar[1]*self.a['^BVSP'].iloc[k-1]+e;pred=(b[0]+b[1]*(ms>0)+b[2]*ms+b[3]*ms*(ms>0)).mean()
    self.assertAlmostEqual(f[t,j,3],pred,places=12);self.assertAlmostEqual(f[t,j,2],bt[0]+bt[1]*ms.mean(),places=12)
 def test_gate_fallback_retains_asset(self):
  a=self.a.copy();a.iloc[650:801,0]=np.nan;f,stats=forecast_fold(a,['A','B'],800,252,np.arange(801,810));self.assertEqual(stats['status'][0],'historical_mean_fallback');self.assertEqual(f.shape,(9,2,4));np.testing.assert_array_equal(f[:,0,1],f[:,0,2]);np.testing.assert_array_equal(f[:,0,2],f[:,0,3])
 def test_gap_guard_cannot_consult_future_missing_flags(self):
  idx=np.arange(801,810);base,_=forecast_fold(self.a,['A','B'],800,252,idx,gap_guard=True);changed=self.a.copy();changed.iloc[801,0]=np.nan;got,_=forecast_fold(changed,['A','B'],800,252,idx,gap_guard=True);np.testing.assert_array_equal(base,got)
 def test_causal_gap_guard_retrospectively_masks_only_known_training_gaps(self):
  a=self.a.copy();a.iloc[800,0]=np.nan;f,stats=forecast_fold(a,['A','B'],800,252,np.array([801]),gap_guard=True)
  self.assertEqual(stats['n_pairs'][0],247);self.assertTrue(np.isfinite(f).all())
 def test_global_gap_mask_is_forbidden(self):
  with self.assertRaises(ValueError):masked_matrix(self.a,'gap')

 def test_training_dates_strictly_precede_target(self):
  sample=pd.DataFrame({'papel_id':['x','y'],'ticker':['A','B'],'setor_economico':['s','s']});p=forecast_panel(self.a,sample,504,2019,'test')
  self.assertTrue((p['origins']<p['dates']).all());self.assertTrue((p['previous_market_dates']<p['dates']).all())
  for row in p['audit']:self.assertLess(row['max_train_date'],row['target_start'])
 def test_target_return_changes_scores_not_its_forecast(self):
  f,_=forecast_fold(self.a,['A','B'],800,252,np.array([801]));a=self.a.copy();a.iloc[801,0]=1e6;g,_=forecast_fold(a,['A','B'],800,252,np.array([801]));np.testing.assert_array_equal(f,g)

if __name__=='__main__':unittest.main()

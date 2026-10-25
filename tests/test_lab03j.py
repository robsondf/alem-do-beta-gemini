import importlib.util,io,sys,unittest,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03j import estimates,liquidity_coefficient,block_weights,holm

class LiquidityControlsTests(unittest.TestCase):
 def test_FWL_matches_dense_OLS_with_reestimated_beta(self):
  rng=np.random.default_rng(41);N=64;liq=rng.normal(size=N);size=.3*liq+rng.normal(size=N);sector=np.array(['a','b','c','d']*(N//4));beta=rng.normal(size=(8,N));y=.4*liq+.7*size+.2*beta+rng.normal(size=(8,N));a,p=liquidity_coefficient(y,beta,liq,size,sector,('size','sector','beta'))
  for j in range(8):
   X=np.column_stack([np.ones(N),liq,size,*[(sector==s).astype(float) for s in ['b','c','d']],beta[j]]);b=np.linalg.lstsq(X,y[j],rcond=None)[0];self.assertAlmostEqual(a[j],b[1],places=12)
  self.assertEqual(p,7)
 def test_asset_pairwise_regime_and_traditional_OLS_in_each_draw(self):
  rng=np.random.default_rng(8);m=rng.normal(size=260);R=rng.normal(size=(260,3));R[[7,12,38],0]=np.nan;w,ix=block_weights(260,21,rng,3);delta,beta=estimates(R,m,w)
  for b in range(3):
   for j in range(3):
    mm=m[ix[b]];yy=R[ix[b],j];v=np.isfinite(yy);bb=np.linalg.lstsq(np.column_stack([np.ones(v.sum()),mm[v]]),yy[v],rcond=None)[0][1];self.assertAlmostEqual(beta[b,j],bb,places=12);slopes=[]
    for sign in [-1,1]:
     use=v&(mm*sign>0);slopes.append(np.linalg.lstsq(np.column_stack([np.ones(use.sum()),mm[use]]),yy[use],rcond=None)[0][1])
    self.assertAlmostEqual(delta[b,j],slopes[1]-slopes[0],places=12)
 def test_complete_inner_XML_from_partial_outer_does_not_certify_archive(self):
  spec=importlib.util.spec_from_file_location('collector',ROOT/'scripts/collect_lab03j_originals.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
  inner=io.BytesIO()
  with zipfile.ZipFile(inner,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('CapitalSocial.xml','<root>42</root>');z.writestr('attachment.bin',np.random.default_rng(3).bytes(50000))
  outer=io.BytesIO()
  with zipfile.ZipFile(outer,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('file.fre',inner.getvalue())
  partial=c.members(outer.getvalue()[:1000],partial=True);xml=c.members(partial['file.fre']);self.assertEqual(xml['CapitalSocial.xml'],b'<root>42</root>');self.assertNotIn('attachment.bin',xml)
 def test_Holm_retains_all_sixteen_slots(self):
  p=np.r_[.001,np.ones(15)];self.assertAlmostEqual(holm(p)[0],.016)

if __name__=='__main__':unittest.main()

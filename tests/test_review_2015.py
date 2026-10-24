import importlib.util,tempfile,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review2015',ROOT/'scripts/replicate_review_2015.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ReconstructionTests(unittest.TestCase):
    def test_missing_trade_session_prevents_both_adjacent_daily_returns(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);dates=pd.to_datetime(['2016-01-04','2016-01-05','2016-01-06','2016-01-07']);pd.DataFrame({'data':dates,'ibov':[100,101,102,103]}).to_csv(p/'ibov.csv',index=False)
            observations=pd.DataFrame({'data':dates[[0,1,3]],'ticker':'TEST3','isin':'BRTESTACNOR1','preult':[10.,10.1,10.3],'voltot':[1.,2.,3.]});r,m=module.reconstruct(observations,p/'ibov.csv',p)
            self.assertAlmostEqual(r.loc[dates[1]].iloc[0],np.log(1.01));self.assertTrue(np.isnan(r.loc[dates[2]].iloc[0]));self.assertTrue(np.isnan(r.loc[dates[3]].iloc[0]))

    def test_market_shock_is_retained_but_clear_factor_is_only_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);dates=pd.to_datetime(['2016-01-04','2016-01-05','2016-01-06']);pd.DataFrame({'data':dates,'ibov':[100,75,75]}).to_csv(p/'ibov.csv',index=False)
            observations=pd.DataFrame({'data':dates,'ticker':'TEST3','isin':'BRTESTACNOR1','preult':[10.,7.5,15.],'voltot':[1.,2.,3.]});r,m=module.reconstruct(observations,p/'ibov.csv',p)
            self.assertAlmostEqual(r.loc[dates[1]].iloc[0],np.log(.75));self.assertTrue(np.isnan(r.loc[dates[2]].iloc[0]));flags=pd.read_csv(p/'events_reproduced.csv');self.assertEqual(len(flags),1);self.assertEqual(flags.data.iloc[0],'2016-01-06')


if __name__=='__main__':unittest.main()

"""Finite-mechanism Monte Carlo rank envelope, with fresh calibration/validation.

This is model-class conditional inference, not distribution-free market certification.
"""
import numpy as np


def precalculate(d):
    for p in d['panels']:
        k=p['kernel'];lev=np.zeros_like(k['weights'])
        for mask,n,mean,w in [k['plus'],k['minus']]:
            center=np.where(mask,k['m'][:,None]-mean,0);ss=(center*center).sum(0);lev+=np.where(mask,1/n+center*center/ss,0)
        if (lev>=1-1e-10).any():raise ArithmeticError('Near-unit leverage')
        k['envelope_score_weight']=k['weights']/(1-lev)*np.sqrt(k['correction'])


def statistic(d,noise):
    estimates=[];scales=[]
    for p in d['panels']:
        k=p['kernel'];y=np.where(k['valid'],noise[np.ix_(p['time_index'],p['asset_index'])],0);fit=np.zeros_like(y)
        for mask,n,mean,w in [k['plus'],k['minus']]:
            slope=np.sum(w*y,axis=0);a=np.where(mask,y,0).sum(0)/n-slope*mean;fit+=np.where(mask,a+slope*k['m'][:,None],0)
        score=k['envelope_score_weight']*np.where(k['valid'],y-fit,0);v=np.einsum('ij,ij->j',score,score)
        for lag in range(1,6):v+=2*(1-lag/6)*np.einsum('ij,ij->j',score[lag:],score[:-lag])
        if (v<=1e-28).any():raise ArithmeticError('Degenerate MC statistic')
        estimates.append(np.sum(k['weights']*y,axis=0));scales.append(np.sqrt(v))
    return np.concatenate(estimates),np.concatenate(scales)


"""Exploratory joint size/liquidity contrasts. Old J families remain unchanged."""
import numpy as np
from lab03j import summarize

def design(liquidity, size, sector):
    labels=['intercept','liquidity','size']
    sectors=sorted(set(sector)); cols=[np.ones(len(size)),liquidity,size]
    for name in sectors[1:]:
        labels.append('sector:'+name);cols.append((np.asarray(sector)==name).astype(float))
    X=np.column_stack(cols)
    if len(X)<40 or len(X)-X.shape[1]<10 or np.linalg.matrix_rank(X)<X.shape[1]:
        raise ValueError('insufficient cross section, residual df or design rank')
    return X,labels

def coefficients(Y,X,beta=None):
    """All coefficients, reestimating an optional generated preperiod regressor."""
    Y=np.atleast_2d(Y);pinv=np.linalg.pinv(X);coef=Y@pinv.T
    if beta is not None:
        beta=np.atleast_2d(beta);projection=beta@pinv.T
        br=beta-projection@X.T;yr=Y-coef@X.T;den=np.sum(br*br,axis=1)
        if np.any(den<=1e-12):raise ValueError('rank-deficient generated beta')
        eta=np.sum(br*yr,axis=1)/den
        coef=np.column_stack([coef-eta[:,None]*projection,eta])
    return coef

def joint(point,draws):
    """Fixed bootstrap-covariance radius; not a bootstrap-t with nested SEs."""
    point=np.asarray(point);draws=np.asarray(draws)
    if draws.ndim!=2 or draws.shape[1]!=2 or not np.isfinite(draws).all():
        raise ValueError('joint draws must be finite B x 2')
    cov=np.cov(draws,rowvar=False);condition=np.linalg.cond(cov)
    if np.linalg.matrix_rank(cov)<2 or condition>1e12:
        return dict(status='singular_covariance',p=np.nan,condition=float(condition))
    inverse=np.linalg.inv(cov);err=draws-point
    stat=float(point@inverse@point);radius=np.einsum('bi,ij,bj->b',err,inverse,err)
    return dict(status='estimated',p=float((1+np.sum(radius>=stat))/(len(draws)+1)),statistic=stat,
                condition=float(condition),cov_ll=float(cov[0,0]),cov_lg=float(cov[0,1]),cov_gg=float(cov[1,1]))

def floors(R,M):
    valid=np.isfinite(R)&np.isfinite(M)[:,None];n=valid.sum(0)
    return (n>=200)&((valid&(M>0)[:,None]).sum(0)>=60)&((valid&(M<0)[:,None]).sum(0)>=60)&(n/np.isfinite(M).sum()>=.95)

def delta_weights(valid,M,W):
    """Linear functional of returns for each resample, with regime intercepts."""
    out=np.zeros_like(W,dtype=float)
    for sign,mask in [(1,M>0),(-1,M<0)]:
        v=valid&mask&np.isfinite(M);n=W@v.astype(float)
        sm=W@np.where(v,M,0.);smm=W@np.where(v,M*M,0.)
        den=smm-sm*sm/n
        if np.any(n<2) or np.any(den<=1e-12):raise ValueError('invalid inner regime fit')
        out+=sign*W*v*(M[None,:]-sm[:,None]/n[:,None])/den[:,None]
    return out

def marginal_rows(coef,labels,metadata):
    return [dict(**metadata,parameter=label,**summarize(coef[0,j],coef[1:,j])) for j,label in enumerate(labels)]

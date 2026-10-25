#!/usr/bin/env python3
"""Render existing, frozen estimates for the editorial edition; no fitting."""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'results/tables/lab03k_20261025'

def build(paper,check=False):
    coefs=pd.read_csv(SOURCE/'coefficients.csv',float_precision='round_trip')
    tests=pd.read_csv(SOURCE/'joint_tests.csv',float_precision='round_trip')
    assert len(coefs)==333 and len(tests)==24
    def coefficient(cohort,model,param):
        x=coefs.query('cohort==@cohort and model==@model and block==21 and parameter==@param')
        assert len(x)==1;return x.iloc[0]
    f=lambda x:f'{x:.4f}'.replace('.',',')
    cell=lambda r:f'{f(r.estimate)} [{f(r.ci_low)}; {f(r.ci_high)}]'
    cohorts=['original80','union118'];labels={'original80':'Originais','union118':'União'}
    def emit(path,text):
        if check:
            assert path.read_text()==text,('display differs from frozen estimates',str(path))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    table=[r'\begin{tabular}{lcc}',r'\toprule',r'Parâmetro & Originais ($N=62$) & União ($N=76$)\\',r'\midrule']
    rows=[]
    for title,model,param,meaning in [
        (r'Volume/giro, porte fixo ($\lambda$)','reference','liquidity','volume_or_turnover_at_fixed_size'),
        (r'Porte, volume fixo ($\gamma$)','reference','size','size_at_fixed_volume'),
        (r'Porte, giro fixo ($\lambda+\gamma$)','turnover_equivalent','size','size_at_fixed_turnover')]:
        values=[]
        for cohort in cohorts:
            r=coefficient(cohort,model,param);values.append(cell(r));rows.append(dict(cohort=cohort,meaning=meaning,estimate=r.estimate,ci_low=r.ci_low,ci_high=r.ci_high,raw_marginal_p=r.p,interval_role='nominal basic95%, not simultaneous or dual to centered test'))
        table.append(title+' & '+' & '.join(values)+r'\\')
    table.append(r'\midrule');vals=[]
    for cohort in cohorts:
        r=tests.query('cohort==@cohort and model=="reference" and block==21').iloc[0];vals.append(f(r.p)+' / '+f(r.p_holm_family))
    table.append(r'Teste conjunto: $p$ / Holm 2 & '+' & '.join(vals)+r'\\')
    table += [r'\bottomrule',r'\end{tabular}']
    out=paper/'tables';emit(out/'editorial_v8_controls.tex','\n'.join(table)+'\n')
    sens=tests[tests.model.ne('reference')].copy();assert len(sens)==18
    models={'beta2015':r'+ $\beta_{2015}$','exclude_unmatched':'Sem ativos sinalizados','Amihud2015':'Amihud/porte/setor'}
    lines=[r'\begin{tabular}{llrrrr}',r'\toprule',r'Coorte & Modelo & Bloco & $N$ & $p$ bruto & Holm 6\\',r'\midrule']
    for L in [21,5,63]:
        for r in sens[sens.block.eq(L)].itertuples():lines.append(f'{labels[r.cohort]} & {models[r.model]} & {L} & {r.N} & {f(r.p)} & {f(r.p_holm_family)}'+r'\\')
        if L!=63:lines.append(r'\midrule')
    lines += [r'\bottomrule',r'\end{tabular}'];emit(out/'editorial_v8_joint_sensitivity.tex','\n'.join(lines)+'\n')
    result=ROOT/'results/tables/editorial_v8'
    emit(result/'displayed_coefficients.csv',pd.DataFrame(rows).to_csv(index=False))
    emit(result/'displayed_joint_sensitivities.csv',sens[['cohort','model','block','N','p','p_holm_family','family']].to_csv(index=False))
    receipt=dict(fitted_new_models=False,source_rows=dict(coefficients=len(coefs),joint_tests=len(tests)),raw_p_below_005_block21=int(sens[sens.block.eq(21)].p.lt(.05).sum()),source_sha256={n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in ['coefficients.csv','joint_tests.csv']})
    assert receipt['raw_p_below_005_block21']==4
    emit(ROOT/'data/editorial_v8/table_derivation.json',json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--paper',type=Path,default=ROOT/'paper');p.add_argument('--check',action='store_true');a=p.parse_args();build(a.paper,a.check)

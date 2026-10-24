#!/usr/bin/env python3
"""Describe archived uncertainty; no estimation, power test or data collection.

Authenticate the uncompressed Colab CSV against its original export manifest,
check fixed-panel counts/common reuse, and export deterministic paper rows.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median


def summarize(source, manifest):
    raw = gzip.decompress(source.read_bytes()) if source.suffix == '.gz' else source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == json.loads(manifest.read_text())['asset_betas.csv']
    records = list(csv.DictReader(io.StringIO(raw.decode())))
    assert len(records) == 277
    by_scenario = {s: [r for r in records if r['scenario'] == s]
                   for s in ['decada', 'decada_periodo_comum', 'recente']}
    assert {s: len(a) for s, a in by_scenario.items()} == {
        'decada': 80, 'decada_periodo_comum': 80, 'recente': 117}
    numeric = ['delta', 'delta_se', 'delta_ci_low', 'delta_ci_high', 'delta_p', 'delta_p_holm_197']
    recent = {r['papel_id']: r for r in by_scenario['recente']}
    for row in by_scenario['decada_periodo_comum']:
        assert all(row[k] == recent[row['papel_id']][k] for k in numeric)
    summary = []
    for scenario, rows in by_scenario.items():
        widths = []
        for row in rows:
            assert row['status_conditional'] == 'ok'
            values = [float(row[k]) for k in numeric]
            assert all(math.isfinite(x) for x in values)
            delta, se, low, high = values[:4]
            h = (high - low) / 2
            assert math.isclose((high + low) / 2, delta, abs_tol=1e-12)
            assert math.isclose(h, 1.959963984540054 * se, rel_tol=1e-10, abs_tol=1e-12)
            widths.append(h)
        summary.append(dict(scenario=scenario, assets=len(rows),
            median_absolute_delta=median(abs(float(r['delta'])) for r in rows),
            median_delta_se=median(float(r['delta_se']) for r in rows),
            median_marginal_ci_halfwidth=median(widths),
            unadjusted_rejections=sum(float(r['delta_p']) < .05 for r in rows),
            holm_rejections=sum(float(r['delta_p_holm_197']) < .05 for r in rows)))
    return summary, digest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'manifest', 'output', 'tex']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    rows, sha = summarize(a.source, a.manifest)
    a.output.mkdir(parents=True, exist_ok=True)
    with (a.output / 'precision.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    report = dict(source_uncompressed_sha256=sha, source_rows=277, common_exact_reuse=True,
        scope='Medians of individual marginal confidence intervals, not confidence intervals for a median',
        power_estimated=False, equivalence_tested=False, models_modified=False,
        economic_margin_selected=False, primary_family_size=197, global_homologated=0)
    (a.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    labels = ['80, 2016--2025', 'Mesmos 80, 2021--2025', '117, 2021--2025']
    bs = chr(92)
    tex = [bs + 'begin{tabular}{lrrr}', bs + 'toprule',
           r'Recorte & $|\widehat\Delta|$ & $EP(\widehat\Delta)$ & $h_{95}$' + bs * 2,
           bs + 'midrule']
    for label, row in zip(labels, rows):
        values = [format(row[k], '.4f').replace('.', ',') for k in
                  ['median_absolute_delta', 'median_delta_se', 'median_marginal_ci_halfwidth']]
        tex.append(label + ' & ' + ' & '.join(values) + chr(92) * 2)
    tex.extend([bs + 'bottomrule', bs + 'end{tabular}'])
    a.tex.parent.mkdir(parents=True, exist_ok=True)
    a.tex.write_text('\n'.join(tex) + '\n')
    print(json.dumps(dict(rows=rows, validation=report), indent=2))

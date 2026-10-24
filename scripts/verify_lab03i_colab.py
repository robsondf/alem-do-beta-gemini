#!/usr/bin/env python3
"""Audit the saved H/I Colab sources and export without executing received code."""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import fitz
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(notebook, export, output, local_export=None):
    delivered = json.loads((ROOT / 'notebooks/Lab03I_selecao_liquidez.ipynb').read_text())
    nb = json.loads(notebook.read_text())
    assert len(nb['cells']) == len(delivered['cells']) == 10
    for actual, expected in zip(nb['cells'], delivered['cells']):
        assert actual['cell_type'] == expected['cell_type']
        assert ''.join(actual['source']) == ''.join(expected['source'])
    codes = [c for c in nb['cells'] if c['cell_type'] == 'code']
    assert [c.get('execution_count') for c in codes] == list(range(1, 7))
    assert not any(o.get('output_type') == 'error' for c in codes for o in c.get('outputs', []))
    stream = ''.join(''.join(o.get('text', [])) for c in codes for o in c.get('outputs', []))
    match = re.search(r'Export: (\S+) \| bytes: (\d+) \| SHA256: ([0-9a-f]{64})', stream)
    assert match and (export.name, export.stat().st_size, sha(export)) == (match[1], int(match[2]), match[3])
    constants = {}
    for node in ast.parse(''.join(nb['cells'][3]['source'])).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ['SOURCE_PINS', 'SOURCE_COMMIT']:
                    constants[target.id] = ast.literal_eval(node.value)
    pins = constants['SOURCE_PINS']
    assert len(pins) == 149 and constants['SOURCE_COMMIT'] == '4689c35c49a303e84f35b66c55320190fb630937'
    if local_export:
        prior = json.loads((ROOT / 'data/lab03i/validacao_notebook_local.json').read_text())
        assert sha(local_export) == prior['export_sha256']
        assert local_export.stat().st_size == prior['export_bytes']
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(export) as z:
        assert z.testzip() is None
        manifest = json.loads(z.read('manifesto_exports.json'))
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == set(manifest) | {'manifesto_exports.json'}
        assert len(manifest) == 206 and len(z.namelist()) == 207
        assert not any(Path(name).suffix.lower() == '.zip' for name in z.namelist())
        for name, digest in manifest.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            raw = z.read(name)
            assert hashlib.sha256(raw).hexdigest() == digest, name
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for name, digest in pins.items():
            assert manifest['runtime/' + name] == digest, name
            assert sha(ROOT / name) == digest, name
    h = output / 'outputs'
    i = output / 'outputs_I'
    comparison = json.loads((i / 'notebook_comparison.json').read_text())
    assert comparison['passed'] and comparison['environment'] == 'Colab'
    assert comparison['stage'] == 'H_and_I' and comparison['external_2015_package_reproduced']
    assert comparison['only_existing_caches'] and comparison['new_outer_generators'] == 0
    assert comparison['source_commit'] == constants['SOURCE_COMMIT']
    assert comparison['source_files'] == 149
    assert comparison['compared_values'] == 98361 and comparison['I_compared_values'] == 24706
    assert comparison['p_threshold_positions'] == 300 and comparison['I_p_threshold_positions'] == 312
    report = dict(passed=True, notebook_sha256=sha(notebook), notebook_bytes=notebook.stat().st_size,
                  delivered_notebook_sha256=sha(ROOT / 'notebooks/Lab03I_selecao_liquidez.ipynb'),
                  export_sha256=sha(export), export_bytes=export.stat().st_size,
                  source_cells_identical=10, sequential_code_cells=6, exceptions=0,
                  source_pins_verified=149, export_members=207, source_commit=constants['SOURCE_COMMIT'],
                  notebook_internal_comparison=comparison, tables={}, arrays={}, images={}, tables_LaTeX={})
    total = 0
    maximum = 0.
    thresholds = 0
    for stage, actual, reference in [
        ('H', h, ROOT / 'results/tables/lab03h_pos_parecer_v4_20261024'),
        ('I', i, ROOT / 'results/tables/lab03i_parecer_v4_20261024')]:
        for expected_path in sorted(reference.glob('*.csv*')):
            name = expected_path.name
            if stage == 'I' and name.startswith('gaps_'):
                actual_path = actual / 'gaps_preserved' / name.removeprefix('gaps_')
            else:
                actual_path = actual / name
            a = pd.read_csv(actual_path, float_precision='round_trip')
            b = pd.read_csv(expected_path, float_precision='round_trip')
            assert set(a.columns) == set(b.columns)
            a = a.reindex(columns=b.columns)
            pd.testing.assert_frame_equal(a, b, check_exact=False, atol=1e-10, rtol=1e-9)
            delta = 0.
            for col in a.select_dtypes(include='number'):
                x, y = a[col].to_numpy(float), b[col].to_numpy(float)
                finite = np.isfinite(x) & np.isfinite(y)
                if finite.any():
                    delta = max(delta, float(np.max(np.abs(x[finite] - y[finite]))))
                if col == 'p' or col.startswith('p_'):
                    np.testing.assert_array_equal(x <= .05, y <= .05)
                    thresholds += len(x)
            report['tables'][stage + '/' + name] = dict(rows=len(a), columns=len(a.columns),
                max_absolute_difference=delta, byte_identical=actual_path.read_bytes() == expected_path.read_bytes())
            total += a.size
            maximum = max(maximum, delta)
        for expected_path in sorted(reference.glob('*.tex')):
            if stage == 'I' and expected_path.name == 'lags.tex':
                assert not (actual / expected_path.name).exists()
                report['tables_LaTeX']['I/lags.tex'] = 'Article-only formatting;lag_summary.csv compared numerically'
                continue
            assert (actual / expected_path.name).read_bytes() == expected_path.read_bytes(), expected_path.name
            report['tables_LaTeX'][stage + '/' + expected_path.name] = 'byte_identical'
    banks = [('H', h / 'crisis_draws.npz', ROOT / 'results/tables/lab03h_pos_parecer_v4_20261024/crisis_draws.npz')]
    with zipfile.ZipFile(local_export) if local_export else io.BytesIO() as local:
        if local_export:
            for variant in ['', 'gaps_preserved/']:
                banks.append(('I/' + (variant or 'literal/'), i / variant / 'bootstrap_draws.npz',
                              io.BytesIO(local.read('outputs_I/' + variant + 'bootstrap_draws.npz'))))
        for stage, actual_path, reference_path in banks:
            with np.load(actual_path) as a, np.load(reference_path) as b:
                assert set(a.files) == set(b.files)
                for key in a.files:
                    np.testing.assert_allclose(a[key], b[key], atol=1e-10, rtol=1e-9, equal_nan=True)
                    delta = float(np.nanmax(np.abs(a[key] - b[key])))
                    report['arrays'][stage + '/' + key] = dict(values=a[key].size, max_absolute_difference=delta)
                    total += a[key].size
                    maximum = max(maximum, delta)
    embedded = []
    for c in codes:
        for o in c.get('outputs', []):
            raw = o.get('data', {}).get('image/png')
            if raw:
                embedded.append(base64.b64decode(''.join(raw) if isinstance(raw, list) else raw))
    assert len(embedded) == 3
    for k, (folder, name) in enumerate([(h, 'lab03h_crise'), (h, 'lab03h_periodo_completo'), (i, 'lab03i_liquidez')]):
        raw = (folder / 'figures' / (name + '.png')).read_bytes()
        assert raw == embedded[k]
        with fitz.open(folder / 'figures' / (name + '.pdf')) as a, fitz.open(ROOT / 'paper/figures/lab02' / (name + '.pdf')) as b:
            x = a[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            y = b[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            equal = (x.width, x.height, x.samples) == (y.width, y.height, y.samples)
        report['images'][name] = dict(embedded_matches_export=True, PDF_render_identical_to_paper_144dpi=equal)
    assert thresholds == 612
    report.update(total_values_compared=int(total), max_absolute_difference=maximum,
                  p_threshold_positions_preserved=thresholds, array_vectors_compared=len(report['arrays']),
                  atol=1e-10, rtol=1e-9, new_outer_G_generators=0,
                  table_H_bank_values_compared=int(total - (599880 if local_export else 0)),
                  private_I_bank_values_compared=599880 if local_export else 0,
                  manifest_hashed_members=206, raw_COTAHIST_ZIPs_in_export=False,
                  scope='Saved source/export and numerical consistency;not economic event homologation,association calibration or causal identification')
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'export_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {k: v for k, v in report.items() if k not in ['arrays', 'tables']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--notebook', required=True, type=Path)
    p.add_argument('--export', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--local-export', type=Path, help='Authenticated earlier local export for private I banks.')
    a = p.parse_args()
    print(json.dumps(audit(a.notebook, a.export, a.output, a.local_export), indent=2))

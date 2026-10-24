#!/usr/bin/env python3
"""Read-only packaging checks and the unchanged upstream test suite.

This does not re-estimate financial results, download inputs, or certify
economic identification. Tests requiring omitted upstream artifacts are
reported as skipped unless --require-all-tests is requested.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def verify_snapshot():
    manifest = json.loads((ROOT / 'provenance/selection.json').read_text())
    for item in manifest['selected']:
        raw = (ROOT / item['path']).read_bytes()
        blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
        assert len(raw) == item['bytes'], item['path']
        assert hashlib.sha1(blob).hexdigest() == item['git_blob_sha1'], item['path']
    pins = json.loads((ROOT / 'data/lab03e/runtime_manifest.json').read_text())
    for path, digest in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    internal = {p.stem for p in (ROOT / 'src').glob('*.py')}
    for path in [*(ROOT / 'src').glob('*.py'), *(ROOT / 'scripts').glob('*.py')]:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = [node.module] if isinstance(node, ast.ImportFrom) else (
                [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if name and re.fullmatch(r'lab\w+', name):
                    assert name in internal, (path.name, name)
    main = (ROOT / 'paper/main.tex').read_text()
    body = (ROOT / 'paper/artigo_revisado.tex').read_text()
    for name in re.findall(r'\\input\{([^}]+)\}', main + '\n' + body):
        assert (ROOT / 'paper' / (name if name.endswith('.tex') else name + '.tex')).is_file(), name
    for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body):
        assert (ROOT / 'paper/figures/lab02' / name).is_file(), name
    assert (ROOT / 'paper/references_artigo.bib').is_file()
    return {'selected_source_files_verified': len(manifest['selected']),
            'frozen_E_pins_verified': len(pins),
            'internal_imports_and_article_dependencies': 'passed'}


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def unavailable(test):
    name = test.id()
    if name.startswith('test_lab02_robustness_suite.') and not os.environ.get('LAB02Y_X_ARCHIVE'):
        return 'Authenticated X archive remains external; set LAB02Y_X_ARCHIVE.'
    if name.endswith('.test_authenticated_data_keeps_all_seven_missing_decade_cells'):
        if not all(os.environ.get(k) for k in ['LAB03_X_ARCHIVE', 'LAB03_Y_ARCHIVE']):
            return 'Authenticated X/Y archives remain external; set LAB03_X_ARCHIVE and LAB03_Y_ARCHIVE.'
    if name.endswith('.test_wrong_y_archive_rejected') and not os.environ.get('LAB03_X_ARCHIVE'):
        return 'Authenticated X archive remains external; set LAB03_X_ARCHIVE.'
    if name.endswith('.test_notebook_embeds_exact_versioned_code_and_lock'):
        if not (ROOT / 'notebooks/02_betas.ipynb').is_file():
            return 'Historical Lab02 notebook deliberately omitted; retained at the source commit.'
    return None


class ExternalArtifactTest(unittest.TestCase):
    def __init__(self, original_id, reason):
        super().__init__('runTest')
        self.original_id, self.reason = original_id, reason

    def id(self):
        return self.original_id

    def shortDescription(self):
        return self.original_id

    def runTest(self):
        self.skipTest(self.reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-all-tests', action='store_true',
                        help='Run every upstream test unchanged, requiring external fixtures too.')
    parser.add_argument('--report', type=Path, help='Optional NEW JSON report outside frozen results.')
    args = parser.parse_args()
    report = verify_snapshot()
    suite = unittest.TestSuite()
    for test in flatten(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')):
        reason = None if args.require_all_tests else unavailable(test)
        suite.addTest(ExternalArtifactTest(test.id(), reason) if reason else test)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report.update(tests_run=result.testsRun, tests_passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
                  skipped=[{'test': t.id(), 'reason': reason} for t, reason in result.skipped],
                  failures=[t.id() for t, _ in result.failures], errors=[t.id() for t, _ in result.errors],
                  passed=result.wasSuccessful(),
                  scope='Packaging and existing tests only; no new empirical or Monte Carlo run.')
    if args.report:
        with args.report.open('x', encoding='utf-8') as out:
            json.dump(report, out, indent=2, ensure_ascii=False)
            out.write('\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())

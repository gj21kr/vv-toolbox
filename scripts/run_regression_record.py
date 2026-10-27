"""Run the complete Python suite with before/after source fingerprints."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+', args.name):
        raise ValueError('Use a lowercase evidence name')
    root = Path(__file__).resolve().parents[1]
    stem = root/'docs/evidence'/args.name
    outputs = {kind:Path(str(stem)+suffix) for kind,suffix in
               [('report','.json'),('xml','.xml'),('log','.log'),('sources','-sources.json')]}
    if any(p.exists() for p in outputs.values()):
        raise ValueError('Existing run evidence must not be overwritten')
    def fingerprints():
        paths = [p for folder in ('src','tests','scripts') for p in (root/folder).rglob('*')
                 if p.is_file() and p.suffix in ('.py','.js','.cjs')]
        paths.append(root/'pyproject.toml')
        return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(paths)}
    before = fingerprints()
    outputs['sources'].write_text(json.dumps(before, indent=2)+'\n')
    command = [sys.executable,'-m','pytest','-q','--junitxml='+str(outputs['xml'])]
    report = dict(status='RUNNING', command=command, python=sys.version,
                  scope='Full Python suite; browser and anatomical acceptance are separate',
                  source_count=len(before))
    outputs['report'].write_text(json.dumps(report, indent=2)+'\n')
    started = time.perf_counter()
    with outputs['log'].open('w') as log:
        run = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    after = fingerprints()
    changed = sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
    counts = dict(PASS=0,FAIL=0,ERROR=0,SKIP=0)
    if outputs['xml'].exists():
        for case in ET.parse(outputs['xml']).iter('testcase'):
            key = ('ERROR' if case.find('error') is not None else 'FAIL' if case.find('failure') is not None
                   else 'SKIP' if case.find('skipped') is not None else 'PASS')
            counts[key] += 1
    report.update(status='PASS' if run.returncode==0 and not changed and counts['PASS'] else 'FAIL',
                  exit_code=run.returncode, counts=counts, elapsed_seconds=time.perf_counter()-started,
                  source_files_unchanged=not changed, changed_files=changed,
                  hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in outputs.items()
                          if k!='report' and p.exists()})
    outputs['report'].write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

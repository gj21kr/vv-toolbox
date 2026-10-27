"""Record separate full-suite and UI follow-up runs without hiding skipped tests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT/'docs/evidence/full-validation'
    destination.mkdir(parents=True, exist_ok=True)
    runs, covered = [], {}
    for stem in ('pytest', 'ui-logic'):
        source = ROOT/'exports/full-validation'/f'{stem}.xml'
        cases = list(ET.parse(source).iter('testcase'))
        counts = dict(PASS=0, FAIL=0, ERROR=0, SKIP=0)
        for case in cases:
            status = ('ERROR' if case.find('error') is not None else
                      'FAIL' if case.find('failure') is not None else
                      'SKIP' if case.find('skipped') is not None else 'PASS')
            counts[status] += 1
            covered[case.attrib['classname']+'::'+case.attrib['name']] = status
        runs.append(dict(name=stem, counts=counts, cases=len(cases),
                         junit_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        for suffix in ('xml', 'log'):
            shutil.copyfile(ROOT/'exports/full-validation'/f'{stem}.{suffix}', destination/f'{stem}.{suffix}')
    paths = [p for folder in ('src','tests','scripts') for p in (ROOT/folder).rglob('*')
             if p.is_file() and p.suffix in ('.py','.cjs','.js','.json')]
    paths.append(ROOT/'pyproject.toml')
    hashes = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(paths)}
    packages = subprocess.check_output([sys.executable,'-m','pip','freeze'], text=True).splitlines()
    report = dict(schema='vv-toolbox.test-suite-evidence/1', runs=runs,
                  unique_case_count=len(covered),
                  final_case_counts={status:list(covered.values()).count(status)
                                     for status in ('PASS','FAIL','ERROR','SKIP')},
                  aggregation='Full suite followed by the three Node-dependent tests; not one uninterrupted 802-pass run.',
                  python=sys.version.split()[0],
                  node=subprocess.check_output(['node','--version'],text=True).strip(),
                  packages=[line for line in packages if re.fullmatch(r'[A-Za-z0-9_.-]+==[^\s]+',line)],
                  source_file_sha256=hashes,
                  scope='Automated tests only. Clinical, patient-specific and complete real-atlas geometry acceptance not established.')
    (destination/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('runs','unique_case_count','final_case_counts','python','node')}))


if __name__=='__main__':
    main()

"""Explicit one-time official VMR acquisition. No runtime network access."""
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

from vv_toolbox.reference import DATA_ROOT, MANIFEST_SHA256, PATHS


def main():
    def fetch(url):
        with urllib.request.urlopen(url,timeout=60) as response:
            return response.read(15_000_001)
    manifest=fetch('https://purl.stanford.edu/kd053sz6270.xml')
    if hashlib.sha256(manifest).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('Official manifest changed; review new version before acquisition')
    root=ET.fromstring(manifest)
    names=['Models/0094_0001.vtp','Models/0094_0001.mdl','0011_H_AO_H.pdf']
    names += [f'Paths/{name}.pth' for name in PATHS]
    names += [f'Segmentations/{name}.ctgr' for name in PATHS.values()]
    payloads={'source-manifest.xml':manifest}
    records={}
    for name in names:
        entry=root.find(f".//file[@id='0011_H_AO_H/{name}']")
        url='https://stacks.stanford.edu/file/druid:kd053sz6270/0011_H_AO_H/'+name
        data=fetch(url)
        if len(data)!=int(entry.get('size')) or hashlib.sha1(data).hexdigest()!=entry.find("checksum[@type='sha1']").text:
            raise ValueError('Source manifest mismatch: '+name)
        payloads[name]=data
        records[name]=dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    license_url='https://raw.githubusercontent.com/SimVascular/vascularmodel/7a1c17dfc9ce4b34eec587fd12f709e8e7baea4e/LICENSE'
    payloads['README-COPYRIGHT']=fetch(license_url)
    for name in ('source-manifest.xml','README-COPYRIGHT'):
        records[name]=dict(sha256=hashlib.sha256(payloads[name]).hexdigest(),bytes=len(payloads[name]))
    if sum(map(len,payloads.values()))>15_000_000:
        raise ValueError('Acquisition exceeded size budget')
    for name,data in payloads.items():
        target=DATA_ROOT/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    (DATA_ROOT/'acquisition.json').write_text(json.dumps(dict(source='https://purl.stanford.edu/kd053sz6270',files=records),indent=2))
    print(f'Acquired {len(payloads)} verified files ({sum(map(len,payloads.values()))} bytes) to {DATA_ROOT}')


if __name__=='__main__':
    main()

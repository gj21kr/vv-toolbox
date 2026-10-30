"""Explicit official BodyParts3D 4.0 acquisition; never called by the viewer."""
from pathlib import Path
import hashlib
import json
import urllib.request
from vv_toolbox.atlas import PINNED
from vv_toolbox.source_identity import validate_source_identity

ROOT=Path(__file__).resolve().parents[1]/'reference-data'/'bodyparts3d'
BASE='https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/'
FILES={name:BASE+name for name in ('isa_BP3D_4.0_obj_99.zip','isa_parts_list_e.txt','isa_element_parts.txt','partof_parts_list_e.txt','partof_element_parts.txt','README_e.html')}
FILES['LICENSE.html']='https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html'


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    entries={}
    for name,url in FILES.items():
        target=ROOT/name
        if not target.exists():
            temporary=ROOT/(name+'.partial')
            with urllib.request.urlopen(url,timeout=90) as response,temporary.open('wb') as stream:
                total=0
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>170_000_000:
                        raise ValueError('Source size exceeds acquisition bound')
                    stream.write(chunk)
            temporary.replace(target)
        data=target.read_bytes()
        identity=validate_source_identity(name,data,PINNED[name])
        entries[name]=dict(url=url,bytes=len(data),**identity)
        print(name,len(data),entries[name]['sha256'],flush=True)
    (ROOT/'acquisition.json').write_text(json.dumps(dict(source=BASE,files=entries),indent=2))


if __name__=='__main__':main()

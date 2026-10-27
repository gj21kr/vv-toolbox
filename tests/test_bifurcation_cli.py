import json
import numpy as np
import trimesh
import pytest

from test_bifurcation_surface import design
from vv_toolbox.case_io import save_case
from vv_toolbox.case_cli import main


def inputs(tmp_path):
    case,spec=design()
    source=tmp_path/'case.json';parameters=tmp_path/'spec.json'
    save_case(source,case);parameters.write_text(json.dumps(spec))
    return source,parameters,spec


def test_export_reload_and_no_overwrite(tmp_path,capsys):
    source,parameters,spec=inputs(tmp_path);original=source.read_bytes()
    output=tmp_path/'candidate.npz'
    command=['bifurcation-surface',str(source),str(parameters),str(output),'--spacing-mm','.16']
    assert main(command)==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['status']=='CANDIDATE'
    with np.load(output,allow_pickle=False) as archive:
        metadata=json.loads(str(archive['metadata']))
        assert metadata['specification']==spec and metadata['case_revision']==spec['case_revision']
        assert metadata['edge_ids']==['c','d','e']
        assert metadata['frame']==spec['frame'] and not metadata['accepted_for_generation']
        mesh=trimesh.Trimesh(vertices=archive['vertices_mm'],faces=archive['faces'],process=False)
        assert mesh.is_volume
        assert mesh.contains(np.asarray(metadata['lumen_probe_positions_mm'])).all()
        assert summary['vertices']==len(mesh.vertices) and summary['triangles']==len(mesh.faces)
    saved=output.read_bytes()
    with pytest.raises(SystemExit) as failure:
        main(command)
    assert failure.value.code==2
    assert output.read_bytes()==saved and source.read_bytes()==original
    assert not list(tmp_path.glob('*.tmp'))


def test_rejected_spec_never_publishes_output(tmp_path,capsys):
    source,parameters,spec=inputs(tmp_path)
    spec['case_revision']='0'*64;parameters.write_text(json.dumps(spec))
    output=tmp_path/'rejected.npz'
    with pytest.raises(SystemExit) as failure:
        main(['bifurcation-surface',str(source),str(parameters),str(output),'--spacing-mm','.16'])
    assert failure.value.code==2
    assert not output.exists() and not list(tmp_path.glob('*.tmp'))

from http.server import ThreadingHTTPServer
import json
from unittest.mock import MagicMock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
import vv_toolbox.app as app
from test_interval_application import prepared


def test_actual_apply_undo_http_and_generation_guard(monkeypatch):
    ws, text, _ = prepared()
    ws.graph = {}
    ws.error = None
    calls = []
    ws.render_interval_part = lambda pid: calls.append((pid, ws.generation))
    ws.render_interval_parts = lambda pids: calls.extend((pid, ws.generation) for pid in pids)
    monkeypatch.setattr(app, 'Workspace', lambda *a, **k: ws)
    viser = MagicMock()
    viser.get_port.return_value = 1
    monkeypatch.setattr(app.viser, 'ViserServer', lambda **k: viser)
    servers = []
    def http(*args):
        server = ThreadingHTTPServer(*args)
        servers.append(server)
        return server
    monkeypatch.setattr(app, 'ThreadingHTTPServer', http)
    server = app.serve(0)
    def post(action, generation, body):
        request = Request(f'http://127.0.0.1:{servers[0].server_port}/api/atlas-interval-{action}',
                          data=json.dumps(body).encode(),
                          headers={'Content-Type':'application/json','X-Expected-Generation':str(generation)})
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    try:
        assert post('apply', 6, {'snapshot_text':text})[0] == 409
        status, result = post('apply', 7, {'snapshot_text':text})
        assert status == 200 and result['status'] == 'APPLIED'
        assert calls == [('vessel', 8)]
        status, saved = post('session', 8, {'action':'export'})
        assert status == 200
        assert post('session', 8, {'action':'restore','session_text':saved['session_text']})[0] == 409
        assert post('undo', 7, {})[0] == 409
        status, result = post('undo', 8, {})
        assert status == 200 and result['status'] == 'UNDONE'
        assert calls == [('vessel', 8), ('vessel', 9)]
        assert ws.atlas_modified_parts == {} and ws.atlas_interval_edits == {}
        assert post('session', 8, {'action':'restore','session_text':saved['session_text']})[0] == 409
        status, restored = post('session', 9, {'action':'restore','session_text':saved['session_text']})
        assert status == 200 and restored['status'] == 'RESTORED'
        assert restored['operations'] == 1 and calls[-1] == ('vessel', 10)
        assert post('undo', 10, {})[0] == 200
        assert ws.atlas_modified_parts == {}
    finally:
        server.stop()


def test_parameter_save_and_modification_cannot_omit_active_interval():
    ws = app.Workspace.__new__(app.Workspace)
    import threading
    ws.lock = threading.RLock()
    ws.atlas_interval_edits = {'vessel': [{}]}
    from vv_toolbox.atlas_edit_session import AtlasEditConflict
    with pytest.raises(AtlasEditConflict, match='own save format'):
        ws.update_atlas_edit_session({'action':'save','expected_generation':1})
    with pytest.raises(AtlasEditConflict, match='Undo interval'):
        ws.modify_atlas_part({})

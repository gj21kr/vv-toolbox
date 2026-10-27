from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
import threading
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import vv_toolbox.app as app
import vv_toolbox.atlas_interval_preview as preview
import vv_toolbox.interval_revalidation as revalidation


@pytest.mark.parametrize('path', ['/api/atlas-interval-preview', '/api/atlas-interval-revalidate'])
def test_preview_releases_scene_lock_and_discards_stale_result(monkeypatch, path):
    entered, release = threading.Event(), threading.Event()
    workspace = SimpleNamespace(lock=threading.RLock(), busy=False, graph={}, error=None,
                                source='atlas', generation=1,
                                atlas=SimpleNamespace(metadata={'sha256': 'a'*64}))
    workspace.snapshot = lambda: dict(generation=workspace.generation)
    monkeypatch.setattr(app, 'Workspace', lambda *a, **k: workspace)
    viser = MagicMock()
    viser.get_port.return_value = 1
    monkeypatch.setattr(app.viser, 'ViserServer', lambda **k: viser)
    servers = []
    def http(*args):
        server = ThreadingHTTPServer(*args)
        servers.append(server)
        return server
    monkeypatch.setattr(app, 'ThreadingHTTPServer', http)
    monkeypatch.setattr(preview, 'snapshot_interval_workspace',
                        lambda ws, raw: SimpleNamespace(generation=ws.generation))
    def slow(snapshot, raw):
        entered.set()
        assert release.wait(5)
        return dict(generation=snapshot.generation)
    monkeypatch.setattr(preview, 'preview_interval', slow)
    monkeypatch.setattr(revalidation, 'prepare_revalidation', lambda *a, **k: ({}, 'revision', {}))
    monkeypatch.setattr(revalidation, 'revalidate_interval_snapshot', slow)
    server = app.serve(0)
    base = f'http://127.0.0.1:{servers[0].server_port}'
    def request(path, post=False):
        body = b'{"snapshot_text":"test"}' if path.endswith('revalidate') else b'{}'
        req = Request(base + path, data=body if post else None,
                      headers={'Content-Type': 'application/json', 'X-Expected-Generation': '1'})
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request, path, True)
            assert entered.wait(3)
            assert request('/api/state') == (200, {'generation': 1})
            assert request(path, True)[0] == 409
            with workspace.lock:
                workspace.generation = 2
            release.set()
            status, result = pending.result(timeout=3)
            assert status == 409 and result['code'] == 'generation_conflict'
            assert workspace.interval_preview_busy is False
    finally:
        release.set()
        server.stop()

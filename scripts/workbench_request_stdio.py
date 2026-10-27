"""Isolated real request handler for browser transport verification."""
import json
import sys
from vv_toolbox.label_workbench import process_request

print(json.dumps(process_request(json.load(sys.stdin))))

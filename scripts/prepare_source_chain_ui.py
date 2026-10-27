"""Export a split-source synthetic fixture and current workbench page."""
from pathlib import Path
from test_registered_shape_edit import split_sample
from vv_toolbox.case_io import save_case
from vv_toolbox.label_workbench import HTML

folder=Path('exports/source-chain-ui');folder.mkdir(parents=True,exist_ok=True)
save_case(folder/'input.snapshot.json',split_sample(reverse=True))
(folder/'workbench.html').write_text(HTML,encoding='utf-8')

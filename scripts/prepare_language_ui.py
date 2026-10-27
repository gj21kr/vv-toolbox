from pathlib import Path
from vv_toolbox.ui_language import JS,with_language
from vv_toolbox.web_ui import HTML
from vv_toolbox.label_workbench import HTML as WORKBENCH

folder=Path('exports/language-ui');folder.mkdir(parents=True,exist_ok=True)
for name,text in [('main.html',with_language(HTML.replace('__VISER_PORT__','8094'))),
                  ('workbench.html',with_language(WORKBENCH)),('language.js',JS)]:
    (folder/name).write_text(text,encoding='utf-8')

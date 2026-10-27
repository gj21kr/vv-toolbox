from html.parser import HTMLParser
from vv_toolbox.ui_language import COPY,with_language,JS
from vv_toolbox.label_workbench import HTML as WORKBENCH
from vv_toolbox.web_ui import HTML


def test_local_language_asset_does_not_change_model_or_case_requests():
    for page in (HTML,WORKBENCH):
        result=with_language(page)
        assert result.count('src="/ui-language.js"')==1
        assert result.replace('<script src="/ui-language.js"></script>','')==page
    assert 'localStorage' in JS
    assert 'fetch(' not in JS


def test_initial_page_copy_has_both_languages():
    class Texts(HTMLParser):
        def __init__(self):super().__init__();self.skip=0;self.text=[]
        def handle_starttag(self,tag,attrs):
            if tag in ('script','style'):self.skip+=1
        def handle_endtag(self,tag):
            if tag in ('script','style'):self.skip-=1
        def handle_data(self,text):
            if not self.skip and text.strip():self.text.append(' '.join(text.split()))
    translated={text for pair in COPY for text in pair}
    unchanged={'VV Toolbox','VV Toolbox · Atlas','← VV Toolbox','ATLAS','ACom','1.00','0.00','0°','0.30','0.50'}
    for html in (HTML,WORKBENCH):
        parser=Texts();parser.feed(html)
        assert not set(parser.text)-translated-unchanged

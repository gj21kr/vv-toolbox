"""List local UI copy for translation coverage review."""
from html.parser import HTMLParser
import json
from vv_toolbox.web_ui import HTML
from vv_toolbox.label_workbench import HTML as WORKBENCH

class Texts(HTMLParser):
    def __init__(self):
        super().__init__();self.skip=0;self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip-=1
    def handle_data(self,text):
        if not self.skip and text.strip():self.items.append(text.strip())

if __name__=='__main__':
    for name,html in [('main',HTML),('workbench',WORKBENCH)]:
        parser=Texts();parser.feed(html)
        print(json.dumps({name:parser.items},ensure_ascii=False))

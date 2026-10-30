"""Pinned source identity, including a separately reviewed license content scope."""
import hashlib
import json
from html.parser import HTMLParser

# Reviewed official license content; page chrome and request tokens are excluded.
LICENSE_CONTENT_SHA256 = '9c0ffe8ac89dfe29946cc3f903b39124553f4fbceecd97d25d8ede3df79691fb'


def license_content_sha256(data):
    class Content(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth=0
            self.count=0
            self.tokens=[]

        def handle_starttag(self,tag,attrs):
            if tag=='div' and 'tinymce-content' in dict(attrs).get('class','').split():
                self.count+=1
                if self.depth: raise ValueError('Nested license content')
                self.depth=1
                return
            if self.depth:
                self.tokens.append(['start',tag,sorted(attrs)])
                if tag=='div': self.depth+=1

        def handle_startendtag(self,tag,attrs):
            self.handle_starttag(tag,attrs)
            if tag=='div': self.handle_endtag(tag)

        def handle_endtag(self,tag):
            if self.depth:
                if tag=='div':
                    self.depth-=1
                    if not self.depth: return
                self.tokens.append(['end',tag])

        def handle_data(self,value):
            value=' '.join(value.split())
            if self.depth and value: self.tokens.append(['text',value])

    parser=Content()
    parser.feed(data.decode('utf-8-sig'))
    parser.close()
    if parser.count!=1 or parser.depth or not parser.tokens:
        raise ValueError('Exactly one complete license content section required')
    encoded=json.dumps(parser.tokens,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def validate_source_identity(name,data,expected):
    raw=hashlib.sha256(data).hexdigest()
    if raw==expected:
        return dict(method='raw-sha256',sha256=raw)
    if name=='LICENSE.html':
        content=license_content_sha256(data)
        if content==LICENSE_CONTENT_SHA256:
            return dict(method='reviewed-license-content-v1',sha256=raw,
                        content_sha256=content,legacy_raw_sha256=expected)
    raise ValueError('Pinned atlas source hash mismatch: '+name)

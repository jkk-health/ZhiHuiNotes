"""Canonical rich text, legacy Markdown and safe plain-text extraction."""
import base64
from html.parser import HTMLParser

import markdown
import nh3

TAGS = {'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', 'em', 'i',
        'u', 's', 'blockquote', 'pre', 'code', 'ul', 'ol', 'li', 'a', 'img', 'span',
        'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr'}
CLASSES = {'ql-align-center', 'ql-align-right', 'ql-align-justify', 'ql-size-small',
           'ql-size-large', 'ql-size-huge', 'ql-font-serif', 'ql-font-monospace',
           'ql-code-block', 'ql-code-block-container'} | {f'ql-indent-{i}' for i in range(1, 9)}


def attribute_filter(tag, attr, value):
    if attr == 'href' and value.lower().startswith(('data:', 'javascript:')):
        return None
    if tag == 'img' and attr == 'src' and value.startswith('data:'):
        header, sep, encoded = value.partition(',')
        if header not in {'data:image/png;base64', 'data:image/jpeg;base64',
                          'data:image/gif;base64', 'data:image/webp;base64'} or not sep:
            return None
        try:
            if len(base64.b64decode(encoded, validate=True)) > 2 * 1024 * 1024:
                raise ValueError('内嵌图片不能超过 2MB')
        except (ValueError, TypeError) as exc:
            raise ValueError('内嵌图片无效或超过 2MB') from exc
    return value


def clean_html(value):
    if not isinstance(value, str):
        raise ValueError('正文必须是字符串')
    class ImageCheck(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for name, content in attrs:
                if tag == 'img' and name == 'src' and content:
                    attribute_filter(tag, name, content)
    ImageCheck().feed(value)
    return nh3.clean(value, tags=TAGS, clean_content_tags={'script', 'style', 'iframe', 'object'},
                     attributes={'*': {'style'}, 'a': {'href', 'title'}, 'img': {'src', 'alt'},
                                 'li': {'data-list'}, 'div': {'data-language'}},
                     allowed_classes={tag: CLASSES for tag in TAGS},
                     filter_style_properties={'color', 'background-color', 'text-align'},
                     url_schemes={'http', 'https', 'mailto', 'data'},
                     attribute_filter=attribute_filter)


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.headings = [], []
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag in {'p', 'br', 'div', 'li', 'pre'} or tag.startswith('h'):
            self.parts.append('\n')
        if tag in {'h1', 'h2', 'h3'}:
            self.heading = [int(tag[1]), []]

    def handle_endtag(self, tag):
        if self.heading and tag == f'h{self.heading[0]}':
            text = ''.join(self.heading[1]).strip()
            if text:
                self.headings.append((self.heading[0], text))
            self.heading = None
        if tag in {'p', 'div', 'li', 'pre', 'h1', 'h2', 'h3'}:
            self.parts.append('\n')

    def handle_data(self, data):
        self.parts.append(data)
        if self.heading:
            self.heading[1].append(data)

    @property
    def text(self):
        return '\n'.join(line.strip() for line in ''.join(self.parts).splitlines() if line.strip())


def parse_html(html):
    parser = TextParser()
    parser.feed(html)
    return parser


def note_html(note):
    html = note.content_html or markdown.markdown(note.content_md or '', extensions=['extra', 'nl2br'])
    return clean_html(html)


def note_text(note):
    return parse_html(note_html(note)).text


def apply_content(note, data):
    if 'content_html' in data:
        note.content_html = clean_html(data['content_html'])
        note.content_md = parse_html(note.content_html).text
    elif 'content_md' in data:
        if not isinstance(data['content_md'], str):
            raise ValueError('正文必须是字符串')
        # Legacy clients still send Markdown; invalidate an older rich-text copy.
        note.content_md = data['content_md']
        note.content_html = ''

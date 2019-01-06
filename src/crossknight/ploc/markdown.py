# coding:utf-8
from mistune import markdown
from mistune import Renderer
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound


def _get_lexer(code, lang):
    if lang:
        try:
            return get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            pass
    try:
        return guess_lexer(code, stripall=True)
    except ClassNotFound:
        return None


def render(text):
    return markdown(text, escape=False, renderer=_Renderer())


class _Renderer(Renderer):
    def block_code(self, code, lang=None):
        lexer = _get_lexer(code, lang)
        if lexer:
            return highlight(code, lexer, _HtmlFormatter(language=lexer.name, classprefix="pygm-"))
        else:
            return super().block_code(code, lang)


class _HtmlFormatter(HtmlFormatter):
    def __init__(self, language, **options):
        super().__init__(**options)
        self.language = language.lower().replace(" ", "")

    def _wrap_div(self, inner):
        for tup in inner:
            yield tup

    def _wrap_pre(self, inner):
        yield 0, '<pre><code class="language-%s">' % self.language
        for tup in inner:
            yield tup
        yield 0, "</code></pre>\n"

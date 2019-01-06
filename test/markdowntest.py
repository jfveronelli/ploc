# coding:utf-8
from crossknight.ploc.markdown import render
from unittest import TestCase


class ModuleTest(TestCase):

    def testRender(self):
        html = render("Hello, **world**!")

        self.assertEqual("<p>Hello, <strong>world</strong>!</p>", html.strip())

    def testRenderWithHtmlBlock(self):
        html = render("Hello, <b>world</b>!")

        self.assertEqual("<p>Hello, <b>world</b>!</p>", html.strip())

    def testRenderWithUnknownCodeBlock(self):
        html = render("```\nhello\n```")

        self.assertEqual('<pre><code class="language-textonly">hello\n</code></pre>', html.strip())

    def testRenderWithInvalidCodeBlock(self):
        html = render("```shelby\n$ ls $HOME\n```")

        expected = '<pre><code class="language-bash">$ ls <span class="pygm-nv">$HOME</span>\n</code></pre>'
        self.assertEqual(expected, html.strip())

    def testRenderWithBashCodeBlockWithManyLines(self):
        html = render("```bash\n$ ls $HOME\n$ ls /etc\n```")

        expected = '<pre><code class="language-bash">$ ls <span class="pygm-nv">$HOME</span>\n$ ls /etc\n</code></pre>'
        self.assertEqual(expected, html.strip())

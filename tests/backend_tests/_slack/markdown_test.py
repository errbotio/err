import sys
import unittest
import logging
import os
from tempfile import mkdtemp
from mock import MagicMock

from errbot.backends._slack.markdown import *


log = logging.getLogger(__name__)


class SlackMarkdownTests(unittest.TestCase):

    def testSlackMarkdownConverter(self):
        md = slack_markdown_converter()
        markdown = md.convert('**hello** [link](http://to.site/path)')
        self.assertEqual(markdown, '*hello* <http://to.site/path|link>')

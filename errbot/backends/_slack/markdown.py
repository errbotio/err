import re
from markdown import Markdown
from markdown.extensions.extra import ExtraExtension
from markdown.preprocessors import Preprocessor
from errbot.rendering.ansiext import AnsiExtension, enable_format, IMTEXT_CHRS

MARKDOWN_LINK_REGEX = re.compile(r"(?<!!)\[(?P<text>[^\]]+?)\]\((?P<uri>[a-zA-Z0-9]+?:\S+?)\)")


def slack_markdown_converter(compact_output=False):
    """
    This is a Markdown converter for use with Slack.
    """
    enable_format("imtext", IMTEXT_CHRS, borders=not compact_output)
    md = Markdown(output_format="imtext", extensions=[ExtraExtension(), AnsiExtension()])
    md.preprocessors.register(LinkPreProcessor(md), "LinkPreProcessor", 30)
    md.stripTopLevelTags = False
    return md


class LinkPreProcessor(Preprocessor):
    """
    This preprocessor converts markdown URL notation into Slack URL notation
    as described at https://api.slack.com/docs/formatting, section "Linking to URLs".
    """

    def run(self, lines):
        for i, line in enumerate(lines):
            lines[i] = MARKDOWN_LINK_REGEX.sub(r"&lt;\2|\1&gt;", line)
        return lines

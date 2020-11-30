import sys
import unittest
import logging
import os
from tempfile import mkdtemp
from mock import MagicMock

from errbot.bootstrap import bot_config_defaults

log = logging.getLogger(__name__)

try:
    from errbot.backends import slack

    class TestSlackBackend(slack.SlackBackend):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.test_msgs = []
            self.sc = MagicMock()

        def callback_message(self, msg):
            self.test_msgs.append(msg)

        def username_to_userid(self, username, *args, **kwargs):
            """Have to mock because we don't have a slack server."""
            return 'Utest'

        def channelname_to_channelid(self, channelname):
            return 'Ctest'

        def channelid_to_channelname(self, channelid):
            return 'meh'

        def get_im_channel(self, id_):
            return 'Cfoo'

        def find_user(self, user):
            m = MagicMock()
            m.name = user
            return m

except SystemExit:
    log.exception("Can't import backends.slack for testing")


@unittest.skip("Tests needs a refactor!!!")
class SlackTests(unittest.TestCase):

    def setUp(self):
        # make up a config.
        tempdir = mkdtemp()
        # reset the config every time
        sys.modules.pop('errbot.config-template', None)
        __import__('errbot.config-template')
        config = sys.modules['errbot.config-template']
        bot_config_defaults(config)
        config.BOT_DATA_DIR = tempdir
        config.BOT_LOG_FILE = os.path.join(tempdir, 'log.txt')
        config.BOT_EXTRA_PLUGIN_DIR = []
        config.BOT_LOG_LEVEL = logging.DEBUG
        config.BOT_IDENTITY = {'username': 'err@localhost', 'token': '___'}
        config.BOT_ASYNC = False
        config.BOT_PREFIX = '!'
        config.CHATROOM_FN = 'blah'

        self.slack = TestSlackBackend(config)

    def testBotMessageWithAttachments(self):
        attachment = {
            'title': 'sometitle',
            'id': 1,
            'fallback': ' *Host:* host-01', 'color': 'daa038',
            'fields': [{'title': 'Metric', 'value': '1', 'short': True}],
            'title_link': 'https://xx.com'
        }
        bot_id = 'B04HMXXXX'
        bot_msg = {
            'channel': 'C0XXXXY6P',
            'icons': {'emoji': ':warning:', 'image_64': 'https://xx.com/26a0.png'},
            'ts': '1444416645.000641',
            'type': 'message',
            'text': '',
            'bot_id': bot_id,
            'username': 'riemann',
            'subtype': 'bot_message',
            'attachments': [attachment]
        }

        self.slack._dispatch_slack_message(bot_msg)
        msg = self.slack.test_msgs.pop()

        self.assertEqual(msg.extras['attachments'], [attachment])

    def testSlackEventObjectAddedToExtras(self):
        bot_id = 'B04HMXXXX'
        bot_msg = {
            'channel': 'C0XXXXY6P',
            'icons': {'emoji': ':warning:', 'image_64': 'https://xx.com/26a0.png'},
            'ts': '1444416645.000641',
            'type': 'message',
            'text': '',
            'bot_id': bot_id,
            'username': 'riemann',
            'subtype': 'bot_message',
        }

        self.slack._dispatch_slack_message(bot_msg)
        msg = self.slack.test_msgs.pop()

        self.assertEqual(msg.extras['slack_event'], bot_msg)

    def testPrepareMessageBody(self):
        test_body = """
        hey, this is some code:
            ```
            foobar
            ```
        """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body]

        test_body = """this block is unclosed: ``` foobar """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body + "\n```\n"]

        test_body = """``` foobar """
        parts = self.slack.prepare_message_body(test_body, 10000)
        assert parts == [test_body + "\n```\n"]

        test_body = """closed ``` foobar ``` not closed ```"""
        # ---------------------------------^ 21st char
        parts = self.slack.prepare_message_body(test_body, 21)
        assert len(parts) == 2
        assert parts[0].count('```') == 2
        assert parts[0].endswith('```')
        assert parts[1].count('```') == 2
        assert parts[1].endswith('```\n')

    def test_extract_identifiers(self):
        extract_from = self.slack.extract_identifiers_from_string

        self.assertEqual(
            extract_from("<@U12345>"),
            (None, "U12345", None, None)
        )

        self.assertEqual(
            extract_from("<@U12345|UName>"),
            ("UName", "U12345", None, None)
        )

        self.assertEqual(
            extract_from("<@B12345>"),
            (None, "B12345", None, None)
        )

        self.assertEqual(
            extract_from("<#C12345>"),
            (None, None, None, "C12345")
        )

        self.assertEqual(
            extract_from("<#G12345>"),
            (None, None, None, "G12345")
        )

        self.assertEqual(
            extract_from("<#D12345>"),
            (None, None, None, "D12345")
        )

        self.assertEqual(
            extract_from("@person"),
            ("person", None, None, None)
        )

        self.assertEqual(
            extract_from("#general/someuser"),
            ("someuser", None, "general", None)
        )

        self.assertEqual(
            extract_from("#general"),
            (None, None, "general", None)
        )

        with self.assertRaises(ValueError):
            extract_from("")

        with self.assertRaises(ValueError):
            extract_from("general")

        with self.assertRaises(ValueError):
            extract_from("<>")

        with self.assertRaises(ValueError):
            extract_from("<C12345>")

        with self.assertRaises(ValueError):
            extract_from("<@I12345>")

    def test_build_identifier(self):
        build_from = self.slack.build_identifier

        def check_person(person, expected_uid, expected_cid):
            return person.userid == expected_uid and person.channelid == expected_cid
        assert build_from("<#C12345>").name == 'meh'
        assert check_person(build_from("<@U12345>"), "U12345", "Cfoo")
        assert check_person(build_from("@user"), "Utest", "Cfoo")
        assert build_from("#channel").name == 'meh'  # the mock always return meh ;)

        self.assertEqual(
            build_from("#channel/user"),
            slack.SlackRoomOccupant(None, "Utest", "Cfoo", self.slack)
        )

    def test_uri_sanitization(self):
        sanitize = self.slack.sanitize_uris

        self.assertEqual(
            sanitize(
                "The email is <mailto:test@example.org|test@example.org>."),
            "The email is test@example.org."
        )

        self.assertEqual(
            sanitize(
                "Pretty URL Testing: <http://example.org|example.org> with "
                "more text"),
            "Pretty URL Testing: example.org with more text"
        )

        self.assertEqual(
            sanitize("URL <http://example.org>"),
            "URL http://example.org"
        )

        self.assertEqual(
            sanitize("Normal &lt;text&gt; that shouldn't be affected"),
            "Normal &lt;text&gt; that shouldn't be affected"
        )

        self.assertEqual(
            sanitize(
                "Multiple uris <mailto:test@example.org|test@example.org>, "
                "<mailto:other@example.org|other@example.org> and "
                "<http://www.example.org>, <https://example.com> and "
                "<http://subdomain.example.org|subdomain.example.org>."),
            "Multiple uris test@example.org, other@example.org and "
            "http://www.example.org, https://example.com and subdomain.example.org."
        )

    def test_slack_markdown_link_preprocessor(self):
        convert = self.slack.md.convert
        self.assertEqual(
            "This is <http://example.com/|a link>.",
            convert("This is [a link](http://example.com/).")
        )
        self.assertEqual(
            "This is <https://example.com/|a link> and <mailto:me@comp.org|an email address>.",
            convert("This is [a link](https://example.com/) and [an email address](mailto:me@comp.org).")
        )
        self.assertEqual(
            "This is <http://example.com/|a link> and a manual URL: https://example.com/.",
            convert("This is [a link](http://example.com/) and a manual URL: https://example.com/.")
        )
        self.assertEqual(
            "<http://example.com/|This is a link>",
            convert("[This is a link](http://example.com/)")
        )
        self.assertEqual(
            "This is http://example.com/image.png.",
            convert("This is ![an image](http://example.com/image.png).")
        )
        self.assertEqual(
            "This is [some text] then <http://example.com|a link>",
            convert("This is [some text] then [a link](http://example.com)")
        )

    def test_mention_processing(self):
        self.slack.sc.server.users.find = MagicMock(side_effect=self.slack.find_user)

        mentions = self.slack.process_mentions

        self.assertEqual(
            mentions(
                "<@U1><@U2><@U3>"),
            (
                "@U1@U2@U3",
                [self.slack.build_identifier('<@U1>'),
                 self.slack.build_identifier('<@U2>'),
                 self.slack.build_identifier('<@U3>')])
        )

        self.assertEqual(
            mentions(
                "Is <@U12345>: here?"),
            (
                "Is @U12345: here?", [self.slack.build_identifier('<@U12345>')])
        )

        self.assertEqual(
            mentions(
                "<@U12345> told me about @a and <@U56789> told me about @b"),
            (
                "@U12345 told me about @a and @U56789 told me about @b",
                [self.slack.build_identifier('<@U12345>'),
                 self.slack.build_identifier('<@U56789>')])
        )

        self.assertEqual(
            mentions(
                "!these!<@UABCDE>!mentions! will !still!<@UFGHIJ>!work!"),
            (
                "!these!@UABCDE!mentions! will !still!@UFGHIJ!work!",
                [self.slack.build_identifier('<@UABCDE>'),
                 self.slack.build_identifier('<@UFGHIJ>')])
        )

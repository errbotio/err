# coding=utf-8
import unittest
import os
from queue import Queue, Empty
from errbot.backends.base import Identifier, Backend, Message
from errbot.backends.base import build_message, build_text_html_message_pair
from errbot import botcmd, templating
from errbot.utils import mess_2_embeddablehtml

LONG_TEXT_STRING = "This is a relatively long line of output, but I am repeated multiple times.\n"

class DummyBackend(Backend):
    outgoing_message_queue = Queue()
    jid = Identifier('err@localhost/err')

    def build_message(self, text):
        return build_message(text, Message)

    def send_message(self, mess):
        self.outgoing_message_queue.put(mess)

    def pop_message(self, timeout=3, block=True):
        return self.outgoing_message_queue.get(timeout=timeout, block=block)

    @botcmd
    def return_args_as_str(self, mess, args):
        return "".join(args)

    @botcmd(template='args_as_html')
    def return_args_as_html(self, mess, args):
        return {'args': args}

    @botcmd
    def raises_exception(self, mess, args):
        raise Exception("Kaboom!")

    @botcmd
    def yield_args_as_str(self, mess, args):
        for arg in args:
            yield arg

    @botcmd(template='args_as_html')
    def yield_args_as_html(self, mess, args):
        for arg in args:
            yield {'args': [arg]}

    @botcmd
    def yields_str_then_raises_exception(self, mess, args):
        yield "foobar"
        raise Exception("Kaboom!")

    @botcmd
    def return_long_output(self, mess, args):
        return LONG_TEXT_STRING * 3

    @botcmd
    def yield_long_output(self, mess, args):
        for i in range(2):
            yield LONG_TEXT_STRING * 3

    def __init__(self):
        super(DummyBackend, self).__init__()
        self.commands['return_args_as_str'] = self.return_args_as_str
        self.commands['return_args_as_html'] = self.return_args_as_html
        self.commands['raises_exception'] = self.raises_exception
        self.commands['yield_args_as_str'] = self.yield_args_as_str
        self.commands['yield_args_as_html'] = self.yield_args_as_html
        self.commands['yields_str_then_raises_exception'] = self.yields_str_then_raises_exception
        self.commands['return_long_output'] = self.return_long_output
        self.commands['yield_long_output'] = self.yield_long_output


class TestBase(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()

    def test_identifier_parsing(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

        id2 = Identifier(jid="gbin@gootz.net")
        self.assertEqual(id2.getNode(), "gbin")
        self.assertEqual(id2.getDomain(), "gootz.net")
        self.assertIsNone(id2.getResource())

    def test_identifier_matching(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        id2 = Identifier(jid="gbin@gootz.net/titi")
        id3 = Identifier(jid="gbin@giitz.net/titi")
        self.assertTrue(id1.bareMatch(id2))
        self.assertFalse(id2.bareMatch(id3))

    def test_identifier_stripping(self):
        id1 = Identifier(jid="gbin@gootz.net/toto")
        self.assertEqual(id1.getStripped(), "gbin@gootz.net")

    def test_identifier_str_rep(self):
        self.assertEqual(str(Identifier(jid="gbin@gootz.net/toto")), "gbin@gootz.net/toto")
        self.assertEqual(str(Identifier(jid="gbin@gootz.net")), "gbin@gootz.net")

    def test_identifier_unicode_rep(self):
        self.assertEqual(str(Identifier(jid="gbin@gootz.net/へようこそ")), "gbin@gootz.net/へようこそ")

    def test_xhtmlparsing_and_textify(self):
        text_plain, node = build_text_html_message_pair("<html><body>Message</body></html>")
        self.assertEqual(text_plain, "Message")
        self.assertEqual(node.tag, "html")
        self.assertEqual(node.getchildren()[0].tag, "body")
        self.assertEqual(node.getchildren()[0].text, 'Message')

    def test_identifier_double_at_parsing(self):
        id1 = Identifier(jid="gbin@titi.net@gootz.net/toto")
        self.assertEqual(id1.getNode(), "gbin@titi.net")
        self.assertEqual(id1.getDomain(), "gootz.net")
        self.assertEqual(id1.getResource(), "toto")

    def test_buildreply(self):
        dummy = self.dummy

        m = dummy.build_message("Content")
        m.setFrom("from@fromdomain.net/fromresource")
        m.setTo("to@todomain.net/toresource")
        resp = dummy.build_reply(m, "Response")

        self.assertEqual(str(resp.getTo()), "from@fromdomain.net")
        self.assertEqual(str(resp.getFrom()), "err@localhost/err")
        self.assertEqual(str(resp.getBody()), "Response")


class TestExecuteAndSend(unittest.TestCase):
    def setUp(self):
        self.dummy = DummyBackend()
        self.example_message = self.dummy.build_message("some_message")
        self.example_message.setFrom("noterr@localhost/resource")
        self.example_message.setTo("err@localhost/resource")

        assets_path = os.path.dirname(__file__) + os.sep + "assets"
        templating.template_path.append(templating.make_templates_path(assets_path))
        templating.env = templating.Environment(loader=templating.FileSystemLoader(templating.template_path))

    def test_commands_can_return_string(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_str', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.return_args_as_str._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().getBody())

    def test_commands_can_return_html(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='return_args_as_html', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.return_args_as_html._err_command_template)
        response = dummy.pop_message()
        self.assertEqual("foobar", response.getBody())
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">foo</strong>'
                         '<em xmlns:ns0="http://jabber.org/protocol/xhtml-im">bar</em>\n\n',
                         mess_2_embeddablehtml(response)[0])

    def test_exception_is_caught_and_shows_error_message(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='raises_exception', args=[], mess=m, jid='noterr@localhost', template_name=dummy.raises_exception._err_command_template)
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().getBody())

        dummy._execute_and_send(cmd='yields_str_then_raises_exception', args=[], mess=m, jid='noterr@localhost', template_name=dummy.yields_str_then_raises_exception._err_command_template)
        self.assertEqual("foobar", dummy.pop_message().getBody())
        self.assertIn(dummy.MSG_ERROR_OCCURRED, dummy.pop_message().getBody())

    def test_commands_can_yield_strings(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_str', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.yield_args_as_str._err_command_template)
        self.assertEqual("foo", dummy.pop_message().getBody())
        self.assertEqual("bar", dummy.pop_message().getBody())

    def test_commands_can_yield_html(self):
        dummy = self.dummy
        m = self.example_message

        dummy._execute_and_send(cmd='yield_args_as_html', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.yield_args_as_html._err_command_template)
        response1 = dummy.pop_message()
        response2 = dummy.pop_message()
        self.assertEqual("foo", response1.getBody())
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">foo</strong>\n\n',
                         mess_2_embeddablehtml(response1)[0])
        self.assertEqual("bar", response2.getBody())
        self.assertEqual('<strong xmlns:ns0="http://jabber.org/protocol/xhtml-im">bar</strong>\n\n',
                         mess_2_embeddablehtml(response2)[0])

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_returned(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='return_long_output', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.return_long_output._err_command_template)
        for i in range(3):  # return_long_output outputs a string that's 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING, dummy.pop_message().getBody())
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})

    def test_output_longer_than_max_message_size_is_split_into_multiple_messages_when_yielded(self):
        dummy = self.dummy
        m = self.example_message
        self.dummy.MESSAGE_SIZE_LIMIT = len(LONG_TEXT_STRING)

        dummy._execute_and_send(cmd='yield_long_output', args=['foo', 'bar'], mess=m, jid='noterr@localhost', template_name=dummy.yield_long_output._err_command_template)
        for i in range(6):  # yields_long_output yields 2 strings that are 3x longer than the size limit
            self.assertEqual(LONG_TEXT_STRING, dummy.pop_message().getBody())
        self.assertRaises(Empty, dummy.pop_message, *[], **{'block': False})

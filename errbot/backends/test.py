import logging
import sys

import unittest
import pytest

from os.path import sep, abspath
from queue import Queue
from tempfile import mkdtemp
from threading import Thread

__import__('errbot.config-template')
config_module = sys.modules['errbot.config-template']
sys.modules['config'] = config_module

tempdir = mkdtemp()
config_module.BOT_DATA_DIR = tempdir
config_module.BOT_LOG_FILE = tempdir + sep + 'log.txt'
config_module.BOT_EXTRA_PLUGIN_DIR = []
config_module.BOT_LOG_LEVEL = logging.DEBUG

# Errbot machinery must not be imported before this point
# because of the import hackery above.
from errbot.backends.base import Message, build_message, Identifier, MUCRoom, MUCOccupant
from errbot.builtins.wsview import reset_app
from errbot.errBot import ErrBot
from errbot.main import main

incoming_stanza_queue = Queue()
outgoing_message_queue = Queue()
joined_rooms = {}  # {'room1_jid': MUCRoom_instance, 'room2_jid': MUCRoom_instance..}

QUIT_MESSAGE = '$STOP$'

STZ_MSG = 1
STZ_PRE = 2
STZ_IQ = 3


class MUCRoom(MUCRoom):
    def __init__(self, jid, occupants=None, topic=None):
        """
        :param jid: JID of the room
        :param occupants: Occupants of the room
        :param topic: The MUC's topic
        """
        if occupants is None:
            occupants = []

        self.jid = jid
        self._occupants = occupants
        self._topic = topic

    @property
    def occupants(self):
        return {jid: MUCOccupant(jid) for jid in self._occupants}

    @property
    def topic(self):
        return self._topic

    @topic.setter
    def topic(self, topic):
        self._topic = topic


class TestBackend(ErrBot):
    def send_message(self, mess):
        super(TestBackend, self).send_message(mess)
        outgoing_message_queue.put(mess.body)

    def serve_forever(self):
        import config

        self.jid = Identifier('Err')  # whatever
        self.connect_callback()  # notify that the connection occured
        self.sender = config.BOT_ADMINS[0]  # By default, assume this is the admin talking
        try:
            while True:
                stanza_type, entry = incoming_stanza_queue.get()
                if entry == QUIT_MESSAGE:
                    logging.info("Stop magic message received, quitting...")
                    break
                if stanza_type is STZ_MSG:
                    msg = Message(entry)
                    msg.frm = self.sender
                    msg.to = self.jid  # To me only
                    self.callback_message(msg)
                elif stanza_type is STZ_PRE:
                    logging.info("Presence stanza received.")
                    self.callback_presence(entry)
                elif stanza_type is STZ_IQ:
                    logging.info("IQ stanza received.")
                else:
                    logging.error("Unknown stanza type.")

        except EOFError as _:
            pass
        except KeyboardInterrupt as _:
            pass
        finally:
            logging.debug("Trigger disconnect callback")
            self.disconnect_callback()
            logging.debug("Trigger shutdown")
            self.shutdown()

    def connect(self):
        return

    def build_message(self, text):
        return build_message(text, Message)

    def shutdown(self):
        super(TestBackend, self).shutdown()

    def join_room(self, room, username=None, password=None):
        import config
        if room in joined_rooms:
            logging.warning("Attempted to join room '{0}', but already in this room".format(room))
        else:
            bot_itself = config.BOT_IDENTITY['username']
            joined_rooms[room] = MUCRoom(jid=room, occupants=[bot_itself])

    def leave_room(self, room):
        try:
            joined_rooms.pop(room)
            logging.info("Left room {0}".format(room))
        except KeyError:
            logging.warning("Attempted to leave room '{0}', but not in this room".format(room))

    @property
    def mode(self):
        return 'text'

    @property
    def rooms(self):
        return joined_rooms


def pop_message(timeout=5, block=True):
    return outgoing_message_queue.get(timeout=timeout, block=block)


def push_message(msg):
    incoming_stanza_queue.put((STZ_MSG, msg), timeout=5)


def push_presence(presence):
    """ presence must at least duck type base.Presence
    """
    incoming_stanza_queue.put((STZ_PRE, presence), timeout=5)


# def pushIQ(stanza):
#    pass

def zap_queues():
    while not incoming_stanza_queue.empty():
        msg = incoming_stanza_queue.get(block=False)
        logging.error('Message left in the incoming queue during a test : %s' % msg)

    while not outgoing_message_queue.empty():
        msg = outgoing_message_queue.get(block=False)
        logging.error('Message left in the outgoing queue during a test : %s' % msg)


def leave_all_rooms():
    """Leaves all joined rooms"""
    global joined_rooms
    for room in joined_rooms.keys():
        logging.info("Left room {0}".format(room))
    joined_rooms = {}


class TestBot(object):
    """
    A minimal bot utilizing the TestBackend, for use with unit testing.

    Only one instance of this class should globally be active at any one
    time.

    End-users should not use this class directly. Use
    :func:`~errbot.backends.test.testbot` or
    :class:`~errbot.backends.test.FullStackTest` instead, which use this
    class under the hood.
    """
    bot_thread = None

    def __init__(self, extra_plugin_dir=None, loglevel=logging.DEBUG):
        """
        :param extra_plugin_dir: Path to a directory from which additional
            plugins should be loaded.
        :param loglevel: Logging verbosity. Expects one of the constants
            defined by the logging module.
        """
        # reset logging to console
        logging.basicConfig(format='%(levelname)s:%(message)s')
        file = logging.FileHandler(config_module.BOT_LOG_FILE, encoding='utf-8')
        self.logger = logging.getLogger('')
        self.logger.setLevel(loglevel)
        self.logger.addHandler(file)

        import config
        config.BOT_EXTRA_PLUGIN_DIR = extra_plugin_dir
        config.BOT_LOG_LEVEL = loglevel

    def start(self):
        """
        Start the bot

        Calling this method when the bot has already started will result
        in an Exception being raised.
        """
        if self.bot_thread is not None:
            raise Exception("Bot has already been started")
        self.bot_thread = Thread(target=main, name='TestBot main thread', args=(TestBackend, self.logger))
        self.bot_thread.setDaemon(True)
        self.bot_thread.start()

        # Ensure bot is fully started and plugins are loaded before returning
        push_message("!echo ready")
        assert pop_message(timeout=60) == "ready"

    def stop(self):
        """
        Stop the bot

        Calling this method before the bot has started will result in an
        Exception being raised.
        """
        if self.bot_thread is None:
            raise Exception("Bot has not yet been started")
        push_message(QUIT_MESSAGE)
        self.bot_thread.join()
        reset_app()  # empty the bottle ... hips!
        logging.info("Main bot thread quits")
        zap_queues()
        leave_all_rooms()
        self.bot_thread = None


class FullStackTest(unittest.TestCase, TestBot):
    """
    Test class for use with Python's unittest module to write tests
    against a fully functioning bot.

    For example, if you wanted to test the builtin `!about` command,
    you could write a test file with the following::

        from errbot.backends.test import FullStackTest, push_message, pop_message

        class TestCommands(FullStackTest):
            def test_about(self):
                push_message('!about')
                self.assertIn('Err version', pop_message())
    """

    def setUp(self, extra_plugin_dir=None, extra_test_file=None, loglevel=logging.DEBUG):
        """
        :param extra_plugin_dir: Path to a directory from which additional
            plugins should be loaded.
        :param extra_test_file: [Deprecated but kept for backward-compatibility,
            use extra_plugin_dir instead]
            Path to an additional plugin which should be loaded.
        :param loglevel: Logging verbosity. Expects one of the constants
            defined by the logging module.
        """
        if extra_plugin_dir is None and extra_test_file is not None:
            extra_plugin_dir = sep.join(abspath(extra_test_file).split(sep)[:-2])

        TestBot.__init__(self, extra_plugin_dir=extra_plugin_dir, loglevel=loglevel)
        self.start()

    def tearDown(self):
        self.stop()

    def assertCommand(self, command, response, timeout=5):
        """Assert the given command returns the given response"""
        push_message(command)
        self.assertIn(response, popMessage(), timeout)

    def assertCommandFound(self, command, timeout=5):
        """Assert the given command does not exist"""
        push_message(command)
        self.assertNotIn('not found', popMessage(), timeout)


@pytest.fixture
def testbot(request):
    """
    Pytest fixture to write tests against a fully functioning bot.

    For example, if you wanted to test the builtin `!about` command,
    you could write a test file with the following::

        from errbot.backends.test import testbot, push_message, pop_message

        def test_about(testbot):
            push_message('!about')
            assert "Err version" in pop_message()

    It's possible to provide additional configuration to this fixture,
    by setting variables at module level or as class attributes (the
    latter taking precedence over the former). For example::

        from errbot.backends.test import testbot, push_message, pop_message

        extra_plugin_dir = '/foo/bar'

        def test_about(testbot):
            pushMessage('!about')
            assert "Err version" in pop_message()

    ..or::

        from errbot.backends.test import testbot, push_message, pop_message

        extra_plugin_dir = '/foo/bar'

        class Tests(object):
            # Wins over `extra_plugin_dir = '/foo/bar'` above
            extra_plugin_dir = '/foo/baz'

            def test_about(self, testbot):
                push_message('!about')
                assert "Err version" in pop_message()

    ..to load additional plugins from the directory `/foo/bar` or
    `/foo/baz` respectively. This works for the following items, which are
    passed to the constructor of :class:`~errbot.backends.test.TestBot`:

    * `extra_plugin_dir`
    * `loglevel`
    """

    def on_finish():
        bot.stop()

    kwargs = {}
    for attr, default in (
        ('extra_plugin_dir', None),
        ('loglevel', logging.DEBUG),
    ):
            if hasattr(request, 'instance'):
                kwargs[attr] = getattr(request.instance, attr, None)
            if kwargs[attr] is None:
                kwargs[attr] = getattr(request.module, attr, default)

    bot = TestBot(**kwargs)
    bot.start()

    request.addfinalizer(on_finish)
    return bot


# Backward compatibility
popMessage = pop_message
pushMessage = push_message
pushPresence = push_presence
zapQueues = zap_queues

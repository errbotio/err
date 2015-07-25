import logging
from uuid import uuid4

from errbot import BotPlugin, PY3, botcmd, SeparatorArgParser, ShlexArgParser
from errbot.backends.base import RoomNotJoinedError
from errbot.exceptions import SlackAPIResponseError
from errbot.version import VERSION
from errbot.utils import compat_str

log = logging.getLogger(__name__)

__author__ = 'gbin'

# 2to3 hack
# thanks to https://github.com/oxplot/fysom/issues/1
# which in turn references http://www.rfk.id.au/blog/entry/preparing-pyenchant-for-python-3/
if PY3:
    basestring = (str, bytes)


SLACK_USER_IS_BOT_HELPTEXT = (
    "Connected to Slack using a bot account, which cannot manage "
    "channels itself (you must invite the bot to channels instead, "
    "it will auto-accept) nor invite people.\n\n"
    "If you need this functionality, you will have to create a "
    "regular user account and connect Err using that account. "
    "For this, you will also need to generate a user token at "
    "https://api.slack.com/web."
)


class ChatRoom(BotPlugin):
    min_err_version = VERSION  # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    connected = False

    def callback_connect(self):
        log.info('Callback_connect')
        if not self.connected:
            self.connected = True
            for room in self.bot_config.CHATROOM_PRESENCE:
                log.debug('Try to join room %s' % repr(room))
                room_name = compat_str(room)
                if room_name is not None:
                    room, username, password = (room_name, self.bot_config.CHATROOM_FN, None)
                else:
                    room, username, password = (room[0], self.bot_config.CHATROOM_FN, room[1])
                log.info("Joining room {} with username {}".format(room, username))
                try:
                    self.query_room(room).join(username=self.bot_config.CHATROOM_FN, password=password)
                except NotImplementedError:
                    # Backward compatibility for backends which do not yet have a
                    # query_room implementation and still have a join_room method.
                    logging.warning("query_room not implemented on this backend, using legacy join_room instead")
                    self.join_room(room, username=username, password=password)
                except SlackAPIResponseError as e:
                    if e.error != "user_is_bot":
                        raise
                    log.warning("Ignoring entries from CHATROOM_PRESENCE. " + SLACK_USER_IS_BOT_HELPTEXT)
                    return

    def deactivate(self):
        self.connected = False
        super(ChatRoom, self).deactivate()

    @botcmd(split_args_with=SeparatorArgParser())
    def room_create(self, message, args):
        """
        Create a chatroom.

        Usage:
        !room create <room>

        Examples (XMPP):
        !room create example-room@chat.server.tld

        Examples (IRC):
        !room create #example-room

        Example (TOX): (no room name at creation)
        !room create
        """
        if self.mode == 'tox':
            if len(args) != 0:
                return "You cannot specify a chatgroup name on TOX."
            room = self.query_room(None)
        else:
            if len(args) < 1:
                return "Please tell me which chatroom to create."
            room = self.query_room(args[0])

        try:
            room.create()
        except SlackAPIResponseError as e:
            if e.error != "user_is_bot":
                raise
            return "Unable to create rooms. " + SLACK_USER_IS_BOT_HELPTEXT

        return "Created the room {}".format(room)

    @botcmd()
    def room_join(self, message, args):
        """
        Join (creating it first if needed) a chatroom.

        Usage:
        !room join <room> [<password>]

        Examples (XMPP):
        !room join example-room@chat.server.tld
        !room join example-room@chat.server.tld super-secret-password

        Examples (IRC):
        !room join #example-room
        !room join #example-room super-secret-password
        """
        # We must account for password with whitespace before, after or in the middle
        args = args.split(' ', 1)
        arglen = len(args)
        if arglen < 1:
            return "Please tell me which chatroom to join."
        args[0].strip()

        room, password = (args[0], None) if arglen == 1 else (args[0], args[1])
        try:
            self.query_room(room).join(username=self.bot_config.CHATROOM_FN, password=password)
        except SlackAPIResponseError as e:
            if e.error != "user_is_bot":
                raise
            return "Unable to join rooms. " + SLACK_USER_IS_BOT_HELPTEXT
        return "Joined the room {}".format(room)

    @botcmd(split_args_with=SeparatorArgParser())
    def room_leave(self, message, args):
        """
        Leave a chatroom.

        Usage:
        !room leave <room>

        Examples (XMPP):
        !room leave example-room@chat.server.tld

        Examples (IRC):
        !room leave #example-room
        """
        if len(args) < 1:
            return "Please tell me which chatroom to leave."
        try:
            self.query_room(args[0]).leave()
        except SlackAPIResponseError as e:
            if e.error != "user_is_bot":
                raise
            return "Unable to leave rooms. " + SLACK_USER_IS_BOT_HELPTEXT
        return "Left the room {}".format(args[0])

    @botcmd(split_args_with=SeparatorArgParser())
    def room_destroy(self, message, args):
        """
        Destroy a chatroom.

        Usage:
        !room destroy <room>

        Examples (XMPP):
        !room destroy example-room@chat.server.tld

        Examples (IRC):
        !room destroy #example-room
        """
        if len(args) < 1:
            return "Please tell me which chatroom to destroy."
        try:
            self.query_room(args[0]).destroy()
        except SlackAPIResponseError as e:
            if e.error != "user_is_bot":
                raise
            return "Unable to destroy rooms. " + SLACK_USER_IS_BOT_HELPTEXT
        return "Destroyed the room {}".format(args[0])

    @botcmd(split_args_with=SeparatorArgParser())
    def room_invite(self, message, args):
        """
        Invite one or more people into a chatroom.

        Usage:
        !room invite <room> <identifier1> [<identifier2>, ..]

        Examples (XMPP):
        !room invite room@conference.server.tld bob@server.tld

        Examples (IRC):
        !room invite #example-room bob
        """
        if len(args) < 2:
            return "Please tell me which person(s) to invite into which room."
        try:
            self.query_room(args[0]).invite(*args[1:])
        except SlackAPIResponseError as e:
            if e.error != "user_is_bot":
                raise
            return "Unable to invite people into rooms. " + SLACK_USER_IS_BOT_HELPTEXT
        return "Invited {} into the room {}".format(", ".join(args[1:]), args[0])

    @botcmd
    def room_list(self, message, args):
        """
        List chatrooms the bot has joined.

        Usage:
        !room list

        Examples:
        !room list
        """
        rooms = [str(room) for room in self.rooms()]
        if len(rooms):
            return "I'm currently in these rooms:\n\t{}".format("\n\t".join(rooms))
        else:
            return "I'm not currently in any rooms."

    @botcmd(split_args_with=ShlexArgParser())
    def room_occupants(self, message, args):
        """
        List the occupants in a given chatroom.

        Usage:
        !room occupants <room 1> [<room 2> ..]

        Examples (XMPP):
        !room occupants room@conference.server.tld

        Examples (IRC):
        !room occupants #example-room #another-example-room
        """
        if len(args) < 1:
            yield "Please supply a room to list the occupants of."
            return
        for room in args:
            try:
                occupants = [o.person for o in self.query_room(room).occupants]
                yield "Occupants in {}:\n\t{}".format(room, "\n\t".join(occupants))
            except RoomNotJoinedError as e:
                yield "Cannot list occupants in {}: {}".format(room, e)

    @botcmd(split_args_with=ShlexArgParser())
    def room_topic(self, message, args):
        """
        Get or set the topic for a room.

        Usage:
        !room topic <room> [<new topic>]

        Examples (XMPP):
        !room topic example-room@chat.server.tld
        !room topic example-room@chat.server.tld "Err rocks!"

        Examples (IRC):
        !room topic #example-room
        !room topic #example-room "Err rocks!"
        """
        arglen = len(args)
        if arglen < 1:
            return "Please tell me which chatroom you want to know the topic of."

        if arglen == 1:
            try:
                topic = self.query_room(args[0]).topic
            except RoomNotJoinedError as e:
                return "Cannot get the topic for {}: {}".format(args[0], e)
            if topic is None:
                return "No topic is set for {}".format(args[0])
            else:
                return "Topic for {}: {}".format(args[0], topic)
        else:
            try:
                self.query_room(args[0]).topic = args[1]
            except RoomNotJoinedError as e:
                return "Cannot set the topic for {}: {}".format(args[0], e)
            return "Topic for {} set.".format(args[0])

    @botcmd
    def gtalk_room_create(self, mess, args):
        """ Create an adhoc chatroom for Google talk and invite the listed persons.
            If no person is listed, only the requestor is invited.

            Examples:
            !root create
            !root create gbin@gootz.net toto@gootz.net
        """
        room_name = "private-chat-%s@groupchat.google.com" % uuid4()
        self.join_room(room_name)
        to_invite = (mess.frm.stripped,) if not args else (jid.strip() for jid in args.split())
        self.invite_in_room(room_name, to_invite)
        return "Room created (%s)" % room_name

    def callback_message(self, mess):
        try:
            mess_type = mess.type
            if mess_type == 'chat':
                username = mess.frm.person
                if username in self.bot_config.CHATROOM_RELAY:
                    log.debug('Message to relay from %s.' % username)
                    body = mess.body
                    rooms = self.bot_config.CHATROOM_RELAY[username]
                    for room in rooms:
                        self.send(room, body, message_type='groupchat')
            elif mess_type == 'groupchat':
                fr = mess.frm
                chat_room = fr.room
                if chat_room in self.bot_config.REVERSE_CHATROOM_RELAY:
                    users_to_relay_to = self.bot_config.REVERSE_CHATROOM_RELAY[chat_room]
                    log.debug('Message to relay to %s.' % users_to_relay_to)
                    body = '[%s] %s' % (fr.person, mess.body)
                    for user in users_to_relay_to:
                        self.send(user, body)
        except Exception as e:
            log.exception('crashed in callback_message %s' % e)

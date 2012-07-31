import logging
import xmpp
from errbot.botplugin import BotPlugin
from errbot.utils import get_jid_from_message
from threading import Timer
from errbot.version import VERSION

__author__ = 'gbin'
from config import CHATROOM_PRESENCE, CHATROOM_FN, CHATROOM_RELAY, HIPCHAT_MODE, REVERSE_CHATROOM_RELAY

class ChatRoom(BotPlugin):
    min_err_version = VERSION # don't copy paste that for your plugin, it is just because it is a bundled plugin !
    max_err_version = VERSION

    connected = False
    def keep_alive(self):
        # logging.debug('Keep alive sent')
        if HIPCHAT_MODE:
            self.send('nobody', ' ', message_type='groupchat') # hack from hipchat itself
        else:
            pres = xmpp.Presence()
            self.bare_send(pres)

        self.t = Timer(10.0, self.keep_alive)
        self.t.setDaemon(True) # so it is not locking on exit
        self.t.start()

    def callback_connect(self):
        logging.info('Callback_connect')
        if not self.connected:
            self.connected = True
            for room in CHATROOM_PRESENCE:
                logging.info('Join room ' + room)
                self.join_room(room, CHATROOM_FN)

            logging.info('Start keep alive')
            self.keep_alive()

    def callback_message(self, conn, mess):
        #if mess.getBody():
        #    logging.debug(u'Received message %s' % mess.getBody())
        try:
            mess_type = mess.getType()
            if mess_type == 'chat':
                username = get_jid_from_message(mess)
                if username in CHATROOM_RELAY:
                    logging.debug('Message to relay from %s.' % username)
                    body = mess.getBody()
                    rooms = CHATROOM_RELAY[username]
                    for room in rooms:
                        self.send(room, body, message_type='groupchat')
            elif mess_type == 'groupchat':
                fr = mess.getFrom()
                chat_room = fr.node + '@' + fr.domain
                if chat_room in REVERSE_CHATROOM_RELAY:
                    users_to_relay_to = REVERSE_CHATROOM_RELAY[chat_room]
                    logging.debug('Message to relay to %s.' % users_to_relay_to)
                    body = '[%s] %s' % (fr.resource, mess.getBody())
                    for user in users_to_relay_to:
                        self.send(user, body, message_type='chat')
        except Exception as e:
            logging.exception('crashed in callback_message %s' % e)


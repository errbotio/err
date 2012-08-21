import logging
import os
from config import BOT_DATA_DIR
import sys
from PySide import QtCore, QtGui, QtWebKit
from PySide.QtGui import QCompleter
from PySide.QtCore import Qt, QUrl
import config
import errbot
from errbot.backends.base import Connection, Message, Identifier
from errbot.errBot import ErrBot

class CommandBox(QtGui.QLineEdit, object):
    history_index = 0

    def reset_history(self):
        self.history_index = len(self.history)

    def __init__(self, history, commands):
        self.history = history
        self.reset_history()
        super(CommandBox, self).__init__()
        completer = QCompleter(['!' + name for name in commands])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(completer)

    #noinspection PyStringFormat
    def keyPressEvent(self, *args, **kwargs):
        key = args[0].key()
        if key == Qt.Key_Up:
            if self.history_index > 0:
                self.history_index -= 1
                self.setText('!%s %s' % self.history[self.history_index])
                return
        elif key == Qt.Key_Down:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setText('!%s %s' % self.history[self.history_index])
                return
        super(CommandBox, self).keyPressEvent(*args, **kwargs)
        if key == QtCore.Qt.Key_Return:
            self.reset_history()

class ConnectionMock(Connection, QtCore.QObject):

    newAnswer = QtCore.Signal(str, bool)
    def send_message(self, mess):
        self.send(mess)
    def send(self, mess):
        if hasattr(mess, 'getBody') and mess.getBody() and not mess.getBody().isspace():
            html_content = mess.getHTML()

            if html_content:
                body = html_content.getTag('body')
                answer = ''.join([unicode(kid) for kid in body.kids]) + body.getData()
            else:
                answer = mess.getBody()
            self.newAnswer.emit(answer, bool(html_content))

import re
urlfinder = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')
def linkify(text):
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = unicode(url)
        if text.startswith('http://'):
            text = text.replace('http://', '', 1)
        elif text.startswith('https://'):
            text = text.replace('https://', '', 1)

        if text.startswith('www.'):
            text = text.replace('www.', '', 1)

        imglink = ''
        for a in ['png', '.gif', '.jpg', '.jpeg', '.svg']:
            if text.lower().endswith(a):
                imglink = '<br /><img src="' + url + '" />'
                break
        return '<a href="' + url + '" target="_blank" rel="nofollow">' + text + '<img class="imglink" src="/images/linkout.png"></a>' + imglink

    return urlfinder.sub(replacewithlink, text)

def htmlify(text, is_html, receiving):
    tag = 'div' if is_html else 'pre'
    if not is_html:
        text = linkify(text)
    style = 'background-color : rgba(251,247,243,0.5); border-color:rgba(251,227,223,0.5);' if receiving else 'background-color : rgba(243,247,251,0.5); border-color: rgba(223,227,251,0.5);'
    return '<%s style="margin:0px; padding:20px; border-style:solid; border-width: 0px 0px 1px 0px; %s"> %s </%s>' % (tag, style, text, tag)

class GraphicBackend(ErrBot):

    conn = ConnectionMock()

    def send_command(self):
        self.new_message(self.input.text(), False)
        msg = Message(self.input.text())
        msg.setFrom(Identifier(node=config.BOT_ADMINS[0])) # assume this is the admin talking
        self.callback_message(self.conn, msg)
        self.input.clear()


    def new_message(self, text, is_html, receiving = True):
        self.buffer += htmlify(text, is_html, receiving)
        self.output.setHtml(self.buffer)

    def scroll_output_to_bottom(self):
        self.output.page().mainFrame().scroll(0, self.output.page().mainFrame().scrollBarMaximum(QtCore.Qt.Vertical))

    def build_message(self, text):
        txt, node = self.build_text_html_message_pair(text)
        if node :
            return Message(txt, html = node) # rebuild a pure html snippet to include directly in the console html
        return Message(txt)

    def serve_forever(self):
        self.jid = Identifier('blah') # whatever
        self.connect() # be sure we are "connected" before the first command
        self.connect_callback() # notify that the connection occured

        # create window and components
        app = QtGui.QApplication(sys.argv)
        self.mainW = QtGui.QWidget()
        self.mainW.setWindowTitle('Err...')
        icon_path = os.path.dirname(errbot.__file__) + os.sep + 'err.svg'
        bg_path = os.path.dirname(errbot.__file__) + os.sep + 'err-bg.svg'
        self.mainW.setWindowIcon(QtGui.QIcon(icon_path))
        vbox = QtGui.QVBoxLayout()
        self.input = CommandBox(self.cmd_history, self.commands)
        self.output = QtWebKit.QWebView()

        # init webpage
        self.buffer = """<html>
                           <head>
                                <link rel="stylesheet" type="text/css" href="%s/style/style.css" />
                           </head>
                           <body style=" background-image: url('%s'); background-repeat: no-repeat; background-position:center center; background-attachment:fixed; background-size: contain; margin:0;">
                           """ % (QUrl.fromLocalFile(BOT_DATA_DIR).toString(), QUrl.fromLocalFile(bg_path).toString())
        self.output.setHtml(self.buffer)

        # layout
        vbox.addWidget(self.output)
        vbox.addWidget(self.input)
        self.mainW.setLayout(vbox)

        # setup web view to open liks in external browser
        self.output.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)

        # connect signals/slots
        self.output.page().mainFrame().contentsSizeChanged.connect(self.scroll_output_to_bottom)
        self.output.page().linkClicked.connect(QtGui.QDesktopServices.openUrl)
        self.input.returnPressed.connect(self.send_command)
        self.conn.newAnswer.connect(self.new_message)

        self.mainW.show()
        try:
            app.exec_()
        finally:
            self.disconnect_callback()
            self.shutdown()
            exit(0)

    def connect(self):
        if not self.conn:
            self.conn = ConnectionMock()
        return self.conn

    def join_room(self, room, username=None, password=None):
        pass # just ignore that

    def shutdown(self):
        super(GraphicBackend, self).shutdown()

    @property
    def mode(self):
        return 'graphic'

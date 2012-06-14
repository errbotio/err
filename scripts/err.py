#!/usr/bin/python2.7

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import logging
from os import path, access, makedirs, sep, getcwd
from posix import W_OK
import sys
import argparse
from time import sleep
import daemon

logging.basicConfig(format='%(levelname)s:%(message)s')
logger = logging.getLogger('')
logger.setLevel(logging.INFO)

def check_config(config_path):
    __import__('errbot.config-template') # - is on purpose, it should not be imported normally ;)
    template = sys.modules['errbot.config-template']
    config_fullpath = config_path + sep + 'config.py'

    if not path.exists(config_fullpath):
        logging.error('I cannot find the file config.py in the directory %s \n(You can change this directory with the -c parameter see --help)' % config_path)
        logging.info('You can use the template %s as a base and copy it to %s. \nYou can then customize it.' % (path.dirname(template.__file__) + sep + 'config-template.py',  config_path + sep))
        exit(-1)

    try:
        import config
        diffs = [item for item in set(dir(template)) - set(dir(config)) if not item.startswith('_')]
        if diffs:
            logging.error('You are missing configs defined from the template :')
            for diff in diffs:
                logging.error('Missing config : %s' % diff)
            exit(-1)
    except Exception, e:
        logging.exception('I could not import your config from %s, please check the error below...' % config_fullpath)
        exit(-1)
    logging.info('Config check passed...')

def main():
    # from here the environment is supposed to be set (daemon / non daemon,
    # config.py in the python path )
    from errbot.utils import PLUGINS_SUBDIR
    from errbot.errBot import ErrBot
    from errbot import holder
    from config import BOT_IDENTITY, BOT_LOG_LEVEL, BOT_DATA_DIR, BOT_LOG_FILE

    holder.bot = ErrBot(**BOT_IDENTITY)

    if BOT_LOG_FILE:
        hdlr = logging.FileHandler(BOT_LOG_FILE)
        hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(hdlr)
    logger.setLevel(BOT_LOG_LEVEL)

    d = path.dirname(BOT_DATA_DIR)
    if not path.exists(d):
        raise Exception('The data directory %s for the bot does not exist' % BOT_DATA_DIR)
    if not access(BOT_DATA_DIR, W_OK):
        raise Exception('The data directory %s should be writable for the bot' % BOT_DATA_DIR)

    # make the plugins subdir to store the plugin shelves
    d = BOT_DATA_DIR + sep + PLUGINS_SUBDIR
    if not path.exists(d):
        makedirs(d)

    holder.bot.update_dynamic_plugins()
    logging.debug('serve from %s' % holder.bot)
    holder.bot.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='The main entry point of the XMPP bot err.')
    parser.add_argument('-d', '--daemon', action='store_true', help='Detach the process from the console')
    parser.add_argument('-c', '--config', default=getcwd(), help='Specify the directory where your config.py is (default: current working directory)')
    parser.add_argument('-t', '--test', action='store_true', help='put err in test mode on the console')

    args = vars(parser.parse_args()) # create a dictionary of args
    config_path = args['config']
    # setup the environment to be able to import the config.py
    sys.path.append(config_path) # appends the current directory in order to find config.py
    check_config(config_path) # check if everything is ok before attempting to start

    if args['daemon']:
        if args['test']:
            raise Exception('You cannot run in test and daemon mode at the same time')
        with daemon.DaemonContext(detach_process=True,working_directory=getcwd()): # put the initial working directory to be sure not to lost it after daemonization
            main()

    if args['test']:
        # Sets a minimal logging on the console for the critical config errors
        from errbot.testmode import patch_jabberbot
        patch_jabberbot()

    main()
    logging.info('Process exiting')

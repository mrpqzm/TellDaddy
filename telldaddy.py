import logging
import os.path
import signal
import socket
import sys

from appdirs import AppDirs

pkgname = 'urlwatch'
urlwatch_dir = os.path.expanduser(os.path.join('~', '.' + pkgname))
urlwatch_cache_dir = AppDirs(pkgname).user_cache_dir

if not os.path.exists(urlwatch_dir):
    urlwatch_dir = AppDirs(pkgname).user_config_dir

# Check if we are installed in the system already
(prefix, bindir) = os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))

if bindir != 'bin':
    sys.path.insert(0, os.path.join(prefix, bindir, 'lib'))

from urlwatch.command import UrlwatchCommand
from urlwatch.config import CommandConfig
from urlwatch.main import Urlwatch
from urlwatch.storage import YamlConfigStorage, CacheMiniDBStorage, UrlsYaml

# One minute (=60 seconds) timeout for each request to avoid hanging
socket.setdefaulttimeout(60)

# Ignore SIGPIPE for stdout (see https://github.com/thp/urlwatch/issues/77)
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except AttributeError:
    # Windows does not have signal.SIGPIPE
    ...

logger = logging.getLogger(pkgname)

CONFIG_FILE = 'urlwatch.yaml'
URLS_FILE = 'urls.yaml'
CACHE_FILE = 'cache.db'
HOOKS_FILE = 'hooks.py'


def setup_logger(verbose):
    if verbose:
        root_logger = logging.getLogger('')
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(asctime)s %(module)s %(levelname)s: %(message)s'))
        root_logger.addHandler(console)
        root_logger.setLevel(logging.DEBUG)
        root_logger.info('turning on verbose logging mode')


if __name__ == '__main__':
    config_file = os.path.join(urlwatch_dir, CONFIG_FILE)
    urls_file = os.path.join(urlwatch_dir, URLS_FILE)
    hooks_file = os.path.join(urlwatch_dir, HOOKS_FILE)
    new_cache_file = os.path.join(urlwatch_cache_dir, CACHE_FILE)
    old_cache_file = os.path.join(urlwatch_dir, CACHE_FILE)
    cache_file = new_cache_file
    if os.path.exists(old_cache_file) and not os.path.exists(new_cache_file):
        cache_file = old_cache_file

    command_config = CommandConfig(pkgname, urlwatch_dir, bindir, prefix,
                                   config_file, urls_file, hooks_file, cache_file, False)
    setup_logger(command_config.verbose)

    # setup storage API
    config_storage = YamlConfigStorage(command_config.config)
    cache_storage = CacheMiniDBStorage(command_config.cache)
    urls_storage = UrlsYaml(command_config.urls)

    # setup urlwatcher
    urlwatch = Urlwatch(command_config, config_storage, cache_storage, urls_storage)
    urlwatch_command = UrlwatchCommand(urlwatch)

    # run urlwatcher
    urlwatch_command.run()

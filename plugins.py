#!/usr/bin/python

import glob
import json

from color_print import ColorPrint

#from enum import Enum


#class PluginAttribute(Enum):
#    NAME = 'name'
#    TYPE = 'type'
#    FLAG = 'flag'
#    ACTIVE = 'active'
#    NOTIFY = 'notify'
#    COMMANDS = 'commands'
#    PLUGINS = 'plugins'
#    DESC = 'description'###


class PluginsLoader(object):
    """
    This class responsible to load the plugins
    """
    def __init__(self, plugins_dir):
        self.plugins_dir = plugins_dir
        ColorPrint.info("Init: PluginsLoader")
        self.plugins = dict()

    def load_plugins(self):
        for file_path in glob.iglob(r'{0}/*.json'.format(self.plugins_dir)):
            with open(file_path) as json_file:
                plugin = json.load(json_file)
                if plugin['active']:
                    ColorPrint.info("Loading plugin {0}".format(plugin['name']))
                    self.plugins[plugin['flag']] = plugin

        return self.plugins


if __name__ == '__main__':
    pl = PluginsLoader("./plugins")
    pl.load_plugins()
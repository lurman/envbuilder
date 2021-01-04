#!/usr/local/bin/python

from ConfigParser import RawConfigParser
from ConfigParser import NoSectionError
import os
from color_print import ColorPrint

ENVBUILDER_CONF = 'envbuilder.conf'
ENVB_PATH = 'ENVB_PATH'

class SncConfig(object):
    def __init__(self):
        self.config = RawConfigParser(allow_no_value=False)
        try:
            if ENVB_PATH in os.environ:
                self.config_file_path = os.environ[ENVB_PATH] + os.sep + ENVBUILDER_CONF;
                if len(str(self.config_file_path).strip()) > len(ENVBUILDER_CONF):
                    self.config.read(self.config_file_path)
                else:
                    self.config.read(ENVBUILDER_CONF)
            else:
                self.config.read(ENVBUILDER_CONF)
                os.environ[ENVB_PATH] = os.getcwd()
        except:
            ColorPrint.err("Config file {0} not found".format(ENVBUILDER_CONF))
            exit(1)


    def getstring(self, section, param_name):
        try:
            return self.config.get(section, param_name)
        except:
            ColorPrint.err("Config file {0} or section not found".format(ENVBUILDER_CONF))
            exit(1)

    def getboolean(self,section, param_name):
        try:
            return self.config.getboolean(section, param_name)
        except :
            ColorPrint.err("Config file {0} or section not found".format(ENVBUILDER_CONF))
            exit(1)

    def getint(self,section,param_name):
        try:
            return self.config.getint(section, param_name)
        except:
            ColorPrint.err("Config file {0} or section not found".format(ENVBUILDER_CONF))
            exit(1)

    def getlist(self, section, param_name):
        try:
            cfg_list = self.config.get(section, param_name)
            return cfg_list.split(",")
        except:
            ColorPrint.err("Config file {0} or section not found".format(ENVBUILDER_CONF))
            exit(1)

    def getsection(self, section_name):
        try:
            return self.config.items(section_name)
        except:
            ColorPrint.err("Config file {0} or section not found".format(ENVBUILDER_CONF))
            exit(1)


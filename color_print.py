#!/usr/bin/env python


class ColorPrint(object):

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = "\033[1m"

    @staticmethod
    def info(msg):
        print ColorPrint.OKGREEN + ' ' + msg + ' ' + ColorPrint.ENDC

    @staticmethod
    def warn(msg):
        print ColorPrint.WARNING + ' ' + msg + ' ' + ColorPrint.ENDC

    @staticmethod
    def err(msg):
        print ColorPrint.FAIL + ' ' + msg + ' ' + ColorPrint.ENDC

    @staticmethod
    def blue_highlight(msg):
        print ColorPrint.OKBLUE + ' ' + msg + ' ' + ColorPrint.ENDC



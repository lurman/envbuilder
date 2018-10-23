#!/usr/bin/python


class Properties(object):

    def __init__(self, path_to_file):
        self.separator = "="
        self.properties = {}

        # I named your file conf and stored it
        # in the same directory as the script

        with open(path_to_file) as f:

            for line in f:
                if self.separator in line:
                    # Find the name and value by splitting the string
                    name, value = line.split(self.separator, 1)

                    # Assign key value pair to dict
                    # strip() removes white space from the ends of strings
                    self.properties[name.strip()] = value.strip()

    def get_all_properies(self):
        return self.properties

    def get_property(self,key):
        if key in self.properties.keys():
            return self.properties[key]
        return None
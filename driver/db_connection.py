"""
DB Connection
"""

import pymysql
import configparser
import os

class Connection_Manager:
    _instance_ = None

    def __new__(cm):
        if cm._instance_ is None:
            cm._instance_ = super(Connection_Manager, cm).__new__(cm)

            config_parser = configparser.ConfigParser()
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_parser.read(os.path.join(project_dir, 'config.ini'))
            
            cm._instance_.config = {
                'host': config_parser['Database']['Host'],
                'user': config_parser['Database']['User'],
                'password': config_parser['Database']['Password'],
                'database': config_parser['Database']['Name'],
                'charset': config_parser['Database']['Charset'],
                'cursorclass': pymysql.cursors.DictCursor
            }
            cm._instance_._conn = None

        return cm._instance_
    
    #get a connection, persistent conn for optimization
    def get_connection(self):
        #when conn is unlinked
        if self._conn is None:
            self._conn = pymysql.connect(**self.config)
        #else check conn idle or reconnect,
        else:
            try:
                self._conn.ping(reconnect=True)
            except:
                self._conn = pymysql.connect(**self.config)

        #return an available conn
        return self._conn
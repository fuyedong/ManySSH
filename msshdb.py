# -*- coding:utf-8 -*-
'''
File: msshdb.py
Author: Wayne Xue <xwsou@gmail.com>
Date: 2014-11-11
Description: ManySSH Database
'''

import os
import sqlite3


class Database(object):
    """Database init"""
    def __init__(self, version_num):
        self.upgrade_action_existed = False
        self.version_num = version_num
        home = os.path.expanduser("~") + "/.mssh"
        if not os.path.exists(home):
            os.mkdir(home, 0700)
        dbfile = home + '/mssh.db'
        self.conn = sqlite3.connect(dbfile)
        self.init()
        self.upgrade()

    def add_connection(self, host, user="root", passwd="", port=22,
                       id_file="", alias=""):
        """add connection"""
        sql = '''INSERT INTO connections
                 (id, host, user, password, port, idfile, alias)
                 VALUES(NULL, :host, :user, :passwd, :port, :idfile, :alias)'''
        self.conn.execute(sql, {"host": host, "user": user, "passwd": passwd,
                                "port": port, "idfile": id_file,
                                "alias": alias})
        self.conn.commit()

    def find_connections(self, host='', user='', port=0, cid=0, alias='', ecid=0):
        """find connection via host, user and port"""
        sql = '''SELECT id, host, user, port, password, idfile, alias
                 FROM connections'''
        cond = ''
        if host != '':
            if host[0] == '*':
                cond += ' AND host LIKE :host'
                host = '%' + host[1:] + '%'
            else:
                cond += ' AND host = :host'
        if user != '':
            cond += ' AND user = :user'
        if port != 0:
            cond += ' AND port = :port'
        if cid != 0:
            cond += ' AND id = :id'
        if ecid != 0:
            cond += ' AND id != :eid'
        if alias != '':
            cond += ' AND alias = :alias'
        if cond != '':
            cond = ' WHERE 1' + cond
        sql += cond + ' ORDER BY id ASC'
        param = {"host": host, "user": user, "port": port, "id": cid,
                 "alias": alias, "eid": ecid}
        return self.conn.execute(sql, param).fetchall()

    def get_connection_dict(self, r):
        """get one connection dict data"""
        d = {
            'id': r[0],
            'host': r[1],
            'user': r[2],
            'port': r[3],
            'password': r[4],
            'idfile': r[5]
        }
        return d

    def delete_connection_by_id(self, cid):
        """delete connection by id"""
        sql = "DELETE FROM connections WHERE id = :id"
        self.conn.execute(sql, {"id": cid})
        self.conn.commit()

    def edit_connection_by_id(self, cid, field, value):
        """edit connection by id"""
        sql = "UPDATE connections"
        sql += " SET `" + field + "` = :val"
        sql += " WHERE id = :id"
        self.conn.execute(sql, {"id": cid, "val": value})
        self.conn.commit()

    def init(self):
        """init system database"""
        sqls = {
            "connections": ('''CREATE TABLE connections
                               (id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                                host TEXT NOT NULL,
                                user TEXT NOT NULL,
                                password TEXT DEFAULT '' NOT NULL,
                                port INTEGER DEFAULT 22 NOT NULL,
                                idfile TEXT DEFAULT '' NOT NULL);''',
                            '''CREATE UNIQUE INDEX h
                                ON connections(host, user, port);'''),
            "tags": ('''CREATE TABLE tags
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT NOT NULL UNIQUE);'''),
            "relations": ('''CREATE TABLE relations
                             (connection_id INT NOT NULL,
                              tag_id INT NOT NULL);''',
                          '''CREATE UNIQUE INDEX r
                                ON relations(connection_id, tag_id);'''),
            "version": ('CREATE TABLE version (version_num INTEGER NOT NULL);',
                        'INSERT INTO version (version_num) VALUES (1);')
        }
        if not self.table_exists("version"):
            for table in sqls.keys():
                self.just_do_it(sqls[table])

    def upgrade(self):
        '''upgrade system database'''
        upgrades = {
            3: ("ALTER TABLE connections ADD alias TEXT DEFAULT '' NOT NULL;",
                "CREATE INDEX IF NOT EXISTS alias ON connections (alias);",
                "DROP TABLE IF EXISTS tags;")
        }
        sql = '''SELECT version_num FROM version;'''
        r = self.conn.execute(sql).fetchone()
        if r is None:
            self.init()
            version = 1
        else:
            version = int(r[0])
        if version != self.version_num:
            self.record_backup_action(version, "backup")
            if(self.backup()):
                print "Database upgrading:"
                for ver in upgrades:
                    self.record_backup_action(ver, "upgrade")
                    if ver > version and ver <= self.version_num:
                        print "Upgrading to version " + str(ver) + ", latest " + str(self.version_num) + "."
                        self.just_do_it(upgrades[ver])
                self.just_do_it(("DELETE FROM version;",
                                 "INSERT INTO version(version_num) VALUES ("
                                 + str(self.version_num) + ");",
                                 "DELETE FROM upgrade_action;"))

                print "Done."

    def just_do_it(self, sqls):
        '''execute one or more sqls and no return'''
        if isinstance(sqls, (list, tuple)):
            for sql in sqls:
                self.conn.execute(sql)
        else:
            self.conn.execute(sqls)
        self.conn.commit()

    def backup(self):
        ''''backup database'''
        print "Generating backup:",
        r = False
        if(True):
            r = True
            print "done."
        else:
            print "failed."
        return r

    def record_backup_action(self, ver, action):
        '''Record backup actions'''
        if not self.upgrade_action_existed:
            if not self.table_exists("upgrade_action"):
                sql = '''CREATE TABLE upgrade_action
                         (version INTEGER NOT NULL,
                          action TEXT NOT NULL);'''
                self.conn.execute(sql)
            self.upgrade_action_existed = True
        pass

    def table_exists(self, table):
        exists_sql = ('''SELECT name FROM sqlite_master
                         WHERE type='table' AND name=?;''')
        return self.conn.execute(exists_sql, [table]).fetchone() is not None

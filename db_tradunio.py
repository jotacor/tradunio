#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb
import ConfigParser

db_name = 'db_tradunio'

Config = ConfigParser.ConfigParser()
if not Config.read('../config.conf'):
    Config.read('config.conf')

db = MySQLdb.connect (
    host = Config.get(db_name, 'host'),
    user = Config.get(db_name, 'user'),
    passwd = Config.get(db_name, 'passwd'),
    port = Config.getint(db_name, 'port'),
    db = Config.get(db_name, 'db'),
    charset = Config.get(db_name, 'charset')
)
cursor = db.cursor()

def simple_query (sql):
    '''
    Transaccio sobre la base de dades simple, es a dir sense commit
    @param bbdd: nombre de la base de dades en el fitxer de configuracio
    @param sql: sql que volem executar en la base de dades
    @return: Retornara la consulta associada al sql
    '''
    cursor.execute(sql)
    res = cursor.fetchall()
    return res

def close_connection():
    '''
    Cierra la conexión con BBDD
    '''
    cursor.close()
    db.close()

def commit():
    '''
    Realiza commit a todo lo ejecutado
    '''
    db.commit()

def nocommit_query (sql):
    '''
    Transaccio sobre la base de dades sense commit. Utilitzarem esta classe per a fer inserts, updates o truncates
    @param sql: sql que volem executar en la base de dades
    @return: Executara la accio i fara un commit de la base de dades
    '''
    cursor.execute(sql)
    return cursor.lastrowid

def commit_query (sql):
    '''
    Transaccio sobre la base de dades amb commit. Utilitzarem esta classe per a fer inserts, updates o truncates
    @param sql: sql que volem executar en la base de dades
    @return: Executara la accio i fara un commit de la base de dades
    '''
    cursor.execute(sql)
    db.commit()

def rowcount (sql):
    '''
    Seleccio en la que averiguem si una determinada tupla existeix o no
    @param bbdd: nombre de la base de dades en el fitxer de configuracio
    @param sql: sql que volem executar en la base de dades
    @return: Si la tupla no existeix, el rowcount tornara 0 i si existeix tornara un 1
    '''
    cursor.execute(sql)
    return cursor.rowcount

def many_commit_query(sql,valores):
    '''
    Inserta todas las tuplas pasadas como parametro de una sola vez
    @param bbdd: nombre de la base de dades en el fitxer de configuracio
    @param sql: sql que volem executar en la base de dades
    '''
    cursor.executemany(sql,valores)
    db.commit()

def many_nocommit_query(sql,valores):
    '''
    Inserta todas las tuplas pasadas como parametro de una sola vez
    @param bbdd: nombre de la base de dades en el fitxer de configuracio
    @param sql: sql que volem executar en la base de dades
    '''
    cursor.executemany(sql,valores)
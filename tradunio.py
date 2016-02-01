#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Oct 21, 2014
@author: jotacor
"""

# TODO: Init function for the database (clubs, users, and transactions)
# TODO: Create object user
# TODO: Refactoring: Make functions inserting players, points, prices, so on
# TODO: Change position to a number instead the position name (problem with different languages)


import argparse
import db_tradunio as db
from ComunioPy import Comunio
from ConfigParser import ConfigParser
from datetime import date, timedelta, datetime
from operator import itemgetter
import re
import requests
from tabulate import tabulate
from time import sleep

BLUE = '\033[94m'
CYAN = '\033[96m'
ENDC = '\033[0m'
GREEN = '\033[92m'
GREY = '\033[90m'
PURPLE = '\033[95m'
RED = '\033[91m'
YELLOW = '\033[93m'
WHITE = '\033[97m'
FILTRO_STOP = 0.05

config = ConfigParser()
config.read('config.conf')
c_user = config.get('comunio', 'user')
c_passwd = config.get('comunio', 'passwd')
c_user_id = config.getint('comunio', 'user_id')
community_id = config.getint('comunio', 'community_id')
num_users  = config.getint('comunio', 'num_users')
com = Comunio(c_user, c_passwd, c_user_id, community_id, 'BBVA')
today = date.today()

def main():
    parser = argparse.ArgumentParser(description='Calcula cuando debes vender o comprar un jugador del Comunio.')
    parser.add_argument('-a', '--all', action='store_true', dest='all',
                        help='Realiza una ejecución completa.')
    parser.add_argument('-v', '--vender', action='store_true', dest='vender',
                        help='Muestra los jugadores a vender.')
    parser.add_argument('-c', '--comprar', action='store_true', dest='comprar',
                        help='Muestra los jugadores que tienes que comprar.')
    parser.add_argument('-t', '--trans', action='store_true', dest='trans',
                        help='Descarga de comunio las transacciones y las guarda en base de datos.')
    parser.add_argument('-u', '--update', action='store_true', dest='update',
                        help='Update all data of all players and users.')
    parser.add_argument('-i', '--init', action='store_true', dest='init',
                        help='Initialize the database with users, clubs.')
    args = parser.parse_args()

    sleep(1)

    if args.init:
        print '\nInitializing the database...'
        if db.rowcount('SELECT * FROM users'):
            res = raw_input(
                '\nDatabase contains data, %sdo you want to remove%s it and load data again? (y/n) ' % (RED, ENDC))
            if res == 'y':
                db.commit_query('SET FOREIGN_KEY_CHECKS=0;')
                queries = db.simple_query('SELECT Concat("DELETE FROM ",table_schema,".",TABLE_NAME, " WHERE 1;") \
                    FROM INFORMATION_SCHEMA.TABLES WHERE table_schema in ("tradunio");')
                for query in queries:
                    print query[0] + '...',
                    db.commit_query(query[0])
                    print "done"
                db.commit_query('SET FOREIGN_KEY_CHECKS=1;')
            else:
                exit(0)

        users = set_users_data()
        for user in users:
            username, points, teamvalue, money, maxbid = users[user][0:5]
            for player in users[user][5]:
                idp, playername, club_id, clubname, value, points, position = player
                set_player_data(idp=idp, playername=playername)

    if args.update or args.all:
        print '\n[*] Updating money, team value, save players, prices and transactions.'
        users = set_users_data()
        for user_id in users:
            my_players = list()
            username, points, teamvalue, money, maxbid = users[user_id][0:5]
            for player in users[user_id][5]:
                idp, playername, club_id, clubname, value, points, position = player
                if club_id == 25:
                    # Player is not in Primera División
                    continue
                bars = set_player_data(idp=idp, playername=playername)
                dat = bars[-1][1]
                to_copy = [idp, playername, club_id, clubname, float(value), points, position, dat.isoformat()]
                my_players.append(to_copy)

            set_transactions(user_id)
            remove_sold_players()

            if user_id != com.get_myid():
                continue

            print '\n%s:' % username
            print u'Teamvalue: %s € - Money: %s € - Max bid: %s € - Points: %s' % (
                format(teamvalue, ",d"), format(money, ",d"), format(maxbid, ",d"), points)
            headers = ['Player ID', 'Name', 'Club ID', 'Club', 'Value', 'Points', 'Position', 'Last date']
            print tabulate(my_players, headers, tablefmt="rst", floatfmt=",.0f")


    if args.trans or args.all:
        sleep(1)
        print '\n[*] Actualizamos mis transacciones:'
        table = write_transactions(com.myid)
        headers = ['Player ID', 'Name', 'Price', 'Date', 'Type', 'Rent']
        print tabulate(table, headers, tablefmt="rst", numalign="right", floatfmt=",.0f")

    if args.comprar or args.all:
        sleep(1)
        print '\n[*] Jugadores para comprar:'
        on_sale = sorted(com.players_onsale(com.community_id, only_computer=False), key=itemgetter(2), reverse=True)
        headers = ['Name', 'Mkt Price', 'Min Price', 'Owner', 'Last Points', 'Racha']
        table = list()
        for player in on_sale:
            name = player[0]
            min_price = float(player[2])
            mkt_price = float(player[3])
            owner = player[6]
            last_points = db.simple_query(
                'SELECT p.points,p.gameday FROM players pl INNER JOIN points p ON p.idp=pl.idp AND pl.name="%s" ORDER BY p.gameday ASC' % name)
            racha = sum([int(x[0]) for x in last_points])
            last_points = ['+' + str(x[0]) if x[0] >= 0 else str(x[0]) for x in last_points]
            # comprar = check_buy(name, min_price, mkt_price)
            # mkt_price = locale.format("%d", mkt_price, grouping=True)
            # min_price = locale.format("%d", min_price, grouping=True)

            table.append([name, mkt_price, min_price, owner, '[' + ']['.join(last_points) + ']', racha])

        table = sorted(table, key=itemgetter(5), reverse=True)
        print tabulate(table, headers, tablefmt="psql", numalign="right", floatfmt=",.0f")
        print '#################################################'

    if args.vender or args.all:
        sleep(1)
        print '\n[*] Jugadores que hay que vender:'
        #my_players = write_user_players(com.myid, 'Javi')
        #table = check_sell(my_players)
        headers = ['Player ID', 'Name', 'To sell?', 'Purchase date', 'Purchase price', 'Mkt price', 'Rent']
        print tabulate(table, headers, tablefmt="rst", numalign="right", floatfmt=",.0f")
        print '#################################################'

    com.logout()


def get_users_data():
    info = dict()
    last_date = db.simple_query('SELECT MAX(date) FROM user_data LIMIT 1')[0][0]
    if last_date == today:
        users = db.simple_query('SELECT u.idu,u.name,d.date,d.points,d.money,d.teamvalue,d.maxbid \
                        FROM users u, user_data d WHERE u.idu=d.idu AND date = "%s"' % last_date)
        for user in users:
            user_id, username, date, points, money, teamvalue, maxbid = user
            # TODO: Use INNER JOIN
            players = db.simple_query('SELECT p.idp,p.name,c.idcl,c.name,pr.price,0,p.position \
                                      FROM players p, clubs c, owners o, prices pr \
                                      WHERE p.idcl=c.idcl AND o.idp=p.idp \
                                      AND pr.idp=p.idp AND o.idu=%s' % user_id)
            info[user_id] = [username, points, teamvalue, money, maxbid, players]
            # for player in players:
            #     player_id, name, club_id, clubname, value, points, position = player
            #     info[user_id].append(player)
    else:
        info = set_users_data()

    return info


def set_users_data(uid=None):
    """
    :param uid: ID of the user to update his information
    :return: information about the user and his players
    """
    # TODO: check first in database if I already have it all
    last_date_user = db.simple_query('SELECT MAX(date) FROM user_data LIMIT 1')[0][0]
    news = com.get_news()
    info = dict()
    today = date.today()
    last_news_date = news[1][0]

    if last_news_date != today or last_date_user == today:
        print "No data already computed by Comunio or data up to date."
        info = get_users_data()
    else:
        users_info = com.get_users_info()
        for user in users_info:
            [user_name, user_id, points, teamvalue, money, maxbid] = user

            print '\nUpdating %s data =>' % user_name,
            db.nocommit_query('INSERT IGNORE INTO users (idu, name) VALUES (%s, "%s")' % (user_id, user_name))
            db.nocommit_query('INSERT IGNORE INTO user_data (idu, date, points, money, teamvalue, maxbid) \
                VALUES (%s, "%s", %s, %s, %s, %s)' % (user_id, today, points, money, teamvalue, maxbid))

            user_players = com.get_user_players(user_id)
            for player in user_players:
                [player_id, playername, club_id, club_name, value, points, position] = player
                db.nocommit_query('INSERT IGNORE INTO clubs (idcl, name) VALUES (%s, "%s")' % (club_id, club_name))
                db.nocommit_query('INSERT IGNORE INTO players (idp, name, position, idcl) VALUES (%s, "%s", "%s", %s)' % (
                    player_id, playername, position, club_id))
                db.nocommit_query('INSERT IGNORE INTO owners (idp, idu) VALUES (%s, %s)' % (player_id, user_id))
                set_player_data(idp=player_id, playername=playername)
            print '%sdone%s' % (GREEN, ENDC),
            info[user_id] = [user_name, points, teamvalue, money, maxbid, user_players]
        db.commit()

    return info


def set_player_data(idp=None, playername=None):
    """
    Sets prices and points for all the players of the user
    :param idp: Id of the football player
    :param playername: Football player name
    :return: Players of the user id
    """
    days_left = days_wo_price(idp)
    to_insert = list()
    if days_left:
        dates, prices = get_player_prices(playername)
        dates = translate_dates(dates)
        if days_left == 365:
            days_left = len(dates)
        for index in range(days_left):
            p_date = datetime.strptime(dates[index], "%Y-%m-%d").date()
            try:
                price = int(prices[index])
            except:
                price = 0
            to_insert.append((idp, p_date, price))
        db.many_commit_query('INSERT IGNORE INTO prices (idp,date,price) VALUES (%s,%s,%s)', to_insert)
    else:
        prices = db.simple_query('SELECT price FROM prices WHERE idp="%s" ORDER BY date ASC' % idp)
        dates = db.simple_query('SELECT date FROM prices WHERE idp="%s" ORDER BY date ASC' % idp)
        to_insert = [[idp, p_date, price] for p_date, price in zip(dates, prices)]

    if len(dates) != len(prices):
        print "%sThe prices arrays and dates haven't the same size.%s" % (RED, ENDC)

    return to_insert


def remove_sold_players():
    # Para esto añadir fecha 'added' a los jugadores de la base de datos y borrar los anteriores a 1 mes y que no estén en cartera
    """ Seleccionamos los jugadores vendidos para buscar la compra anterior """
    cleaned = list()
    limpiar = db.simple_query('SELECT idp,date FROM transactions WHERE type="Sell" ORDER BY date DESC')
    for limpia in limpiar:
        borrar = db.simple_query(
            'SELECT idp,date FROM transactions WHERE type="Buy" AND idp=%s AND date<%s ORDER BY date DESC LIMIT 1'
            % (limpia[0], limpia[1]))
        if borrar:
            db.commit_query('UPDATE players SET idu=NULL WHERE idp=%s' % limpia[0])
            cleaned.append(limpia)
    return cleaned


def check_sell(my_players):
    """
    Comprueba si el jugador puede o debe ser vendido
    """
    vender = list()
    for player in my_players:
        idp = player[0]
        name = player[1]
        vende = False
        hoy = date.today().strftime('%Y%m%d')

        compra = db.simple_query(
            'SELECT date,price FROM transactions WHERE idp=%s AND type="Buy" ORDER BY date DESC LIMIT 1' % idp)
        if compra is None:
            precio_actual = float(
                db.simple_query('SELECT price FROM prices WHERE idp=%s ORDER BY date DESC LIMIT 1' % idp)[0])
            precio_inicial = float(db.simple_query(
                'SELECT price FROM prices WHERE idp=%s AND date>%s ORDER BY date ASC LIMIT 1' % (
                    idp, '%s0801' % date.today().year))[0])
            rent = (precio_actual - precio_inicial) / precio_inicial * 100
            vender.append([idp, name, vende, '-', precio_inicial, precio_actual, colorize_rentability(rent), rent])
            continue

        precio_ant = 0
        stop = 0
        fecha_compra = compra[0]
        precio_compra = float(compra[1])

        barras = db.simple_query(
            'SELECT idp,date,price FROM prices WHERE idp=%s AND date>=%s ORDER BY date ASC' % (idp, compra[0]))
        # Si el jugador no tuviera barras las rellena, o si estuvieran desactualizadas
        if len(barras) == 0 or barras[-1][1] < hoy:
            barras = set_player_data(idp, name)

        for barra in barras:
            precio = float(barra[2])
            if precio > precio_ant:
                precio_ant = precio
                stop = int(precio_ant - (precio_ant * FILTRO_STOP))

            # Comprobamos si el precio ha roto el stop
            if precio < stop:
                vende = True

            # Si el precio del jugador se ha recuperado y ya había entrado en venta, se demarca la venta
            if precio > stop and vende:
                vende = False

        # Calculamos la rentabilidad
        rent = (precio - precio_compra) / precio_compra * 100

        if vende:
            vender.append([idp, name, '%s%s%s' % (GREEN, vende, ENDC), fecha_compra, precio_compra, precio,
                           colorize_rentability(rent), rent])
        else:
            vender.append(
                [idp, name, '%s' % (vende), fecha_compra, precio_compra, precio, colorize_rentability(rent), rent])

        # Guardamos rentabilidad de los jugadores en cartera
        db.commit_query(
            'INSERT IGNORE INTO rentabilities (idp, date, rentability) VALUES (%s, %s, %s)' % (idp, hoy, int(rent)))

    # Ordenamos por el último elemento y luego lo eliminamos
    vender = sorted(vender, key=itemgetter(7), reverse=True)
    return [[a, b, m, d, e, f, g] for a, b, m, d, e, f, g, h in vender]


def set_transactions(user_id):
    news = com.get_news()
    for new in news:
        ndate = new[0]
        text = new[1]




def write_transactions(myid):
    """
    Save in database all transactions.
    """
    # TODO: Check last transaction date para no refrescar todo cada vez
    ret = []
    from_you = com.bids_from_you()
    for trans in from_you:
        if trans[6] == 'Efectuada':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            db.nocommit_query('INSERT OR REPLACE INTO players (idp, name, idu) VALUES (%s,%s,%s)' % (idp, player, myid))
            db.nocommit_query('INSERT OR REPLACE INTO transactions (idp,type,price,date) VALUES (%s,%s,%s,%s)' %
                              (idp, 'Buy', price, trans_date))
            db.commit()
            ret.append([idp, player, float(price), trans_date, '%sBought%s' % (GREEN, ENDC), colorize_rentability(0.0)])
        elif trans[6] == 'Pendiente':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            ret.append([idp, player, float(price), trans_date, '%sBid%s' % (BLUE, ENDC), colorize_rentability(0.0)])

    to_you = com.bids_to_you()
    for trans in to_you:
        if trans[6] == 'Efectuada':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            db.commit_query('INSERT OR REPLACE INTO transactions (idp,type,price,date) VALUES (%s,%s,%s,%s)' %
                            (idp, 'Sell', price, trans_date))
            compra = db.simple_query(
                'SELECT date,price FROM transactions WHERE idp=%s AND type="Buy" ORDER BY date DESC LIMIT 1' % idp)
            if compra is None:
                # Si el jugador lo tenemos dede el inicio...
                compra = db.simple_query(
                    'SELECT date,price FROM prices WHERE idp=%s AND date>%s ORDER BY date ASC LIMIT 1' %
                    (idp, '%s0801' % date.today().year))

            precio_compra = float(compra[1])
            rent = (price - precio_compra) / precio_compra * 100
            ret.append([idp, player, float(price), trans_date, '%sSelled%s' % (RED, ENDC), colorize_rentability(rent)])
            # db.commit_query('DELETE FROM prices WHERE idp=?', (idp,) )
            # db.commit_query('DELETE FROM players WHERE idp=?', (idp,) )
        elif trans[6] == 'Pendiente':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            compra = db.simple_query(
                'SELECT date,price FROM transactions WHERE idp=%s AND type="Buy" ORDER BY date DESC LIMIT 1' % idp)

            if compra is None:
                # Si el jugador lo tenemos dede el inicio...
                compra = db.simple_query(
                    'SELECT date,price FROM prices WHERE idp=%s AND date>%s ORDER BY date ASC LIMIT 1' %
                    (idp, '%s0801' % date.today().year))

            precio_compra = float(compra[1])
            # Calculamos la rentabilidad y configuramos el color
            rent = (price - precio_compra) / precio_compra * 100
            ret.append(
                [idp, player, float(price), trans_date, '%sOffer%s' % (YELLOW, ENDC), colorize_rentability(rent)])

    return sorted(ret, key=itemgetter(3), reverse=True)


def colorize_rentability(rent):
    color = WHITE
    if rent <= -10:
        color = RED
    elif rent < 0:
        color = YELLOW
    elif rent < 10:
        color = CYAN
    else:
        color = GREEN

    return '%s%4d%%%s' % (color, rent, ENDC)


def days_wo_price(idp):
    """
    Devuelve la cantidad de días que lleva un jugador sin actualizarse en la base de datos.
    """
    max_date = db.simple_query('SELECT MAX(date) FROM prices WHERE idp=%s LIMIT 1' % idp)[0][0]
    res = 365
    try:
        res = (date.today() - max_date).days
    except:
        pass
    if res > 365:
        res = 365
    return res


def get_prices_player(idp):
    days_left = days_wo_price(idp)
    if not days_left:
        # Devolvemos las barras desde la fecha de compra, si no lo hemos comprado devolvemos todas las barras
        barras = db.simple_query(
            'SELECT p.idp,p.date,p.price FROM prices p WHERE p.idp=%s \
             AND p.date>=(SELECT t.date FROM transactions t \
                          WHERE t.idp=%s AND t.type="Buy" ORDER BY t.date DESC LIMIT 1) \
             ORDER BY p.date ASC' % (idp, idp))
        if len(barras) == 0:
            barras = db.simple_query('SELECT p.idp,p.date,p.price FROM prices p \
                                      WHERE p.idp=%s ORDER BY p.date ASC' % idp)
        return barras


def write_new_player(player):
    """
    Write new player on database whether exists or not
    @return: idp
    """
    idp = com.info_player_id(player)
    rows = db.rowcount('SELECT count(*) FROM players WHERE idp=%s AND name=%s' % (idp, player))
    if not rows:
        try:
            db.commit_query('INSERT OR IGNORE INTO players (idp,name) VALUES (%s,%s)' % (idp, player))
        except:
            print 'No se ha podido guardar al jugador %s-%s' % (idp, player)
    return idp


def current_player_price(player_name):
    info_player = com.info_player(com.info_player_id(player_name))
    return info_player[5].replace(".", "")


def get_player_prices(playername, prices=0):
    """
    Get prices from a player
    @return: [dates],[data]
    """
    session = requests.session()
    url_comuniazo = 'http://www.comuniazo.com'
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0'
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", 'Referer': url_comuniazo,
               "User-Agent": user_agent}
    url_jugadores = url_comuniazo + '/comunio/jugadores/'
    suffix = ''
    lastname = ''
    count = 0
    dates = []
    while True and len(dates) < 2:
        playername = check_exceptions(playername)
        req = session.get(url_jugadores + playername.replace(" ", "-").replace(".", "").replace("'", "") + suffix, headers=headers).content
        dates_re = re.search("(\"[0-9 ][0-9] de \w+\",?,?)+", req)
        try:
            dates = dates_re.group(0).replace('"', '').split(",")
        except:
            if count == 0:
                suffix = '-2'
                count += 1
                continue
            elif count == 1:
                lastname = playername.split(" ")[1]
                playername = playername.split(" ")[0]
                suffix = ''
                count += 1
                continue
            elif count == 2:
                playername = lastname
                count += 1
                continue

        data_re = re.search("data: \[(([0-9null]+,?)+)\]", req)
        prices = data_re.group(1).split(',')

        if suffix == '-2' or len(dates) > 2:
            break
        else:
            suffix = '-2'

    return dates, prices


def check_exceptions(playername):
    exceptions = {'Banega': 'Ever Banega', }
    return exceptions.get(playername, playername)


def check_buy(name, min_price, mkt_price):
    """
    Check whether it's in maximus now
    @return: boolean
    """
    set_player_data(playername=name)
    from_date = (date.today() - timedelta(days=5)).strftime('%Y%m%d')
    rows = db.simple_query(
        'SELECT pr.price,pr.date FROM prices pr,players pl \
         WHERE pl.idp=pr.idp AND pl.name=%s AND pr.date>%s ORDER BY pr.date ASC' % (name, from_date))
    max_h = 0
    fecha = '19700101'
    for row in rows:
        if row[0] > max_h:
            maxH = row[0]
            fecha = row[1]
    # Si la fecha a la que ha llegado es la de hoy (max_h) y el precio que solicitan no es superior al de mercado+10%, se compra
    if fecha == date.today().strftime('%Y%m%d') and min_price < (mkt_price * 1.2):
        return True
    else:
        return False


def translate_dates(dates):
    """
    Translates dates format'dd.mm' to 'yyyymmdd'
    @return: [[date,]]
    """
    ret = list()
    last = 0
    for dat in dates:
        if dat == '':
            # Si encontramos algún hueco repetimos valor
            ret.append(ret[-1])
            continue
        day = dat[:2]
        if int(day) < 10:
            day = '0' + day[1]
        if dat[6:] != '':
            # Cuando se recuperan fechas de Comuniazo
            month = \
                {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}[dat[6:]]
        else:
            # Fechas de Comunio
            month = dat[3:5]
        year = str(date.today().year - last)
        if month + day == '0101':
            last = 1

        ret.append('%s-%s-%s' % (year, month, day))
    return ret


if __name__ == '__main__':
    main()

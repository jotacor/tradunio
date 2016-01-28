#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Oct 21, 2014
@author: jotacor
"""

# TODO: Recoger únicamente un año de histórico, no hace falta almacenar más
# TODO: función limpieza de base de datos
# TODO: crear función my_players en ComunioPy por
# TODO: Acumular en ComunioPy los precios y jugadores consultados en objetos, por si queremos volver a consultarlos
# TODO: Introducir Buy por cada jugador que nos dé la máquina para cuando lo vendamos poder calcular la rentabilidad


import argparse
import db_tradunio as db
from ComunioPy import Comunio
from ConfigParser import ConfigParser
from datetime import date, timedelta
import locale
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
user = config.get('comunio', 'user')
passwd = config.get('comunio', 'passwd')
com = Comunio(user, passwd, 'BBVA')

locale.setlocale(locale.LC_ALL, 'en_US.utf8')


def main():
    parser = argparse.ArgumentParser(description='Calcula cuando debes vender o comprar un jugador del Comunio.')
    parser.add_argument('-a', '--all', action='store_true', dest='all', help='Realiza una ejecución completa.')
    parser.add_argument('-v', '--vender', action='store_true', dest='vender', help='Muestra los jugadores a vender.')
    parser.add_argument('-c', '--comprar', action='store_true', dest='comprar',
                        help='Muestra los jugadores que tienes que comprar.')
    parser.add_argument('-t', '--trans', action='store_true', dest='trans',
                        help='Descarga de comunio las transacciones y las guarda en base de datos.')
    parser.add_argument('-u', '--update', action='store_true', dest='update',
                        help='Actualiza todos los datos de usuario y sus jugadores en la base de datos.')
    args = parser.parse_args()

    sleep(1)
    try:
        com.get_myid()
    except:
        com.myid = '10170858'
        com.community_id = '2867202'
        com.username = 'jotacor'

    if args.update or args.all:
        print '\n[*] Actualizamos dinero, valor del equipo y guardamos jugadores y sus precios.'
        money, teamvalue = write_money_teamvalue(com.myid)
        my_players = write_user_players(com.myid, com.username)
        for i, player in enumerate(my_players):
            barras = write_prices_player(idp=player[0], player=player[1])
            precio = float(barras[-1][2])
            date = barras[-1][1]
            my_players[i].extend([precio, date])

        headers = ['Player ID', 'Name', 'Mkt price', 'Last date']
        print 'Valor del equipo: %s € - Dinero: %s €' % (
        locale.format("%d", teamvalue, grouping=True), locale.format("%d", money, grouping=True))
        print tabulate(my_players, headers, tablefmt="rst", floatfmt=",.0f")
        clean_players()

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
                'SELECT p.points,g.gameday FROM players pl INNER JOIN points p ON p.idp=pl.idp INNER JOIN gamedays g ON p.idg=g.idg AND pl.name="%s" ORDER BY cast(g.gameday as unsigned) ASC' % name)[
                          -5:]
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
        my_players = write_user_players(com.myid, 'Javi')
        table = check_sell(my_players)
        headers = ['Player ID', 'Name', 'To sell?', 'Purchase date', 'Purchase price', 'Mkt price', 'Rent']
        print tabulate(table, headers, tablefmt="rst", numalign="right", floatfmt=",.0f")
        print '#################################################'

    com.logout()


def clean_players():
    # Para esto añadir fecha 'added' a los jugadores de la base de datos y borrar los anteriores a 1 mes y que no estén en cartera
    """ Seleccionamos los jugadores vendidos para buscar la compra anterior """
    limpiados = list()
    limpiar = db.simple_query('SELECT idp,date FROM transactions WHERE type="Sell" ORDER BY date DESC')
    for limpia in limpiar:
        borrar = db.simple_query(
            'SELECT idp,date FROM transactions WHERE type="Buy" AND idp=? AND date<? ORDER BY date DESC LIMIT 1',
            (limpia[0], limpia[1],))
        if borrar:
            db.commit_query('UPDATE players SET idu=NULL WHERE idp=?', (limpia[0]))
            limpiados.append(limpia)
    return limpiados


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
        if compra == None:
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
            barras = write_prices_player(name, idp)

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


def write_money_teamvalue(idp):
    """
    Escribe en base de datos el valor del equipo y el dinero que poseemos.
    """
    hoy = date.today().strftime('%Y%m%d')
    money = com.get_money()
    db.nocommit_query('INSERT IGNORE INTO money (idu,date,money) VALUES (%s,%s,%s)' % (idp, hoy, money))

    value = com.get_team_value()
    db.nocommit_query('INSERT IGNORE INTO teamvalue (idu,date,value) VALUES (%s,%s,%s)' % (idp, hoy, value))

    db.commit()
    return money, value


def write_transactions(myid):
    """
    Guarda en base de datos las compras realizadas
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
            db.nocommit_query('INSERT OR REPLACE INTO players (idp, name, idu) VALUES (?,?,?)', (idp, player, myid,))
            db.nocommit_query('INSERT OR REPLACE INTO transactions (idp,type,price,date) VALUES (?,?,?,?)',
                              (idp, 'Buy', price, trans_date,))
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
            db.commit_query('INSERT OR REPLACE INTO transactions (idp,type,price,date) VALUES (?,?,?,?)',
                            (idp, 'Sell', price, trans_date,))
            compra = db.simple_query(
                'SELECT date,price FROM transactions WHERE idp=? AND type="Buy" ORDER BY date DESC LIMIT 1', (idp,))
            if compra is None:
                # Si el jugador lo tenemos dede el inicio...
                compra = db.simple_query(
                    'SELECT date,price FROM prices WHERE idp=? AND date>? ORDER BY date ASC LIMIT 1',
                    (idp, '%s0801' % date.today().year,))

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
            compra = db.simple_query('SELECT date,price FROM transactions WHERE idp=? AND type="Buy" ORDER BY date DESC LIMIT 1',
                      (idp,))

            if compra is None:
                # Si el jugador lo tenemos dede el inicio...
                compra = db.simple_query('SELECT date,price FROM prices WHERE idp=? AND date>? ORDER BY date ASC LIMIT 1',
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
    elif rent > -10 and rent < 0:
        color = YELLOW
    elif rent > 0 and rent < 10:
        color = CYAN
    elif rent >= 10:
        color = GREEN

    return '%s%4d%%%s' % (color, rent, ENDC)


def _days_wo_price(player):
    """
    Devuelve la cantidad de días que lleva un jugador sin actualizarse en la base de datos.
    """
    idp = com.info_player_id(player)
    max_date = db.simple_query('SELECT MAX(date) FROM prices WHERE idp=%s LIMIT 1' % idp)
    res = 365
    for last_date in max_date:
        try:
            a = date(int(last_date[:4]), int(last_date[4:6]), int(last_date[6:8]))
        except:
            continue
        res = (date.today() - a).days
        if res > 365:
            res = 365
    return res


def write_user_players(myid, username):
    """
    Guarda en base de datos los futbolistas del usuario.
    """
    info_user = com.info_user(myid)
    db.commit_query('INSERT OR REPLACE INTO users (idu, name) VALUES (?, ?)', (myid, username))
    result = []
    for dato in info_user[6:]:
        player_name = dato[1].strip()
        idp = com.info_player_id(player_name)
        db.commit_query('INSERT OR REPLACE INTO players (idp, name, idu) VALUES (?,?,?)', (idp, player_name, myid))
        result.append([idp, player_name])

    return sorted(result, key=itemgetter(1))


def write_prices_player(player, idp=None):
    days = _days_wo_price(player)
    if days == 0:
        # Devolvemos las barras desde la fecha de compra, si no lo hemos comprado devolvemos todas las barras
        barras = db.simple_query(
            'SELECT p.idp,p.date,p.price FROM prices p WHERE p.idp=? AND p.date>=(SELECT t.date FROM transactions t WHERE t.idp=? AND t.type="Buy" ORDER BY t.date DESC LIMIT 1) ORDER BY p.date ASC',
            (idp, idp))
        if len(barras) == 0:
            barras = db.simple_query('SELECT p.idp,p.date,p.price FROM prices p WHERE p.idp=? ORDER BY p.date ASC', (idp,))
        return barras

    to_insert = list()
    if not idp:
        idp = write_new_player(player)
    dates, prices = player_prices(player)
    dates = translate_dates(dates)

    if len(dates) != len(prices):
        print "Los arrays de precios y de fechas no tienen el mismo tamaño."
    else:
        if days == 365:
            days = len(dates)
        for index in range(days):
            to_insert.append((idp, dates[index], prices[index]))

    db.many_commit_query('INSERT OR IGNORE INTO prices (idp,date,price) VALUES (?,?,?)', to_insert)
    # Devolvemos las barras desde la fecha de compra, si no lo hemos comprado devolvemos todas las barras
    barras = db.simple_query(
        'SELECT p.idp,p.date,p.price FROM prices p WHERE p.idp=? AND p.date>=(SELECT t.date FROM transactions t WHERE t.idp=? AND t.type="Buy" ORDER BY t.date DESC LIMIT 1) ORDER BY p.date ASC',
        (idp, idp,))
    if len(barras) == 0:
        barras = db.simple_query('SELECT p.idp,p.date,p.price FROM prices p WHERE p.idp=? ORDER BY p.date ASC', (idp,))
    return barras


def write_new_player(player):
    """
    Write new player on database whether exists or not
    @return: idp
    """
    idp = com.info_player_id(player)
    rows = db.rowcount('SELECT count(*) FROM players WHERE idp=? AND name=?', (idp, player))
    if not rows:
        try:
            db.commit_query('INSERT OR IGNORE INTO players (idp,name) VALUES (?,?)', (idp, player))
        except:
            print 'No se ha podido guardar al jugador %s-%s' % (idp, player)
    return idp


def current_player_price(player_name):
    info_player = com.info_player(com.info_player_id(player_name))
    return info_player[5].replace(".", "")


def player_prices(name):
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
    sufijo = ''
    dates = []
    # Existen jugadores como "Cristian Álvarez" que están duplicados, el  primero no tiene datos
    while True and len(dates) < 2:
        req = session.get(url_jugadores + name.replace(" ", "-").replace(".", "") + sufijo, headers=headers).content
        dates_re = re.search("(\"[0-9 ][0-9] de \w+\",?,?)+", req)
        dates = dates_re.group(0).replace('"', '').split(",")
        data_re = re.search("data: \[(([0-9null]+,?)+)\]", req)
        prices = data_re.group(1).split(',')
        if sufijo == '-2' or len(dates) > 2:
            break
        else:
            sufijo = '-2'

    return dates, prices


def check_buy(name, min_price, mkt_price):
    """
    Check whether it's in maximus now
    @return: boolean
    """
    write_prices_player(name)
    from_date = (date.today() - timedelta(days=5)).strftime('%Y%m%d')
    rows = db.simple_query(
        'SELECT pr.price,pr.date FROM prices pr,players pl WHERE pl.idp=pr.idp AND pl.name=? AND pr.date>? ORDER BY pr.date ASC',
        (name, from_date,))
    maxH = 0
    fecha = '19700101'
    for row in rows:
        if row[0] > maxH:
            maxH = row[0]
            fecha = row[1]
    # Si la fecha a la que ha llegado es la de hoy (maxH) y el precio que solicitan no es superior al de mercado+10%, se compra
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
            {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06', 'julio': '07',
             'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}[dat[6:]]
        else:
            # Fechas de Comunio
            month = dat[3:5]
        year = str(date.today().year - last)
        if month + day == '0101':
            last = 1

        ret.append(year + month + day)
    return ret


if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Oct 21, 2014
@author: jotacor
"""

# TODO: User Class Comunio (active record)
# TODO: Refactoring: Make functions inserting players, points, prices and so on
# TODO: Change position to a number instead the position name (problem with different languages)
# TODO: Unify sell, but options to a function
# TODO: Return always both: html and console from all funtions

import argparse
from bs4 import BeautifulSoup
import db_tradunio as db
from ComunioPy import Comunio
from ConfigParser import ConfigParser
from datetime import date, timedelta, datetime
from mailer import Mailer, Message
from operator import itemgetter
import re
import requests
from tabulate import tabulate
from time import sleep

BLUE = '\033[94m'
CYAN = '\033[96m'
CYAN_HTML = '#33ccff'
ENDC = '\033[0m'
GREEN = '\033[92m'
GREEN_HTML = '#33cc33'
GREY = '\033[90m'
PURPLE = '\033[95m'
RED = '\033[91m'
RED_HTML = '#cc3300'
YELLOW = '\033[93m'
YELLOW_HTML = '#ff9900'
WHITE = '\033[97m'
FILTRO_STOP = 0.05

config = ConfigParser()
config.read('config.conf')
c_user = config.get('comunio', 'user')
c_passwd = config.get('comunio', 'passwd')
c_user_id = config.getint('comunio', 'user_id')
community_id = config.getint('comunio', 'community_id')
fr_email = config.get('comunio', 'fr_email')
to_email = config.get('comunio', 'to_email')
com = Comunio(c_user, c_passwd, c_user_id, community_id, 'BBVA')
today = date.today()


def main():
    parser = argparse.ArgumentParser(description='Helps you to play in Comunio.')

    parser.add_argument('-i', '--init', action='store_true', dest='init',
                        help='Initialize the database with users, clubs, players and transactions.')
    parser.add_argument('-u', '--update', action='store_true', dest='update',
                        help='Update all data of all players and users.')
    parser.add_argument('-b', '--buy', action='store_true', dest='buy',
                        help='Check all the players to buy.')
    parser.add_argument('-s', '--sell', action='store_true', dest='sell',
                        help='Players that you should sell.')
    parser.add_argument('-m', '--mail', action='store_true', dest='mail',
                        help='Send email with the results.')

    args = parser.parse_args()
    sleep(1)

    ##### INIT
    if args.init:
        print '\n[*] Initializing the database.'
        if db.rowcount('SELECT * FROM users'):
            res = raw_input(
                '\tDatabase contains data, %sdo you want to remove%s it and load data again? (y/n) ' % (RED, ENDC))
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
                print "\tExecution aborted."
                exit(0)

        users = set_users_data()
        set_transactions()
        for user_id in users:
            username, points, teamvalue, money, maxbid = users[user_id]
            players = set_user_players(user_id, username)
            for player in players:
                player_id, playername, club_id, clubname, value, points, position = player
                set_player_data(player_id=player_id, playername=playername)

    ##### UPDATE
    if args.update:
        if not com.logged:
            exit(1)

        print '\n[*] Updating money, team value, save players, prices and transactions.'
        users = set_users_data()
        set_transactions()
        for user_id in users:
            username, userpoints, teamvalue, money, maxbid = users[user_id]
            players = set_user_players(user_id, username)
            for player in players:
                player_id, playername, club_id, clubname, value, points, position = player
                if club_id == 25:
                    # Player is not in Primera División
                    continue
                set_player_data(player_id=player_id, playername=playername)

            if user_id == com.get_myid():
                # TODO: Add parse option to print or not all users
                print_user_data(username, teamvalue, money, maxbid, userpoints, players)

    ##### BUY
    if args.buy:
        sleep(1)
        print '\n[*] Checking players to buy in the market.'
        max_gameday = db.simple_query('SELECT MAX(gameday) from points')[0][0]
        players_on_sale = sorted(com.players_onsale(com.community_id, only_computer=False), key=itemgetter(2),
                                 reverse=True)
        gamedays = [('%3s' % gameday) for gameday in range(max_gameday - 4, max_gameday + 1)]
        headers = ['Name', 'Position', 'Owner', 'Month ago', 'Week ago', 'Day ago', 'Mkt. price', 'Min. price', ' '.join(gamedays), 'Streak']
        table = list()
        for player in players_on_sale:
            player_id, playername, team_id, team, min_price, market_price, points, date, owner, position = player
            last_points = db.simple_query(
                'SELECT p.gameday,p.points \
                FROM players pl INNER JOIN points p ON p.idp=pl.idp AND pl.idp = "%s" \
                ORDER BY p.gameday DESC LIMIT 5' % player_id)[::-1]

            if not last_points and not db.rowcount('SELECT idp FROM players WHERE idp = %s' % player_id):
                set_new_player(player_id, playername, position, team_id)
                _, last_points = set_player_data(player_id=player_id, playername=playername)
                last_points = last_points[-5:]
            elif not last_points:
                _, last_points = set_player_data(player_id=player_id, playername=playername)
                last_points = last_points[-5:]
            elif team_id == 25:
                continue

            streak = sum([int(x[1]) for x in last_points])
            last_points = {gameday: points for (gameday, points) in last_points}
            last_points_array = list()
            for gameday in range(max_gameday - 4, max_gameday + 1):
                points = last_points.get(gameday, 0)
                points = colorize_points(points)
                last_points_array.append(points)

            prices = db.simple_query(
                'SELECT p.date,p.price \
                FROM players pl INNER JOIN prices p ON p.idp=pl.idp AND pl.idp = "%s" \
                ORDER BY p.date ASC' % player_id)
            day, week, month = 0, 0, 0
            try:
                day = colorize_profit(calculate_profit(float(prices[-2][1]), market_price))
                week = colorize_profit(calculate_profit(float(prices[-8][1]), market_price))
                month = colorize_profit(calculate_profit(float(prices[-30][1]), market_price))
            except IndexError:
                pass

            table.append([playername, position, owner, month, week, day, market_price, min_price, ' '.join(last_points_array), streak])

        table = sorted(table, key=itemgetter(9), reverse=True)
        print tabulate(table, headers, tablefmt="psql", numalign="right", floatfmt=",.0f")

        if args.mail:
            send_email(fr_email, to_email, 'Tradunio players to buy', str(tabulate(table, headers, tablefmt="html", numalign="right", floatfmt=",.0f")))

    ##### SELL
    if args.sell:
        print '\n[*] Checking players to sell.'
        max_gameday = db.simple_query('SELECT MAX(gameday) from points')[0][0]
        gamedays = [('%3s' % gameday) for gameday in range(max_gameday - 4, max_gameday + 1)]
        console, html, table = list(), list(), list()
        players = get_user_players(user_id=com.myid)
        for player in players:
            player_id, playername, club_id, club_name, position = player
            last_points = db.simple_query(
                'SELECT p.gameday,p.points \
                FROM players pl INNER JOIN points p ON p.idp=pl.idp AND pl.idp = "%s" \
                ORDER BY p.gameday DESC LIMIT 5' % player_id)[::-1]

            if not last_points and not db.rowcount('SELECT idp FROM players WHERE idp = %s' % player_id):
                set_new_player(player_id, playername, position, club_id)
                _, last_points = set_player_data(player_id=player_id, playername=playername)
                last_points = last_points[-5:]
            elif not last_points:
                _, last_points = set_player_data(player_id=player_id, playername=playername)
                last_points = last_points[-5:]

            streak = sum([int(x[1]) for x in last_points])
            last_points = {gameday: points for (gameday, points) in last_points}
            last_points_array = list()
            for gameday in range(max_gameday - 4, max_gameday + 1):
                points = last_points.get(gameday, 0)
                points = colorize_points(points)
                last_points_array.append(points)

            bought_date, bought_price, market_price, to_sell, profit = check_sell(player_id, playername)
            to_sell = colorize_boolean(to_sell)
            profit = colorize_profit(profit)
            table.append([playername, to_sell, bought_date, bought_price, market_price, profit, ' '.join(last_points_array), streak])
            # console.append(cons)
            # html.append(email)

        # console = sorted(console, key=itemgetter(0), reverse=True)
        # console = [[c,d,e,f,g,h] for a,b,c,d,e,f,g,h in console]
        # html = sorted(html, key=itemgetter(0), reverse=True)
        # html = [[c.encode('ascii', 'xmlcharrefreplace'),d,e,f,g,h] for a,b,c,d,e,f,g,h in html]
        # headers = ['Name', 'To sell?', 'Purchase date', 'Purchase price', 'Mkt price', 'Profit']
        table = sorted(table, key=itemgetter(5), reverse=True)
        headers = ['Name', 'To sell?', 'Purchase date', 'Purchase price', 'Mkt price', 'Profit', ' '.join(gamedays), 'Streak']
        print tabulate(table, headers, tablefmt="psql", numalign="right", floatfmt=",.0f")

        if args.mail:
            send_email(fr_email, to_email, 'Tradunio players to sell', str(tabulate(html, headers, tablefmt="html", numalign="right", floatfmt=",.0f")))

    com.logout()
    db.close_connection()


def get_users_data():
    """
    Gets data of the user
    :return:
    """
    last_date = db.simple_query('SELECT MAX(date) FROM user_data LIMIT 1')[0][0]
    if last_date == today:
        users_data = dict()
        users = db.simple_query('SELECT u.idu,u.name,d.points,d.money,d.teamvalue,d.maxbid \
                        FROM users u, user_data d WHERE u.idu=d.idu AND date = "%s"' % last_date)
        for user in users:
            user_id, username, user_points, money, teamvalue, maxbid = user
            users_data[user_id] = [username, user_points, teamvalue, money, maxbid]
    else:
        users_data = set_users_data()

    return users_data


def set_users_data():
    """
    Gets the last data of the user from Comunio and saves it to database.
    :return: information about the users
    """
    users_data = dict()
    today = date.today()

    users_info = com.get_users_info()
    print 'Updating users data =>',
    for user in users_info:
        [user_name, user_id, user_points, teamvalue, money, maxbid] = user
        db.nocommit_query('INSERT IGNORE INTO users (idu, name) VALUES (%s, "%s")' % (user_id, user_name))
        db.nocommit_query('INSERT IGNORE INTO user_data (idu, date, points, money, teamvalue, maxbid) \
            VALUES (%s, "%s", %s, %s, %s, %s)' % (user_id, today, user_points, money, teamvalue, maxbid))
        db.nocommit_query('DELETE FROM owners WHERE idu="%s"' % user_id)
        users_data[user_id] = [user_name, user_points, teamvalue, money, maxbid]
        db.commit()
    print '%sdone%s.' % (GREEN, ENDC)
    return users_data


def get_user_players(user_id=None):
    """
    Get the players of the users checking first if it is updated in database.
    @param user_id:
    @return:
    """
    players = db.simple_query('SELECT pl.idp,pl.name,cl.idcl,cl.name,pl.position \
                              FROM players pl, clubs cl, owners o \
                              WHERE o.idp=pl.idp AND pl.idcl=cl.idcl AND o.idu=%s' % user_id)
    return players


def set_user_players(user_id=None, username=None):
    user_players = com.get_user_players(user_id)
    print 'Updating players of %s =>' % username,
    for player in user_players:
        player_id, playername, club_id, club_name, value, player_points, position = player
        db.nocommit_query('INSERT IGNORE INTO clubs (idcl, name) VALUES (%s, "%s")' % (club_id, club_name))
        db.nocommit_query('INSERT IGNORE INTO players (idp, name, position, idcl) VALUES (%s, "%s", "%s", %s)' % (
            player_id, playername, position, club_id))
        db.nocommit_query('INSERT IGNORE INTO owners (idp, idu) VALUES (%s, %s)' % (player_id, user_id))
        db.commit()
    print '%sdone%s.' % (GREEN, ENDC)
    return user_players


def get_player_data(player_id=None, playername=None):
    """
    Get prices from a player
    @return: [dates], [prices], [points]
    """
    session = requests.session()
    url_comuniazo = 'http://www.comuniazo.com'
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:35.0) Gecko/20100101 Firefox/35.0'
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", 'Referer': url_comuniazo,
               "User-Agent": user_agent}
    url_jugadores = url_comuniazo + '/comunio/jugadores/'
    suffix, lastname = '', ''
    count = 0
    dates, points, prices = list(), list(), list()
    while True and len(dates) < 2:
        if player_id == 1698:
            pass
        playername = check_exceptions(playername)
        req = session.get(url_jugadores + playername.replace(" ", "-").replace(".", "").replace("'", "") + suffix,
                          headers=headers).content
        dates_re = re.search("(\"[0-9 ][0-9] de \w+\",?,?)+", req)
        try:
            dates = dates_re.group(0).replace('"', '').split(",")
            dates = translate_dates(dates)
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

        data_re = re.search("data: \[(([0-9nul]+,?)+)\]", req)
        for price in data_re.group(1).split(','):
            try:
                prices.append(int(price))
            except:
                prices.append(0)

        try:
            html = BeautifulSoup(req)
            points_rows = html.find('table', {'class': 'points-list'}).find_all('tr')
            for row in points_rows:
                gameday = int(row.td.text)
                if row.div:
                    points.append([gameday, int(row.div.text)])
                else:
                    points.append([gameday, 0])
        except:
            # Player without points
            pass

        if suffix == '-2' or len(dates) > 2:
            break
        else:
            suffix = '-2'

    return dates, prices, points


def set_player_data(player_id=None, playername=None):
    """
    Sets prices and points for all the players of the user
    @param player_id: Id of the football player
    @param playername: Football player name
    @param max_gameday: Max gameday to retrieve. This will avoid get point in middle of gameday.
    @return: Players of the user id
    """
    days_left = days_wo_price(player_id)
    prices, points = list(), list()
    if days_left:
        dates, prices, points = get_player_data(player_id=player_id, playername=playername)
        if days_left >= 365:
            days_left = len(dates)

        db.many_commit_query('INSERT IGNORE INTO prices (idp,date,price) VALUES (%s' % player_id + ',%s,%s)',
                             zip(dates[:days_left], prices[:days_left]))
        db.many_commit_query('INSERT IGNORE INTO points (idp,gameday,points) VALUES (%s' % player_id + ',%s,%s)',
                             points)

        if len(dates) != len(prices):
            print "%sThe prices arrays and dates haven't the same size.%s" % (RED, ENDC)

    return prices, points


def set_new_player(player_id, playername, position, team_id):
    """
    Set new player in the database.
    @param player_id:
    @param playername:
    @param position:
    @param team_id:
    """
    db.commit_query('INSERT IGNORE INTO players (idp,name,position,idcl) VALUES (%s,"%s","%s",%s)'
                    % (player_id, playername, position, team_id))


def set_transactions():
    """
    Save to database all the transactions.
    :return: None
    """
    print 'Updating transactions =>',
    until_date = db.simple_query('SELECT MAX(date) FROM transactions')[0][0]-timedelta(days=10)
    news = com.get_news(until_date)
    for new in news:
        ndate, title, text = new
        if 'Fichajes' not in title:
            continue
        pattern = re.compile(
            ur'(?:(?:\\n)?([(\w+|\w+ \w+|\w+\-\w+)]+?)(?: cambia por )([0-9\.\,]*?)(?: .*? de )(.+?) a (.+?)\.)', re.UNICODE)
        transactions = re.findall(pattern, text)
        for trans in transactions:
            playername, value, fr, to = trans
            value = int(value.replace('.', ''))
            playername = playername.strip()
            try:
                # TODO: Refactor please
                player_id = db.simple_query('SELECT idp FROM players WHERE name LIKE "%%%s%%"' % playername)[0][0]
                if 'Computer' in fr:
                    kind = 'Buy'
                    user_id = db.simple_query('SELECT idu FROM users WHERE name LIKE "%%%s%%"' % to)[0][0]
                    db.commit_query(
                        'INSERT IGNORE INTO transactions (idp, idu, type, price, date) VALUES (%s,%s,"%s",%s,"%s")'
                        % (player_id, user_id, kind, value, ndate))
                elif 'Computer' in to:
                    kind = 'Sell'
                    user_id = db.simple_query('SELECT idu FROM users WHERE name LIKE "%%%s%%"' % fr)[0][0]
                    db.commit_query(
                        'INSERT IGNORE INTO transactions (idp, idu, type, price, date) VALUES (%s,%s,"%s",%s,"%s")'
                        % (player_id, user_id, kind, value, ndate))
                else:
                    kind = 'Buy'
                    user_id = db.simple_query('SELECT idu FROM users WHERE name LIKE "%%%s%%"' % to)[0][0]
                    db.commit_query(
                        'INSERT IGNORE INTO transactions (idp, idu, type, price, date) VALUES (%s,%s,"%s",%s,"%s")'
                        % (player_id, user_id, kind, value, ndate))
                    user_id = db.simple_query('SELECT idu FROM users WHERE name LIKE "%%%s%%"' % fr)[0][0]
                    kind = 'Sell'
                    db.commit_query(
                        'INSERT IGNORE INTO transactions (idp, idu, type, price, date) VALUES (%s,%s,"%s",%s,"%s")'
                        % (player_id, user_id, kind, value, ndate))
            except:
                # Player selled before having in database
                pass
    print '%sdone%s.' % (GREEN, ENDC)


def check_bids(user_id):
    # TODO: Check last transaction date para no refrescar todo cada vez
    ret = []
    from_you = com.bids_from_you()
    for trans in from_you:
        if trans[6] == 'Efectuada':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            db.nocommit_query('INSERT OR REPLACE INTO players (idp, name, idu) VALUES (%s,%s,%s)'
                              % (idp, player, user_id))
            db.nocommit_query('INSERT OR REPLACE INTO transactions (idp,type,price,date) VALUES (%s,%s,%s,%s)' %
                              (idp, 'Buy', price, trans_date))
            db.commit()
            ret.append([idp, player, float(price), trans_date, '%sBought%s' % (GREEN, ENDC), colorize_profit(0.0)])
        elif trans[6] == 'Pendiente':
            player = trans[0]
            price = trans[3]
            trans_date = translate_dates([trans[5]])[0]
            idp = com.info_player_id(player)
            ret.append([idp, player, float(price), trans_date, '%sBid%s' % (BLUE, ENDC), colorize_profit(0.0)])

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
            ret.append([idp, player, float(price), trans_date, '%sSelled%s' % (RED, ENDC), colorize_profit(rent)])
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
            rent = calculate_profit(precio_compra, price)
            ret.append(
                [idp, player, float(price), trans_date, '%sOffer%s' % (YELLOW, ENDC), colorize_profit(rent)])

    return sorted(ret, key=itemgetter(3), reverse=True)


def check_buy(name, min_price, mkt_price):
    """
    Check if it's a good deal buy a player
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


def check_sell(player_id, playername):
    """
    Check the rentability of our players.
    """
    to_sell = list()
    sell = False
    hoy = date.today()

    try:
        bought = db.simple_query(
            'SELECT date,price FROM transactions \
            WHERE idp=%s AND type="Buy" \
            ORDER BY date DESC LIMIT 1' % player_id)[0]
    except IndexError:
        first_date = db.simple_query('SELECT MIN(date) FROM transactions')[0][0]
        current_price = float(db.simple_query(
            'SELECT price FROM prices \
            WHERE idp=%s \
            ORDER BY date DESC LIMIT 1' % player_id)[0][0])
        init_price = float(db.simple_query(
            'SELECT price FROM prices \
            WHERE idp=%s AND date>"%s" \
            ORDER BY date ASC LIMIT 1' % (player_id, first_date))[0][0])
        profit = calculate_profit(init_price, current_price)
        # to_sell_console = [profit, player_id, playername, colorize_boolean(sell, html=False), '-', init_price, current_price, colorize_profit(profit, html=False)]
        # to_sell_html = [profit, player_id, playername, colorize_boolean(sell, html=True), '-', init_price, current_price, colorize_profit(profit, html=True)]
        return '-', init_price, current_price, sell, profit

    prev_price, stop = 0, 0
    bought_date, bought_price = bought[0], float(bought[1])

    prices = db.simple_query(
        'SELECT idp,date,price \
        FROM prices \
        WHERE idp=%s AND date>="%s" \
        ORDER BY date ASC' % (player_id, bought_date))

    for price_data in prices:
        price = float(price_data[2])
        if price > prev_price:
            prev_price = price
            stop = int(prev_price - (prev_price * FILTRO_STOP))

        # Comprobamos si el precio ha roto el stop
        if price < stop:
            sell = True

        # Si el precio del jugador se ha recuperado y ya había entrado en venta, se demarca la venta
        if price > stop and sell:
            sell = False

    # Calculate profit
    profit = calculate_profit(bought_price, price)

    to_sell_console = [profit, player_id, playername, colorize_boolean(sell, html=False),
                       bought_date, bought_price, price,
                       colorize_profit(profit, html=False)]

    to_sell_html = [profit, player_id, playername, colorize_boolean(sell, html=True),
                    bought_date, bought_price, price,
                    colorize_profit(profit, html=True)]

    return bought_date, bought_price, price, sell, profit


def translate_dates(dates):
    """
    Translates dates format from 'dd.mm' to date('yyyy-mm-dd')
    @return: [[date,]]
    """
    formatted_dates = list()
    last = 0
    for dat in dates:
        if dat == '':
            # Repeat the last value if we find some gap in the dates
            formatted_dates.append(formatted_dates[-1])
            continue
        day = dat[:2]
        if int(day) < 10:
            day = '0' + day[1]
        if dat[6:] != '':
            # Transform month from Comuniazo
            month = \
                {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}[dat[6:]]
        else:
            # Dates from Comunio
            month = dat[3:5]
        year = str(date.today().year - last)
        if month + day == '0101':
            last = 1

        p_date = datetime.strptime('%s-%s-%s' % (year, month, day), "%Y-%m-%d").date()
        formatted_dates.append(p_date)
    return formatted_dates


def colorize_profit(profit, html=False):
    color = {
        True: {
            profit<=-10: RED_HTML,
            -10<profit<=0: YELLOW_HTML,
            0<profit<10: GREEN_HTML,
            10<=profit<9999: CYAN_HTML },
        False: {
            profit<=-10: RED,
            -10<profit<=0: YELLOW,
            0<profit<10: GREEN,
            10<=profit<9999: CYAN },
    }[html][True]

    if html:
        font = '<font color="%s">%4d%%</font>' % (color, profit)
    else:
        font = '%s%4d%%%s' % (color, profit, ENDC)

    return font


def colorize_points(points, html=False):
    color = {
        True: {
            points<=0: RED_HTML,
            0<points<=9: GREEN_HTML,
            10<=points<99: CYAN_HTML },
        False: {
            points<=0: RED,
            0<points<=9: GREEN,
            10<=points<99: CYAN },
    }[html][True]

    points = str(abs(points))
    if html:
        font = '<font color="%s">%3s%%</font>' % (color, points)
    else:
        font = '%s%3s%s' % (color, points, ENDC)

    return font


def colorize_boolean(bool, html=False):
    decide = {True: {
                True: '<font color="#33cc33">%s</font>' % bool,
                False: '<font color="#cc3300">%s</font>' % bool },
              False: {
                  True: GREEN + str(bool) + ENDC,
                  False: RED + str(bool) + ENDC }
             }

    return decide[html][bool]


def calculate_profit(price_ago, current_price):
    profit = (current_price - price_ago) / price_ago * 100
    return profit


def days_wo_price(idp):
    """
    Returns the days that the player hasn't price in the database.
    @param idp: Player ID
    @return: Days without price (max 365 days)
    """
    max_date = db.simple_query('SELECT MAX(date) FROM prices WHERE idp=%s LIMIT 1' % idp)[0][0]
    try:
        res = (date.today() - max_date).days
        if not (0 < res < 365):
            res = 365
    except:
        res = 365

    return res


def check_exceptions(playername):
    exceptions = {'Banega': 'Ever Banega',}
    return exceptions.get(playername, playername)


def print_user_data(username, teamvalue, money, maxbid, points, players):
    print '\n%s:' % username
    print u'Teamvalue: %s € - Money: %s € - Max bid: %s € - Points: %s' % (
        format(teamvalue, ",d"), format(money, ",d"), format(maxbid, ",d"), points)
    headers = ['Name', 'Club ID', 'Club', 'Value', 'Points', 'Position']
    print tabulate(players[1:], headers, tablefmt="rst", floatfmt=",.0f")


def send_email(fr, to, subject, text):
    message = Message(From=fr, To=to)
    message.Subject = subject
    message.Html = text
    sender = Mailer('localhost')
    sender.send(message)

if __name__ == '__main__':
    main()

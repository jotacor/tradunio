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
BUY_LIMIT = 1.2
MIN_STREAK = 20

config = ConfigParser()
config.read('config.conf')
c_user = config.get('comunio', 'user')
c_passwd = config.get('comunio', 'passwd')
c_user_id = config.getint('comunio', 'user_id')
community_id = config.getint('comunio', 'community_id')
fr_email = config.get('comunio', 'fr_email')
to_email = config.get('comunio', 'to_email')
admin_email = config.get('comunio', 'admin_email').split(',')
max_players = config.getint('comunio', 'max_players')
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
    if not com.logged:
        print "Not logged in Comunio, existing."
        exit(0)

    # INIT
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
                    print query[0],
                    db.commit_query(query[0])
                    print '%sdone%s.' % (GREEN, ENDC)
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

    # UPDATE
    if args.update:
        print '\n[*] Updating money, team value, save players, prices and transactions.'
        users = set_users_data()
        set_transactions()
        max_players_text = ''
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
                _ = [player.pop(0) for player in players]
                _ = [player.pop(1) for player in players]
                if args.mail:
                    if len(players) < max_players - 4:
                        num_players = '<font color="%s">%s</font>' % (GREEN_HTML, len(players))
                    elif len(players) < max_players - 2:
                        num_players = '<font color="%s">%s</font>' % (YELLOW_HTML, len(players))
                    else:
                        num_players = '<font color="%s">%s</font>' % (RED_HTML, len(players))

                    text = 'User: %s #Players: %s<br/>' % (username, num_players)
                    text += u'Teamvalue: %s € - Money: %s € - Max bid: %s € - Points: %s<br/>' % (
                        format(teamvalue, ",d"), format(money, ",d"), format(maxbid, ",d"), format(userpoints, ",d"))
                    text = text.encode('utf8')
                    headers = ['Name', 'Club', 'Value', 'Points', 'Position']
                    text += tabulate(players, headers, tablefmt="html", numalign="right", floatfmt=",.0f").encode(
                        'utf8')
                    send_email(fr_email, to_email, 'Tradunio update %s' % today, text)
                else:
                    print_user_data(username, teamvalue, money, maxbid, userpoints, players)

            if len(players) > max_players:
                max_players_text += 'User %s has reached the max players allowed with #%s<br/>'\
                                    % (username, len(players))

        if max_players_text:
            send_email(fr_email, admin_email, 'User max players reached %s' % today, max_players_text)

    # BUY
    if args.buy:
        print '\n[*] Checking players to buy in the market.'
        max_gameday = db.simple_query('SELECT MAX(gameday) from points')[0][0]
        players_on_sale = sorted(com.players_onsale(com.community_id, only_computer=False), key=itemgetter(2),
                                 reverse=True)
        gamedays = [('%3s' % gameday) for gameday in range(max_gameday - 4, max_gameday + 1)]
        bids = check_bids_offers(kind='bids')
        table = list()
        for player in players_on_sale:
            player_id, playername, team_id, team, min_price, market_price, points, dat, owner, position = player
            to_buy = colorize_boolean(check_buy(player_id, playername, min_price, market_price))
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
                day = colorize_profit(calculate_profit(prices[-2][1], market_price))
                week = colorize_profit(calculate_profit(prices[-8][1], market_price))
                month = colorize_profit(calculate_profit(prices[-30][1], market_price))
            except IndexError:
                pass

            bid, extra_price = 0.0, colorize_profit(0.0)
            if player_id in bids:
                bid = bids[player_id][2]
                extra_price = colorize_profit(bids[player_id][3])

            table.append([playername, position, to_buy, owner, month, week, day,
                          market_price, min_price, bid, extra_price, ' '.join(last_points_array), streak])

        headers = ['Name', 'Position', 'To Buy?', 'Owner', 'Month ago', 'Week ago', 'Day ago',
                   'Mkt. price', 'Min. price', 'Bid', 'Extra', ' '.join(gamedays), 'Streak']
        table = sorted(table, key=itemgetter(12), reverse=True)

        if args.mail:
            text = tabulate(table, headers, tablefmt="html", numalign="right", floatfmt=",.0f").encode('utf8')
            send_email(fr_email, to_email, 'Tradunio players to buy %s' % today, text)
        else:
            print tabulate(table, headers, tablefmt="psql", numalign="right", floatfmt=",.0f")

    # SELL
    if args.sell:
        print '\n[*] Checking players to sell.'
        max_gameday = db.simple_query('SELECT MAX(gameday) from points')[0][0]
        gamedays = [('%3s' % gameday) for gameday in range(max_gameday - 4, max_gameday + 1)]
        console, table = list(), list()
        players = get_user_players(user_id=com.myid)
        offers = check_bids_offers(kind='offers')
        for player in players:
            player_id, playername, club_id, club_name, position = player
            bought_date, bought_price, market_price, to_sell, profit = check_sell(player_id)

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

            prices = db.simple_query(
                'SELECT p.date,p.price \
                FROM players pl INNER JOIN prices p ON p.idp=pl.idp AND pl.idp = "%s" \
                ORDER BY p.date ASC' % player_id)
            day, week, month = 0, 0, 0

            try:
                day = colorize_profit(calculate_profit(prices[-2][1], market_price))
                week = colorize_profit(calculate_profit(prices[-8][1], market_price))
                month = colorize_profit(calculate_profit(prices[-30][1], market_price))
            except IndexError:
                pass

            to_sell = colorize_boolean(to_sell)
            profit_color = colorize_profit(profit)

            offer, extra_price, who = 0.0, colorize_profit(0.0), '-'
            if player_id in offers:
                who = offers[player_id][1]
                offer = offers[player_id][2]
                extra_price = colorize_profit(offers[player_id][3])

            table.append(
                [playername, position, to_sell, bought_date, month, week, day, ' '.join(last_points_array),
                 streak, bought_price, market_price, profit_color, offer, who, extra_price])

        table = sorted(table, key=itemgetter(8), reverse=True)
        headers = ['Name', 'Position', 'To sell?', 'Purchase date', 'Month ago', 'Week ago', 'Day ago',
                   ' '.join(gamedays), 'Streak', 'Purchase price', 'Mkt price', 'Profit', 'Offer', 'Who', 'Profit']
        if args.mail:
            text = tabulate(table, headers, tablefmt="html", numalign="right", floatfmt=",.0f").encode('utf8')
            send_email(fr_email, to_email, 'Tradunio players to sell %s' % today, text)
        else:
            print tabulate(table, headers, tablefmt="psql", numalign="right", floatfmt=",.0f")

    com.logout()
    db.close_connection()


def get_users_data():
    """
    Gets data of the users.
    :return: {{user_id: username, user_points, teamvalue, money, maxbid}}
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
    Gets the last data of the users from Comunio and saves it to database.
    :return: {{user_id: username, user_points, teamvalue, money, maxbid}}
    """
    users_data = dict()
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
    :param user_id: Id of the user.
    :return: ((player_id, playername, club_id, clubname, position))
    """
    players = db.simple_query('SELECT pl.idp,pl.name,cl.idcl,cl.name,pl.position \
                              FROM players pl, clubs cl, owners o \
                              WHERE o.idp=pl.idp AND pl.idcl=cl.idcl AND o.idu=%s' % user_id)
    return players


def set_user_players(user_id=None, username=None):
    """
    Set the players of the user.
    :param user_id: Id of the user.
    :param username: Name of the user.
    :return: [[player_id, playername, club_id, club_name, value, player_points, position]]
    """
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


def get_player_data(playername=None):
    """
    Get prices from a player
    :param playername: Name of the player.
    :return: [dates], [prices], [points]
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
        playername = check_exceptions(playername)
        req = session.get(url_jugadores + playername.replace(" ", "-").replace(".", "").replace("'", "") + suffix,
                          headers=headers).content
        dates_re = re.search("(\"[0-9 ][0-9] de \w+\",?,?)+", req)
        try:
            dates = dates_re.group(0).replace('"', '').split(",")
            dates = translate_dates(dates)
        except AttributeError:
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
        if data_re is None:
            pass
        for price in data_re.group(1).split(','):
            try:
                prices.append(int(price))
            except ValueError:
                # No price
                pass

        try:
            html = BeautifulSoup(req)
            points_rows = html.find('table', {'class': 'points-list'}).find_all('tr')
            for row in points_rows:
                gameday = int(row.td.text)
                if row.div:
                    points.append([gameday, int(row.div.text)])
                else:
                    points.append([gameday, 0])
        except AttributeError:
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
    :param player_id: Id of the football player
    :param playername: Football player name
    :return: Players of the user id
    """
    days_left = days_wo_price(player_id)
    prices, points = list(), list()
    if days_left:
        dates, prices, points = get_player_data(playername=playername)
        if days_left >= 365:
            days_left = len(dates)

        if not db.rowcount('SELECT idp FROM players WHERE idp=%s' % player_id):
            playername, position, club_id, price = com.get_player_info(player_id)
            set_new_player(player_id, playername, position, club_id)

        db.many_commit_query('INSERT IGNORE INTO prices (idp,date,price) VALUES (%s' % player_id + ',%s,%s)',
                             zip(dates[:days_left], prices[:days_left]))
        for point in points:
            db.nocommit_query('INSERT INTO points (idp,gameday,points) VALUES (%s,%s,%s) \
                              ON DUPLICATE KEY UPDATE points=%s' % (player_id, point[0], point[1], point[1]))
        db.commit()
        if len(dates) != len(prices):
            print "%sThe prices arrays and dates haven't the same size.%s" % (RED, ENDC)

    return prices, points


def set_new_player(player_id, playername, position, team_id):
    """
    Set new player in the database.
    :param player_id:
    :param playername:
    :param position:
    :param team_id:
    """
    db.commit_query('INSERT IGNORE INTO players (idp,name,position,idcl) VALUES (%s,"%s","%s",%s)'
                    % (player_id, playername, position, team_id))


def set_transactions():
    """
    Save to database all the transactions.
    """
    print 'Updating transactions =>',
    until_date = db.simple_query('SELECT MAX(date) FROM transactions')[0][0] - timedelta(days=10)
    news = com.get_news(until_date)
    for new in news:
        ndate, title, text = new
        if 'Fichajes' not in title:
            continue
        pattern = re.compile(
            ur'(?:(?:\\n)?([(\S+ )]+?)(?: cambia por )([0-9\.,]*?)(?: .*? de )(.+?) a (.+?)\.)',
            re.UNICODE)
        transactions = re.findall(pattern, text)
        for trans in transactions:
            playername, value, fr, to = trans
            value = int(value.replace('.', ''))
            playername = playername.strip()
            try:
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
            except IndexError:
                # Player selled before having in database
                pass
    print '%sdone%s.' % (GREEN, ENDC)


def check_bids_offers(kind=None):
    """
    Check if you have offers for your players or show you the bids made for other players.
    :param kind:
    :return:
    """
    bids_offers = dict()
    if kind == 'bids':
        from_you = com.bids_from_you()
        for bid in from_you:
            player_id, playername, owner, team_id, team, price, bid_date, trans_date, status = bid
            if status == 'Pendiente' or status == 'Pending':
                _, prices, _ = get_player_data(playername=playername)
                extra_price = calculate_profit(prices[0], price)
                bids_offers[player_id] = [playername, owner, price, extra_price]
    elif kind == 'offers':
        to_you = sorted(com.bids_to_you())
        player_ant, price_ant = 0, 0
        for offer in to_you:
            player_id, playername, who, team_id, team, price, bid_date, trans_date, status = offer
            if status == 'Pendiente' or status == 'Pending':
                if player_ant == player_id and price < price_ant:
                    # Only saves the max offer for every player
                    continue
                precio_compra = db.simple_query(
                    'SELECT price FROM transactions WHERE idp=%s AND type="Buy" ORDER BY date DESC LIMIT 1'
                    % player_id)

                if not precio_compra:
                    first_date = db.simple_query('SELECT MIN(date) FROM transactions')[0][0]
                    precio_compra = db.simple_query(
                        'SELECT price FROM prices WHERE idp=%s AND date>"%s" ORDER BY date ASC LIMIT 1'
                        % (player_id, first_date))

                profit = calculate_profit(precio_compra[0][0], price)
                bids_offers[player_id] = [playername, who, price, profit]
                player_ant, price_ant = player_id, price

    return bids_offers


def check_buy(player_id, playername, min_price, mkt_price):
    """
    Check if it's a good deal buy a player
    :param player_id: Id of the football player.
    :param playername: Name of the football player.
    :param min_price: Minimum price requested.
    :param mkt_price: Market price.
    :return: True/False if it is a good deal to buy it.
    """
    _, points = set_player_data(player_id=player_id, playername=playername)
    first_date = db.simple_query('SELECT MIN(date) FROM transactions')[0][0]
    last_days = (today - timedelta(days=3))
    prices = db.simple_query(
        'SELECT pr.price,pr.date FROM prices pr,players pl \
         WHERE pl.idp=pr.idp AND pl.idp=%s AND pr.date>"%s" ORDER BY pr.date ASC' % (player_id, first_date))
    max_h = 0
    fecha = date(1970, 01, 01)
    for row in prices:
        price, dat = row
        if price > max_h:
            max_h = price
            fecha = dat

    streak = sum([int(point) for gameday, point in points[-5:]])
    # Si la fecha a la que ha llegado es la de hoy (max_h) y
    #   el precio que solicitan no es superior al de mercado+BUY_LIMIT, se compra
    if fecha > last_days and min_price < (mkt_price * BUY_LIMIT) and streak > MIN_STREAK:
        return True
    else:
        return False


def check_sell(player_id):
    """
    Check the rentability of our players.
    :param player_id: Football player id.
    :return: bought_date, bought_price, current_price, sell, profit
    """
    sell = False
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

        return '-', init_price, current_price, sell, profit

    prev_price, stop, price = 0, 0, 0
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

    return bought_date, bought_price, price, sell, profit


def translate_dates(dates):
    """
    Translates dates format from 'xx de Month' or 'dd.mm' to date('yyyy-mm-dd')
    :param dates: Array dates from Comuniazo or Comunio.
    :return: [[date,]]
    """
    formatted_dates = list()
    year = str(today.year)
    for dat in dates:
        if dat == '':
            continue
        day = dat[:2]
        mont = dat[6:]
        if int(day) < 10:
            day = '0' + day[1]
        if mont != '':
            # Month from Comuniazo
            month = \
                {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}[mont]
        else:
            # Month from Comunio
            month = dat[3:5]

        if month + day == '0101' or (formatted_dates and int(month) > formatted_dates[-1].month):
            # One year less
            year = str(today.year - 1)

        p_date = datetime.strptime('%s-%s-%s' % (year, month, day), "%Y-%m-%d").date()
        formatted_dates.append(p_date)
    return formatted_dates


def colorize_profit(profit):
    """
    Colorize the profit depending on its value.
    :param profit: Profit.
    :return: console_colored, html_colored
    """
    color = {
        'html': {
            profit <= -10: RED_HTML,
            -10 < profit <= 0: YELLOW_HTML,
            0 < profit < 10: GREEN_HTML,
            10 <= profit < 9999: CYAN_HTML
        },
        'console': {
            profit <= -10: RED,
            -10 < profit <= 0: YELLOW,
            0 < profit < 10: GREEN,
            10 <= profit < 9999: CYAN
        },
    }

    # html_colored = '<font color="%s">%4d%%</font>' % (color['html'][True], profit)
    console_colored = '%s%4d%%%s' % (color['console'][True], profit, ENDC)

    return console_colored


def colorize_points(points):
    """
    Colorize the points depending on its value.
    :param points: Points of a player in a gameday.
    :return: Console colored points
    """
    color = {
        'html': {
            points <= 0: RED_HTML,
            0 < points <= 9: GREEN_HTML,
            10 <= points < 99: CYAN_HTML
        },
        'console': {
            points <= 0: RED,
            0 < points <= 9: GREEN,
            10 <= points < 99: CYAN
        },
    }

    points = str(abs(points))
    # html_colored = '<font color="%s">%3s%%</font>' % (color['html'][True], points)
    console_colored = '%s%3s%s' % (color['console'][True], points, ENDC)

    return console_colored


def colorize_boolean(boolean):
    """
    Colorize the boolean depending on its value.
    :param boolean: True or False.
    :return: True in green, False in red
    """
    color = {
        'html': {
            True: '<font color="#33cc33">%s</font>' % boolean,
            False: '<font color="#cc3300">%s</font>' % boolean
        },
        'console': {
            True: GREEN + str(boolean) + ENDC,
            False: RED + str(boolean) + ENDC
        }
    }

    return color['console'][boolean]


def calculate_profit(price_ago, current_price):
    """
    Calculates the profit of a price regarding a previous one.
    :param price_ago: First price.
    :param current_price: Last price.
    :return: Profit in percentage.
    """
    profit = (current_price - price_ago) / float(price_ago) * 100
    return profit


def days_wo_price(player_id):
    """
    Returns the days that the player has not a price in the database.
    :param player_id: Player ID
    :return: Days without price (max 365 days)
    """
    max_date = db.simple_query('SELECT MAX(date) FROM prices WHERE idp=%s LIMIT 1' % player_id)[0][0]
    try:
        res = (date.today() - max_date).days
    except TypeError:
        res = 365

    if not (0 < res < 365):
        res = 365

    return res


def check_exceptions(playername):
    """
    Fix exceptions for a player name between Comunio and Comuniazo.
    :param playername: Name of the football player.
    :return: Corrected name.
    """
    exceptions = {'Banega': 'Ever Banega', 'Mikel': u'Mikel González', u'Isma López': u'Ismael López'}
    return exceptions.get(playername, playername)


def print_user_data(username, teamvalue, money, maxbid, userpoints, players):
    """
    Prints a table with all data of an user.
    :param username: Name of the user.
    :param teamvalue: Value of his team.
    :param money: Current money.
    :param maxbid: Current max bid.
    :param userpoints: Current points.
    :param players: Array of the players to print.
    """
    if len(players) < max_players - 4:
        num_players = '%s%s%s' % (GREEN, len(players), ENDC)
    elif len(players) < max_players - 2:
        num_players = '%s%s%s' % (YELLOW, len(players), ENDC)
    else:
        num_players = '%s%s%s' % (RED, len(players), ENDC)

    print '\nUser: %s - #Players: %s' % (username, num_players)
    print u'Teamvalue: %s € - Money: %s € - Max bid: %s € - Points: %s' % (
        format(teamvalue, ",d"), format(money, ",d"), format(maxbid, ",d"), format(userpoints, ",d"))
    headers = ['Name', 'Club', 'Value', 'Points', 'Position']
    print tabulate(players, headers, tablefmt="psql", floatfmt=",.0f")


def send_email(fr, to, subject, text):
    """
    Send an email.
    :param fr: From.
    :param to: Recipient.
    :param subject: Subject.
    :param text: Text in html.
    """
    text = parse_console_to_html(text)
    message = Message(From=fr, To=to, charset='utf-8')
    message.Subject = subject
    message.Html = text
    sender = Mailer('localhost')
    sender.send(message)
    print 'Email sent.'


def parse_console_to_html(text):
    html_init = '<font color="%s">'
    html_end = '</font>'
    text = text.replace(RED, html_init % RED_HTML).replace(CYAN, html_init % CYAN_HTML) \
        .replace(GREEN, html_init % GREEN_HTML).replace(YELLOW, html_init % YELLOW_HTML)
    text = text.replace(ENDC, html_end)
    return text


if __name__ == '__main__':
    main()

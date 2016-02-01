#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Feb 01, 2016
@author: jotacor
"""

import db_tradunio as db
import tabulate


class User:
    def __init__(self, idu):
        self.id = idu
        self.username = None
        self.user_data = []
        self.players = []
        self.transactions = []
        self.load_players(idu)
        self.load_user_data(idu)

    def __repr__(self):
        return 'Teamvalue: %s € - Money: %s € - Max bid: %s € - Points: %s' % (
                format(self.user_data[-1].teamvalue, ",d"),
                format(self.user_data[-1].money, ",d"),
                format(self.user_data[-1].maxbid, ",d"),
                self.user_data[-1].points)

    def load_players(self, idu):
        players = db.simple_query(
            'SELECT p.idp, p.name, p.position, c.name \
            FROM players p, clubs c, owners o \
            WHERE o.idp=p.idp AND p.idcl=c.idcl AND o.idu=%s' % idu)
        for player in players:
            idp, playername, position, clubname = player
            ob_player = Player(idp, playername, position, clubname)
            self.players.append(ob_player)

    def load_user_data(self, idu):
        user_data = db.simple_query(
            'SELECT u.name, d.date, d.points, d.money, d.teamvalue, d.maxbid \
            FROM users u, user_data d \
            WHERE u.idu=d.idu AND u.idu=%s ORDER BY d.date ASC' % idu)
        self.username = user_data[0][0]
        for data in user_data:
            name, date, points, money, teamvalue, maxbid = data
            ob_user_data = UserData(date, points, money, int(teamvalue), maxbid)
            self.user_data.append(ob_user_data)

    def load_transactions(self, idu):
        transactions = db.simple_query(
            'SELECT date, type, price FROM transactions WHERE idu=%s ORDER BY date ASC' % idu)
        for transaction in transactions:
            date, trans, price = transaction
            ob_transaction = Transaction(date, trans, price)
            self.transactions.append(ob_transaction)


class Player:
    def __init__(self, idp, playername, position, clubname):
        self.name = playername
        self.clubname = clubname
        self.position = position
        self.prices = list()
        self.points = list()
        self.load(idp)

    def __repr__(self):
        headers = ['Name', 'Club', 'Value', 'Points', 'Position', 'Last date']
        total_points = sum(p.points for p in self.points)
        table = [self.name, self.clubname, self.position, self.prices[-1].price, total_points, self.prices[-1].date]
        return tabulate(table, headers, tablefmt="rst", numalign="right", floatfmt=",.0f")

    def load(self, idp):
        prices = db.simple_query('SELECT date, price FROM prices WHERE idp=%s ORDER BY date ASC' % idp)
        for price in prices:
            date, price = prices
            ob_price = Price(date, price)
            self.prices.append(ob_price)

        points = db.simple_query('SELECT gameday, points FROM points WHERE idp=%s ORDER BY gameday ASC' % idp)
        for point in points:
            gameday, poin = point
            ob_point = Points(gameday, poin)
            self.points.append(ob_point)


class UserData:
    def __init__(self, date, points, money, teamvalue, maxbid):
        self.date = date
        self.points = points
        self.money = money
        self.teamvalue = teamvalue
        self.maxbid = maxbid


class Transaction:
    def __init__(self, date, transaction, price):
        self.date = date
        self.type = transaction
        self.price = price


class Price:
    def __init__(self, date, price):
        self.date = date
        self.price = price


class Points:
    def __init__(self, gameday, points):
        self.gameday = gameday
        self.points = points


def test():
    user = User(15797714)
    pass


if __name__ == '__main__':
    test()

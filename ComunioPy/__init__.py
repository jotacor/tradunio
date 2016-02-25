#!/usr/bin/env python
# -*- coding: utf-8 -*- 

from bs4 import BeautifulSoup
from datetime import date as dt
from datetime import datetime
import json
import os
import re
import requests
import sys
import time

Leagues = {'BBVA': 'www.comunio.es',
           'Adelante': 'www.comuniodesegunda.es',
           'Bundesliga': 'www.comunio.de',
           'Bundesliga2': 'www.comdue.de',
           'Serie A': 'www.comunio.it',
           'Premier League': 'www.comunio.co.uk',
           'Liga Sagres': 'www.comunio.pt'}

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0'


class Comunio:
    def __init__(self, username, password, user_id, community_id, league):
        self.username = username
        self.password = password
        self.domain = Leagues[league]
        self.session = requests.session()
        self.myid = user_id
        self.money = None
        self.teamvalue = None
        self.community_id = community_id
        self.news = list()
        self.logged = self.login()

    def login(self):
        payload = {'login': self.username,
                   'pass': self.password,
                   'action': 'login'}
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   "User-Agent": user_agent}
        req = self.session.post('http://' + self.domain + '/login.phtml', headers=headers, data=payload).content
        if 'puntos en proceso' in req or 'points in process' in req:
            print 'Comunio webpage not available.'
            return False

        return self.load_info()  # Function to load the account information

    def load_info(self):
        """ Get info from logged account """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/login.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/team_news.phtml', headers=headers).content
        soup = BeautifulSoup(req)

        estado = soup.find('div', {'id': 'content'}).find('div', {'id': 'manager'}).string
        if estado:
            print estado.strip()
            return False

        [s.extract() for s in soup('strong')]
        if soup.find('div', {'id': 'userid'}) is not None:
            self.myid = int(soup.find('div', {'id': 'userid'}).p.text.strip()[2:])
            self.money = int(soup.find('div', {'id': 'manager_money'}).p.text.strip().replace(".", "")[:-2])
            self.teamvalue = int(soup.find('div', {'id': 'teamvalue'}).p.text.strip().replace(".", "")[:-2])
            self.community_id = int(soup.find('link')['href'][24:])
            # self.username = soup.find('div', {'id': 'username'}).p.a.text

        return True

    def get_money(self):
        """Get my money"""
        return self.money

    def get_team_value(self):
        """Get my team value"""
        return self.teamvalue

    def get_myid(self):
        """Get my id"""
        return self.myid

    def get_username(self):
        """Name of the user"""
        return self.username

    def get_news(self, until_date=None):
        """ Get all the news until the date until_date included.
        :param until_date: Last date, included, we want the news.
        """
        if not self.news:
            more_news = True
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                       'Referer': 'http://' + self.domain + '/login.phtml', "User-Agent": user_agent}
            req = self.session.get('http://' + self.domain + '/team_news.phtml', headers=headers).content
            soup = BeautifulSoup(req)
            newsheader = soup.find_all('div', {'class', 'newsheader'})[1:]
            for index, i in enumerate(soup.find_all('div', {'class', 'article_content_text'})[1:]):
                news_date = datetime.strptime(newsheader[index].span['title'][0:8], "%d.%m.%y").date()
                news_title = newsheader[index].text.split(">")[1].strip()
                if news_date < until_date:
                    more_news = None
                    break
                self.news.append([news_date, news_title, i.text])
            first_news = 10
            while more_news and first_news < 200:
                other_news = BeautifulSoup(
                    self.session.post('http://' + self.domain + '/team_news.phtml', headers=headers,
                                      data={'newsAction': 'reload', 'first_news': first_news}).content)
                newsheader = other_news.find_all('div', {'class', 'newsheader'})
                for index, i in enumerate(other_news.find_all('div', {'class', 'article_content_text'})):
                    news_date = datetime.strptime(newsheader[index].span['title'][0:8], "%d.%m.%y").date()
                    news_title = newsheader[index].text.split(">")[1].strip()
                    if news_date < until_date:
                        more_news = None
                        break
                    self.news.append([news_date, news_title, i.text])
                first_news += 10
                time.sleep(1)
        return self.news

    def logout(self):
        """Logout from Comunio"""
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   "User-Agent": user_agent}
        self.session.get('http://' + self.domain + '/logout.phtml', headers=headers)

    def standings(self):
        """Get standings from the community's account"""
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/standings.phtml', headers=headers).content
        soup = BeautifulSoup(req)
        table = soup.find('table', {'id': 'tablestandings'}).find_all('tr')
        clasificacion = list()
        [clasificacion.append('%s\t%s\t%s\t%s\t%s' % (
            tablas.find('td').text, tablas.find('div')['id'], tablas.a.text, tablas.find_all('td')[3].text,
            tablas.find_all('td')[4].text)) for tablas in table[1:]]
        return clasificacion

    def get_user_players(self, userid):
        """Get user info using a ID
        @param userid: Id of the user
        @return: [username, points,[[player_id, name, club, value, points, position],]]
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/standings.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/playerInfo.phtml?pid=' + str(userid),
                               headers=headers).content
        soup = BeautifulSoup(req)
        # title = soup.title.string
        # community = soup.find_all('table', border=0)[1].a.text
        # username = re.search('\((.*?)\)', soup.find('div', id='title').text).group(1)
        players_info = list()
        for i in soup.find('table', cellpadding=2).find_all('tr')[1:]:
            cad = i.find_all('td')
            player_id = int(re.findall('\d+', i.find_all('img')[0]['src'])[0])
            name = cad[2].text.strip()
            club = cad[3].find('img')['alt']
            club_id = int(re.findall('\d+', i.find_all('img')[1]['src'])[0])
            value = float(cad[4].text.replace(".", ""))
            totalpoints = float(cad[5].text)
            position = cad[6].text
            players_info.append([player_id, name, club_id, club, value, totalpoints, position])
        return players_info

    def lineup_user(self, userid):
        """Get user lineup using a ID"""
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/standings.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/playerInfo.phtml?pid=' + userid, headers=headers).content
        soup = BeautifulSoup(req)
        info = list()
        for i in soup.find_all('td', {'class': 'name_cont'}):
            info.append(i.text.strip())
        return info

    def get_users_info(self):
        """
        Get comunity info using a ID
        @return: [[user_name, user_id, user_points, team_value, money, max_bid],]
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/standings.phtml', "User-Agent": user_agent}
        soup = BeautifulSoup(self.session.get('http://' + self.domain + '/teamInfo.phtml?tid=' + str(self.community_id),
                                              headers=headers).content)

        headers_zo = {'Accept': '*/*', 'Referer': 'http://www.comuniazo.com/comunio/dinero',
                      'Host': 'www.comuniazo.com', 'X-Requested-With': 'XMLHttpRequest'}
        money = requests.session()
        money.get('http://www.comuniazo.com/comunio/dinero', headers=headers_zo)
        money_bids = json.loads(
            money.get('http://www.comuniazo.com/ajax/dinero.php?user=%s&dinero=20000000' % self.username,
                      headers=headers_zo).content)

        info = list()
        for row in soup.find('table', cellpadding=2).find_all('tr')[1:]:
            money, max_bid = [0, 0]
            user_name = row.a.text
            user_id = row.find('a')['href'].split('pid=')[1]
            user_points = int(row.find_all('td')[3].text)
            team_value = int(row.find_all('td')[4].text.replace('.', ''))
            for user in money_bids['lista']['players']:
                if user['id'] == user_id:
                    money = int(user['dinero'].replace('.', ''))
                    max_bid = int(user['puja'].replace('.', ''))
            info.append([user_name, int(user_id), user_points, team_value, money, max_bid])
        return info

    def get_player_info(self, player_id):
        """'
        Get info football player using a ID
        @return: [playername,position,team_id,price]
        :param player_id: Id of the football player.
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/tradableInfo.phtml?tid=' + str(player_id), headers=headers).content
        soup = BeautifulSoup(req)
        playername = soup.title.text.strip()
        rows = soup.find('table', cellspacing=1).find_all('tr')
        position = rows[0].find_all('td')[1].text
        club_id = int(re.findall('\d+', rows[1].find_all('td')[1].img['src'])[0])
        for row in rows:
            try:
                price = int(row.find_all('td')[1].text.replace(".", ""))
                if price > 150000:
                    break
            except ValueError:
                continue

        return [playername, position, club_id, price]

    def info_player_id(self, playername):
        """Get id using name football player
        :param playername:
        """
        number = 0
        name = playername.title().replace(" ", "+")
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://stats.comunio.es/search.php?name=' + playername, headers=headers).content
        soup = BeautifulSoup(req)
        for i in soup.find_all('a', {'class', 'nowrap'}):
            number = re.search("([0-9]+)-", str(i)).group(1)
            break  # Solo devuelve la primera coincidencia
        return number

    def club_info(self, cid):
        """
        Get info by real team using a ID
        @return: name,[player list]
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/clubInfo.phtml?cid=' + cid, headers=headers).content
        soup = BeautifulSoup(req)
        plist = list()
        for i in soup.find('table', cellpadding=2).find_all('tr')[1:]:
            plist.append('%s\t%s\t%s\t%s\t%s' % (
                i.find_all('td')[0].text, i.find_all('td')[1].text, i.find_all('td')[2].text, i.find_all('td')[3].text,
                i.find_all('td')[4].text))
        return soup.title.text, plist

    def club_id(self, club_name):
        """
        Get team ID using a real team name
        @param club_name: Name of the real club.
        @return id
        """
        # UTF-8 comparison
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain, headers=headers).content
        soup = BeautifulSoup(req)
        for i in soup.find('table', cellpadding=2).find_all('tr'):
            # Get teamid from the bets
            team1 = i.find('a')['title']
            team2 = i.find_all('a')[1]['title']
            if club_name == team1:
                return i.find('a')['href'].split('cid=')[1]
            elif club_name == team2:
                return i.find_all('a')[1]['href'].split('cid=')[1]
        return None

    def user_id(self, user):
        """ 
        Get userid from a name
        @return: id
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/standings.phtml', headers=headers).content
        soup = BeautifulSoup(req)
        for i in soup.find('table', cellpadding=2).find_all('tr'):
            try:
                if user == i.find_all('td')[2].text.encode('utf8'):
                    return i.find('a')['href'].split('pid=')[1]
            except:
                continue
        return None

    def players_onsale(self, community_id, only_computer=False):
        """
        Returns the football players currently on sale
        @return: [[name, team, min_price, market_price, points, date, owner, position]]
        :param only_computer:
        :param community_id:
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/teamInfo.phtml?tid=' + str(community_id),
                               headers=headers).content
        soup = BeautifulSoup(req)

        current_year = dt.today().year
        current_month = dt.today().month
        on_sale = list()
        year_flag = 0
        for i in soup.find_all('table', {'class', 'tablecontent03'})[2].find_all('tr')[1:]:
            columns = i.find_all('td')
            player_id = int(re.findall('\d+', columns[0].img['src'])[0])
            playername = columns[1].text.strip()
            team_id = int(re.findall('\d+', columns[2].img['src'])[0])
            team = columns[2].a['title'].strip()
            min_price = float(columns[3].text.replace(".", "").strip())
            market_price = float(columns[4].text.replace(".", "").strip())
            points = int(columns[5].text.strip().strip())
            # Controlamos el cambio de año, ya que comunio no lo dá
            if current_month <= 7 < int(columns[6].text[3:5]):
                year_flag = 1
            date = str(current_year - year_flag) + columns[6].text[3:5] + columns[6].text[:2]
            owner = columns[7].text.strip()
            position = columns[8].text.strip()
            # Comprobamos si solamente queremos los de la computadora o no
            if (only_computer and owner == 'Computer') or not only_computer:
                on_sale.append([player_id, playername, team_id, team, min_price, market_price, points, date, owner, position])

        return on_sale

    def bids_to_you(self):
        """
        Get bids made to you
        @return: [[player,owner,team,money,date,datechange,status],]
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/exchangemarket.phtml?viewoffers_x=', headers=headers).content
        soup = BeautifulSoup(req)
        table = list()
        for i in soup.find('table', {'class', 'tablecontent03'}).find_all('tr')[1:]:
            player_id, player, who, team_id, team, price, bid_date, trans_date, status = self.parse_bid_table(i)
            table.append([player_id, player, who, team_id, team, price, bid_date, trans_date, status])
        return table

    def bids_from_you(self):
        """
        Get your bids made for
        @return: [[player,owner,team,money,date,datechange,status],]
        """
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",
                   'Referer': 'http://' + self.domain + '/team_news.phtml', "User-Agent": user_agent}
        req = self.session.get('http://' + self.domain + '/exchangemarket.phtml?viewoffers_x=', headers=headers).content
        soup = BeautifulSoup(req)
        table = list()
        for i in soup.find_all('table', {'class', 'tablecontent03'})[1].find_all('tr')[1:]:
            player_id, player, owner, team_id, team, price, bid_date, trans_date, status = self.parse_bid_table(i)
            table.append([player_id, player, owner, team_id, team, price, bid_date, trans_date, status])
        return table

    @staticmethod
    def parse_bid_table(table):
        """
        Convert table row values into strings
        @return: player, owner, team, price, bid_date, trans_date, status
        """
        columns = table.find_all('td')
        player_id = int(re.findall('\d+', columns[0].a['href'])[0])
        player = columns[0].text
        owner = columns[1].text
        team_id = int(re.findall('\d+', columns[2].img['src'])[0])
        team = table.img['alt']
        price = int(columns[3].text.replace(".", ""))
        bid_date = columns[4].text
        trans_date = columns[5].text
        status = columns[6].text
        return player_id, player, owner, team_id, team, price, bid_date, trans_date, status

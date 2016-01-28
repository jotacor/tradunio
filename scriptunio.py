#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
'''
Descarga todos los jugadores, los nuevos que entran en la liga, los que salen y todos sus puntos y precios.
@author: jotacor
'''
#TODO: no funciona bien el cambio de año al recuperar las jornadas

import argparse
from bs4 import BeautifulSoup as bs4
import db_tradunio as db
from ConfigParser import ConfigParser
from datetime import date, timedelta
import locale
import logging
import re
import requests
from suds.client import Client
from suds import WebFault

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

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0'
headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain",'Referer': 'http://www.comunio.es',"User-Agent": user_agent}
soapclient = Client('http://www.comunio.es/soapservice.php?wsdl')
SEASON = '2014/2015'
URL_AS = 'http://resultados.as.com'
JORNADA_ACTUAL = URL_AS + '/resultados/futbol/primera/2014_2015/jornada'
CALENDARIO = URL_AS + '/resultados/futbol/primera/2014_2015/calendario'
JORNADA_VARIABLE = URL_AS + '/resultados/futbol/primera/2014_2015/jornada/regular_a_%s'


def main():
    parser = argparse.ArgumentParser(description='Calcula cuando debes vender o comprar un jugador del Comunio.')
    #Opciones de carga
    parser.add_argument('-a', '--all', action='store_true', dest='all', help='Realiza una ejecución completa.')
    parser.add_argument('-gpa', '--get-players-all', action='store_true', dest='get_players_all', help='Guarda en base de datos todos los jugadores y sus precios.')
    parser.add_argument('-gpra', '--get-prices-all', action='store_true', dest='get_prices_all', help='Guarda en base de datos todos los jugadores y sus precios.')
    parser.add_argument('-gan', '--get-as-names', action='store_true', dest='get_as_names', help='Guarda los nombres de los jugadores del AS.')

    #Opciones incrementales
    parser.add_argument('-gma', '--get-matches', action='store_true', dest='get_matches', help='Guarda las jornadas.')
    parser.add_argument('-gpn', '--get-players-new', action='store_true', dest='get_players_new', help='Guarda en base de datos los nuevos fichajes y sus precios.')
    parser.add_argument('-gpr', '--get-prices', action='store_true', dest='get_prices', help='Recupera los precios que falten.')
    parser.add_argument('-gpt', '--get-points', action='store_true', dest='get_points', help='Recupera los puntos que falten.')
    
    logging.getLogger('suds.client').setLevel(logging.CRITICAL)
    
    args=parser.parse_args()
    
    if args.get_players_all or args.all:
        get_all_players()
    
    if args.get_prices_all or args.all:
        get_all_prices(incremental=False, clean=False)
    
    if args.get_players_new:
        get_new_players()

    if args.get_prices:
        get_all_prices(incremental=True)

    if args.get_points or args.all:
        get_points(incremental=True)
        
    if args.get_matches or args.all:
        get_matches(incremental=True)



def get_all_players():
    ''' Get all players '''
    req = requests.get('http://stats.comunio.es/squad',headers=headers).content
    soup = bs4(req)
    clubs = soup.find('td',{'class':'clubPics'}).find_all('a')
    for club in clubs:
        link = club['href']
        club_num = re.search("([0-9]+)-(.*)", link).group(1)
        club_name = re.search("([0-9]+)-(.*)", link).group(2).replace("+", " ")
        db.commit_query('INSERT IGNORE INTO clubs (idcl, name) VALUES (%s, "%s")' % (club_num, club_name))
        soup = bs4(requests.get('http://stats.comunio.es' + link,headers=headers).content)
        for row in soup.find('table', {'class': 'rangliste'}).find_all('tr',  re.compile(r"r[1-2]"))[1:-1]:
            nuna = re.search("([0-9]+)-(.*)", row.find('a', {'class':'nowrap'})['href'])
            number = nuna.group(1)
            name = nuna.group(2).replace("+", " ").strip()
            position = _position_translation(row.contents[5].text)
            
            db.nocommit_query(' INSERT INTO players (idp, name, position, idcl) VALUES (%s, "%s", %s, %s) ' % (number, name, position, club_num))
        
        db.commit()


def get_all_prices(name=None,incremental=True,clean=False):
    ''' Get all prices from a player '''
    sql = 'SELECT idp,name FROM players'
    if name != None:
        sql += ' WHERE name = "%s" ' % name.title()

    players = db.simple_query(sql)
    if incremental:
        for player in players:
            idp = player[0]
            name = player[1]
            
            days_wo_price = _array_days_wo_price(name)
            for day in days_wo_price:
                try:
                    #Consultamos el webservice de comunio
                    price = int(soapclient.service.getquote(idp, day))
                    db.nocommit_query('INSERT IGNORE INTO prices (idp,date,price) VALUES (%s,"%s",%s)' % (idp, day.replace("-",""), price))
                except WebFault:
                    continue
    
            db.commit()
    else:
        if clean:
            day_ini = date.today()
        players = map(list, players)
        for player in players:
            idp = player[0]
            name = player[1]
            days=0
            first = str(db.simple_query('SELECT date FROM prices WHERE idp=%s ORDER BY date ASC LIMIT 1' % idp)[0][0])
            day_ini = date(int(first[:4]),int(first[4:6]),int(first[6:8]))
            while True:
                try:
                    day = day_ini - timedelta(days=days)
                    #Consultamos el webservice de comunio
                    price = int(soapclient.service.getquote(idp, day.strftime('%Y-%m-%d')))
                    db.nocommit_query('INSERT IGNORE INTO prices (idp,date,price) VALUES (%s,"%s",%s)' % (idp, day.strftime('%Y%m%d'), price))
                    days+=1
                except WebFault:
                    #Cuando no exista más precios para ese jugador romperemos el while
                    db.commit()
                    break
                except:
                    db.commit()
                    days+=1
                    continue


def get_new_players():
    ''' Obtiene los fichajes y ventas de la liga '''
    session = requests.session()
    session.get('http://stats.comunio.es/transfers.php', headers=headers)
    soup = bs4(session.get('http://stats.comunio.es/transfers.php', headers=headers).content)
    new_members=True
    for table in soup.find_all('table', {'class': 'rangliste'}):
        if new_members:
            for row in table.find_all('tr',  re.compile(r"r[1-2]"))[1:]:
                nuna = re.search("([0-9]+)-(.*)", row.find('a', {'class':'nowrap'})['href'])
                number = nuna.group(1)
                name = nuna.group(2).replace("+", " ").strip()
                club = row.find('td',{'class':'clubPic'}).a['href']
                club_id = re.search("([0-9]+)-(.*)", club).group(1)
                club_name = re.search("([0-9]+)-(.*)", club).group(2).replace("+", " ")
                position = _position_translation(row.contents[6].text)
                db.commit_query('INSERT IGNORE INTO players (idp, name, position, idcl) VALUES (%s, "%s", %s, %s)' % (number, name, position, club_id))
                get_all_prices(name, incremental=True)
                print 'Alta jugador %s (%s) en el club %s (%s) como %s (%s)' % (name,number,club_name,club_id,row.contents[6].text, position)
            new_members=False
        else:
            for row in table.find_all('tr',  re.compile(r"r[1-2]"))[1:]:
                nuna = re.search("([0-9]+)-(.*)", row.find('a', {'class':'nowrap'})['href'])
                number = nuna.group(1)
                name = nuna.group(2).replace("+", " ").strip()
                club = row.find('td',{'class':'clubPic'}).a['href']
                club_id = re.search("([0-9]+)-(.*)", club).group(1)
                club_name = re.search("([0-9]+)-(.*)", club).group(2).replace("+", " ")
                db.commit_query('UPDATE players SET idcl=NULL WHERE idp=%s' % (number))
                print 'Baja jugador %s (%s) del club %s (%s)' % (name,number,club_name,club_id)


def get_points(name=None,incremental=True):
    ''' Obtenemos todos los puntos de la jornada actual '''
    jornadas = list()
    if not incremental:
        jornada = JORNADA_VARIABLE
        for index in range(1,39):
            jornadas.append(jornada % index)
    else:
        jornadas.append(JORNADA_ACTUAL)

    for jornada_actual in jornadas:
        soup = bs4(requests.get(jornada_actual, headers=headers).content)
        n_jornada = soup.find('h3', class_='tit-module-internal s-m-b').text[-2:].strip()
        id_gameday = _get_gameday(n_jornada)
        
        for match in soup.find_all('a', class_='resultado resul_post'):
            partido = dict()
            match_link = match['href']
            if 'resultados.as.com' not in match_link:
                match_link = URL_AS + match_link
            web_match = bs4(requests.get(match_link, headers=headers).content)
            
            #Nos quedamos unicamente con la parte derecha del nombre del equipo
            team_left = web_match.find('h2', class_='s-Ltext-nc rlt-title gap-3 s-left').text.strip().split()[-1]
            team_right = web_match.find('h2', class_='s-Ltext-nc rlt-title gap-3 s-right').text.strip().split()[-1]
            
            #Recorremos jugadores TitHome,ResHome,TitAway,ResAway
            for jugadores in ['gap-3 s-left','gap-3 s-left s-mm-t','gap-3 s-right','gap-3 s-right s-mm-t']:
                equipo = team_left
                if 'right' in jugadores:
                    equipo = team_right
    
                for team in web_match.find_all('li', class_=jugadores):
                    for player in team.find_all('div', class_='cf'):
                        name = player.p.text.strip()
                        picas = player.div.text.count('punto')
                        if picas == 0 and player.div.text.count('-') == 0:
                            picas = -1
    
                        partido[name] = {'picas': picas, 'goles': 0, 'penalty': 0, 'd_amarilla': 0, 'roja': 0, 'equipo': equipo}
            
            #Recogemos los goles
            for lineas in web_match.find_all('section', class_='fld-ftr-section')[1:2]:
                for linea in lineas.find_all('li'):
                    name = linea.find('p', class_='s-inb-sm s-stext-nc s-stext-link-2').text.strip().replace("\n(p)","")
                    gol = len(linea.strong)
                    if linea.text.count('(p)'):
                        partido[name].update({'penalty': partido[name]['penalty']+gol})
                    elif '(p.p.)' not in linea.text:
                        partido[name].update({'goles': partido[name]['goles']+gol})
    
            #Buscamos los expulsados por roja directa o doble amarilla
            for lineas in re.findall('Expulsado:(.*)', web_match.text):
                try:
                    name = lineas.strip()
                    for red in web_match.find_all('strong', class_='cmt-red'):
                        if red.parent.text.title().count(name) and len(re.findall("[Aa][Mm][Aa][Rr][Ii][Ll][Ll][Aa]", red.parent.text)) and not partido[name]['roja']:
                            partido[name].update({'d_amarilla': 1})
                        elif red.parent.text.title().count(name) and not partido[name]['d_amarilla']:
                            partido[name].update({'roja': 1})
                except:
                    continue
            
            #Procesamos lo recogido
            for name,values in partido.items():
                try:
                    search_name = _check_exceptions(name,partido)
                    player = db.simple_query('SELECT pl.idp,pl.name,pl.position,cl.name FROM players pl, clubs cl WHERE cl.idcl=pl.idcl AND pl.name REGEXP ".*%s.*" AND cl.name LIKE "%%%s%%" ' % (search_name,values['equipo']))
                    if len(player) != 1:
                        player = db.simple_query('SELECT pl.idp,pl.name,pl.position,cl.name FROM players pl, clubs cl WHERE cl.idcl=pl.idcl AND pl.name REGEXP "%s" AND cl.name LIKE "%%%s%%" ' % (search_name,values['equipo']))
                        if len(player) != 1:
                            player = db.simple_query('SELECT pl.idp,pl.name,pl.position,cl.name FROM players pl, clubs cl WHERE cl.idcl=pl.idcl AND pl.name = "%s" AND cl.name LIKE "%%%s%%" ' % (search_name,values['equipo']))
                            if len(player) != 1:
                                # Pablo Hernández es "Hernández" en comunio
                                player = db.simple_query('SELECT pl.idp,pl.name,pl.position,cl.name FROM players pl, clubs cl WHERE cl.idcl=pl.idcl AND pl.name REGEXP "%s" AND cl.name LIKE "%%%s%%" ' % (search_name.split(" ")[1],values['equipo']))
                                if len(player) != 1:
                                    player = db.simple_query('SELECT pl.idp,pl.name,pl.position,cl.name FROM players pl, clubs cl WHERE cl.idcl=pl.idcl AND pl.name = "%s" AND cl.name LIKE "%%%s%%" ' % (search_name.split(" ")[0],values['equipo']))
                                    if len(player) != 1:
                                        print "No se ha podido recuperar de la base de datos el nombre del AS '%s' del '%s' " % (name,values['equipo'])
                                        continue
                            
                    points = _compute_points(position=player[0][2], partido=values)
                    db.commit_query('INSERT IGNORE INTO points (idp,idg,points) VALUES (%s,%s,%s)' % (player[0][0],id_gameday,points))
                except IndexError as e:
                    print "No se ha podido recuperar de la base de datos el nombre del AS '%s' del '%s' " % (name,values['equipo'])
                except Exception as e:
                    print 'Error:',e


def get_matches(incremental=True):
    ''' Obtiene todos los partidos del calendario'''
   
    calendario = bs4(requests.get(CALENDARIO, headers=headers).content)

    for jornada in calendario.find_all('div', class_='fecha-jor-cal'):
        n_jornada = re.search("Jornada ([0-9]+)", jornada.p.text).group(1)
        id_gameday = _get_gameday(n_jornada)
  
        for match in jornada.find_all('tr', itemtype='http://schema.org/SportsEvent'):
            clubs = match.find_all('td', itemtype='http://schema.org/SportsTeam')
            left_team = clubs[0].text.strip().split()[-1]
            left_team = db.simple_query('SELECT idcl FROM clubs WHERE name LIKE "%%%s%%" LIMIT 1' % left_team)[0][0]
            right_team = clubs[1].text.strip().split()[-1]
            right_team = db.simple_query('SELECT idcl FROM clubs WHERE name LIKE "%%%s%%" LIMIT 1' % right_team)[0][0]
            dia,hora = _translate_xml_date(match.time['content'])
            
            db.commit_query('INSERT INTO matches (idclh,idcla,idg,date,time) VALUES (%s,%s,%s,"%s","%s") \
                ON DUPLICATE KEY UPDATE date="%s",time="%s" ' % (left_team,right_team,id_gameday,dia,hora,dia,hora))
        
        print "Jornada %s guardada (idg:%s)" % (n_jornada, id_gameday)


def _translate_dates(dates):
    ''' Translates dates format'dd.mm' to 'yyyymmdd'
       @return: [[date,]]
    '''
    ret=list()
    last=0
    for dat in dates:
        if dat == '':
            # Si encontramos algún hueco repetimos valor
            ret.append(ret[-1])
            continue
        day = dat[:2]
        if int(day) < 10:
            day = '0'+day[1]
        if dat[6:] != '':
            # Cuando se recuperan fechas de Comuniazo
            month = {'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06','julio':'07','agosto':'08','septiembre':'09','octubre':'10','noviembre':'11','diciembre':'12'}[dat[6:]]
        else:
            # Fechas de Comunio
            month = dat[3:5] 
        year  = str(date.today().year-last)
        if month+day == '0101': 
            last=1

        ret.append(year+month+day)
    return ret


def _translate_AS_date(fecha):
    #D-21/12 17:00
    #weekday = fecha[0]
    dia = fecha[2:4]
    mes = fecha[5:7]
    hora = fecha[8:10]
    minu = fecha[11:13]
    return str(date.today().year)+mes+dia, hora+minu


def _translate_xml_date(fecha):
    #2014-08-23T19:00:00+02:00
    year = fecha[0:4]
    mes = fecha[5:7]
    dia = fecha[8:10]
    hora = fecha[11:13]
    minu = fecha[14:16]
    return year+mes+dia, hora+minu


def _days_wo_price(name):
    ''' Devuelve la cantidad de días que lleva un jugador sin actualizarse en la base de datos '''
    last_dates = db.simple_query('SELECT MAX(pr.date) FROM prices pr,players pl WHERE pr.idp=pl.idp AND pl.name="%s" LIMIT 1' % (name))
    res = 365

    for last_date in last_dates:
        try:
            a = date(int(last_date[0][:4]), int(last_date[0][4:6]), int(last_date[0][6:8]))
        except:
            continue
        res = (date.today()-a).days
        if res > 365:
            res = 365

    return res


def _array_days_wo_price(name):
    ''' Devuelve devuelve un array con las fechas de los precios que faltan '''
    last_date = db.simple_query('SELECT MAX(pr.date) FROM prices pr,players pl WHERE pr.idp=pl.idp AND pl.name="%s" LIMIT 1' % (name))[0][0]
    array_days_wo_price = list()
    if not last_date:
        last_date = (date.today() - timedelta(days=30)).strftime('%Y%m%d')
    last_date = date(int(last_date[:4]), int(last_date[4:6]), int(last_date[6:8]))
    diff = date.today() - last_date
    for i in range(diff.days):
        array_days_wo_price.append(str(last_date + timedelta(days=i+1)))
    
    return array_days_wo_price


def _array_days_wo_points(name):
    ''' Devuelve devuelve un array con las fechas de los puntos que faltan '''
    last_date = db.simple_query('SELECT MAX(po.date) FROM points po,players pl WHERE po.idp=pl.idp AND pl.name="%s" LIMIT 1' % (name))[0][0]
    array_days_wo_points = list()
    if len(last_date):
        last_date = date(int(last_date[:4]), int(last_date[4:6]), int(last_date[6:8]))
        diff = date.today() - last_date
        for i in range(diff.days):
            array_days_wo_points.append(str(last_date + timedelta(days=i+1)))
    else:
        array_days_wo_points
    
    return array_days_wo_points


def _compute_points(position,partido):
    points = partido['penalty'] * 3
    points += {-1:0,0:-2,1:2,2:6,3:10,4:14}[partido['picas']]
    points += partido['goles'] * position
    
    points -= partido['d_amarilla'] * 3
    points -= partido['roja'] * 6
    
    return points
    
    
def _check_exceptions(name,partido):
    #Mismo nombre mismo equipo
    if partido[name]['equipo'] == u'Levante' and name == u'Víctor':
        return 'V.*ctor Casades.*s'
    if partido[name]['equipo'] == u'Málaga' and (name == u'Samu' or name == u'Samuel'):
        return 'Samu Garc.*a'   
    if partido[name]['equipo'] == u'Valencia' and name == u'De Paul':
        return 'Rodrigo de Paul'
    if partido[name]['equipo'] == u'Atlético' and name == u'Saúl':
        return 'Sa.*l .*guez'
    
    #Sustitute "'ÁÉÍÓÚáéíóú.žã" por ".*", después nombres especiales porque AS no pone acentos en algunos
    name = re.sub(u'[\u0027\u00C1\u00C9\u00CD\u00D3\u00DA\u00E1\u00E9\u00ED\u00F3\u00FA\u002E\u017E\u00E3]', u'\u002E\u002A', name)

    #Especiales    
    name = re.sub(u'Javi', u'Javi\u002E\u002A', name)
    
    return {name:name, u'Simao':u'Sim.*o', u'Orban':u'Orb.*n', u'Cordoba':u'C.*rdoba', u'Diakit.*':u'Diakhit.*',
            u'Cebolla':u'Cristian Rodr.*guez', u'Moya':'Moy.*', u'Godin':'God.*n', u'Diego Godin':u'God.*n',
            u'Coentrao':u'Coentr.*o', u'Fede':u'Fede Cartabia', u'Florin Andone':u'Florin',
            u'Jony':u'Jonny', u'Pablo Hern.*ndez':u'Hern.*ndez', u'Fontas':u'Font.*s',
            u'Leo Baptistao':u'Leo Baptist.*o', u'Vintra':u'Vyntra', u'Victor Rodriguez':u'V.*ctor Rodr.*guez',
            u'Corominas':u'Coro'}[name]


def _month_num(month):
    return {'Ene':1,'Feb':2,'Mar':3,'Abr':4,'May':5,'Jun':6,'Jul':7,'Ago':8,'Sep':9,'Oct':10,'Nov':11,'Dic':12}[month]


def _get_gameday(n_jornada):
    idg = db.simple_query('SELECT idg FROM gamedays WHERE gameday="%s" AND season="%s"' % (n_jornada,SEASON))
    try:
        idg = idg[0][0]
    except IndexError:
        db.commit_query('INSERT INTO gamedays (gameday,season) VALUES ("%s","%s")' % (n_jornada,SEASON))
        idg = db.simple_query('SELECT idg FROM gamedays WHERE gameday="%s" AND season="%s" LIMIT 1' % (n_jornada,SEASON))[0][0]

    return idg


def _position_translation(position):
    return {'Torwart': 6,'Abwehr': 5,'Mittelfeld': 4,'Sturm': 3, 'Portero': 6, 'Defensa': 5, 'Centrocampista': 4, 'Delantero': 3}[position]


if __name__ == '__main__':
    main()
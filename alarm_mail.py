#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Busca en la base de datos para notificar los puntos
@author: jotacor
'''
# Import smtplib for the actual sending function
import db_tradunio as db
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import smtplib
from tabulate import tabulate

def main():
    sender = 'jotacor@buhardillaPC'
    receiver = 'javi.corbin@gmail.com'
    result = db.simple_query('SELECT pl.name as player,po.points,cl.name as club FROM points po, players pl, clubs cl WHERE po.idp=pl.idp AND pl.idcl=cl.idcl AND gameday = 7 AND (cl.idcl=6 OR cl.idcl=75)')

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = 'Resultados partido'
    
    if len(result) > 1:
        headers = [u'Nombre', u'Puntos', u'Club']
        players = list()
        for row in result:
            players.append([row[0],row[1],row[2]])
    msg.attach(MIMEText(tabulate(players, headers,tablefmt="rst"), 'plain','utf-8'))
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, receiver , msg.as_string())
    s.quit()


if __name__ == '__main__':
    main()

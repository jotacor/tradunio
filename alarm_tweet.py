#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ConfigParser
import re
import sqlite3
import sys
import os
import urllib
import threading
from twython import Twython
from lxml.html import *
from pyshorturl import Googl, GooglError
from twill import *
from twill.commands import *

config = ConfigParser.RawConfigParser()
config.read('/volume1/homes/admin/etc/config.twt')

u = [[]] * 5
minDisc = int(80)
maxDisc = int(100)

class myThread(threading.Thread):
	def __init__(self, idCamp, t, db):
		self.idCamp = idCamp
		self.t = t
		self.db = db
		self.b = connect_bv()
		threading.Thread.__init__(self)
	def run(self):
		#b = connect_bv()
		idsCat = getCats(self.idCamp, b)

		#Iterate all Cats from each Campaign
		for idCat in idsCat:
			idsLine = getLines(self.idCamp, idCat, b)
		
			#Iterate all Products from each Category from each Campaign
			for idLine in idsLine:
				if not existDisc(self.idCamp, idCat, idLine, minDisc, maxDisc, b):
					print '''Any discounts for Camp: %s, Cat: %s, Line: %s''' % (self.idCamp, idCat, idLine)
					continue
				idsProd = getProds(self.idCamp, idCat, idLine, b)
				for idProd in idsProd:
					tweetProds(self.idCamp, idCat, idLine, idProd, minDisc, maxDisc, b, self.t)
		sql = '''insert into visitedCamp values (%s)''' % (idCamp)
		print sql
		c = self.db.cursor()
		result = c.execute(sql)
		self.db.commit()
		print "########Ending thread camp:", self.idCamp

def user_config(username):
	u[0] = config.get(username, 'userId')
	u[1] = config.get(username, 'consumer_key')
	u[2] = config.get(username, 'consumer_secret')
	u[3] = config.get(username, 'access_token')
	u[4] = config.get(username, 'access_token_secret')

	return Twython(
		app_key = u[1],
		app_secret = u[2],
		oauth_token = u[3],
		oauth_token_secret = u[4]
	)

#Get all Campaign IDs
def getCamps(db):
	idsCamp = []
	b = connect_bv()
	html = b.get_html()
	p = re.compile('<a class="goshop" href="(.+)">')
	links = p.findall(html)
	p = re.compile('idCampaign=([0-9]*)')
	for num in links:
		idCamp = p.search(num).group(1)
		sql = '''select distinct(camp) from visitedCamp where camp=%s''' % (idCamp)
		#print sql
		campDB = db.execute(sql)
		if len(campDB.fetchall()) == 1:
			continue
		idsCamp.append(idCamp)
	return idsCamp
	
#Get all Categories from a Campaign
def getCats(idCamp):
	idsCat = []
	b.go('''http://es.buyvip.com/CampaignRegisterAction.bv?idCampaign=%s''' % (idCamp))
	html = b.get_html()
	p = re.compile('idCategory=([0-9]*)')
	links = p.findall(html)
	for link in links:
		idsCat.append(link)
	return idsCat

#Connect to BuyVip and return a browser
def connect_bv():
	b = get_browser()
	b.go('http://es.buyvip.com/CatalogAction.bv')
	fv("formLogin", "txtLoginEmail", "javi.corbin@gmail.com")
	fv("formLogin", "txtLoginPassword", "")
	b.submit('0')
	return b
	
#Get all Lines from a Category from a Campaign
def getLines(idCamp, idCat):
	idsLine = []
	b.go('''http://es.buyvip.com/CategoryAction.bv?idCampaign=%s&idCategory=%s''' % (idCamp, idCat))
	html = b.get_html()
	p = re.compile('idLine=(-?[0-9]*)')
	links = p.findall(html)
	for link in links:
		if idsLine.count(link) == 0:
			idsLine.append(link)
	return idsLine

#Get all Products from a Line, from a Category, from a Campaign
def getProds(idCamp, idCat, idLine):
	idsProd = []
	b.go('''http://es.buyvip.com/LineAction.bv?idCampaign=%s&idCategory=%s&idLine=%s''' % (idCamp, idCat, idLine))
	html = b.get_html()
	p = re.compile('idProduct=([0-9]*)')
	links = p.findall(html)
	link_ant = ""
	for link in links:
		if link == link_ant:
			continue
		idsProd.append(link)
		link_ant = link
	return idsProd
	
#Check if in this Line there is discounts > minDisc
def existDisc(idCamp, idCat, idLine, minDisc, maxDisc):
	b.go('''http://es.buyvip.com/LineAction.bv?idCampaign=%s&idCategory=%s&idLine=%s''' % (idCamp, idCat, idLine))
	p = re.compile('class="discount">(.*[0-9]*)')
	html = b.get_html()
	discs = p.findall(html)
	for disc in discs:
		if int(disc) > minDisc and int(disc) < maxDisc:
			return True
		else:
			return False
                        
def replaceNonAscii(s):
	ret = "".join(i for i in s if ord(i)<128)
	ret = ret.replace('&amp;', '&')
	ret = ret.replace('La boutique del ', '')
	return ret 

def tweetProds(idCamp, idCat, idLine, idProd, minDisc, maxDisc, t):
	b.go('''http://es.buyvip.com/ProductAction.bv?idCampaign=%s&idCategory=%s&idLine=%s&idProduct=%s''' % (idCamp, idCat, idLine, idProd))
	html = b.get_html()
	try:	
		prodNoAvail = re.search('SelectedWaitingList.bv\?idCampaign=([0-9]*)&idCategory=([0-9]*)&idLine=(-?[0-9]*)&idProduct=([0-9]*)', html).group(4)
		print "No avail (SelectedWaitings):", prodNoAvail
		print "############"
		return 1
	except:
		print "Available..."
		pass	
	prices = re.findall('[0-9]*,[0-9]{2}', html)
	actualPrice = float(prices[0].replace(",", "."))
	realPrice = float(prices[1].replace(",", "."))
	dto = float((realPrice - actualPrice) / realPrice * 100)
	print "...and discount??"
	if dto > minDisc and dto < maxDisc:
		#Get sizes if any
		#TODO
		print "...YESSSS!!!"	
		nameBrand = re.search('''idCampaign=%s">(.*)&raquo;''' % (idCamp), html.replace("\n", "")).group(1)
		nameBrand = replaceNonAscii(nameBrand.split('<')[0].strip())[:15]
		nameProd = re.search('<h3>(.*)</h3>', html).group(1)
		nameProd = replaceNonAscii(nameProd)[:50]
		g = Googl()
		shortedurl = g.shorten_url('''http://es.buyvip.com/ProductAction.bv?idCampaign=%s&idCategory=%s&idLine=%s&idProduct=%s''' % (idCamp, idCat, idLine, idProd))
		imageUrl = re.search('http://static(.*).jpg', html).group(0)
		nameImage = idCamp+"_"+idCat+"_"+idLine+"_"+idProd+".jpg"
		#urllib.urlretrieve(imageUrl, nameImage)
		
		#print nameBrand
		#print nameProd
		#print actualPrice
		#print realPrice
		#print dto
		#print shortedurl 
		
		tweet = '''%s | %s | %.2fe/%.2fe | %.0f%%dto | %s | ''' % (nameBrand, nameProd, actualPrice, realPrice, dto, shortedurl)	
		try:
			#t.PostUpdate(tweet)
			#t.updateStatusWithMedia(nameImage, status=tweet)
			print nameImage
			print tweet
			#os.remove(nameImage)
			print "############"
		except:
			print "Exception: Cannot post tweet"
			#f = open('/volume1/homes/admin/logs/buyvip70.log', 'a')
			#f.write(tweet+"\n")
			#err = sys.exc_info()[1].message
			#err = err+"\n#####\n"
			#f.write(err)
			#f.close()
			pass
	else:
		print "NOOOO :("
		print "############"

def main():
	#minDisc = int(70)
	#maxDisc = int(100)
	#b = connect_bv()
	db = sqlite3.Connection(':memory:')
	c = db.cursor()
	c.execute('create table visitedCamp(camp)')
	db.commit()
	#redirect_output('/dev/null')
	idsCamp = getCamps(db)
	t = user_config('BuyVipDtos70')
	threads = []
	#Iterate all Campaigns
	for idCamp in idsCamp:
		thread = myThread(idCamp, t, db)
		thread.start()
		threads.append(thread)
		print "Thread %s created" %(idCamp)
	
	print "Now waiting for all them"
	for j in threads:
		j.join()
	print "Exiting"		
	c.close()			
	
if __name__ == "__main__":
	main()

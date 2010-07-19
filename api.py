# coding=utf8

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson as json

from google.appengine.ext import db

import models, errors, settings

class UserWishesList(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'application/json'
		wishlist_user_name = self.request.get('user', None)
		wishes = []
		
		if wishlist_user_name != None:
			wishlist_user = db.GqlQuery('SELECT * FROM User WHERE user = USER(:1)', wishlist_user_name).get()
			if wishlist_user != None:
				wishes = [ {'wish': w.wish, 'date': w.date.strftime('%H:%M %d/%m/%Y'), 'promises_count': len(w.promised_by)} for w in db.Query(models.UserWish).filter('owner', wishlist_user).order('-date').fetch(settings.MAX_WISHES) ]
		
		self.response.out.write(json.dumps(wishes))
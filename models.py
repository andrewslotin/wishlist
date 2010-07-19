# coding=utf8

from google.appengine.api import users
from google.appengine.ext import db

class User(db.Model):
    user = db.UserProperty()
    
    def promises(self):
        return db.Query(UserWish).filter('promised_by', self.user)

class UserWish(db.Model):
    owner = db.ReferenceProperty(User)
    wish = db.StringProperty(multiline = True)
    date = db.DateTimeProperty(auto_now_add = True)
    promised_by = db.ListProperty(db.Key)
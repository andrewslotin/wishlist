# coding=utf8

import os

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import models, errors, settings, api

class ProtectedPage(webapp.RequestHandler):
    def __init__(self):
        webapp.RequestHandler.__init__(self)
        self._user = users.get_current_user()
        self._template_values = {
            'current_user': self._user,
            'is_admin':     users.is_current_user_admin()
        }

class MainPage(ProtectedPage):
    def get(self):
        self._template_values.update({
            'users':       [ w.user for w in models.User.all() if w.user != self._user ],
            'signin_url':  users.create_login_url(self.request.uri),
            'signout_url': users.create_logout_url(self.request.uri)
        })
        
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, self._template_values))

class WishlistPage(ProtectedPage):
    def get(self):
        wishlist_user = None
        wishlist_user_name = self.request.get('user', None)
        if wishlist_user_name == None:
            if self._user:
                wishlist_user_name = self._user.email()
            else:
                self.redirect('/')
                return
        
        if wishlist_user_name:
            try:
                wishlist_user = db.GqlQuery('SELECT * FROM User WHERE user = USER(:1)', wishlist_user_name).get()
                current_user_key = self._user and db.GqlQuery('SELECT __key__ FROM User WHERE user = :1', self._user).get() or None
                is_owner = (wishlist_user == None and wishlist_user_name == self._user.email()) or (wishlist_user.user == self._user)
                
                wishes = db.Query(models.UserWish).filter('owner', wishlist_user).order('-date').fetch(settings.MAX_WISHES)
                
                self._template_values.update({
                    'is_owner':      is_owner,
                    'wishlist_user': wishlist_user,
                    'wishes':        [ {
                                        'key':      w.key(), 
                                        'wish':     w.wish, 
                                        'date':     w.date.strftime('%H:%M %d/%m/%Y'),
                                        'promises_count': len(w.promised_by),
                                        'promised': current_user_key and current_user_key in w.promised_by
                                       } for w in wishes ],
                    'signin_url':   users.create_login_url(self.request.uri),
                    'signout_url':  users.create_logout_url(self.request.uri)
                })
                
                path = os.path.join(os.path.dirname(__file__), 'wishlist.html')
                self.response.out.write(template.render(path, self._template_values))
            except users.UserNotFoundError:
                self.response.out.write('Такого пользователя нет.')
        
    
    def post(self):
        try:
            user = models.User.gql('WHERE user = :1', self._user).get()
            
            if user == None:
                user = models.User( user = self._user )
                user.put()
            
            if user:
                if models.UserWish.gql('WHERE owner=:1', user).count(settings.MAX_WISHES) < settings.MAX_WISHES:
                    new_wish = models.UserWish(
                                        owner = user,
                                        wish = self.request.get('new_wish', '').strip()
                                       )
                    
                    if len(new_wish.wish): new_wish.put()
                    self.redirect(self.request.uri)
                else:
                    raise errors.TooMuchWishesError()
        except errors.TooMuchWishesError, e: 
            self.response.out.write(e)

class RemoveWishPage(ProtectedPage):
    def get(self):
        try:
            wish_key = self.request.get('wish', None)
            if not wish_key:
                self.redirect('/')
                return
            
            wish = db.get(wish_key)
            if wish.owner.user !=  self._user:
                raise Exception('Это не ваше желание.')
            
            wish.delete()
            self.redirect('/wishlist')
        except Exception, e:
            self.response.out.write(e)

class UserPromisesPage(ProtectedPage):
    def get(self):
        if not self._user:
            self.redirect('/')
        else:
            current_user_key = self._user and db.GqlQuery('SELECT __key__ FROM User WHERE user = :1', self._user).get() or None
            
            if current_user_key:
                self._template_values.update({
                    'promises':    db.Query(UserWish).filter('promised_by', current_user_key).fetch(settings.MAX_PROMISES),
                    'signin_url':  users.create_login_url(self.request.uri),
                    'signout_url': users.create_logout_url(self.request.uri)
                })
            
            path = os.path.join(os.path.dirname(__file__), 'promises.html')
            self.response.out.write(template.render(path, self._template_values))

class PromisePage(ProtectedPage):
    def get(self):
        if not self._user:
            self.redirect('/')
            return
            
        try:
            user = models.User.gql('WHERE user = :1', self._user).get()
            
            if user == None:
                user = models.User( user=self._user )
                user.put()
            else:
                if user.promises().count() >= settings.MAX_PROMISES:
                    raise errors.TooMuchPromisesError()
            
            wish = None
            wish_id = self.request.get('wish')
            if wish_id:
                wish = db.get(wish_id)
            
            if wish:
                if user.key() not in wish.promised_by:
                    wish.promised_by.append(user.key())
                else:
                    del wish.promised_by[wish.promised_by.index(user.key())]
                wish.put()
                self.redirect('/wishlist?user=%s' % wish.owner.user.email())
            else:
                self.response.out.write(wish and 'Вы уже обещали выполнить это пожелание' or 'Таких желаний ни у кого не возникало')
        except errors.TooMuchPromisesError, e:
            self.response.out.write(e)

class DumpPage(ProtectedPage):
    def get(self):
        if not (self._user and users.is_current_user_admin()):
            self.redirect('/')
            return
        
        self.response.headers['Content-Type'] = 'text/plain'
        
        self.response.out.write('Users:\n')
        registered_users = models.User.all()
        field_size = {
            'key':  max( [ len(str(u.key())) for u in registered_users ] ),
            'user': max( [ len(str(u.user)) for u in registered_users ] )
        }
        for u in registered_users:
            self.response.out.write("| %s | %s |\n" % (
                str(u.key()).ljust(field_size['key']), 
                str(u.user).ljust(field_size['user'])
            ))
        self.response.out.write('\n')
        
        self.response.out.write('Wishes:\n')
        wishes = models.UserWish.all()
        field_size = {
            'owner': max( [ w.owner and len(str(w.owner.user)) or 0 for w in wishes ] ),
            'wish':  max( [ len(w.wish) for w in wishes ] ),
            'date':  26
        }
        for w in wishes:
            self.response.out.write("| %s | %s | %s | %s |\n" % (
                str(w.owner and w.owner.user or None).ljust(field_size['owner']), 
                w.wish.ljust(field_size['wish']), 
                str(w.date).ljust(field_size['date']), 
                ', '.join([ str(k) for k in w.promised_by] )
            ))
        self.response.out.write('\n')

application = webapp.WSGIApplication(
                                     [
                                        ('/', MainPage), 
                                        ('/wishlist', WishlistPage), 
                                        ('/remove', RemoveWishPage), 
                                        ('/promise', PromisePage), 
                                        ('/revoke', PromisePage),
                                        ('/promises', UserPromisesPage),
                                        ('/dump', DumpPage),
										# RPC
										('/api/wishes', api.UserWishesList)
                                    ],
                                     debug=True
                                    )

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

import datetime
import logging
import os
import StringIO
import time
import wsgiref.handlers

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import minifb

import accounts
import hash
import mailer
import quotes
import system
import web

class FacebookSupport:
  def __init__(self, handler):
    minifb.urllib2.urlopen = urlopenWrapper
    self.handler = handler
    session = handler.session
    sys = system.getSystem()
    self.fb_api_key = sys.facebook_api_key
    self.fb_secret = sys.facebook_secret
    if not self.fb_api_key or not self.fb_secret:
      self.valid = False
      logging.info('facebook API key and secret not defined!')
      return
    args = minifb.validate(self.fb_secret, self.handler.request.POST)
    self.fb_auth_token = args.get('auth_token')
    u = getattr(session, 'facebook_user', 0)
    session.facebook_user = long(args.get('user', u))
    k = getattr(session, 'facebook_session_key', '')
    session.facebook_session_key = args.get('session_key', k)
    if session.facebook_user:
      self.valid = True
      logging.info('facebook_user = %r', session.facebook_user)
      account = accounts.Account.getByFacebookId(session.facebook_user)
      if account:
        logging.info('Logging in via facebook id: %s', account.name)
        self.handler.setAccount(account)
      else:
        account = self.handler.account
        if account.trusted and account.facebook_id is None:
          logging.info('Already logged in as: %s', account.name)
          account.facebook_id = session.facebook_user
    else:
      self.valid = False
      logging.info('failed to validate, args: %r', args)
      logging.info('fsk: %r', getattr(session, 'facebook_session_key'))
    session.put()

  def __call__(self, method, **kwargs):
    session = self.handler.session
    if not hasattr(session, 'facebook_session_key'):
      if not self.fb_auth_token:
        result = minifb.call('facebook.auth.createToken',
                             self.fb_api_key, self.fb_secret)
        self.fb_auth_token = result
      result = minifb.call('facebook.auth.getSession',
                           self.fb_api_key, self.fb_secret,
                           auth_token=self.fb_auth_token)
      session.facebook_session_key = db.String(result['session_key'])
    logging.info('API key = %r, secret = %r', self.fb_api_key, self.fb_secret)
    logging.info('session key = %r', session.facebook_session_key)
    logging.info('kwargs: %r', kwargs)
    return minifb.call(method, self.fb_api_key, self.fb_secret, call_id=False,
                       session_key=session.facebook_session_key, **kwargs)


class FacebookPage(web.TemplatePage):
  path = 'facebook/index.html'

  def loadSession(self):
    web.TemplatePage.loadSession(self)
    self.facebook = FacebookSupport(self)

  def callFB(self, method, **kwargs):
    return self.facebook(method, **kwargs)

  def handlePost(self):
    pass


class LinkAccountPage(FacebookPage):
  path = 'facebook/link-account.html'

  def handlePost(self):
    if self.request.get('new'):
      self.new()
      return
    name = self.request.get('name')
    password = self.request.get('password')
    self['name'] = name
    if name and password:
      self.link(name, password)

  def new(self):
    if not self.session.facebook_user:
      return
    userinfo = self.callFB('facebook.users.getInfo',
                           fields='name',
                           uids=self.session.facebook_user,
                          )
    name = userinfo[0]['name']

    # TODO: handle collisions
    logging.info('Creating facebook account for %s (%r)',
                 name, self.session.facebook_user)
    account = accounts.Account.create(name='facebook:%s' % name,
                                      email='facebook:%s' % self.session.facebook_user,
                                      facebook_id=self.session.facebook_user,
                                     )
    self.setAccount(account)

  def link(self, name, password):
    try:
      logging.info('logging in potential FB user: %s', name)
      account = accounts.Account.login(name, password)
    except accounts.NoSuchNameException:
      self['error'] = 'Invalid account name'
    except accounts.InvalidPasswordException:
      self['error'] = 'Password incorrect'
    except accounts.NotActivatedException:
      self['error'] = 'Account not activated'
      self['activate'] = True
    else:
      if self.session.facebook_user:
        logging.info('linking %s to %d', account.name, self.session.facebook_user)
        account.facebook_id = self.session.facebook_user
        account.put()
        self.setAccount(account)


def urlopenWrapper(url, args):
  logging.info('opening: %r, %r', url, args)
  response = urlfetch.fetch(url, args, method=urlfetch.POST, headers={'Content-type': 'application/x-www-form-urlencoded'})
  logging.info('response.content:\n%s', response.content)
  return StringIO.StringIO(response.content)


def main():
  pages = [
    ('/facebook/link-account', LinkAccountPage),
    ('/facebook/', FacebookPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

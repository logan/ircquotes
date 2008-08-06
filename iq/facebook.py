import datetime
import logging
import os
import StringIO
import time
import wsgiref.handlers

from louie import dispatcher

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import minifb

import accounts
import hash
import mailer
import quotes
import service
import system

def facebook(path, **kwargs):
  tpath = os.path.join('templates', 'facebook', path)
  service_dec = service.service(**kwargs)
  def decorator(f):
    f = service_dec(f)
    def wrapper(self):
      def pre_hook():
        self.facebook = FacebookSupport(self)
      tmpl = service.Template()
      f(self, template=tmpl, pre_hook=pre_hook)
      self.response.out.write(template.render(tpath, tmpl.__dict__, debug=True))
    return wrapper
  return decorator


class FacebookSupport:
  def __init__(self, handler):
    # minifb uses urllib2, but only urlfetch is available to us
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
      dispatcher.connect(receiver=self.reportAction, sender=system.record)
      account = accounts.Account.getById('facebook/%d' % session.facebook_user)
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
    #session.put()

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

  def reportAction(self, action):
    reporter = getattr(self, 'report_%s' % action.verb, None)
    if callable(reporter):
      logging.info('[FB]: publishing %r action: %s', action.verb, action)
      reporter(action)

  def report_publish(self, action):
    quote = action.targets[0]
    self.facebook('feed.publishTemplatizedAction',
                  title_template='{actor} added a'
                                 ' <a href="{app}/quote?key={quote}">quote</a>'
                                 ' to <a href="{app}">IrcQuotes</a>',
                  title_data={'app': self.handler.request.application_url,
                              'quote': str(quote.key()),
                             },
                  # XXX: facebook doesn't like any of the JSON encodings I tried
                  format='XML',
                 )


class LinkAccountPage(service.LoginService):
  @facebook('link-account.html')
  def post(self):
    if self.request.get('new'):
      return self.new()
    if self.request.get('unlink'):
      return self.unlink()
    if self.login():
      self.link()

  def unlink(self):
    self.account.facebook_id = None
    self.account.put()
    self.setAccount(accounts.Account.getAnonymous())

  def new(self):
    if not self.facebook.valid:
      return
    userinfo = self.facebook('facebook.users.getInfo',
                             fields='name',
                             uids=self.session.facebook_user,
                            )
    name = userinfo[0]['name']

    # TODO: Support different account namespaces
    logging.info('Creating facebook account for %s (%r)',
                 name, self.session.facebook_user)
    account = accounts.Account.createFacebook(name, self.session.facebook_user)
    self.setAccount(account)

  def link(self):
    name = self.request.get('name')
    password = self.request.get('password')
    try:
      logging.info('logging in potential FB user: %s', name)
      account = accounts.Account.login(name, password)
    except accounts.AccountException, e:
      self.template.exception = e
    else:
      if self.session.facebook_user:
        logging.info('linking %s to %d', account.name, self.session.facebook_user)
        account.facebook_id = self.session.facebook_user
        account.put()
        self.setAccount(account)


class IndexPage(service.Service):
  @facebook('index.html')
  def post(self):
    pass


def urlopenWrapper(url, args):
  logging.info('opening: %r, %r', url, args)
  response = urlfetch.fetch(url, args, method=urlfetch.POST, headers={'Content-type': 'application/x-www-form-urlencoded'})
  logging.info('response.content:\n%s', response.content)
  return StringIO.StringIO(response.content)


def main():
  pages = [
    ('/facebook/link-account', LinkAccountPage),
    ('/facebook/', IndexPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

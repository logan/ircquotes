import datetime
import logging
import os
import time
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import accounts
import hash
import quotes

class TemplateHandler(webapp.RequestHandler):
  def __init__(self, *args, **kwargs):
    webapp.RequestHandler.__init__(self, *args, **kwargs)
    self.variables = {}

  def handleMethod(self, method):
    handler = getattr(self, 'handle%s' % method, None)
    if not callable(handler):
      self.response.set_status(405)
      return
    self.loadSession()
    handler()
    self.exportSession()
    self.render()

  def get(self):
    self.handleMethod('Get')

  def post(self):
    self.handleMethod('Post')

  def setCookie(self, name, value, path='/', expires=None):
    if expires is None:
      expires = datetime.timedelta(days=14)
    expire_time = datetime.datetime.now() + expires
    expire_str = expire_time.strftime('%a, %d %b %Y')
    cookie_str = '%s=%s; path=%s; expires=%s' % (name, value, path, expire_str)
    self.response.headers.add_header('Set-Cookie', cookie_str)

  def generateSessionId(self):
    return 's%s' % hash.generate()

  def setAccount(self, account):
    self.session.account = account
    self['account'] = self.session.account

  def loadSession(self):
    accounts.Session.expireAll()
    if 'session' in self.request.cookies:
      session_id = self.request.cookies['session']
    else:
      session_id = self.generateSessionId()
      self.setCookie('session', session_id)
    self.session = accounts.Session.load(session_id)

  def exportSession(self):
    self.session.put()
    if self.session.account:
      self.session.account.put()
    self['session'] = self.session
    if self.session.account:
      self['account'] = self.session.account

  def __setitem__(self, name, value):
    self.variables[name] = value

  def __getitem__(self, name):
    return self.variables[name]

  def __delitem__(self, name):
    del self.variables[name]

  def render(self):
    path = os.path.join(os.path.dirname(__file__), 'templates', self.path)
    self.response.out.write(template.render(path, self.variables))
    

class IndexPage(TemplateHandler):
  path = 'index.html'

  def handleGet(self):
    offset = 0
    try:
      offset = int(self.request.get('offset'))
    except ValueError:
      pass
    limit = 20
    qs = quotes.Quote.all().fetch(offset=offset, limit=limit)
    self['quotes'] = qs
    self['start'] = offset + 1
    self['end'] = offset + limit
    self['limit'] = limit


class BrowsePage(TemplateHandler):
  PAGE_SIZE = 10

  path = 'browse.html'

  def handleGet(self):
    self.page_size = BrowsePage.PAGE_SIZE
    self['limit'] = self.page_size
    self['mode'] = self.mode
    self['quotes'] = self.getQuotes()


class BrowseRecentPage(BrowsePage):
  mode = 'recent'

  def getQuotes(self):
    start = None
    try:
      start = int(self.request.get('start'))
    except ValueError:
      pass
    offset = 0
    try:
      offset = int(self.request.get('offset'))
    except ValueError:
      pass
    query = quotes.Quote.all()
    if start is not None:
      logging.info('submitted <= %s', start)
      query.filter('submitted <=', datetime.datetime.utcfromtimestamp(start))
    query.order('-submitted')
    qs = query.fetch(offset=offset, limit=self.page_size)
    if len(qs) == self.page_size:
      for i in xrange(2, self.page_size + 1):
        if qs[-i].submitted != qs[-1].submitted:
          break
      self['next_start'] = int(time.mktime(qs[-1].submitted.utctimetuple()))
      self['next_offset'] = i - 1
    else:
      self['end'] = True
    return qs


class LoginPage(TemplateHandler):
  path = 'login.html'

  def handleGet(self):
    self.session.url_on_login = self.request.get('url')

  def handlePost(self):
    name = self.request.get('name')
    password = self.request.get('password')
    try:
      account = accounts.Account.login(name, password)
      if account:
        self.setAccount(account)
    except accounts.Account.NoSuchNameException:
      self['error'] = 'invalid account name'
    except accounts.Account.InvalidPasswordException:
      self['error'] = 'password incorrect'
    except accounts.Account.NotActivatedException:
      accounts.Account.setupActivation(name, self.session.url_on_login)
      self['error'] = 'account not activated'
      self['activate'] = True
      self['name'] = name


class LogoutPage(TemplateHandler):
  path = 'logout.html'

  def handleGet(self):
    self.session.account = None
    self.redirect('/')


class ActivationPage(TemplateHandler):
  path = 'activate.html'

  def handleGet(self):
    name = self.request.get('name')
    account = accounts.Account.getByName(name)
    self['account'] = account
    if account:
      logging.info("Account to activate: %s/%r", account.name, account.activation)
    activation = self.request.get('activation')
    if account and account.activation == activation:
      self['authenticated'] = True
    if self.request.get('send_email'):
      if account:
        self['email_sent'] = True
        account.sendConfirmationEmail()

  def handlePost(self):
    name = self.request.get('name')
    account = accounts.Account.getByName(name)
    self['account'] = account
    activation = self.request.get('activation')
    if account and account.activation == activation:
      self['authenticated'] = True
      password = self.request.get('password')
      password_confirmation = self.request.get('password2')
      logging.info("checking password")
      if password and password == password_confirmation:
        logging.info("account activated!")
        account.activation = None
        account.password = password
        account.put()
        self.setAccount(account)
        self['activated'] = True
        return
      elif password != password_confirmation:
        logging.info("passwords didn't match")
        self['error'] = 'Passwords did not match'
      else:
        logging.info("no password given")
        self['error'] = 'Please choose a password'
    else:
      logging.info("password form lost activation code!")


class DebugPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-type'] = 'text/plain'
    print >> self.response.out, "Cookies:\n"
    for name, value in self.request.cookies.iteritems():
      print >> self.response.out, "  %s: %r" % (name, value)
    print >> self.response.out, "\nEnvironment:\n"
    for name, value in self.request.environ.iteritems():
      print >> self.response.out, "  %s: %r" % (name, value)
    

def main():
  pages = [
    ('/', BrowseRecentPage),
    ('/activate', ActivationPage),
    ('/browse-recent', BrowseRecentPage),
    ('/debug', DebugPage),
    ('/login', LoginPage),
    ('/logout', LogoutPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

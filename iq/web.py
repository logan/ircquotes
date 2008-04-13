import datetime
import logging
import md5
import os
import time
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

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
    # TODO: Make session ID generation more random
    digester = md5.new()
    digester.update(str(time.time()))
    digester.update(self.request.environ['REMOTE_ADDR'])
    return 's%s' % digester.hexdigest()

  def loadSession(self):
    quotes.Session.expireAll()
    if 'session' in self.request.cookies:
      session_id = self.request.cookies['session']
    else:
      session_id = self.generateSessionId()
      self.setCookie('session', session_id)
    self.session = quotes.Session.load(session_id)

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
    pass


class LoginPage(TemplateHandler):
  path = 'login.html'

  def handleGet(self):
    self.session.url_on_login = self.request.get('url')

  def handlePost(self):
    name = self.request.get('name')
    password = self.request.get('password')
    try:
      self.session.account = quotes.Account.login(name, password)
    except quotes.Account.NoSuchNameException:
      self['error'] = 'invalid account name'
    except quotes.Account.InvalidPasswordException:
      self['error'] = 'password incorrect'


class LogoutPage(TemplateHandler):
  path = 'logout.html'

  def handleGet(self):
    self.session.account = None
    self.redirect('/')


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
    ('/', IndexPage),
    ('/debug', DebugPage),
    ('/login', LoginPage),
    ('/logout', LogoutPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

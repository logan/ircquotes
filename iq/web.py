import datetime
import logging
import os
import time
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template

import accounts
import hash
import quotes
import mailer

class TemplateHandler(webapp.RequestHandler):
  anonymous = True

  def __init__(self, *args, **kwargs):
    webapp.RequestHandler.__init__(self, *args, **kwargs)
    self.variables = {}

  def handleMethod(self, method):
    if self.inTestingMode():
      self.mailer = mailer.TestingModeMailer()
      self['mailer'] = self.mailer
      self['testing'] = True
    else:
      self.mailer = mailer.ProductionModeMailer()
    handler = getattr(self, 'handle%s' % method, None)
    if not callable(handler):
      self.response.set_status(405)
      return
    self.loadSession()
    if not self.anonymous and not self.account.trusted:
      self.response.set_status(403)
      return
    handler()
    self['request'] = self.request
    self.exportSession()
    self.render()

  def get(self):
    self.handleMethod('Get')

  def post(self):
    self.handleMethod('Post')

  def inTestingMode(self):
    if self.request.environ['SERVER_SOFTWARE'].startswith('Dev'):
      return True
    return self.request.host.startswith('iq-test')

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
    logging.info('Setting account to: %s', account.name)
    self.session.account = account
    self.account = account
    self['account'] = self.session.account

  def loadSession(self):
    accounts.Session.expireAll()
    if 'session' in self.request.cookies:
      session_id = self.request.cookies['session']
    else:
      session_id = self.generateSessionId()
      self.setCookie('session', session_id)
    self.session = accounts.Session.load(session_id)
    self.account = self.session.account
    if self.account.trusted:
      self.account.put()

  def exportSession(self):
    self.session.put()
    self['session'] = self.session
    self['account'] = self.account

  def __setitem__(self, name, value):
    self.variables[name] = value

  def __getitem__(self, name):
    return self.variables[name]

  def __delitem__(self, name):
    del self.variables[name]

  def render(self):
    path = os.path.join('templates', self.path)
    self.response.out.write(template.render(path, self.variables, debug=True))
    

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
      start_ts = int(self.request.get('start'))
      start = datetime.datetime.utcfromtimestamp(start_ts)
    except ValueError:
      pass
    offset = 0
    try:
      offset = int(self.request.get('offset'))
    except ValueError:
      pass
    qs = quotes.Quote.getRecentQuotes(start=start,
                                      offset=offset,
                                      limit=self.page_size,
                                     )
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
    except accounts.NoSuchNameException:
      self['error'] = 'invalid account name'
    except accounts.InvalidPasswordException:
      self['error'] = 'password incorrect'
    except accounts.NotActivatedException:
      self['error'] = 'account not activated'
      self['activate'] = True
      self['name'] = name


class LogoutPage(TemplateHandler):
  path = 'logout.html'

  def handleGet(self):
    self.setAccount(accounts.Account.getAnonymous())
    self.redirect(self.request.get('url', '/'))


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
        self['url'] = account.activation_url
        return
      elif password != password_confirmation:
        logging.info("passwords didn't match")
        self['error'] = 'Passwords did not match'
      else:
        logging.info("no password given")
        self['error'] = 'Please choose a password'
    else:
      logging.info("password form lost activation code!")


class CreateAccountPage(TemplateHandler):
  path = 'create-account.html'

  def handleGet(self):
    self['url'] = self.request.get('url')

  def handlePost(self):
    errors = []
    url = self.request.get('url')
    self['url'] = url
    name = self.request.get('name')
    email = self.request.get('email')
    ok = name and email
    if name:
      self['name'] = name
      account = accounts.Account.getByName(name)
      if account:
        self['name_conflict'] = account
        ok = False
      else:
        try:
          accounts.Account.validateName(name)
        except accounts.InvalidName, e:
          self['name_error'] = e.message
          ok = False
    elif email:
      self['name_needed'] = True
    if email:
      self['email'] = email
      account = accounts.Account.getByEmail(email)
      if account:
        self['email_conflict'] = account
        ok = False
      else:
        try:
          accounts.Account.validateEmail(email)
        except accounts.InvalidEmail, e:
          self['email_error'] = e.message
          ok = False
    elif name:
      self['email_needed'] = True
    if ok:
      account = accounts.Account.create(name, email)
      account.setupActivation(self.mailer, self.request.application_url, url)
      self.setAccount(account)


class SubmitPage(TemplateHandler):
  anonymous = False
  path = 'submit.html'

  def handleGet(self):
    pass

  def handlePost(self):
    dialog = self.request.get('dialog').strip()
    if not dialog:
      return
    draft = quotes.Quote.createDraft(self.account, dialog)
    logging.info("Created draft: key=%s", draft.key())
    self.redirect('/edit-draft?quote=%s' % draft.key())


class EditDraftPage(TemplateHandler):
  anonymous = False
  path = 'edit-draft.html'

  def getDraft(self):
    key = self.request.get('quote')
    self['key'] = key
    logging.info('Fetching draft by key: %s', key)
    draft = quotes.Quote.get(key)
    if draft and draft.draft and draft.parent_key() == self.account.key():
      self['draft'] = draft
      self['quote'] = draft
      return draft
    return None

  def handleGet(self):
    self.getDraft()

  def handlePost(self):
    draft = self.getDraft()
    if not draft:
      return
    self['draft'] = draft
    self['quote'] = draft
    dialog = self.request.get('dialog').strip()
    if self.request.get('save'):
      draft.update(dialog=dialog)
    elif self.request.get('discard'):
      draft.delete()
      # TODO: What should the result of draft deletion be?
      self.redirect('/')
    elif self.request.get('publish'):
      quote = draft.publish()
      self.redirect('/quote?key=%s' % quote.key())


class QuotePage(TemplateHandler):
  path = 'quote.html'

  def handleGet(self):
    quote = quotes.Quote.getPublishedQuote(self.request.get('key'))
    if quote is None:
      self.response.set_status(404)
      return
    self['quote'] = quote


class DebugPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-type'] = 'text/plain'
    print >> self.response.out, "Cookies:\n"
    for name, value in self.request.cookies.iteritems():
      print >> self.response.out, "  %s: %r" % (name, value)
    print >> self.response.out, "\nEnvironment:\n"
    for name, value in self.request.environ.iteritems():
      print >> self.response.out, "  %s: %r" % (name, value)


class ClearDataStorePage(webapp.RequestHandler):
  @staticmethod
  def deleteAllKindEntities(kind, batch_size):
    logging.info('Deleting all of a kind: %r', kind)
    query = kind.all().fetch(limit=batch_size)
    i = 0
    for i, entity in enumerate(query):
      logging.info("  Deleting %s %s", kind, i)
      entity.delete()
    return i + 1 == batch_size

  def get(self):
    batch_size = 20
    if not self.request.get('worker'):
      return self.start()
    kind = self.request.get('kind')
    counter = 0
    try:
      counter = int(self.request.get('counter'))
    except ValueError:
      pass
    modules = [accounts, quotes]
    for module in modules:
      for value in module.__dict__.itervalues():
        if isinstance(value, type) and issubclass(value, db.Model):
          if self.deleteAllKindEntities(value, batch_size):
            if value.__name__ != kind:
              counter = 0
            self.continuation(value.__name__, counter + batch_size)
            return
    self.response.headers['Content-type'] = 'text/plain'
    print >> self.response.out, "Cleared the data store!"

  def start(self):
    out = self.response.out
    print >> out, '<html>'
    print >> out, '<body>'
    print >> out, '<span id="m">&nbsp;</span>'
    print >> out, '<iframe src="/clear-data-store?worker=1"></iframe>'
    print >> out, '</body>'
    print >> out, '</html>'

  def continuation(self, culprit, counter):
    out = self.response.out
    print >> out, '<html>'
    print >> out, '<body>Still working on %s...</body>' % culprit
    print >> out, '<script>'
    print >> out, 'var m = window.top.document.getElementById("m");'
    print >> out, 'm.innerHTML = "[%d] Working on %s...";' % (counter, culprit)
    print >> out, 'window.location = "/clear-data-store?worker=1&kind=%s&&counter=%d";' % (culprit, counter)
    print >> out, '</script>'
    print >> out, '</html>'
    

def real_main():
  pages = [
    ('/', BrowseRecentPage),
    ('/activate', ActivationPage),
    ('/browse-recent', BrowseRecentPage),
    ('/clear-data-store', ClearDataStorePage),
    ('/create-account', CreateAccountPage),
    ('/debug', DebugPage),
    ('/edit-draft', EditDraftPage),
    ('/login', LoginPage),
    ('/logout', LogoutPage),
    ('/quote', QuotePage),
    ('/submit', SubmitPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


def profile_main():
  try:
    import cProfile, pstats
  except:
    return real_main()
  prof = cProfile.Profile()
  prof = prof.runctx("real_main()", globals(), locals())
  print '<pre id="profile">'
  stats = pstats.Stats(prof)
  stats.sort_stats("time")  # Or cumulative
  stats.print_stats(80)  # 80 = how many to print
  # The rest is optional.
  # stats.print_callees()
  # stats.print_callers()
  print "</pre>"


main = real_main


if __name__ == '__main__':
  main()

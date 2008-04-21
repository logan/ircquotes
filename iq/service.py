import datetime
import logging
import os
import urllib

from google.appengine.ext import webapp

import accounts
import hash
import mailer
import quotes
import system

class Template:
  pass


def service(require_trusted=False, require_admin=False):
  def decorator(f):
    def wrapper(self, template=None, pre_hook=None):
      if template is None:
        template = Template()
      return self.handleRequest(f,
                                require_trusted=require_trusted,
                                require_admin=require_admin,
                                template=template,
                                pre_hook=pre_hook,
                               )
    return wrapper
  return decorator


class Service(webapp.RequestHandler):
  def __init__(self, *args, **kwargs):
    webapp.RequestHandler.__init__(self, *args, **kwargs)
    self.variables = {}

  def _getParam(self, name, args, kwargs, parser=str):
    default_provided = True
    if args:
      default = args[0]
    elif 'default' in kwargs:
      default = kwargs['default']
    else:
      default_provided = False
    value = self.request.get(name, None)
    if value is None:
      if default_provided:
        return default
      else:
        raise KeyError
    try:
      return parser(value)
    except ValueError, e:
      if default_provided:
        return default
      else:
        raise

  def getParam(self, name, *args, **kwargs):
    return self._getParam(name, args, kwargs)

  def getIntParam(self, name, *args, **kwargs):
    return self._getParam(name, args, kwargs, int)

  def getLongParam(self, name, *args, **kwargs):
    return self._getParam(name, args, kwargs, long)

  @staticmethod
  def _parseDateTimeParam(value):
    items = map(int, value.split(','))
    if len(items) < 3 or len(items) > 7:
      raise ValueError('Expected list of 3-7 integers, got: %r' % value)
    return datetime.datetime(*items)

  def getDateTimeParam(self, name, *args, **kwargs):
    return self._getParam(name, args, kwargs, self._parseDateTimeParam)

  def handleRequest(self, impl, require_trusted, require_admin, template,
                    pre_hook=None):
    self.template = template
    if self.inTestingMode():
      self.mailer = mailer.TestingModeMailer()
      self.template.mailer = self.mailer
      self.template.testing = True
    else:
      self.mailer = mailer.ProductionModeMailer()
    self.setupSession()
    self.setupTemplate()
    if require_trusted and not self.account.trusted:
      self.response.set_status(403)
    if require_admin and not self.account.admin:
      self.response.set_status(403)
    if pre_hook:
      pre_hook()
    impl(self)
    self.session.put()

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
    logging.info('Setting account for remainder of request to: %s', account.id)
    self.session.account = account
    self.account = account
    self.template.account = account

  def setupSession(self):
    # Clear out any orphan sessions
    accounts.Session.expireAll()

    if self.request.get('session'):
      # Session ID in CGI parameters has highest precedence
      session_id = self.request.get('session')
    elif 'session' in self.request.cookies:
      # Next is the "session" cookie
      session_id = self.request.cookies['session']
    else:
      # If no ID is provided, generate a new one
      session_id = self.generateSessionId()

    self.setCookie('session', str(session_id))

    # Get or create corresponding session
    self.session = accounts.Session.load(session_id)
    self.account = self.session.account

  def setupTemplate(self):
    self.template.session = self.session
    self.template.account = self.account
    self.template.request = self.request
    self.template.system = system.getSystem()


class LoginService(Service):
  def login(self):
    id = self.request.get('id')
    self.template.id = id
    password = self.request.get('password')
    try:
      account = accounts.Account.login(id, password)
      if account:
        self.setAccount(account)
        self.template.success = True
        return True
    except accounts.AccountException, e:
      self.template.exception = e
    return False


class LogoutService(Service):
  def logout(self):
    self.setAccount(accounts.Account.getAnonymous())
    self.redirect(self.request.get('url', '/'))


class CreateAccountService(Service):
  def checkName(self):
    name = self.request.get('name')
    if not name:
      return
    try:
      self.template.name = name
      accounts.Account.validateName(name)
      return name
    except accounts.InvalidName, e:
      self.template.name_error = e.message

  def checkEmail(self):
    email = self.request.get('email')
    if not email:
      return
    try:
      self.template.email = email
      accounts.Account.validateEmail(email)
      return email
    except accounts.InvalidEmail, e:
      self.template.email_error = e.message

  def createAccount(self, name, email):
    password = self.request.get('password')
    if name and email and password:
      try:
        account = accounts.Account.createIq(name=name,
                                            email=email,
                                            password=password,
                                           )
        account.setupActivation(self.mailer, self.request.application_url)
        if self.inTestingMode():
          self.template.activation = account.activation
          self.template.confirmation = self.mailer.getLastSentEmail()
        return account
      except accounts.AccountException, e:
        self.template.exception = e

  def maybeCreateAccount(self):
    self.template.created = False
    name = self.checkName()
    email = self.checkEmail()
    if name and email and self.getIntParam('create', 0):
      account = self.createAccount(name, email)
      if account:
        self.template.created = True
        return account


class ActivationService(Service):
  def activate(self):
    self.template.activated = False
    id = self.request.get('id')
    activation = self.request.get('activation')
    try:
      account = accounts.Account.activate(id, activation)
      self.template.activated = True
      self.setAccount(account)
      return account
    except accounts.AccountException, e:
      self.template.exception = e

  def resendEmail(self):
    self.template.email_sent = False
    id = self.request.get('id')
    try:
      self.template.email_sent = accounts.Account.resendActivation(id)
    except accounts.AccountException, e:
      self.template.exception = e


class CreateDraftService(Service):
  def createDraft(self):
    dialog = self.request.get('dialog').strip()
    if dialog:
      self.template.quote = quotes.Quote.createDraft(self.account, dialog)
      return self.template.quote


class EditDraftService(Service):
  def getDraft(self):
    key = self.request.get('key')
    self.template.key = key
    try:
      self.template.quote = quotes.Quote.getDraft(self.account, key)
      return self.template.quote
    except quotes.QuoteException, e:
      self.template.exception = e

  def save(self):
    draft = self.getDraft()
    if draft:
      # TODO: Support metadata, note
      dialog = self.request.get('dialog')
      draft.update(dialog=dialog)
      return draft

  def discard(self):
    draft = self.getDraft()
    if draft:
      draft.delete()

  def publish(self):
    draft = self.save()
    if draft:
      draft.update(publish=True)
      self.redirect('/quote?key=%s' % urllib.quote(str(draft.key())))


class QuoteService(Service):
  def getQuote(self):
    try:
      quote = quotes.Quote.getQuoteByKey(key=self.request.get('key'),
                                         account=self.account,
                                        )
      self.template.quote = quote
      return quote
    except quotes.QuoteException, e:
      self.template.exception = e


class DeleteQuoteService(QuoteService):
  def delete(self):
    quote = self.getQuote()
    if quote and self.request.get('really-do-it'):
      quote.unpublish()
      return True

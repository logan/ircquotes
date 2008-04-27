import datetime
import logging
import os
import re
import urllib

from google.appengine.api import users
from google.appengine.ext import db
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
    self.status = 200

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
    logging.info('require_trusted=%r, account.trusted=%r',
                 require_trusted, self.account.trusted)
    logging.info('require_admin=%r, account.admin=%r',
                 require_admin, self.account.admin)
    if require_trusted and not self.account.trusted:
      self.status = 403
      return
    if require_admin and not self.account.admin:
      self.status = 403
      return
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

  def setupApiSession(self, user_id, secret):
    account = accounts.Account.getById('api/%s' % user_id)
    if not account or secret != account.password:
      self.status = 403
      return
    self.session = accounts.Session.temporary()
    self.setAccount(account)

  def setupSession(self):
    api_user_id = self.request.get('iq_user_id')
    api_secret = self.request.get('iq_secret')
    if api_user_id and api_secret:
      self.setupApiSession(api_user_id, api_secret)
      return

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

    if not self.account.trusted:
      user = users.get_current_user()
      if user:
        self.setAccount(accounts.Account.getByGoogleAccount(user))

  def setupTemplate(self):
    self.template.session = self.session
    self.template.account = self.account
    self.template.request = self.request
    self.template.system = system.getSystem()
    self.template.google_signin = users.create_login_url(self.request.path)


class LoginService(Service):
  def login(self):
    id = self.request.get('id')
    self.template.id = id
    password = self.request.get('password')
    try:
      logging.info('headers: %s', self.request.headers)
      logging.info('body: %s', self.request.body)
      logging.info('post: %s', self.request.POST.items())
      logging.info('logging in with id = %r', id)
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
    id = self.account.id
    self.setAccount(accounts.Account.getAnonymous())
    if id.startswith('google/'):
      self.redirect(users.create_logout_url('/'))
    else:
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


class ResetPasswordService(Service):
  def reset(self):
    id = self.request.get('id')
    if not id:
      return
    if not id.startswith('iq/') and '@' not in id:
      id = 'iq/%s' % id
    if id.startswith('iq/'):
      account = accounts.Account.getById(id)
    else:
      account = accounts.Account.getByEmail(id)
    if not account:
      self.template.error = 'Account does not exist'
      return False
    activation = self.request.get('activation')
    if activation:
      if account.activation != activation:
        self.template.error = 'Invalid activation code'
        return False
      self.template.id = id
      self.template.activation = activation
      p1 = self.request.get('password1')
      p2 = self.request.get('password2')
      if p1 or p2:
        if p1 != p2:
          self.template.error = 'Passwords did not match'
          return False
        else:
          logging.info('setting new password and logging in')
          account.setPassword(p1)
          account.put()
          self.setAccount(account)
          return True
      return False
    logging.info('sending email')
    self.template.email_sent = True
    account.requestPasswordReset(self.mailer, self.request.application_url)
    return False


class CreateDraftService(Service):
  def createDraft(self):
    dialog = self.request.get('dialog').strip()
    if dialog:
      self.template.quote = quotes.Quote.createDraft(self.account, dialog)
      return self.template.quote


class EditService(Service):
  def edit(self):
    quote = quotes.Quote.getQuoteByKey(key=self.request.get('key'),
                                       account=self.account,
                                      )
    draft = quote.edit(self.account)
    return draft


class QuoteService(Service):
  def getQuote(self):
    try:
      quote = quotes.Quote.getQuoteByKey(key=self.request.get('key'),
                                         account=self.account,
                                        )
      self.template.quote = quote
      if self.account.admin and self.getIntParam('rebuild', 0):
        quote.rebuild()
      return quote
    except quotes.QuoteException, e:
      self.template.exception = e



class EditDraftService(QuoteService):
  LABEL_SPLITTER = re.compile(r'[\s,]')

  def getDraft(self):
    key = self.request.get('key')
    self.template.key = key
    try:
      self.template.quote = quotes.Quote.getDraft(self.account, key)
      return self.template.quote
    except quotes.QuoteException, e:
      logging.exception("QuoteException")
      self.template.exception = e.__class__.__name__

  def save(self):
    draft = self.getDraft()
    if draft:
      draft.clearLabels()
      for name, value in self.request.params.iteritems():
        if value and name.startswith('label.'):
          draft.addLabel('%s:%s' % (name[len('label.'):], value))
      for label in self.LABEL_SPLITTER.split(self.request.get('labels', '')):
        if label:
          draft.addLabel(label)
      preserve_formatting = self.request.get('preserve_formatting') == 'on'
      draft.update(dialog=self.request.get('dialog'),
                   note=self.request.get('note'),
                   preserve_formatting=preserve_formatting,
                  )
      return draft

  def discard(self):
    draft = self.getDraft()
    if draft:
      draft.delete()

  def publish(self):
    draft = self.save()
    if draft:
      clone = draft.clone_of
      draft.update(publish=True)
      if clone:
        quote = clone
      else:
        quote = draft
      self.redirect('/quote?key=%s' % urllib.quote(str(quote.key())))


class DeleteQuoteService(QuoteService):
  def getQuote(self):
    if self.request.get('deleted'):
      return None
    return QuoteService.getQuote(self)

  def delete(self):
    quote = self.getQuote()
    if quote and self.request.get('really-do-it'):
      quote.unpublish()
      self.template.quote = None
      self.template.deleted = True
      return True


class ClearDataService(Service):
  DEFAULT_BATCH_SIZE = 20
  MODULES = [quotes, accounts]

  def deleteChunkOfKind(self, kind, batch_size):
    logging.info('session: %s', self.session.key())
    query = kind.all().fetch(limit=batch_size)
    count = 0
    for i, entity in enumerate(query):
      key = entity.key()
      if key == self.account.key():
        logging.info('Skipping deletion of active user!')
      elif key == self.session.key():
        logging.info("Skipping deletion of active session!")
      else:
        logging.info('  [%5d] Deleting %s %s',
                     i, kind.__name__, key.id_or_name() or key)
        entity.delete()
        count += 1
    return count

  @classmethod
  def getKinds(cls):
    for module in cls.MODULES:
      for value in module.__dict__.itervalues():
        if isinstance(value, type) and issubclass(value, db.Model):
          yield value

  def deleteChunk(self):
    batch_size = self.getIntParam('batch_size', self.DEFAULT_BATCH_SIZE)
    total = self.getIntParam('total', 0)
    for kind in self.getKinds():
      count = self.deleteChunkOfKind(kind, batch_size)
      if count:
        self.template.kind = kind.__name__
        self.template.count = count
        return
    self.template.done = True

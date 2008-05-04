import datetime
import logging
import re

from google.appengine.api import mail
from google.appengine.ext import db

import hash
import mailer
import provider
import system

ACTIVATION_EMAIL_TEMPLATE = '''Dear %(name)s,

Welcome to IrcQuotes!  Before you can log into the site, you will need to
activate your account.  Simply visit the URL below to activate your account:

%(base_url)s/activate?id=%(id)s&activation=%(activation)s

Thank you for registering!
IrcQuotes Administration'''


PASSWORD_EMAIL_TEMPLATE = '''Dear %(name)s,

We are sending you this email because you or someone else has requested that
the password of your IrcQuotes account be reset.  If you do want to reset your
password, please visit the URL below:

%(base_url)s/reset-password?id=%(id)s&activation=%(activation)s

Your IrcQuotes account is still secure if you did not request this email.  If
you have questions or concerns, please reply to this email.

Thank you,
IrcQuotes Administration'''


class AccountException(Exception):
  pass


class InvalidName(AccountException):
  INVALID_CHARACTER = ('An account name may only contain letters, numerals,'
                       ' apostrophes, spaces, and other characters acceptable'
                       ' in IRC nicks.')
  MISSING_LETTER = 'An account name must contain at least one letter.'
  TOO_LONG = 'An account name may only be at most %d characters in length.'
  IN_USE = 'This name is already in use.'


class InvalidEmail(AccountException):
  INVALID_FORMAT = "This doesn't look like a valid email address."
  TOO_LONG = 'We only support email addresses up to %d characters long.'
  IN_USE = 'This email is already in use.'


class NoSuchAccountException(AccountException): pass
class InvalidPasswordException(AccountException): pass
class NotActivatedException(AccountException): pass
class InvalidAccountStateException(AccountException): pass
class InvalidActivationException(AccountException): pass


VERB_SIGNED_UP = system.Verb('signed up')

@system.capture(VERB_SIGNED_UP)
def onAccountActivated(action):
  system.incrementAccountCount()


class Account(db.Expando):
  # Unique identifier for this account
  #   Examples:
  #     iq/logan
  #     facebook/1234567
  id = db.StringProperty(required=True)

  # Another unique identifier, but not every account necessarily has one.
  # All stored emails should be lowercased before storage.
  email = db.EmailProperty()

  # For ids in the iq namespace, this is required to log in.
  password = db.StringProperty()

  # Access control
  trusted = db.BooleanProperty(default=False)
  admin = db.BooleanProperty(default=False)

  # Publicly displayed name for the account.  Details from the id may also
  # be displayed (such as the fact that the user comes from Facebook).
  name = db.StringProperty(required=True)

  # Timestamps
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  activated = db.DateTimeProperty()
  active = db.DateTimeProperty(required=True, auto_now=True)

  # Account activation support
  activation = db.StringProperty()
  activation_url = db.StringProperty()

  # Migration support
  legacy_id = db.IntegerProperty()

  # Counters
  quote_count = db.IntegerProperty(default=0)
  draft_count = db.IntegerProperty(default=0)

  MAX_NAME_LENGTH = 20
  NAME_INVALID_CHARACTER_PATTERN = re.compile(r"[^\w\d'\[\]{}\\| -]")
  NAME_LETTER_PATTERN = re.compile(r'[A-Za-z]')

  MAX_EMAIL_LENGTH = 32
  EMAIL_PATTERN = re.compile(r'.+@.+\...+')

  def put(self):
    self.id = self.id.lower()
    if self.email:
      self.email = self.email.lower()
    return db.Model.put(self)

  @classmethod
  def validateName(cls, name):
    name = name.strip()
    if cls.NAME_INVALID_CHARACTER_PATTERN.search(name):
      raise InvalidName(InvalidName.INVALID_CHARACTER)
    if cls.NAME_LETTER_PATTERN.search(name) is None:
      raise InvalidName(InvalidName.MISSING_LETTER)
    if len(name) > cls.MAX_NAME_LENGTH:
      raise InvalidName(InvalidName.TOO_LONG % cls.MAX_NAME_LENGTH)
    if cls.getById('iq/%s' % name):
      raise InvalidName(InvalidName.IN_USE)

  @classmethod
  def validateEmail(cls, email):
    email = email.strip()
    if cls.EMAIL_PATTERN.match(email) is None:
      raise InvalidEmail(InvalidEmail.INVALID_FORMAT)
    if len(email) > cls.MAX_EMAIL_LENGTH:
      raise InvalidEmail(InvalidEmail.TOO_LONG % cls.MAX_EMAIL_LENGTH)
    if cls.getByEmail(email):
      raise InvalidEmail(InvalidEmail.IN_USE)

  @classmethod
  def getById(cls, id):
    query = cls.all().filter('id =', id.lower())
    return query.get()

  @classmethod
  def getByShortId(cls, id):
    return cls.get_by_id(id)

  @classmethod
  def getByLegacyId(cls, legacy_id):
    return cls.all().filter('legacy_id =', legacy_id).get()

  @classmethod
  def getByEmail(cls, email):
    email = email.strip().lower()
    logging.info("Looking up account by email: %r", email)
    return cls.all().filter('email =', email).get()

  @classmethod
  def getByGoogleAccount(cls, user):
    account = cls.getById('google/%s' % user.nickname())
    if not account:
      account = cls.createGoogleAccount(user)
    return account

  @classmethod
  def getAnonymous(cls):
    account = cls.getById('iq/anonymous')
    if account is None:
      account = cls(id='iq/anonymous', name='Anonymous')
      account.put()
    return account

  @classmethod
  def activate(cls, id, activation):
    logging.info('Attempting to activate %r', id)
    account = cls.getById(id)
    if not account:
      raise NoSuchAccountException
    if not account.activation:
      raise InvalidAccountStateException
    if account.activation != activation:
      raise InvalidActivationException
    account.activated = provider.IClock(None).now()
    account.activation = None
    account.trusted = True
    account.put()
    system.record(account, VERB_SIGNED_UP)
    return account

  @classmethod
  def login(cls, id, password):
    if id.startswith('iq/') and '@' in id:
      logging.info('getting by email: %r', id[3:])
      account = cls.getByEmail(id[3:])
    else:
      logging.info('getting by id: %r', id)
      account = cls.getById(id)
    if not account or not account.trusted:
      raise NoSuchAccountException
    if account.activated is None and account.password is None:
      raise NotActivatedException
    hashpw = hash.IHash(password)
    if account.password != password and account.password != hashpw:
      raise InvalidPasswordException
    return account

  @classmethod
  def createIq(cls, name, email, password):
    name = name.strip()
    account = cls(id='iq/%s' % name.lower(),
                  name=name,
                  email=email.strip().lower(),
                 )
    # setPassword also calls put
    account.setPassword(password)
    return account

  @classmethod
  def createLegacy(cls, user_id, name, email, password, created):
    account = cls(id='iq/%s' % name.lower(),
                  name=name,
                  email=email.lower(),
                  password=password,
                  created=created,
                  activated=provider.IClock(None).now(),
                  legacy_id=user_id,
                  trusted=True,
                 )
    account.put()
    system.incrementAccountCount()
    return account

  @classmethod
  def createFacebook(cls, facebook_id, name):
    account = cls(id='facebook/%s' % facebook_id,
                  name=name,
                  activated=provider.IClock(None).now(),
                  trusted=True,
                 )
    account.put()
    system.record(account, VERB_SIGNED_UP)
    return account

  @classmethod
  def createGoogleAccount(cls, user):
    account = cls(id='google/%s' % user.nickname(),
                  name=user.nickname(),
                  activated=provider.IClock(None).now(),
                  trusted=True,
                 )
    account.put()
    system.record(account, VERB_SIGNED_UP)
    return account

  @classmethod
  def createApi(cls, name, admin=False):
    account = cls(id='api/%s' % name,
                  name=name,
                  password = hash.IHash(None),
                  activated=provider.IClock(None).now(),
                  trusted=True,
                  admin=admin,
                 )
    account.put()
    return account

  def setupActivation(self, mailer, base_url):
    if not self.activation:
      self.activation = hash.IHash(None)
      self.put()
      logging.info("Activating account: id=%r, email=%r, activation=%r",
                   self.id, self.email, self.activation)
      self.sendConfirmationEmail(mailer, base_url)

  def sendConfirmationEmail(self, mailer, base_url):
    mailer.send(account=self,
                subject='IrcQuotes account activation',
                body=ACTIVATION_EMAIL_TEMPLATE % {
                  'id': self.id,
                  'name': self.name,
                  'activation': self.activation,
                  'base_url': base_url,
                })

  def requestPasswordReset(self, mailer, base_url):
    if not self.trusted:
      return self.setupActivation(mailer, base_url)
    self.activation = hash.IHash(None)
    self.put()
    mailer.send(account=self,
                subject='IrcQuotes password reset',
                body=PASSWORD_EMAIL_TEMPLATE % {
                  'id': self.id,
                  'name': self.name,
                  'activation': self.activation,
                  'base_url': base_url,
                })

  def setPassword(self, password):
    self.password = hash.IHash(password)
    self.activation = None
    self.put()

  def isAdmin(self):
    if self.admin:
      return True
    if not self.trusted:
      return False
    sys = system.getSystem()
    if sys.owner:
      return False
    logging.info('Making %s owner and admin', self.name)
    sys.owner = self.name
    sys.put()
    self.admin = True
    self.put()
    return True

  def __repr__(self):
    tags = []
    if not self.trusted:
      tags.append('untrusted')
    if self.admin:
      tags.append('admin')
    return '<Account: %r%s %r>' % (self.id,
                                   tags and (' %s' % ', '.join(tags)) or '',
                                   self.name)


class Session(db.Expando):
  LIFETIME_DAYS = 14

  id = db.StringProperty(required=True)
  account = db.ReferenceProperty(Account)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  active = db.DateTimeProperty(required=True, auto_now=True)

  @classmethod
  def expireAll(cls):
    now = provider.IClock(None).now()
    expiration = now - datetime.timedelta(days=cls.LIFETIME_DAYS)
    query = cls.all().filter("created <", expiration)
    for session in query:
      session.delete()
    logging.info("Deleted sessions: %d", query.count())

  @classmethod
  def load(cls, session_id):
    logging.info("Loading session: %s", session_id)
    session = cls.get_by_key_name(session_id)
    if session is None:
      logging.info("Creating new session: %s", session_id)
      session = cls(key_name=session_id,
                    id=session_id,
                    account=Account.getAnonymous(),
                   )
      session.put()
    return session

  @classmethod
  def deleteAllEntities(cls):
    query = cls.all().fetch(limit=100)
    for i, session in enumerate(query):
      session.delete()
    return i == 100

  @classmethod
  def temporary(cls):
    return cls(id='temporary')

  def put(self):
    if self.id != 'temporary':
      db.Expando.put(self)

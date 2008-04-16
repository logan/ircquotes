import datetime
import logging
import re

from google.appengine.api import mail
from google.appengine.ext import db

import hash
import mailer
import system

ACTIVATION_EMAIL_TEMPLATE = '''Dear %(name)s,

Welcome to IrcQuotes!  Before you can log into the site, you will need to
activate your account.  Simply visit the URL below to activate your account:

%(base_url)s/activate?name=%(name)s&activation=%(activation)s

Thank you for registering!
IrcQuotes Administration'''


class InvalidName(Exception):
  INVALID_CHARACTER = ('An account name may only contain letters, numerals,'
                       ' apostrophes, spaces, and other characters acceptable'
                       ' in IRC nicks.')
  MISSING_LETTER = 'An account name must contain at least one letter.'
  TOO_LONG = 'An account name may only be at most %d characters in length.'


class InvalidEmail(Exception):
  INVALID_FORMAT = "This doesn't look like a valid email address."
  TOO_LONG = 'We only support email addresses up to %d characters long.'


class NoSuchNameException(Exception): pass
class InvalidPasswordException(Exception): pass
class NotActivatedException(Exception): pass


class Account(db.Model):
  name = db.StringProperty(required=True)
  normalized_name = db.StringProperty()
  email = db.EmailProperty(required=True)
  normalized_email = db.StringProperty()
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  password = db.StringProperty()
  activation = db.StringProperty()
  activation_url = db.StringProperty()
  activated = db.DateTimeProperty()
  active = db.DateTimeProperty(required=True, auto_now=True)
  legacy_id = db.IntegerProperty()
  trusted = db.BooleanProperty(default=True)
  quote_count = db.IntegerProperty(default=0)
  draft_count = db.IntegerProperty(default=0)

  MAX_NAME_LENGTH = 20
  NAME_INVALID_CHARACTER_PATTERN = re.compile(r"[^\w\d'\[\]{}\\| -]")
  NAME_LETTER_PATTERN = re.compile(r'\w')

  MAX_EMAIL_LENGTH = 32
  EMAIL_PATTERN = re.compile(r'.+@.+\...+')

  @staticmethod
  def validateName(name):
    name = name.strip()
    if Account.NAME_INVALID_CHARACTER_PATTERN.search(name):
      raise InvalidName(InvalidName.INVALID_CHARACTER)
    if Account.NAME_LETTER_PATTERN.search(name) is None:
      raise InvalidName(InvalidName.MISSING_LETTER)
    if len(name) > Account.MAX_NAME_LENGTH:
      raise InvalidName(InvalidName.TOO_LONG % Account.MAX_NAME_LENGTH)

  def put(self):
    self.normalized_name = self.normalizeName(self.name)
    self.normalized_email = self.normalizeEmail(self.email)
    return db.Model.put(self)

  @staticmethod
  def normalizeName(name):
    return name.lower()

  @staticmethod
  def validateEmail(email):
    email = email.strip()
    if Account.EMAIL_PATTERN.match(email) is None:
      raise InvalidEmail(InvalidEmail.INVALID_FORMAT)
    if len(email) > Account.MAX_EMAIL_LENGTH:
      raise InvalidEmail(InvalidEmail.TOO_LONG % Account.MAX_EMAIL_LENGTH)

  @staticmethod
  def normalizeEmail(email):
    return email.lower()

  @staticmethod
  def getByName(name):
    name = Account.normalizeName(name)
    query = Account.all().filter('normalized_name =', name)
    return query.get()

  @staticmethod
  def getByLegacyId(legacy_id):
    return Account.all().filter('legacy_id =', legacy_id).get()

  @staticmethod
  def getByEmail(email):
    email = Account.normalizeEmail(email)
    logging.info("Looking up account by email: %r", email)
    return Account.all().filter('normalized_email =', email).get()

  @staticmethod
  def getAnonymous():
    account = Account.all().filter('trusted =', False).get()
    if account is None:
      account = Account(name='Anonymous',
                        email='anonymous@ircquotes.com',
                        activated=datetime.datetime.now(),
                        trusted=False,
                       )
      account.put()
    return account

  @staticmethod
  def login(name, password):
    hashpw = hash.generate(password)
    account = Account.getByName(name)
    if not account or not account.trusted:
      raise NoSuchNameException
    if account.password is None:
      raise NotActivatedException
    if account.password != password and account.password != hashpw:
      raise InvalidPasswordException
    return account

  @staticmethod
  def create(name, email, password=None, legacy_id=None, created=None):
    name = name.strip()
    email = email.strip()
    logging.info("Creating account: name=%r, email=%r", name, email)
    kwargs = {}
    if created is not None:
      kwargs['created'] = created
    account = Account(name=name,
                      email=email,
                      password=None,
                      legacy_id=None,
                      **kwargs)
    account.put()
    return account

  def setupActivation(self, mailer, base_url, destination_url):
    if not self.activation:
      self.activation = hash.generate()
      self.activation_url = destination_url
      self.put()
      logging.info("Activating account: name=%r, email=%r, activation=%r",
                   self.name, self.email, self.activation)
      self.sendConfirmationEmail(mailer, base_url)

  def sendConfirmationEmail(self, mailer, base_url):
    mailer.send(account=self,
                subject='IrcQuotes Account Activation',
                body=ACTIVATION_EMAIL_TEMPLATE % {
                  'name': self.name,
                  'activation': self.activation,
                  'base_url': base_url,
                })

  def setPassword(self, password):
    logging.info('setting password')
    if self.password is None:
      logging.info('new account, incrementing counter')
      system.incrementAccountCount()
    self.password = hash.generate(password)
    self.activation = None
    self.put()


class Session(db.Expando):
  LIFETIME_DAYS = 14

  id = db.StringProperty(required=True)
  account = db.ReferenceProperty(Account)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  active = db.DateTimeProperty(required=True, auto_now=True)

  @staticmethod
  def expireAll():
    now = datetime.datetime.now()
    expiration = now - datetime.timedelta(days=Session.LIFETIME_DAYS)
    query = Session.all().filter("created <", expiration)
    for session in query:
      session.delete()
    logging.info("Deleted sessions: %d", query.count())

  @staticmethod
  def load(session_id):
    logging.info("Loading session: %s", session_id)
    session = Session.get_by_key_name(session_id)
    if session is None:
      logging.info("Creating new session: %s", session_id)
      session = Session(key_name=session_id,
                        id=session_id,
                        account=Account.getAnonymous(),
                       )
      session.put()
    return session

  @staticmethod
  def deleteAllEntities():
    query = Session.all().fetch(limit=100)
    for i, session in enumerate(query):
      session.delete()
    return i == 100

import datetime
import logging
import re

from google.appengine.api import mail
from google.appengine.ext import db

import hash

def __shouldBeNone(result):
    return result is not None

def __shouldNotBeNone(result):
    return result is None

__email_tests = [
  (re.compile("^[0-9a-zA-Z\.\-\_]+\@[0-9a-zA-Z\.\-]+$"),
    __shouldNotBeNone, "Failed a"),
  (re.compile("^[^0-9a-zA-Z]|[^0-9a-zA-Z]$"), __shouldBeNone, "Failed b"),
  (re.compile("([0-9a-zA-Z]{1})\@."), __shouldNotBeNone, "Failed c"),
  (re.compile(".\@([0-9a-zA-Z]{1})"), __shouldNotBeNone, "Failed d"),
  (re.compile(".\.\-.|.\-\..|.\.\..|.\-\-."), __shouldBeNone, "Failed e"),
  (re.compile(".\.\_.|.\-\_.|.\_\..|.\_\-.|.\_\_."),
    __shouldBeNone, "Failed f"),
  (re.compile(".\.([a-zA-Z]{2,3})$|.\.([a-zA-Z]{2,4})$"),
    __shouldNotBeNone, "Failed g"),
]

def validEmailAddress(address, debug=None):
  """ Determines if an email address is malformed. """
  for test in __email_tests:
    if test[1](test[0].search(address)):
      if debug:
        return test[2]
      return 0
  return 1


__username_tests = [
  (re.compile("[^A-Za-z0-9'\\[\\]{}\\\\| -]"),
    __shouldBeNone,
    'A username may only contain letters, numerals, apostrophes, spaces, and'
    ' other characters acceptable in IRC nicks.'),
  (re.compile("^ "), __shouldBeNone, 'A username may not begin with a space.'),
  (re.compile(" $"), __shouldBeNone, 'A username may not end with a space.'),
  (re.compile("[A-Za-z]"),
    __shouldNotBeNone, 'A username must contain at least one letter.'),
  (re.compile(".{21}"),
    __shouldBeNone, 'A username may only be at most 20 characters in length.'),
]

def validUsername(username, errors):
  for test in __username_tests:
    if test[1](test[0].search(username)):
      errors.append(test[2])
  return len(errors) == 0


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

  def put(self):
    self.normalized_name = self.normalizeName(self.name)
    self.normalized_email = self.normalizeEmail(self.email)
    return db.Model.put(self)

  class NoSuchNameException(Exception): pass

  class InvalidPasswordException(Exception): pass

  class NotActivatedException(Exception): pass

  @staticmethod
  def normalizeName(name):
    return name.lower()

  @staticmethod
  def validateName(name):
    errors = []
    validName(name, errors)
    return errors

  @staticmethod
  def normalizeEmail(email):
    return email.lower()

  @staticmethod
  def validateEmail(email):
    return validEmailAddress(email)

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
  def login(name, password):
    account = Account.getByName(name)
    if not account:
      raise Account.NoSuchNameException
    if account.password is None:
      raise Account.NotActivatedException
    if account.password != password:
      raise Account.InvalidPasswordException
    return account

  @staticmethod
  def create(name, email):
    logging.info("Creating account: name=%r, email=%r", name, email)
    account = Account(name=name, email=email)
    account.put()
    return account

  def setupActivation(self, base_url, destination_url):
    if not self.activation:
      self.activation = hash.generate()
      self.activation_url = destination_url
      self.put()
      logging.info("Activating account: name=%r, email=%r, activation=%r",
                   self.name, self.email, self.activation)
      self.sendConfirmationEmail(base_url)

  def sendConfirmationEmail(self, base_url):
    mail.send_mail(sender='IrcQuotes Adminstration <logan.hanks@gmail.com>',
                   to='%s <%s>' % (self.name, self.email),
                   subject='IrcQuotes Account Activation',
                   body='''
Dear %(name)s,

Welcome to IrcQuotes!  Before you can log into the site, you will need to
activate your account.  Simply visit the URL below to activate your account:

http://%(base_url)s/activate?name=%(name)s&activation=%(activation)s

Thank you for registering!
IrcQuotes Administration''' % {
                     'name': self.name,
                     'activation': self.activation,
                     'base_url': base_url,
                   })


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
      session = Session(key_name=session_id, id=session_id)
      session.put()
    return session




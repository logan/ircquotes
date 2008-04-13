import datetime
import logging

from google.appengine.api import mail
from google.appengine.ext import db

import hash

class Account(db.Model):
  name = db.StringProperty(required=True)
  canonical_name = db.StringProperty()
  email = db.EmailProperty(required=True)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  password = db.StringProperty()
  activation = db.StringProperty()
  activation_url = db.StringProperty()
  activated = db.DateTimeProperty()
  active = db.DateTimeProperty(required=True, auto_now=True)
  legacy_id = db.IntegerProperty()

  def put(self):
    self.canonical_name = self.name.lower()
    return db.Model.put(self)

  class NoSuchNameException(Exception): pass

  class InvalidPasswordException(Exception): pass

  class NotActivatedException(Exception): pass

  @staticmethod
  def getByName(name):
    name = name.lower()
    query = Account.all().filter('canonical_name =', name)
    return query.get()

  @staticmethod
  def getByLegacyId(legacy_id):
    return Account.all().filter('legacy_id =', legacy_id).get()

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
  def setupActivation(name, url):
    account = Account.getByName(name)
    if not account.activation:
      account.activation = hash.generate()
      account.activation_url = url
      account.put()
      account.sendConfirmationEmail()

  def sendConfirmationEmail(self):
    mail.send_mail(sender='IrcQuotes Adminstration <logan.hanks@gmail.com>',
                   to='%s <%s>' % (self.name, self.email),
                   subject='IrcQuotes Account Activation',
                   body='''
Dear %(name)s,

Welcome to IrcQuotes!  Before you can log into the site, you will need to
activate your account.  Simply visit the URL below to activate your account:

http://intortus.loganh.com:8080/activate?name=%(name)s&activation=%(activation)s

Thank you for registering!
IrcQuotes Administration''' % {
                     'name': self.name,
                     'activation': self.activation,
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




import datetime
import logging

from google.appengine.ext import db

class Network(db.Model):
  name = db.StringProperty(required=True)
  servers = db.StringListProperty()


class Context(db.Model):
  protocol = db.StringProperty(required=True)
  network = db.ReferenceProperty(Network)
  location = db.StringProperty()


class Quote(db.Model):
  author = db.UserProperty()
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty(required=True, auto_now=True)
  context = db.ReferenceProperty(Context, required=True)
  source = db.TextProperty(required=True)


class Comment(db.Model):
  author = db.UserProperty()
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty(required=True, auto_now=True)
  source = db.TextProperty(required=True)
  

class Account(db.Model):
  name = db.StringProperty(required=True)
  canonical_name = db.StringProperty()
  email = db.EmailProperty(required=True)
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  password = db.StringProperty()
  activation = db.StringProperty()
  activated = db.DateTimeProperty()
  active = db.DateTimeProperty(required=True, auto_now=True)
  legacy_id = db.IntegerProperty()

  def put(self):
    self.canonical_name = self.name.lower()
    db.Model.put(self)

  class NoSuchNameException(Exception): pass

  class InvalidPasswordException(Exception): pass

  class NotActivatedException(Exception): pass

  @staticmethod
  def login(name, password):
    if Account.all().get().canonical_name is None:
      logging.info("Fixing canonical names!")
      for a in Account.all():
        a.put()
    name = name.lower()
    logging.info("Logging in as %r", name)
    query = Account.all().filter("canonical_name =", name)
    account = query.get()
    if not account:
      raise Account.NoSuchNameException
    if account.password is None:
      raise NotActivatedException
    if account.password != password:
      raise Account.InvalidPasswordException
    return account


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

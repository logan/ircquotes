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
  owner = db.UserProperty()
  created = db.DateTimeProperty(required=True)

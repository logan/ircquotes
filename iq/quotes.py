import logging

from google.appengine.ext import db

import accounts

class Network(db.Model):
  name = db.StringProperty(required=True)
  canonical_name = db.StringProperty()
  servers = db.StringListProperty()

  def put(self):
    self.canonical_name = self.name.lower()
    return db.Model.put(self)

  @staticmethod
  def getOrCreate(network, server):
    server = server.lower()
    entity = Network.all().filter('canonical_name =', network.lower()).get()
    if entity:
      if server not in entity.servers:
        entity.servers.append(server)
        entity.put()
    else:
      entity = Network(name=network or server, servers=[server])
      entity.put()
    return entity


class Context(db.Model):
  protocol = db.StringProperty(required=True)
  network = db.ReferenceProperty(Network)
  location = db.StringProperty()

  @staticmethod
  def getIrc(network, server, channel):
    if network or server:
      network = Network.getOrCreate(network, server)
    else:
      network = None
    query = Context.all()
    query.filter('protocol =', 'irc')
    query.filter('network =', network)
    query.filter('location =', channel)
    context = query.get()
    if not context:
      context = Context(protocol='irc', network=network, location=channel)
      context.put()
    return context


class Comment(db.Model):
  author = db.UserProperty()
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty(required=True, auto_now=True)
  source = db.TextProperty(required=True)
  

class Quote(db.Model):
  author = db.ReferenceProperty(accounts.Account)
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty(required=True, auto_now=True)
  context = db.ReferenceProperty(Context)
  source = db.TextProperty(required=True)
  note = db.TextProperty()
  legacy_id = db.IntegerProperty()

  @staticmethod
  def getByLegacyId(legacy_id):
    return Quote.all().filter('legacy_id =', legacy_id).get()


class Rating(db.Model):
  account = db.ReferenceProperty(accounts.Account, required=True)
  quote = db.ReferenceProperty(Quote, required=True)
  value = db.IntegerProperty(required=True)
  submitted = db.DateTimeProperty(required=True, auto_now=True)

  @staticmethod
  def rate(account, quote, value):
    query = Rating.all()
    query.filter('account =', account)
    query.filter('quote =', quote)
    rating = query.get()
    if not rating:
      rating = Rating(parent=account,
                      account=account,
                      quote=quote,
                      value=value,
                     )
      rating.put()
    return rating

  @staticmethod
  def getRatingsByQuote(quote):
    query = Rating.all()
    query.filter('quote =', quote)
    return query

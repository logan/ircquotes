import logging

from google.appengine.ext import db

import accounts

class NotInDraftMode(Exception): pass


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


class DialogLine(db.Model):
  offset = db.IntegerProperty(required=True)
  time = db.TimeProperty()
  actor = db.StringProperty()
  text = db.TextProperty(required=True)
  signature = db.StringProperty()

  @staticmethod
  def parse(quote):
    # XXX: Naive parsing for now
    for i, line in enumerate(quote.dialog_source.split('\n')):
      yield DialogLine(parent=quote, offset=i, text=line)


class Quote(db.Model):
  draft = db.BooleanProperty(required=True, default=True)
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty(required=True, auto_now=True)
  context = db.ReferenceProperty(Context)
  dialog_source = db.TextProperty(required=True)
  note = db.TextProperty()
  legacy_id = db.IntegerProperty()

  @staticmethod
  def createDraft(account, source, context=None, note=None):
    quote = Quote(parent=account,
                  draft=True,
                  context=context,
                  dialog_source=source,
                  note=note,
                 )
    quote.put()
    quote.updateDialog()
    return quote

  @staticmethod
  def getByLegacyId(legacy_id):
    return Quote.all().filter('legacy_id =', legacy_id).get()

  @staticmethod
  def getPublishedQuote(key):
    quote = Quote.get(key)
    if quote and not quote.draft:
      return quote

  @staticmethod
  def getRecentQuotes(start=None, offset=0, limit=10):
    query = Quote.all().filter('draft =', False)
    if start is not None:
      query.filter('submitted <=', start)
    query.order('-submitted')
    return list(query.fetch(offset=offset, limit=limit))

  def publish(self):
    if not self.draft:
      raise NotInDraftMode
    self.draft = False
    self.put()
    return self

  def update(self, dialog=None):
    if not self.draft:
      raise NotInDraftMode
    if dialog is not None:
      self.dialog_source = dialog
      self.updateDialog()
    self.put()

  def updateDialog(self):
    new_lines = list(DialogLine.parse(self))
    old_lines = list(self.getDialog())
    if old_lines:
      db.delete(old_lines)
    db.put(new_lines)
    return new_lines

  def getDialog(self):
    return DialogLine.all().ancestor(self)

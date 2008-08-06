import datetime
import logging

from louie import dispatcher

from google.appengine.ext import db

REGISTERED_VERBS = set()

def Verb(verb):
  # XXX: Something weird happens in the GAE environment
  #assert verb not in REGISTERED_VERBS
  #REGISTERED_VERBS.add(verb)
  return verb


class Action(db.Expando):
  timestamp = db.DateTimeProperty(required=True, auto_now_add=True)
  verb = db.StringProperty(required=True)
  actor = db.ReferenceProperty()
  targets = db.ListProperty(db.Key)

  @classmethod
  def getRecentByVerb(cls, verb, offset=0, limit=50):
    query = cls.gql('WHERE verb = :verb ORDER BY timestamp DESC',
                    verb=verb,
                   )
    return query.fetch(offset=offset, limit=limit)


def record(actor, verb, *targets, **kwargs):
  if not targets:
    targets = kwargs.get('targets')
  if not targets:
    targets = [getSystem()]
  if targets:
    kwargs = kwargs.copy()
    kwargs['targets'] = [target.key() for target in targets]
  action = Action(actor=actor,
                  verb=verb,
                  **kwargs)
  action.put()
  dispatcher.send(signal=verb, sender=record, action=action, targets=targets)
  return action


def capture(verb):
  def decorator(f):
    dispatcher.connect(receiver=f, signal=verb, sender=record)
    return f
  return decorator


class System(db.Expando):
  SYSTEM_KEY_NAME = 'system'

  latest_quote = db.DateTimeProperty()
  quote_count = db.IntegerProperty(default=0)
  account_count = db.IntegerProperty(default=0)
  facebook_api_key = db.StringProperty()
  facebook_secret = db.StringProperty()
  owner = db.StringProperty()
  stability_level = db.IntegerProperty(default=0)


def getSystem():
  system = System.get_by_key_name(System.SYSTEM_KEY_NAME)
  if not system:
    system = System(key_name=System.SYSTEM_KEY_NAME)
    system.put()
  return system


def incrementQuoteCount(amount=1, timestamp=None):
  def transaction():
    system = getSystem()
    if timestamp:
      system.latest_quote = timestamp
    system.quote_count += amount
    system.put()
  db.run_in_transaction(transaction)


def incrementAccountCount():
  def transaction():
    system = getSystem()
    system.account_count += 1
    system.put()
  db.run_in_transaction(transaction)

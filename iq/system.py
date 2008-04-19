from google.appengine.ext import db

class System(db.Expando):
  SYSTEM_KEY_NAME = 'system'

  quote_count = db.IntegerProperty(default=0)
  account_count = db.IntegerProperty(default=0)
  facebook_api_key = db.StringProperty()
  facebook_secret = db.StringProperty()


def getSystem():
  system = System.get_by_key_name(System.SYSTEM_KEY_NAME)
  if not system:
    system = System(key_name=System.SYSTEM_KEY_NAME)
  return system


def incrementQuoteCount():
  def transaction():
    system = getSystem()
    system.quote_count += 1
    system.put()
  db.run_in_transaction(transaction)


def incrementAccountCount():
  def transaction():
    system = getSystem()
    system.account_count += 1
    system.put()
  db.run_in_transaction(transaction)

from __future__ import division

import datetime
import logging
import os
import pickle
import wsgiref.handlers

from google.appengine.ext import webapp

import accounts
import quotes
import service

SUPPRESSED_SERVICE_TEMPLATE_FIELDS = [
  'session',
  'account',
  'request',
  'system',
  'mailer',
]

def json(**kwargs):
  service_dec = service.service(**kwargs)
  def decorator(f):
    f = service_dec(f)
    def wrapper(self):
      f(self)
      use_pickle = self.getIntParam('__pickle', 0)
      if use_pickle:
        encoder = pickle.dump
      else:
        encoder = serializeJson
      data = self.template.__dict__.copy()
      for field in SUPPRESSED_SERVICE_TEMPLATE_FIELDS:
        if field in data:
          del data[field]
      def tee(f1, f2):
        class F:
          def write(self, data):
            f1.write(data)
            f2.write(data)
        return F()
      import StringIO
      g = StringIO.StringIO()
      logging.info('data: %r', data)
      encoder(data, tee(g, self.response.out))
      logging.info('JSON response:\n%s', g.getvalue())
    return wrapper
  return decorator


def serializeJson(obj, f):
  if obj is None:
    f.write('null')
  elif isinstance(obj, bool):
    f.write(obj and 'true' or 'false')
  elif isinstance(obj, (int, str)):
    f.write( repr(obj))
  elif isinstance(obj, unicode):
    f.write( repr(obj)[1:])
  elif isinstance(obj, long):
    f.write( str(obj)[:-1])
  elif isinstance(obj, datetime.datetime):
    value = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second,
             obj.microsecond]
    f.write(repr(value))
  elif isinstance(obj, Exception):
    f.write(repr(obj.__class__.__name__))
  elif isinstance(obj, (tuple, list)):
    f.write('[')
    first = True
    for i in obj:
      if first:
        first = False
      else:
        f.write(',')
      serializeJson(i, f)
    f.write(']')
  elif isinstance(obj, dict):
    f.write('{')
    first = True
    for name, value in obj.iteritems():
      if first:
        first = False
      else:
        f.write(',')
      if not isinstance(name, str):
        raise ValueError(name)
      f.write('%r:' % name)
      serializeJson(value, f)
    f.write('}')
  else:
    raise ValueError(obj)


def serializePickle(obj, f):
  pickle.dump(obj, f)


class CreateAccountPage(service.CreateAccountService):
  @json()
  def get(self):
    self.maybeCreateAccount()


class LoginPage(service.LoginService):
  @json()
  def get(self):
    self.login()


class LogoutPage(service.LogoutService):
  @json()
  def get(self):
    self.logout()


class ClearDataPage(service.ClearDataService):
  @json(require_admin=True)
  def get(self):
    self.deleteChunk()


class MigrationPage(service.Service):
  @json(require_admin=True)
  def post(self):
    self.migrate()

    
class MigrateAccountPage(MigrationPage):
  def migrate(self):
    user_id = self.getIntParam('user_id')
    name = self.request.get('name')
    email = self.request.get('email')
    password = self.request.get('password')
    created = datetime.datetime.utcfromtimestamp(self.getIntParam('created'))
    rewrite = self.getIntParam('rewrite', 0)

    if not rewrite and accounts.Account.getByLegacyId(user_id):
      self.template.status = 'skipped'
      return

    if accounts.Account.getById('iq/%s' % name):
      self.template.status = 'conflict: name'
      return

    if accounts.Account.getByEmail(email):
      self.template.status = 'conflict: email'
      return

    account = accounts.Account.createLegacy(user_id=user_id,
                                            name=name,
                                            email=email,
                                            password=password,
                                            created=created,
                                           )
    account.put()
    self.template.status = 'saved'
    self.template.key = str(account.key())


class MigrateQuotePage(MigrationPage):
  def migrate(self):
    quote_id = self.getIntParam('quote_id')
    submitted_timestamp = self.getIntParam('submitted')
    submitted = datetime.datetime.utcfromtimestamp(submitted_timestamp)
    modified_timestamp = self.getIntParam('modified', 0)
    modified = None
    if modified_timestamp:
      modified = datetime.datetime.utcfromtimestamp(modified_timestamp)
    rewrite = self.getIntParam('rewrite', 0)

    if not rewrite and quotes.Quote.getByLegacyId(quote_id):
      self.template.status = 'skipped'
      return

    account = accounts.Account.getByLegacyId(self.getIntParam('user_id'))
    if not account:
      self.template.status = 'missing user'
      return
    
    quote = quotes.Quote.createLegacy(quote_id=quote_id,
                                      account=account,
                                      network=self.request.get('network', None),
                                      server=self.request.get('server', None),
                                      channel=self.request.get('channel', None),
                                      source=self.request.get('source'),
                                      note=self.request.get('note', None),
                                      modified=modified,
                                      submitted=submitted,
                                     )
    self.template.status = 'saved'
    self.template.key = str(quote.key())


def main():
  pages = [
    ('/json/create-account', CreateAccountPage),
    ('/json/migrate-account', MigrateAccountPage),
    ('/json/migrate-quote', MigrateQuotePage),
    ('/json/login', LoginPage),
    ('/json/logout', LogoutPage),
    ('/json/wipe', ClearDataPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

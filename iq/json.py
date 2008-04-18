from __future__ import division

import datetime
import logging
import os
import pickle
import time
import wsgiref.handlers

from google.appengine.ext import webapp

import accounts
import mailer
import quotes

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


class Response(dict):
  """
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)
    def getState():
      x = self.copy()
      del x['__getstate__']
    self['__getstate__'] = getState
    lambda: dict([i for i in self.iteritems() if i[0] != '__getstate__'])
  """

  def __setattr__(self, name, value):
    self[name] = value

  def __getattr__(self, name):
    try:
      return self[name]
    except KeyError, e:
      raise NameError(e.message)


class JsonPage(webapp.RequestHandler):
  def get(self):
    self.handleRequest()

  def post(self):
    self.handleRequest()

  def getIntParam(self, name, *args, **kwargs):
    default_provided = True
    if args:
      default = args[0]
    elif 'default' in kwargs:
      default = kwargs['default']
    else:
      default_provided = False
    value = self.request.get(name, None)
    if value is None:
      if default_provided:
        return default
      else:
        raise KeyError(name)
    try:
      return int(value)
    except ValueError:
      if default_provided:
        return default
      else:
        raise

  def getDateTimeParam(self, name, *args, **kwargs):
    default_provided = True
    if args:
      default = args[0]
    elif 'default' in kwargs:
      default = kwargs['default']
    else:
      default_provided = False
    value = self.request.get(name, None)
    if value is None:
      if default_provided:
        return default
      else:
        raise KeyError(name)
    try:
      items = map(int, value.split(','))
      if len(items) < 3 or len(items) > 7:
        raise ValueError('Expected list of 3-7 integers, got: %r' % value)
      return datetime.datetime(*items)
    except ValueError:
      logging.exception('valueerror on dt parsing')
      if default_provided:
        return default
      else:
        raise

  def handleRequest(self):
    use_pickle = self.getIntParam('__pickle', 0)
    if use_pickle:
      self.encoder = pickle.dump
    else:
      self.encoder = serializeJson
    if self.request.environ['SERVER_SOFTWARE'].startswith('Dev'):
      self.testing = True
    else:
      self.testing = self.request.host.startswith('iq-test')
    if self.testing:
      self.mailer = mailer.TestingModeMailer()
    else:
      self.mailer = mailer.ProductionModeMailer()

    # TODO: A subclass that enforces credentials
    # TODO: Exception handling
    response = self.run()

    if use_pickle:
      self.response.headers['Content-type'] = 'application/octet-stream'
    elif self.testing:
      self.response.headers['Content-type'] = 'text/plain'
    else:
      self.response.headers['Content-type'] = 'application/json'
    self.encoder(dict(response), self.response.out)


class CheckNamePage(JsonPage):
  def run(self):
    name = self.request.get('name')
    if not name:
      return dict(name=name,
                  error=True,
                  reason='An account name must be provided.',
                 )
    try:
      accounts.Account.validateName(name)
    except accounts.InvalidName, e:
      return dict(name=name, error=True, reason=e.message)
    if accounts.Account.getByName(name):
      return dict(name=name,
                  error=True,
                  reason='This name is already taken.',
                 )
    return dict(name=name, error=False)


class CheckEmailPage(JsonPage):
  def run(self):
    email = self.request.get('email')
    if not email:
      return dict(email=email,
                  error=True,
                  reason='A valid email must be provided.',
                 )
    try:
      accounts.Account.validateEmail(email)
    except accounts.InvalidEmail, e:
      return dict(email=email, error=True, reason=e.message)
    if accounts.Account.getByEmail(email):
      return dict(email=email,
                  error=True,
                  reason='An account is already registered with this address.',
                 )
    return dict(email=email, error=False)


class CreateAccountPage(JsonPage):
  def run(self):
    name = self.request.get('name')
    email = self.request.get('email')
    password = self.request.get('password')
    bad_fields = []
    try:
      accounts.Account.validateName(name)
    except accounts.InvalidName, e:
      bad_fields.append(('name', e.message))
    try:
      accounts.Account.validateEmail(email)
    except accounts.InvalidEmail, e:
      bad_fields.append(('email', e.message))
    if bad_fields:
      return dict(ok=False,
                  reason='Invalid %s' % ', '.join([f[0] for f in bad_fields]),
                  errors=dict(bad_fields),
                 )
    try:
      account = accounts.Account.create(name=name,
                                        email=email,
                                        password=password,
                                       )
      account.setupActivation(self.mailer, self.request.application_url)
    except Exception:
      logging.exception("Failed to create account %s/%s for JSON request"
                        % (name, email))
      return dict(ok=False,
                  reason='Server side error',
                 )
    response = dict(ok=True, name=name, email=email)
    if self.testing:
      response['activation'] = account.activation
      response['confirmation'] = self.mailer.getLastSentEmail()
    return response


class WalkQuotesPage(JsonPage):
  LIMIT = 1000

  def run(self):
    start = self.getDateTimeParam('start', datetime.datetime.now())
    offset = self.getIntParam('offset', 0)
    limit = min(self.LIMIT, self.getIntParam('limit', self.LIMIT))
    logging.info('getting quotes: start=%s, offset=%d, limit=%d',
                 start, offset, limit)
    qs, start, offset = quotes.Quote.getRecentQuotes(start=start,
                                                     offset=offset,
                                                     limit=limit,
                                                    )
    response = Response(quotes=[str(q.key()) for q in qs],
                        start=start,
                        offset=offset,
                       )
    return response


class RebuildQuotesPage(JsonPage):
  LIMIT = 100

  def run(self):
    offset = self.getIntParam('offset', 0)
    limit = min(self.LIMIT, self.getIntParam('limit', self.LIMIT))
    end = self.getDateTimeParam('end', datetime.datetime.now())
    if self.request.get('ignore_build_time'):
      ignore_build_time = True
      fetcher = quotes.Quote.getRecentQuotes
      start = self.getDateTimeParam('start', datetime.datetime.now())
    else:
      ignore_build_time = False
      fetcher = quotes.Quote.getQuotesByBuildTime
      start = self.getDateTimeParam('start', datetime.datetime.fromtimestamp(0))
    qs, start, offset = fetcher(start=start, offset=offset, limit=limit)
    logging.info('filtering out quotes older than %s', end)
    for q in qs:
      logging.info('  %s', q.built)
    qs = [q for q in qs if q.built is None or q.built <= end]
    logging.info('%d quotes to rebuild', len(qs))
    for quote in qs:
      quote.rebuild()
    return Response(quotes=[str(q.key()) for q in qs],
                    start=start,
                    offset=offset,
                   )


def main():
  pages = [
    ('/json/check-email', CheckEmailPage),
    ('/json/check-name', CheckNamePage),
    ('/json/create-account', CreateAccountPage),
    ('/json/rebuild-quotes', RebuildQuotesPage),
    ('/json/walk-quotes', WalkQuotesPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

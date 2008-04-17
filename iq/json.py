import logging
import os
import wsgiref.handlers

from django.core import serializers
from google.appengine.ext import webapp

import accounts
import mailer
import quotes

def serialize(obj):
  if obj is None:
    return 'null'
  elif isinstance(obj, bool):
    return obj and 'true' or 'false'
  elif isinstance(obj, (int, str)):
    return repr(obj)
  elif isinstance(obj, unicode):
    return repr(obj)[1:]
  elif isinstance(obj, long):
    return str(obj)[:-1]
  elif isinstance(obj, (tuple, list)):
    return '[%s]' % (','.join(serialize(i for i in obj)))
  elif isinstance(obj, dict):
    def serializeDictItem(key, value):
      if not isinstance(key, str):
        raise ValueError(key)
      return '%s:%s' % (key, serialize(value))
    return '{%s}' % (','.join(serializeDictItem(k, v)
                              for (k, v) in obj.iteritems()))
  else:
    raise ValueError(obj)


class JsonPage(webapp.RequestHandler):
  def get(self):
    self.handleRequest()

  def post(self):
    self.handleRequest()

  def handleRequest(self):
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

    if self.testing:
      self.response.headers['Content-type'] = 'text/plain'
    else:
      self.response.headers['Content-type'] = 'application/json'
    output = serialize(response)
    logging.info('output: %r', output)
    self.response.out.write(output)


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


def main():
  pages = [
    ('/json/check-email', CheckEmailPage),
    ('/json/check-name', CheckNamePage),
    ('/json/create-account', CreateAccountPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

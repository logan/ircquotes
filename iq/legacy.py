import datetime
import logging
import os
import pickle
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import quotes

class AccountPage(webapp.RequestHandler):
  def get(self):
    self.post()

  def post(self):
    values = {}
    def CheckForDuplicates(property, value):
      if quotes.Account.all().filter('%s =' % property, value).get():
        raise ValueError('%s %r already in use' % (property, value))
      if value in values.setdefault(property, set()):
        raise ValueError('%s %r already in use' % (property, value))
      values[property].add(value)

    def MigrateAccount(i):
      legacy_id = int(self.request.get('legacy_id%d' % i))
      name = self.request.get('name%d' % i)
      email = self.request.get('email%d' % i)
      created_timestamp = int(self.request.get('created%d' % i))
      created = datetime.datetime.utcfromtimestamp(created_timestamp)

      account = quotes.Account(legacy_id=legacy_id,
                               name=name,
                               email=email,
                               created=created,
                              )
      logging.info("Importing legacy_id=%d", legacy_id)
      account.put()

    results = {}


    try:
      for i in xrange(1000):
        if not self.request.get('legacy_id%d' % i):
          break
        if self.request.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
          continue
        legacy_id = int(self.request.get('legacy_id%d' % i))
        name = self.request.get('name%d' % i)
        email = self.request.get('email%d' % i)
        CheckForDuplicates('legacy_id', legacy_id)
        CheckForDuplicates('name', name)
        CheckForDuplicates('email', email)
      last = i
      logging.info("last = %d", last)

      for i in xrange(last):
        MigrateAccount(i)
      results['ok'] = True
    except ValueError, e:
      results['ok'] = False
      results['error'] = e.message
    
    self.request.headers['Content-type'] = 'text/plain'
    pickle.dump(results, self.response.out)


def main():
  pages = [
    ('/legacy/account', AccountPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

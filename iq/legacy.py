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

class QuotePage(webapp.RequestHandler):
  def get(self):
    self.post()

  def post(self):

    def getTimestamp(name):
      ts_str = self.request.get(name)
      if ts_str:
        ts = int(ts_str)
        return datetime.datetime.utcfromtimestamp(ts)

    def MigrateQuote(i):
      logging.info('Importing quote %d', i)
      legacy_id = int(self.request.get('legacy_id%d' % i))
      legacy_user_id = int(self.request.get('legacy_user_id%d' % i))
      author = quotes.Account.getByLegacyId(legacy_user_id)
      submitted = getTimestamp('submitted%d' % i)
      modified = getTimestamp('modified%d' % i) or submitted
      network = self.request.get('network%d' % i)
      server = self.request.get('server%d' % i)
      channel = self.request.get('channel%d' % i)
      if network or server or channel:
        context = quotes.Context.getIrc(network, server, channel)
      else:
        context = None
      source = self.request.get('source%d' % i)
      note = self.request.get('note%d' % i)

      quote = quotes.Quote(author=author,
                           submitted=submitted,
                           modified=modified,
                           context=context,
                           source=source,
                           note=note or None,
                           legacy_id=legacy_id,
                          )
      quote.put()

    results = {}
      
    def MigrateAll():
      for i in xrange(10000):
        if not self.request.get('legacy_id%d' % i):
          break
      last = i
      logging.info("last = %d", last)

      for i in xrange(last):
        MigrateQuote(i)
      results['ok'] = True

    try:
      if self.request.get('clear'):
        for quote in quotes.Quote.all():
          quote.delete()
      else:
        MigrateAll()
    except ValueError, e:
      results['ok'] = False
      results['error'] = e.message
    
    self.request.headers['Content-type'] = 'text/plain'
    pickle.dump(results, self.response.out)


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
    ('/legacy/quote', QuotePage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

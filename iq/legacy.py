import datetime
import logging
import os
import pickle
import sys
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import accounts
import quotes

class MigratorPage(webapp.RequestHandler):
  def getTimestamp(self, name):
    ts_str = self.request.get(name)
    if ts_str:
      ts = int(ts_str)
      return datetime.datetime.utcfromtimestamp(ts)


class RatingPage(MigratorPage):
  def post(self):
    results = {}
    try:
      self.migrate(results)
    except ValueError, e:
      results['ok'] = False
      results['error'] = e.message
    
    self.request.headers['Content-type'] = 'text/plain'
    pickle.dump(results, self.response.out)

  def migrate(self, results):
    logging.info('rating migration')
    legacy_user_id = int(self.request.get('legacy_user_id'))
    account = accounts.Account.getByLegacyId(legacy_user_id)
    if self.request.get('clear'):
      logging.info('clearing ratings for %s', account.name)
      for rating in quotes.Rating.all().ancestor(account):
        rating.delete()
      results['ok'] = True
      return

    submitted = self.getTimestamp('submitted')
    values = [int(i) for i in self.request.params.getall('value')]
    rating_times = [datetime.datetime.utcfromtimestamp(int(ts))
                    for ts in self.request.params.getall('submitted')]
    logging.info('got params')
    if len(values) != len(rating_times):
      raise ValueError('values and ratings_times are different length')
    legacy_quote_ids = [int(i) for i in
                        self.request.params.getall('legacy_quote_id')]
    if len(values) != len(legacy_quote_ids):
      raise ValueError('values and legacy_quote_ids are different length')
    logging.info('adding %d ratings', len(values))
    for i, data in enumerate(zip(legacy_quote_ids, values, rating_times)):
      logging.info("  %d/%d", i + 1, len(values))
      legacy_quote_id, value, submitted = data
      quote = quotes.Quote.getByLegacyId(legacy_quote_id)
      if not quote:
        continue
      rating = quotes.Rating(parent=account,
                             account=account,
                             quote=quote,
                             value=value,
                             submitted=submitted,
                            )
      rating.put()
    results['ok'] = True


class QuotePage(MigratorPage):
  def post(self):

    def MigrateQuote(i):
      logging.info('Importing quote %d', i)
      legacy_id = int(self.request.get('legacy_id%d' % i))
      legacy_user_id = int(self.request.get('legacy_user_id%d' % i))
      author = accounts.Account.getByLegacyId(legacy_user_id)
      submitted = self.getTimestamp('submitted%d' % i)
      modified = self.getTimestamp('modified%d' % i) or submitted
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


class AccountPage(MigratorPage):
  def get(self):
    self.post()

  def post(self):
    def MigrateAccount(i):
      legacy_id = int(self.request.get('legacy_id%d' % i))
      name = self.request.get('name%d' % i)
      email = self.request.get('email%d' % i)
      password = self.request.get('password%d' % i)
      created_timestamp = int(self.request.get('created%d' % i))
      created = datetime.datetime.utcfromtimestamp(created_timestamp)

      account = accounts.Account(legacy_id=legacy_id,
                                 name=name,
                                 email=email,
                                 password=password,
                                 created=created,
                                )
      logging.info("Importing legacy_id=%d", legacy_id)
      account.put()

    results = {}

    try:
      for i in xrange(sys.max_int):
        if not self.request.get('legacy_id%d' % i):
          break
        if self.request.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
          continue
        legacy_id = int(self.request.get('legacy_id%d' % i))
        name = self.request.get('name%d' % i)
        email = self.request.get('email%d' % i)
        password = self.request.get('password%d' % i)
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
    ('/legacy/rating', RatingPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

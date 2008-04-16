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
    except Exception, e:
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
    results = {}
    try:
      legacy_id = int(self.request.get('legacy_id'))
      if quotes.Quote.getByLegacyId(legacy_id) is not None:
        results['skip'] = True
      else:
        legacy_user_id = int(self.request.get('legacy_user_id'))
        author = accounts.Account.getByLegacyId(legacy_user_id)
        if author is None:
          results['skip'] = True
        else:
          submitted = self.getTimestamp('submitted')
          modified = self.getTimestamp('modified') or submitted
          network = self.request.get('network')
          server = self.request.get('server')
          channel = self.request.get('channel')
          if network or server or channel:
            context = quotes.Context.getIrc(network, server, channel)
          else:
            context = None
          source = self.request.get('source')
          note = self.request.get('note')

          quote = quotes.Quote.createDraft(account=author,
                                           submitted=submitted,
                                           context=context,
                                           source=source,
                                           note=note or None,
                                           legacy_id=legacy_id,
                                          )
          results['key'] = str(quote.key())
          quote.publish(modified=modified)
      results['ok'] = True
    except Exception, e:
      logging.exception('Quote migrator:')
      results['ok'] = False
      results['error'] = e.message
    
    self.request.headers['Content-type'] = 'text/plain'
    pickle.dump(results, self.response.out)


class AccountPage(MigratorPage):
  def post(self):
    results = {}
    try:
      legacy_id = int(self.request.get('legacy_id'))
      name = self.request.get('name')
      email = self.request.get('email')
      password = self.request.get('password')
      created_timestamp = int(self.request.get('created'))
      created = datetime.datetime.utcfromtimestamp(created_timestamp)
      if accounts.Account.getByName(name) or accounts.Account.getByEmail(email):
        results['skip'] = True
      else:
        account = accounts.Account.create(legacy_id=legacy_id,
                                          name=name,
                                          email=email,
                                          password=password,
                                          created=created,
                                         )
        account.put()
        results['key'] = str(account.key())
      results['ok'] = True
    except Exception, e:
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

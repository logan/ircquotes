import datetime
import logging
import os
import pickle
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import accounts
import quotes

class TestingPage(webapp.RequestHandler):
  def get(self):
    dev_mode = self.request.environ['SERVER_SOFTWARE'].startswith('Dev')
    test_mode = self.request.host.startswith('iq-test')
    if not (dev_mode or test_mode):
      self.response.set_status(404)
      return
    self.response.headers['Content-type'] = 'text/plain'
    self.response.out.write(self.handleGet())


class DeleteAccountPage(TestingPage):
  def handleGet(self):
    name = self.request.get('name')
    account = accounts.Account.getByName(name)
    if account:
      logging.info('Deleted account: %s', account.name)
      account.delete()
    else:
      logging.info('No account to delete: %s', name)
    return 'ok'


def main():
  pages = [
    ('/testing/delete-account', DeleteAccountPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

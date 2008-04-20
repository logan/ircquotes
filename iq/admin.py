import logging
import os
import StringIO
import time
import wsgiref.handlers

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import service
import system
import ui

VERB_UPDATED = system.Verb('sys.updated')

def admin(path, **kwargs):
  return ui.ui(os.path.join('admin', path), require_admin=True, **kwargs)


class AdminPage(service.Service):
  @admin('index.html')
  def get(self):
    pass

  @admin('index.html')
  def post(self):
    sys = self.template.system
    sys.owner = self.request.get('owner')
    sys.facebook_api_key = self.request.get('facebook_api_key')
    sys.facebook_secret = self.request.get('facebook_secret')
    sys.put()
    system.record(self.account, VERB_UPDATED, sys)


def main():
  pages = [
    ('/admin', AdminPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
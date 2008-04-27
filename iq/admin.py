import logging
import os
import StringIO
import time
import wsgiref.handlers

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import accounts
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
    sys.stability_level = self.getIntParam('stability_level', 0)
    sys.put()
    system.record(self.account, VERB_UPDATED, sys)


class WipePage(service.Service):
  @admin('wipe.html')
  def get(self):
    pass


class ApiPage(service.Service):
  @admin('api.html')
  def post(self):
    name = self.request.get('name')
    if not name:
      self.template.error = 'No name given'
      return
    admin = 'admin' in self.request.POST
    id = 'api/%s' % name.strip().lower()
    if accounts.Account.getById(id):
      self.template.error = 'Name already in use'
      return
    self.template.new_api_user = accounts.Account.createApi(name, admin)


class EnvironmentPage(service.Service):
  @admin('headers.html')
  def get(self):
    pass


def main():
  pages = [
    ('/admin', AdminPage),
    ('/admin/api', ApiPage),
    ('/admin/env', EnvironmentPage),
    ('/admin/wipe', WipePage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

import logging
import os
import urllib
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import browse
import facebook
import service

def ui(path, **kwargs):
  tpath = os.path.join('templates', path)
  service_dec = service.service(**kwargs)
  def decorator(f):
    f = service_dec(f)
    def wrapper(self):
      def pre_hook():
        self.facebook = facebook.FacebookSupport(self)
        if self.account.trusted:
          self.template.draft_page = browse.PageSpecifier(mode='draft')
      tmpl = service.Template()
      f(self, template=tmpl, pre_hook=pre_hook)
      self.response.out.write(template.render(tpath, tmpl.__dict__, debug=True))
    return wrapper
  return decorator


class IndexPage(browse.BrowseService):
  @ui('browse.html')
  def get(self):
    self.browseQuotes(browse.PageSpecifier(mode='recent'))


class QuotePage(service.QuoteService):
  @ui('quote.html')
  def get(self):
    if not self.getQuote():
      self.response.set_status(404)


class BrowsePage(browse.BrowseService):
  @ui('browse.html')
  def get(self):
    self.browseQuotes()


class SubmitPage(service.CreateDraftService):
  @ui('submit.html', require_trusted=True)
  def get(self):
    pass

  @ui('submit.html', require_trusted=True)
  def post(self):
    draft = self.createDraft()
    if draft:
      self.redirect('/edit-draft?key=%s' % urllib.quote(str(draft.key())))


class EditDraftPage(service.EditDraftService):
  @ui('edit-draft.html', require_trusted=True)
  def get(self):
    self.getDraft()

  @ui('edit-draft.html', require_trusted=True)
  def post(self):
    if self.request.get('save'):
      self.save()
    elif self.request.get('discard'):
      self.discard()
    elif self.request.get('publish'):
      self.publish()


class CreateAccountPage(service.CreateAccountService):
  @ui('create-account.html')
  def get(self):
    pass


class ActivationPage(service.ActivationService):
  @ui('activate.html')
  def get(self):
    self.activate()

  @ui('activate.html')
  def post(self):
    self.activate()


def main():
  pages = [
    ('/', IndexPage),
    ('/activate', ActivationPage),
    ('/browse', BrowsePage),
    ('/create-account', CreateAccountPage),
    ('/edit-draft', EditDraftPage),
    ('/quote', QuotePage),
    ('/submit', SubmitPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

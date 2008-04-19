import logging
import os
import urllib
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import service

def ui(path, **kwargs):
  tpath = os.path.join('templates', path)
  service_dec = service.service(**kwargs)
  def decorator(f):
    f = service_dec(f)
    def wrapper(self):
      tmpl = service.Template()
      f(self, tmpl)
      logging.info('template path: %r', tpath)
      logging.info('template data: %r', tmpl.__dict__)
      self.response.out.write(template.render(tpath, tmpl.__dict__, debug=True))
    return wrapper
  return decorator


class IndexPage(service.Service):
  @ui('index.html')
  def get(self):
    pass


class QuotePage(service.QuoteService):
  @ui('quote.html')
  def get(self):
    if not self.getQuote():
      self.response.set_status(404)


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
    ('/create-account', CreateAccountPage),
    ('/edit-draft', EditDraftPage),
    ('/quote', QuotePage),
    ('/submit', SubmitPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

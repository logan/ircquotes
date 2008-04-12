import logging
import os
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import quotes

class IndexPage(webapp.RequestHandler):
  def get(self):
    output = {}
    user = users.get_current_user()
    if user:
      output['user'] = user
      output['logout_url'] = users.create_logout_url(self.request.uri)
    else:
      output['login_url'] = users.create_login_url(self.request.uri)

    if not quotes.Quote.all().count():
      network = quotes.Network(name='Endernet',
                               servers=['irc.endernet.org'],
                              )
      network.put()
      context = quotes.Context(protocol='irc',
                               network=network,
                               location='#linux',
                              )
      context.put()
      quote = quotes.Quote(author=user,
                           context=context,
                           source='This is the original quote!',
                          )
      quote.put()

    output['quotes'] = quotes.Quote.all()

    for quote in output['quotes']:
      logging.info(quote.context.network.servers)

    path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    self.response.out.write(template.render(path, output))


def main():
  pages = [
    ('/', IndexPage),
  ]
  application = webapp.WSGIApplication([('/', IndexPage)], debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

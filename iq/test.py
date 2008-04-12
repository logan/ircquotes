import wsgiref.handlers

from google.appengine.ext import webapp

class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-type'] = 'text/plain'
    self.response.out.write('j0!')


def main():
  application = webapp.WSGIApplication([('/', MainPage)], debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

import datetime
import logging
import wsgiref.handlers

from google.appengine.ext import webapp

import accounts
import quotes
import service
import system

def feed(f):
  def wrapper(self):
    out = self.response.out
    self.request.headers['Content-type'] = 'application/xhtml+xml'
    print >> out, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    self.xml = Tag('feed', xmlns='http://www.w3.org/2005/Atom')
    f(self)
    self.xml.write(out)
  return wrapper


class Tag(object):
  def __init__(self, name, **kwargs):
    logging.info('instantiating tag: %s', name)
    self._name = name
    self._attrs = kwargs.copy()
    self._children = []

  def __getattribute__(self, name):
    if name.startswith('_') or name in Tag.__dict__:
      return object.__getattribute__(self, name)
    return Tag(name)

  def __call__(self, **kwargs):
    self._attrs.update(kwargs)
    return self

  def __getitem__(self, item):
    if isinstance(item, (tuple, list)):
      for i in item:
        self[i]
    else:
      self._children.append(item)
    return self

  def append(self, item):
    self._children.append(item)

  def write(self, out, depth=0):
    def encode(value):
      return (value.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')).encode('utf-8')
    indent = ' ' * depth * 2
    out.write(indent)
    out.write('<%s' % self._name)
    if self._attrs:
      out.write(' ')
      out.write(' '.join('%s="%s"' % (name, encode(value))
                         for name, value in self._attrs.iteritems()))
    if self._children:
      out.write('>\n')
      for child in self._children:
        if isinstance(child, Tag):
          child.write(out, depth + 1)
        elif isinstance(child, datetime.datetime):
          out.write(child.strftime('%Y-%m-%dT%H:%M:%SZ'))
        elif child is not None:
          out.write(indent)
          out.write('  ')
          out.write(encode(unicode(child).strip().replace('\n', '\n  ' + indent)))
          out.write('\n')
      out.write(indent)
      out.write('</%s>\n' % self._name)
    else:
      out.write('/>\n')


class IndexFeedPage(service.Service):
  @feed
  def get(self):
    actions = list(system.Action.getRecentByVerb(quotes.VERB_PUBLISHED))
    tag = self.xml

    def makeEntry(action):
      quote = quotes.Quote.get(action.targets[0])
      network = None
      server = None
      channel = None
      if quote:
        summary = tag.summary(type='text')[quote.dialog_source]
        summary._attrs['xml:space'] = 'preserve'
        for label in quote.labels:
          if label.startswith('network:'):
            network = label[len('network:'):]
          elif label.startswith('server:'):
            server = label[len('server:'):]
          elif label.startswith('channel:'):
            channel = label[len('channel:'):]
      else:
        summary = None

      if channel:
        while channel.startswith('#'):
          channel = channel[1:]
        title = 'Quote from #%s' % channel
        if network:
          title += ' on %s' % network
        elif server:
          title += ' on %s' % server
      elif network:
        title = 'Quote on %s' % network
      elif server:
        title = 'Quote on %s' % server
      else:
        title = 'Quote published by %s' % action.actor.name

      url = '%s/q/%d/%d' % (self.request.application_url,
                            action.actor.key().id(),
                            action.targets[0].id(),
                           )
      # TODO: summary
      return tag.entry[
        tag.author[
          tag.name[action.actor.name],
          #tag.email[action.actor.email],
        ],
        tag.updated[action.timestamp],
        tag.id[url],
        tag.link(href=url),
        tag.title(type='text')[title],
        summary,
      ]

    return self.xml[
      tag.id[self.request.application_url],
      tag.title['IrcQuotes: Recent Quotes'],
      tag.subtitle['Quotes most recently published to IrcQuotes'],
      tag.link(href=self.request.url,
               rel='self',
               title='IrcQuotes: Recent Quotes Feed',
              ),
      tag.updated[actions[0].timestamp],
      tag.generator(uri=self.request.application_url)['IrcQuotes'],
      [makeEntry(action) for action in actions],
    ]


def main():
  pages = [
    ('/feed', IndexFeedPage),
  ]
  application = webapp.WSGIApplication(pages, debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()

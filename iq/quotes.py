import datetime
import logging
import pickle
import re
import time

from google.appengine.ext import db
from google.appengine.ext import search

import accounts
import system

class QuoteException(Exception):
  pass

class InvalidQuoteStateException(QuoteException): pass
class InvalidKeyException(QuoteException): pass
class NoPermissionException(QuoteException): pass


VERB_PUBLISHED = system.Verb('published')
VERB_DELETED = system.Verb('deleted')
VERB_UPDATED = system.Verb('updated')

@system.capture(VERB_PUBLISHED)
def onQuotePublished(action):
  system.incrementQuoteCount()


@system.capture(VERB_DELETED)
def onQuoteDeleted(action):
  system.incrementQuoteCount(-1)


class Line:
  def __init__(self, line, formatting=None):
    self.original = line
    if formatting is None:
      self.formatting = list(LineFormatterRegistry.parse(line))

  def __repr__(self):
    if len(self.original) > 20:
      line = self.original[:17] + '...'
    else:
      line = self.original
    return '<Line: %r formatting=%s>' % (line, self.formatting)


class LineFormatterRegistry(type):
  NL = re.compile(r'\r?\n')
  INDENT = re.compile(r'^(\s*)')

  registry = []
  
  def __new__(cls, *args, **kwargs):
    instance = type.__new__(cls, *args, **kwargs)
    cls.registry.append(instance)
    return instance

  @classmethod
  def parseDialog(cls, dialog):
    line_start_indent = 0
    cur_line = []
    for line in cls.NL.split(dialog):
      indent = len(cls.INDENT.match(line).group(1))
      if indent <= line_start_indent:
        if cur_line:
          yield Line(' '.join(cur_line))
        del cur_line[:]
        line_start_indent = indent
      cur_line.append(line.strip())
    if cur_line:
      yield Line(' '.join(cur_line))

  @classmethod
  def parse(cls, line):
    for formatter in cls.registry:
      while True:
        match = formatter.match(line)
        if match:
          yield match
          line = line[:match.range[0]] + line[match.range[1]:]
          if not match.multiple:
            break
        else:
          break


class LineFormatter(object):
  """Instances of this class describe how to apply formatting to a quote.

  @type multiple: bool
  @ivar multiple: Whether the formatter could possibly match again.
  @type range: (int, int)
  @ivar range: A tuple giving the range of characters this formatting effect
               applies to.  E.g., line[range[0]:range[1]].
  @type params: A dictionary of data to export to the recipient of the formatted
                line.
  """

  __metaclass__ = LineFormatterRegistry

  def __init__(self, range=None, params=None, multiple=False):
    self.range = range
    self.params = params
    self.multiple = multiple

  def __repr__(self):
    #return '%s(%r, %r)' % (self.__class__.__name__, self.range, self.params)
    return '%s: %r' % (self.__class__.__name__, self.__dict__)

  @classmethod
  def match(cls, line):
    return None


class TimestampFormatter(LineFormatter):
  TIME = re.compile(r'^\s*\[?(?P<hour>\d?\d):(?P<minute>\d\d)(:(?P<second>\d\d))?\]?\s*')

  @classmethod
  def match(cls, line):
    match = cls.TIME.match(line)
    if match:
      groups = match.groupdict(0)
      timestamp = datetime.time(int(groups['hour']), int(groups['minute']),
                                int(groups['second']))
      return cls(range=(match.start(), match.end()),
                 params={'timestamp': timestamp},
                )


class NickFormatter(LineFormatter):
  NICK = re.compile(r'^\s*[\[<\(]?'
                    r'(?P<nickflag>[\s@+])?'
                    r"(?P<nick>[\w\d`\[\]{}\\|-]+)[\]>\):]+\s*")
  NORMALIZATION = re.compile('[^\w\d]')

  @classmethod
  def match(cls, line):
    match = cls.NICK.match(line)
    if match:
      params = {
        'normalized_nick':
          cls.NORMALIZATION.sub('', match.group('nick')).lower(),
      }
      params.update(match.groupdict())
      return cls(range=(match.start(), match.end()),
                 params=params,
                )


class Quote(search.SearchableModel):
  # The text data
  dialog_source = db.TextProperty(required=True)
  note = db.TextProperty()
  formatting = db.BlobProperty()
  labels = db.StringListProperty()

  # State bits
  deleted = db.BooleanProperty(default=False)
  draft = db.BooleanProperty(required=True, default=True)

  # Timestamps
  submitted = db.DateTimeProperty(required=True, auto_now_add=True)
  modified = db.DateTimeProperty()
  built = db.DateTimeProperty(default=datetime.datetime.fromtimestamp(0))

  # Migration support
  legacy_id = db.IntegerProperty()

  @staticmethod
  def createDraft(account, source,
                  context=None,
                  note=None,
                  submitted=None,
                  legacy_id=None,
                 ):
    logging.info('creating draft by %r', account)
    kwargs = {}
    if submitted:
      kwargs['submitted'] = submitted
    quote = Quote(parent=account,
                  draft=True,
                  context=context,
                  dialog_source=source,
                  note=note,
                  legacy_id=legacy_id,
                  **kwargs
                 )
    quote.rebuild()
    def transaction():
      acc = accounts.Account.get(account.key())
      acc.draft_count += 1
      acc.put()
      return quote
    return db.run_in_transaction(transaction)

  @staticmethod
  def getDraft(account, key):
    draft = Quote.getQuoteByKey(account, key)
    if not draft or draft.deleted:
      raise InvalidKeyException
    if not draft.draft:
      raise InvalidQuoteStateException
    return draft

  @staticmethod
  def getQuoteByKey(account, key):
    quote = Quote.get(key)
    if not quote or quote.deleted:
      raise InvalidKeyException
    if quote.draft and account.key() != quote.parent_key():
      raise NoPermissionException
    return quote

  @staticmethod
  def getByLegacyId(legacy_id):
    query = Quote.all()
    query.filter('legacy_id =', legacy_id)
    query.filter('deleted =', False)
    return query.get()

  @staticmethod
  def getPublishedQuote(key):
    quote = Quote.get(key)
    if quote and not quote.deleted and not quote.draft:
      return quote

  @staticmethod
  def getRecentQuotes(reversed=False, **kwargs):
    return Quote.getQuotesByTimestamp('submitted',
                                      descending=not reversed,
                                      include_drafts=False,
                                      **kwargs)

  @staticmethod
  def getQuotesByBuildTime(**kwargs):
    return Quote.getQuotesByTimestamp('built', **kwargs)

  @staticmethod
  def getQuotesByTimestamp(property,
                           start=None,
                           offset=0,
                           limit=10,
                           descending=False,
                           include_drafts=True,
                           ancestor=None,
                          ):
    logging.info('quotes by ts: property=%s, start=%s, offset=%s limit=%s, descending=%s, drafts=%s, ancestor=%s',
                 property, start, offset, limit, descending, include_drafts, ancestor)
    query = Quote.all()
    if ancestor:
      query.ancestor(ancestor)
    if not include_drafts:
      query.filter('draft =', False)
    query.filter('deleted =', False)
    op = '>='
    if descending:
      op = '<='
    if start is not None:
      logging.info('%s %s %s', property, op, start)
      query.filter('%s %s' % (property, op), start)
    if descending:
      query.order('-%s' % property)
    else:
      query.order(property)
    logging.info('offset=%d, limit=%d', offset, limit)
    quotes = list(query.fetch(offset=offset, limit=limit))
    logging.info('got back %d quotes', len(quotes))
    logging.info('%s', [(i, str(quotes[i].submitted), quotes[i].submitted) for i in xrange(len(quotes))])
    if len(quotes) == limit:
      for i in xrange(2, limit + 1):
        if quotes[-i].submitted != quotes[-1].submitted:
          break
      start = quotes[-1].submitted
      offset = i - 1
    return quotes, start, offset

  @staticmethod
  def getDraftQuotes(account, offset=0, limit=10, order='-submitted'):
    query = (Quote.all()
             .ancestor(account)
             .filter('draft =', True)
             .filter('deleted =', False)
             .order(order)
            )
    return list(query.fetch(offset=offset, limit=limit))

  @staticmethod
  def search(query, offset=0, limit=10):
    logging.info('quote search: query=%r, offset=%r, limit=%r', query, offset, limit)
    db_query = Quote.all()
    db_query.search(query)
    db_query.filter('draft =', False)
    db_query.filter('deleted =', False)
    return list(db_query.fetch(offset=offset, limit=limit))

  def unpublish(self):
    self.deleted = True
    self.put()
    system.record(self.parent(), VERB_DELETED, self)

  def publish(self, modified=None):
    if not self.draft:
      raise InvalidQuoteStateException
    def transaction():
      self.draft = False
      self.modified = modified or datetime.datetime.now()
      self.put()
      account = accounts.Account.get(self.parent_key())
      account.quote_count += 1
      account.draft_count -= 1
      account.put()
    db.run_in_transaction(transaction)
    system.record(self.parent(), VERB_PUBLISHED, self)
    return self

  def update(self, dialog=None, publish=False, modified=None):
    if not self.draft:
      raise InvalidQuoteStateException
    if dialog is not None:
      self.dialog_source = dialog
    self.rebuild()
    if publish:
      self.publish(modified=modified)
    else:
      system.record(self.parent(), VERB_UPDATED, self)

  def getDialog(self):
    lines = pickle.loads(self.formatting)
    logging.info('lines: %s', lines)
    for line in lines:
      params = {}
      text = line.original
      for formatter in line.formatting:
        text = text[:formatter.range[0]] + text[formatter.range[1]:]
        params.update(formatter.params)
      yield {'text': text, 'params': params}

  def rebuild(self):
    lines = list(LineFormatterRegistry.parseDialog(self.dialog_source))
    logging.info('formatting: %s', lines)
    self.formatting = db.Blob(pickle.dumps(lines))

    nicks = set()
    for line in lines:
      for formatter in line.formatting:
        if 'normalized_nick' in formatter.params:
          nicks.add(formatter.params['normalized_nick'])

    self.labels = ['nick:%s' % nick for nick in nicks]
    logging.info('labels: %r', self.labels)
    self.built = datetime.datetime.now()
    self.put()

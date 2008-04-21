import datetime
import logging
import urllib

import accounts
import quotes
import service

class BrowseException(Exception):
  pass


class UnsupportedBrowseModeException(BrowseException): pass


class PageSpecifier:
  DEFAULT_SIZE = 10
  MAX_PAGE_SIZE = 20

  def __init__(self, mode,
               start_value=None,
               offset=0,
               size=DEFAULT_SIZE,
               reversed=False,
               account=None,
               context=None,
              ):
    self.mode = mode
    self.start_value = start_value
    self.offset = offset
    self.size = min(self.MAX_PAGE_SIZE, size)
    self.reversed = reversed
    self.account = account
    self.context = context

  def copy(self, **overrides):
    kwargs = overrides.copy()
    def copyAttribute(name):
      if name not in overrides:
        kwargs[name] = getattr(self, name)
    copyAttribute('mode')
    copyAttribute('start_value')
    copyAttribute('offset')
    copyAttribute('size')
    copyAttribute('reversed')
    copyAttribute('account')
    logging.info('page copy: %r', kwargs)
    return PageSpecifier(**kwargs)

  @staticmethod
  def decode(encoded):
    logging.info('decoding page spec: %r', encoded)
    kwargs = {}
    params = encoded.split(';')
    for param in params:
      if param.startswith('m='):
        kwargs['mode'] = param[2:]
      elif param.startswith('d='):
        kwargs['start_value'] = PageSpecifier.decodeDateTime(param[2:])
      elif param.startswith('o='):
        kwargs['offset'] = int(param[2:])
      elif param.startswith('s='):
        kwargs['size'] = int(param[2:])
      elif param.startswith('r='):
        kwargs['reversed'] = bool(int(param[2:]))
      elif param.startswith('a='):
        kwargs['account'] = accounts.Account.getById(param[2:])
    return PageSpecifier(**kwargs)

  def encode(self):
    params = [('m', self.mode)]
    if self.start_value:
      params.append(('d', self.encodeDateTime(self.start_value)))
    if self.offset:
      params.append(('o', self.offset))
    if self.size != self.DEFAULT_SIZE:
      params.append(('s', self.size))
    if self.reversed:
      params.append(('r', '1'))
    if self.account:
      params.append(('a', self.account.id))
    return ';'.join('%s=%s' % param for param in params)
    
  @staticmethod
  def encodeDateTime(value):
    # 2008/04/19 14:02:56.123456 -> 7d8 4 13 0e 02 56 1e240 -> 7d84130e02561e240
    return '%03x%x%02x%02x%02x%02x%05x' % (
        value.year, value.month, value.day, value.hour, value.minute,
        value.second, value.microsecond)

  @staticmethod
  def decodeDateTime(value):
    if len(value) != 17:
      raise ValueError(value)
    year = int(value[:3], 16)
    month = int(value[3], 16)
    day = int(value[4:6], 16)
    hour = int(value[6:8], 16)
    minute = int(value[8:10], 16)
    second = int(value[10:12], 16)
    microsecond = int(value[12:], 16)
    return datetime.datetime(year, month, day, hour, minute, second,
                             microsecond)


class BrowseService(service.Service):
  def browseQuotes(self, default_page=None):
    try:
      page_spec = PageSpecifier.decode(self.request.get('page'))
    except (ValueError, TypeError), e:
      if default_page is None:
        self.template.exception = e
        return
      page_spec = default_page

    logging.info('page spec: %s', page_spec.encode())
    self.template.page = page_spec
    fetcher = getattr(self, 'fetch_%s' % page_spec.mode, None)
    if not callable(fetcher):
      self.template.exception = UnsupportedBrowseModeException()
      return

    quote_list, next_page_spec, prev_page_spec = fetcher(page_spec)
    self.template.quotes = quote_list

    def maybeExportPage(name, spec, require_full_page):
      if not spec:
        return
      if spec.offset < 0:
        return
      if require_full_page and len(quote_list) < page_spec.size:
        return
      logging.info('template should include link to page spec: %r', spec)
      setattr(self.template, name, spec)
    maybeExportPage('next_page', next_page_spec, True)
    maybeExportPage('prev_page', prev_page_spec, False)

  def fetch_recent(self, page):
    result = quotes.Quote.getRecentQuotes(start=page.start_value,
                                          offset=page.offset,
                                          limit=page.size,
                                          reversed=page.reversed,
                                          ancestor=page.account,
                                         )
    quote_list, start, offset = result
    next = page.copy(start_value=start, offset=offset)
    prev = page.copy(reversed=not page.reversed, offset=1)
    return quote_list, next, prev

  def fetch_draft(self, page):
    quote_list = quotes.Quote.getDraftQuotes(account=self.account,
                                             offset=page.offset,
                                             limit=page.size,
                                            )
    next = page.copy(offset=page.offset + page.size)
    prev = page.copy(offset=page.offset - page.size)
    return quote_list, next, prev

  def fetch_search(self, page):
    query = self.request.get('q')
    if not query:
      self.template.quotes = []
      return [], page, page
    quote_list = quotes.Quote.search(query=query,
                                     offset=page.offset,
                                     limit=page.size,
                                    )
    context = 'q=%s' % urllib.quote(query)
    next = page.copy(offset=page.offset + page.size, context=context)
    prev = page.copy(offset=page.offset - page.size, context=context)
    return quote_list, next, prev

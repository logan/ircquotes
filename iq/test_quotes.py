import datetime

import py.test

import accounts
import provider
import quotes
import system
import test_utils

class FakeLineParser:
  provider.implements(quotes.ILineParser)

  def __init__(self, obj=None): pass

  def parse(self, line):
    return list(line)


class TestLine:
  def setup_method(self, method):
    provider.registry.register(type(None), quotes.ILineParser, FakeLineParser)

  def teardown_method(self, method):
    provider.registry.unregister(type(None), quotes.ILineParser, FakeLineParser)

  def test_init(self):
    line = quotes.Line('line')
    assert line.original == 'line'
    assert line.formatting == list('line')

    line = quotes.Line('line', True)
    assert line.original == 'line'
    assert line.formatting == []

  def test_repr(self):
    line = quotes.Line('a' * 20)
    assert repr(line) == '<Line: %r formatting=%s>' % ('a' * 20, ['a'] * 20)
    line = quotes.Line('a' * 21)
    assert repr(line) == '<Line: %r formatting=%s>' % (
        'a' * 17 + '...', ['a'] * 21)


class TestLineFormatterRegistry:
  def setup_method(self, method):
    self.saved_registry = quotes.LineFormatterRegistry.registry
    quotes.LineFormatterRegistry.registry = []

  def teardown_method(self, method):
    quotes.LineFormatterRegistry.registry = self.saved_registry

  def test_parseDialog(self):
    dialog = '\n'.join([
      '  first line',
      '   continues here',
      '    and here',
      ' and still here',
      'second line',
      'third line',
    ])
    expected = [
      quotes.Line('first line continues here and here and still here', True),
      quotes.Line('second line', True),
      quotes.Line('third line', True),
    ]
    parsed = quotes.LineFormatterRegistry.parseDialog(dialog, True)
    assert map(repr, parsed) == map(repr, expected)

  def test_parse(self):
    class F1(quotes.LineFormatter):
      @classmethod
      def match(cls, line):
        if line:
          return cls(range=(0, 1), params={'prefix': line[0]})

    class Null(quotes.LineFormatter): pass

    class F2(F1):
      def __init__(self, range, params):
        F1.__init__(self, range=range, params=params, multiple=True)

    assert len(quotes.LineFormatterRegistry.registry) == 3

    formatting = list(quotes.LineFormatterRegistry.parse('line'))
    assert len(formatting) == len('line')
    for c, f in zip('line', formatting):
      assert f.range == (0, 1)
      assert f.params == {'prefix': c}


def test_TimestampFormatter():
  match = quotes.TimestampFormatter.match('  [3:12  Blah blah blah.')
  assert not match.multiple
  assert match.range == (0, 9)
  assert match.params == {'timestamp': datetime.time(3, 12, 0)}

  match = quotes.TimestampFormatter.match('(23:59:59]Blah')
  assert match.range == (0, 10)
  assert match.params == {'timestamp': datetime.time(23, 59, 59)}
  assert quotes.TimestampFormatter.match('24:00 Blah blah blah.') is None
  assert quotes.TimestampFormatter.match('23:60 Blah blah blah.') is None
  assert quotes.TimestampFormatter.match('23:59:60 Blah blah blah.') is None


def test_NickFormatter():
  match = quotes.NickFormatter.match(' +X:  Blah!')
  assert not match.multiple
  assert match.range == (0, 5)
  assert match.params == dict(nickflag='+', normalized_nick='x', nick='X')

  match = quotes.NickFormatter.match(r'X{\}2[]:j0!')
  assert match.range == (0, 8)
  assert match.params == dict(nickflag=None,
                              normalized_nick=r'x2',
                              nick='X{\}2[]')

  assert quotes.NickFormatter.match('Blah blah blah!') is None


class TestQuote:
  def setup_method(self, method):
    test_utils.setup()
    #provider.registry.register(type(None), quotes.ILineParser, FakeLineParser)

  def teardown_method(self, method):
    pass
    #provider.registry.unregister(type(None), quotes.ILineParser, FakeLineParser)

  def makeAccount(self, id):
    id = str(id)
    return accounts.Account(id=id, name=id, trusted=True).put()

  def getAccount(self, key):
    return accounts.Account.get(key)

  def test_createDraft(self):
    now = datetime.datetime.now()
    then = now - datetime.timedelta(days=1)
    source = '1:23 test: line'
    a1 = self.makeAccount(1)
    q1 = quotes.Quote.createDraft(self.getAccount(a1), source=source)
    assert q1.parent_key() == a1
    assert q1.draft
    assert q1.state == quotes.Quote.DRAFT
    assert q1.dialog_source == source
    assert q1.note is None
    assert q1.legacy_id is None
    assert q1.submitted >= now
    assert len(q1.formatting) > 0

    q2 = quotes.Quote.createDraft(self.getAccount(a1),
                                  source=source,
                                  note='note',
                                  submitted=then,
                                  legacy_id=123,
                                 )
    assert q2.note == 'note'
    assert q2.legacy_id == 123
    assert q2.submitted == then

    account = self.getAccount(a1)
    assert account.draft_count == 2

  def test_createLegacy(self):
    now = datetime.datetime.now()
    then = now - datetime.timedelta(days=1)
    source = '1:23 test: line'
    a1 = self.makeAccount(1)
    q1 = quotes.Quote.createLegacy(account=self.getAccount(a1),
                                   quote_id=123,
                                   network='',
                                   server='',
                                   channel='',
                                   source=source,
                                   note='note',
                                   modified=None,
                                   submitted=then,
                                  )
    assert q1.parent_key() == a1
    assert not q1.draft
    assert q1.state == quotes.Quote.PUBLISHED
    assert q1.dialog_source == source
    assert q1.note == 'note'
    assert q1.legacy_id == 123
    assert q1.submitted == then
    assert q1.modified == then
    assert len(q1.formatting) > 0
    assert q1.labels == ['nick:test']

    full_labels = [
      'network:network',
      'server:server',
      'channel:channel',
      'nick:test',
    ]

    q2 = quotes.Quote.createLegacy(account=self.getAccount(a1),
                                   quote_id=123,
                                   network='network',
                                   server='server',
                                   channel='#cha#nnel',
                                   source=source + '2',
                                   note='note 2',
                                   modified=now,
                                   submitted=then,
                                  )
    assert q2.key() == q1.key()
    assert q2.dialog_source == source + '2'
    assert q2.note == 'note 2'
    assert q2.modified == now
    assert q2.submitted == then
    assert q2.labels == full_labels

    q3 = quotes.Quote.createLegacy(account=self.getAccount(a1),
                                   quote_id=1234,
                                   network='network',
                                   server='server',
                                   channel='#cha#nnel',
                                   source=source,
                                   note=None,
                                   modified=now,
                                   submitted=then,
                                  )
    assert q3.labels == full_labels

    assert system.getSystem().quote_count == 2

  def test_getDraft(self):
    a1 = self.makeAccount(1)
    q1 = quotes.Quote.createDraft(self.getAccount(a1), source='source')
    q2 = quotes.Quote.getDraft(self.getAccount(a1), q1.key())
    assert q2.key() == q1.key()
    q2.publish()
    py.test.raises(quotes.InvalidQuoteStateException,
                   quotes.Quote.getDraft, self.getAccount(a1), q1.key())

  def test_getQuoteByKey(self):
    a1 = self.makeAccount(1)
    a2 = self.makeAccount(2)
    q1 = quotes.Quote.createDraft(self.getAccount(a1), source='source')
    py.test.raises(quotes.NoPermissionException,
                   quotes.Quote.getQuoteByKey, self.getAccount(a2), q1.key())
    q1.publish()
    q2 = quotes.Quote.getQuoteByKey(self.getAccount(a2), q1.key())
    assert q2.key() == q1.key()
    q3 = quotes.Quote.getQuoteByKey(self.getAccount(a1), q1.key())
    assert q3.key() == q1.key()
    q3.delete()
    py.test.raises(quotes.InvalidKeyException,
                   quotes.Quote.getQuoteByKey, self.getAccount(a1), q1.key())

  def test_getQuoteByShortId(self):
    a1 = self.makeAccount(1)
    a2 = self.makeAccount(2)
    q1 = quotes.Quote.createDraft(self.getAccount(a1), source='source')
    py.test.raises(quotes.NoPermissionException,
                   quotes.Quote.getQuoteByShortId, self.getAccount(a2),
                   q1.key().id(), a1)
    q1.publish()
    q2 = quotes.Quote.getQuoteByShortId(self.getAccount(a2), q1.key().id(), a1)
    assert q2.key() == q1.key()
    q3 = quotes.Quote.getQuoteByShortId(self.getAccount(a1), q1.key().id(), a1)
    assert q3.key() == q1.key()
    py.test.raises(quotes.InvalidKeyException,
                   quotes.Quote.getQuoteByShortId, self.getAccount(a1),
                   q1.key().id(), a2)
    q3.delete()
    py.test.raises(quotes.InvalidKeyException,
                   quotes.Quote.getQuoteByShortId, self.getAccount(a1),
                   q1.key().id(), a1)

  def test_getByLegacyId(self):
    assert quotes.Quote.getByLegacyId(123) is None
    a1 = self.makeAccount(1)
    q1 = quotes.Quote(parent=self.getAccount(a1),
                      dialog_source='x',
                      legacy_id=123,
                     )
    q1.put()
    q2 = quotes.Quote.getByLegacyId(123)
    assert q2.key() == q1.key()

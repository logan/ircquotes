import datetime

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


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

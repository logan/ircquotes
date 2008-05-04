import sys

import hash
import provider

class TrueBitGenerator:
  def __init__(self, obj=None): pass

  def getBits(self, count):
    return 2 ** count - 1


class PrefixDigester:
  def __init__(self, obj=None):
    self.content = 'hexdigest:'

  def update(self, data):
    self.content += data

  def hexdigest(self):
    return self.content


class TestGenerate:
  def setup_method(self, method):
    provider.registry.register(type(None), hash.IRandomBitGenerator,
                               TrueBitGenerator)
    provider.registry.register(type(None), hash.IDigester,
                               PrefixDigester)

  def teardown_method(self, method):
    provider.registry.unregister(type(None), hash.IRandomBitGenerator,
                                 TrueBitGenerator)
    provider.registry.unregister(type(None), hash.IDigester,
                                 PrefixDigester)

  def test_generate(self):
    assert hash.IHash(None) == 'hexdigest:%s' % (2 ** 1024 - 1)
    assert hash.IHash('str') == 'hexdigest:str'
    assert hash.IHash(u'unicode') == 'hexdigest:unicode'

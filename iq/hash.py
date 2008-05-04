import md5
import provider
import random

class IRandomBitGenerator(provider.Interface):
  def getBits(self, count):
    """Return an int or long from a sequence of random bits.
    """


class SystemRandomBitGenerator:
  provider.implements(IRandomBitGenerator)

  def __init__(self, obj=None):
    self.generator = random.SystemRandom()

  def getBits(self, count):
    return self.generator.getrandbits(count)

provider.registry.register(type(None), IRandomBitGenerator,
                           SystemRandomBitGenerator)


class IDigester(provider.Interface):
  def update(self, data):
    pass

  def hexdigest(self):
    pass


@provider.adapter(type(None), IDigester)
def md5_digester(_):
  return md5.new()


class IHash(provider.Interface):
  pass


@provider.adapter(type(None), IHash)
def generate(content):
  if content is None:
    generator = IRandomBitGenerator(None)
    content = str(generator.getBits(1024))
  digester = IDigester(None)
  digester.update(content)
  return digester.hexdigest()


@provider.adapter(str, IHash)
def hash_string(value):
  return generate(value)


@provider.adapter(unicode, IHash)
def hash_unicode(value):
  return generate(value)

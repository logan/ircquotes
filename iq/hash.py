import md5
import random

def generate(content=None):
  if content is None:
    generator = random.SystemRandom()
    content = str(generator.getrandbits(1024))
  digester = md5.new()
  digester.update(content)
  return digester.hexdigest()

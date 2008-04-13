import md5
import random

def generate():
  generator = random.SystemRandom()
  bits = generator.getrandbits(1024)
  digester = md5.new()
  digester.update(str(bits))
  return digester.hexdigest()

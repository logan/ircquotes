import provider

def test_clock():
  def now1(_): return 1
  def now2(_): return 2
  def now3(_): return 3
  provider.registry.register(type(None), provider.IClock, now1)
  assert provider.IClock(None) == 1
  provider.registry.register(type(None), provider.IClock, now2)
  assert provider.IClock(None) == 2
  provider.registry.register(type(None), provider.IClock, now3)
  assert provider.IClock(None) == 3

  provider.registry.unregister(type(None), provider.IClock, now2)
  assert provider.IClock(None) == 3
  provider.registry.unregister(type(None), provider.IClock, now3)
  assert provider.IClock(None) == 1


def test_registry():
  class ITest(provider.Interface): pass
  p1 = lambda x: x + 1
  p2 = lambda x: x + 2
  provider.registry.register(int, ITest, p1)
  provider.registry.register(int, ITest, p2)
  provider.registry.register(str, ITest, lambda x: x * 2)

  assert ITest(1) == 3
  assert ITest('1') == '11'
  provider.registry.unregister(int, ITest, p2)
  assert ITest(1) == 2
  provider.registry.unregister(int, ITest, p1)
  assert ITest(1) == 1

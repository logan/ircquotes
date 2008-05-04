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

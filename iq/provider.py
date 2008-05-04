import datetime

from zope.interface import implements, Interface, Attribute
from zope.interface.interface import adapter_hooks

class IClock(Interface):
  def now(self):
    """Return a datetime object for the current local time.
    """


class AdapterRegistry:
  def __init__(self):
    self.adapters = {}

  def register(self, klass, interface, adapter):
    """Register an adapter for instances of a certain class to an interface.
    """
    interface_adapters = self.adapters.setdefault(interface, {})
    interface_adapters.setdefault(klass, []).append(adapter)

  def unregister(self, klass, interface, adapter):
    interface_adapters = self.adapters.setdefault(interface, {})
    adapters_for_klass = interface_adapters.get(klass, [])
    if adapter in adapters_for_klass:
      adapters_for_klass.remove(adapter)
      if not adapters_for_klass:
        del interface_adapters[klass]

  def lookup(self, object, interface):
    """Returns any registered adapter for the object's class and the interface.
    """
    for klass, adapter_list in self.adapters.get(interface, {}).iteritems():
      if isinstance(object, klass):
        return adapter_list[-1]
    return None


registry = AdapterRegistry()


def adapterHook(provided, object):
  adapter = registry.lookup(object, provided)
  if adapter:
    return adapter(object)
  else:
    return object


adapter_hooks.append(adapterHook)


def adapter(klass, interface):
  def decorate(f):
    registry.register(klass, interface, f)
    return f
  return decorate


# Some built in implementations and adapters.

class LocalTimeClock(object):
  implements(IClock)

  def now(self):
    return datetime.datetime.now()


@adapter(type(None), IClock)
def clock(_):
  return LocalTimeClock()

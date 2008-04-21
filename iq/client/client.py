import datetime
import logging
import pickle
import urllib

class JsonResponse:
  def __init__(self, response, pickle_mapping=None):
    self.__response = response.copy()
    for name, value in self.__response.iteritems():
      if isinstance(value, dict):
        value = JsonResponse(value)
      elif isinstance(value, (list, tuple)):
        items = []
        for item in value:
          if isinstance(item, dict):
            items.append(JsonResponse(item))
          else:
            items.append(item)
        value = items
      elif pickle_mapping:
        for data_type, converter in pickle_mapping.iteritems():
          if isinstance(value, data_type):
            value = converter(value)
            break
      setattr(self, name, value)
    logging.debug('JsonResponse: %r', self.__dict__)

  def __getitem__(self, key):
    return self.__response[key]

  def __contains__(self, key):
    return key in self.__response


def pickleDecoder(f):
  def dt(v):
    return [v.year, v.month, v.day, v.hour, v.minute, v.second, v.microsecond]
  return JsonResponse(pickle.load(f), pickle_mapping={datetime.datetime: dt})


def jsonDecoder(f):
  # XXX: We're trusting the server not to do anything nasty!
  # TODO: Use a real JSON parser.
  data = f.read()
  logging.debug('response: %r', data)
  return JsonResponse(eval(data))


class IqJsonClient(object):
  def __init__(self, user_id, secret, host,
               baseuri='/json',
               use_pickle=False,
              ):
    self.user_id = user_id
    self.secret = secret
    self.host = host
    self.baseuri = baseuri
    self.use_pickle = use_pickle
    if self.use_pickle:
      self.decoder = pickleDecoder
    else:
      self.decoder = jsonDecoder

  def __getattr__(self, name):
    if name.startswith('call_'):
      return lambda **params: self.call(name[len('call_'):], **params)
    try:
      return self.__dict__[name]
    except KeyError:
      raise NameError(name)

  def call(self, method, **kwargs):
    params = {
      'iq_user_id': self.user_id,
      'iq_secret': self.secret,
    }
    if self.use_pickle:
      params['__pickle'] = '1'
    params.update(kwargs)
    method = method.replace('_', '-')
    url = '%s%s/%s' % (self.host, self.baseuri, method)
    logging.info('Calling %r', url)
    params = urllib.urlencode(params)
    f = urllib.urlopen(url, params)
    logging.info('  processing response')
    # TODO: Error handling!
    return self.decoder(f)

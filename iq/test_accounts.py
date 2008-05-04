import datetime
import functools

import py

import accounts
import hash
import logging
import mailer
import provider
import system
import test_utils

class FakeClock:
  provider.implements(provider.IClock)

  NOW = datetime.datetime.now()
  THEN = NOW - datetime.timedelta(days=1)

  def __init__(self, obj): pass

  def now(self):
    return self.NOW


def FakeHash(obj=None):
  return 'hash:%s' % obj


class TestAccount:
  def setup_method(self, method):
    test_utils.setup()
    provider.registry.register(type(None), provider.IClock, FakeClock)
    provider.registry.register(type(None), hash.IHash, FakeHash)
    provider.registry.register(str, hash.IHash, FakeHash)

  def teardown_method(self, method):
    provider.registry.unregister(type(None), provider.IClock, FakeClock)
    provider.registry.unregister(type(None), hash.IHash, FakeHash)
    provider.registry.unregister(str, hash.IHash, FakeHash)

  def test_put(self):
    name = 'AbCdE'
    def check(account, email):
      assert account.id == name.lower()
      assert account.name == name
      if email:
        assert account.email == name.lower()
      else:
        assert account.email is None
    a = accounts.Account(id=name, name=name)
    a.put()
    check(a, False)
    a = accounts.Account(id=name, name=name, email=name)
    a.put()
    check(a, True)

  def checkValidation(self, method, error_class, value, error=None):
    try:
      method(value)
      assert error is None
    except error_class, e:
      assert e.message == error


  def test_validateName(self):
    accounts.Account(id='iq/taken', name='taken').put()
    check = functools.partial(self.checkValidation,
                              accounts.Account.validateName,
                              accounts.InvalidName,
                             )

    check('!', accounts.InvalidName.INVALID_CHARACTER)
    check('1', accounts.InvalidName.MISSING_LETTER)
    check('a' * (accounts.Account.MAX_NAME_LENGTH + 1),
          accounts.InvalidName.TOO_LONG % accounts.Account.MAX_NAME_LENGTH)
    check(' TaKeN ', accounts.InvalidName.IN_USE)
    check(' %s ' % ('a' * accounts.Account.MAX_NAME_LENGTH))


  def test_validateEmail(self):
    a = accounts.Account(id='iq/test', name='test', email='taken@test.invalid')
    a.put()
    check = functools.partial(self.checkValidation,
                              accounts.Account.validateEmail,
                              accounts.InvalidEmail,
                             )
    check('abc@def', accounts.InvalidEmail.INVALID_FORMAT)
    check('%s@x.xx' % ('a' * (accounts.Account.MAX_EMAIL_LENGTH - 4)),
          accounts.InvalidEmail.TOO_LONG % accounts.Account.MAX_EMAIL_LENGTH)
    check(' tAkEn@tEsT.InVaLiD ', accounts.InvalidEmail.IN_USE)
    check(' %s@x.xx ' % ('a' * (accounts.Account.MAX_EMAIL_LENGTH - 5)))


  def test_getById(self):
    assert accounts.Account.getById('test') is None
    assert accounts.Account.getById('iq/taken') is None
    accounts.Account(id='tEsT', name='test').put()
    assert accounts.Account.getById('test').id == 'test'
    assert accounts.Account.getById('tEsT').id == 'test'


  def test_getByEmail(self):
    assert accounts.Account.getByEmail('test') is None
    accounts.Account(id='tEsT', name='test', email='eMaIl').put()
    assert accounts.Account.getByEmail('email').id == 'test'
    assert accounts.Account.getByEmail('EmAiL').id == 'test'
    assert accounts.Account.getByEmail(' EmAiL ').id == 'test'


  def test_getByShortId(self):
    key = accounts.Account(id='tEsT', name='test').put()
    id = key.id()
    assert accounts.Account.getByShortId(id).id == 'test'
    assert accounts.Account.getByShortId(id + 1) is None


  def test_getByLegacyId(self):
    accounts.Account(id='test0', name='test0').put()
    assert accounts.Account.getByLegacyId(1) is None
    accounts.Account(id='test1', name='test1', legacy_id=1).put()
    assert accounts.Account.getByLegacyId(1).id == 'test1'

  def test_getByGoogleAccount(self):
    user1 = test_utils.Generic(nickname=lambda: 'nick1')
    user2 = test_utils.Generic(nickname=lambda: 'nick2')
    a1 = accounts.Account.getByGoogleAccount(user1)
    assert a1.id == 'google/nick1'
    assert a1.trusted
    a2 = accounts.Account.getById('google/nick1')
    assert a1.key() == a2.key()
    a3 = accounts.Account.getByGoogleAccount(user2)
    assert a1.key() != a3.key()
    a4 = accounts.Account.getByGoogleAccount(user1)
    assert a1.key() == a4.key()

  def test_getAnonymous(self):
    assert accounts.Account.getById('iq/anonymous') is None
    a1 = accounts.Account.getAnonymous()
    assert a1.id == 'iq/anonymous'
    assert a1.name == 'Anonymous'
    assert not a1.trusted
    a2 = accounts.Account.getAnonymous()
    assert a1.key() == a2.key()

  def test_activate(self):
    a1 = accounts.Account.getAnonymous()
    a2 = accounts.Account(id='test', name='test', activation='activation')
    a2.put()
    py.test.raises(accounts.NoSuchAccountException,
                   accounts.Account.activate, 'nobody', 'activation')
    py.test.raises(accounts.InvalidAccountStateException,
                   accounts.Account.activate, a1.id, 'activation')
    py.test.raises(accounts.InvalidActivationException,
                   accounts.Account.activate, a2.id, 'error')
    assert a2.activated is None
    assert not a2.trusted
    a3 = accounts.Account.activate(a2.id, 'activation')
    assert a2.key() == a3.key()
    assert a3.trusted
    assert a3.activated == FakeClock.NOW
    assert a3.activation is None

  def test_login(self):
    A = accounts.Account
    a1 = A.getAnonymous()
    a2 = A(id='a2', name='a2', email='a2@x', password='a2')
    a2.put()
    a3 = A(id='a3', name='a3', password='a3', trusted=True)
    a3.put()
    a4 = A(id='a4', name='a4', email='a4@x', password='a4', trusted=True)
    a4.put()
    a5 = A(id='a5', name='a5', password=None, trusted=True)
    a5.put()

    py.test.raises(accounts.NoSuchAccountException, A.login, 'nobody', '')
    py.test.raises(accounts.NoSuchAccountException, A.login, 'a2', 'a2')
    a = A.login('a3', 'a3')
    assert a.key() == a3.key()

    py.test.raises(accounts.NoSuchAccountException, A.login, 'a4@x', 'a4')
    py.test.raises(accounts.NoSuchAccountException, A.login, 'iq/a2@x', 'a2')
    a = A.login('iq/a4@x', 'a4')
    assert a.key() == a4.key()

    py.test.raises(accounts.InvalidPasswordException, A.login, 'a3', '!a3')
    py.test.raises(accounts.NotActivatedException, A.login, 'a5', 'a5')
    a5.activated = FakeClock.NOW
    a5.put()
    py.test.raises(accounts.InvalidPasswordException, A.login, 'a5', 'a5')
    a5.password = 'a5'
    a5.put()
    a = A.login('a5', 'a5')
    assert a.key() == a5.key()
    a5.setPassword('a5-2')
    a = A.login('a5', 'a5-2')
    assert a.key() == a5.key()

  def test_createIq(self):
    password = ' pAsSwOrD '
    a = accounts.Account.createIq(' NaMe ', ' eMaIl ', password)
    assert a.id == 'iq/name'
    assert a.email == 'email'
    print a.password
    assert a.password == hash.IHash(password)
    assert not a.trusted
    assert not a.admin

  def test_createLegacy(self):
    a = accounts.Account.createLegacy(user_id=1,
                                      name='NaMe',
                                      email='eMaIl',
                                      password='password',
                                      created=FakeClock.THEN,
                                     )
    assert system.getSystem().account_count == 1
    assert a.id == 'iq/name'
    assert a.name == 'NaMe'
    assert a.email == 'email'
    assert a.password == 'password'
    assert a.created == FakeClock.THEN
    assert a.activated == FakeClock.NOW
    assert a.legacy_id == 1
    assert a.trusted
    assert not a.admin

  def test_createFacebook(self):
    a = accounts.Account.createFacebook(1, 'Facebooker')
    assert system.getSystem().account_count == 1
    assert a.id == 'facebook/1'
    assert a.name == 'Facebooker'
    assert a.email is None
    assert a.activated == FakeClock.NOW
    assert a.trusted
    assert not a.admin

  def test_createGoogleAccount(self):
    user = test_utils.Generic(nickname=lambda: 'NaMe')
    a = accounts.Account.createGoogleAccount(user)
    assert system.getSystem().account_count == 1
    assert a.id == 'google/name'
    assert a.name == 'NaMe'
    assert a.email is None
    assert a.activated == FakeClock.NOW
    assert a.trusted
    assert not a.admin

  def test_createApi(self):
    a1 = accounts.Account.createApi('api1')
    a2 = accounts.Account.createApi('api2', True)
    assert system.getSystem().account_count == 0
    assert a1.id == 'api/api1'
    assert a1.name == 'api1'
    assert a1.password == 'hash:None'
    assert a1.activated == FakeClock.NOW
    assert a1.trusted
    assert not a1.admin

    assert a2.id == 'api/api2'
    assert a2.name == 'api2'
    assert a2.password == 'hash:None'
    assert a2.activated == FakeClock.NOW
    assert a2.trusted
    assert a2.admin

  def test_setupActivation(self):
    m = mailer.IMailer(None)
    a = accounts.Account.createIq('name', 'email', 'password')
    assert a.activation is None

    a.setupActivation(m, 'base_url')
    activation = hash.IHash(None)
    email = 'To: email\nSubject: IrcQuotes account activation\n\n%s' % (
        accounts.ACTIVATION_EMAIL_TEMPLATE
        % {
            'id': a.id,
            'name': a.name,
            'activation': activation,
            'base_url': 'base_url',
          })
    assert m.getLastSentEmail() == email
    assert a.activation == activation

    m = mailer.IMailer(None)
    a.setupActivation(m, 'base_url')
    assert m.getLastSentEmail() is None

  def test_requestPasswordReset(self):
    m = mailer.IMailer(None)
    a1 = accounts.Account.createIq('name', 'email', 'password')
    a1.activation = 'activation'
    a1.put()
    a2 = accounts.Account.createIq('name', 'email', 'password')
    a2.trusted = True
    a2.put()

    # a1 is activated but not trusted; no email should be sent
    a1.requestPasswordReset(m, 'base_url')
    assert m.getLastSentEmail() is None

    # a2 should receive activation code; email should be sent
    assert a2.activation is None
    a2.requestPasswordReset(m, 'base_url')
    activation = hash.IHash(None)
    email = 'To: email\nSubject: IrcQuotes password reset\n\n%s' % (
        accounts.PASSWORD_EMAIL_TEMPLATE
        % {
            'id': a2.id,
            'name': a2.name,
            'activation': activation,
            'base_url': 'base_url',
          })
    assert m.getLastSentEmail() == email
    assert a2.activation == activation

  def test_setPassword(self):
    a = accounts.Account.createIq('name', 'email', '')
    assert a.password == 'hash:'
    a.setPassword('new')
    assert a.password == 'hash:new'
    a = accounts.Account.getById('iq/name')
    assert a.password == 'hash:new'

  def test_isAdmin(self):
    a0 = accounts.Account.createIq('name0', 'email', 'password')
    a1 = accounts.Account.createIq('name1', 'email', 'password')
    a1.trusted = True
    a1.put()
    a2 = accounts.Account.createIq('name2', 'email', 'password')
    a2.trusted = True
    a2.put()
    a3 = accounts.Account.createIq('name3', 'email', 'password')
    a3.admin = True
    a3.put()

    # a0 and a1 compete to become owners; a1 wins because a0 isn't trusted
    # a2 is trusted, but the owner is already selected

    assert not a0.isAdmin()
    assert not a1.admin
    assert a1.isAdmin()
    a1 = accounts.Account.getById('iq/name1')
    assert a1.admin
    assert not a2.isAdmin()
    assert a3.isAdmin()
    assert system.getSystem().owner == 'name1'

  def test_repr(self):
    a = accounts.Account(id='id', name='name')
    assert repr(a) == "<Account: 'id' untrusted 'name'>"
    a.admin = True
    assert repr(a) == "<Account: 'id' untrusted, admin 'name'>"
    a.trusted = True
    assert repr(a) == "<Account: 'id' admin 'name'>"
    a.admin = False
    assert repr(a) == "<Account: 'id' 'name'>"


class TestSession:
  def setup_method(self, method):
    test_utils.setup()
    provider.registry.register(type(None), provider.IClock, FakeClock)

  def teardown_method(self, method):
    provider.registry.unregister(type(None), provider.IClock, FakeClock)

  def test_temporary(self):
    session = accounts.Session.temporary()
    assert session.id == 'temporary'

  def test_put(self):
    session = accounts.Session(id='id')
    key = session.put()
    assert key is not None
    session = accounts.Session.get(key)
    assert session.id == 'id'
    session.id = 'temporary'
    assert session.put() is None

  def test_load(self):
    session = accounts.Session.load('id1')
    assert session.id == 'id1'
    key = session.key()
    assert accounts.Session.all().filter('id =', 'id1').get().key() == key
    session = accounts.Session.load('id1')
    assert session.key() == key
    assert session.account.id == 'iq/anonymous'

  def test_expireAll(self):
    for i in xrange(2 * accounts.Session.LIFETIME_DAYS):
      session = accounts.Session.load('s%d' % i)
      session.created = FakeClock.NOW - datetime.timedelta(days=i)
      session.put()
    accounts.Session.expireAll()
    for i in xrange(2 * accounts.Session.LIFETIME_DAYS):
      session = accounts.Session.load('s%d' % i)
      logging.info('%s created %s', session.id, session.created)
      if i <= accounts.Session.LIFETIME_DAYS:
        assert session.created == FakeClock.NOW - datetime.timedelta(days=i)
      else:
        assert session.created > FakeClock.NOW


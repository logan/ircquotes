import accounts
import browse
import datetime
import test_utils

class TestPageSpecifier:
  def setup_method(self, method):
    test_utils.setup()

  def teardown_method(self, method):
    pass

  def test_init(self):
    p = browse.PageSpecifier('mode')
    assert p.size == browse.PageSpecifier.DEFAULT_SIZE
    p = browse.PageSpecifier('mode', size=browse.PageSpecifier.MAX_PAGE_SIZE)
    assert p.size == browse.PageSpecifier.MAX_PAGE_SIZE
    p = browse.PageSpecifier('mode',
                             size=browse.PageSpecifier.MAX_PAGE_SIZE + 1)
    assert p.size == browse.PageSpecifier.MAX_PAGE_SIZE

  def test_copy(self):
    now = datetime.datetime.now()
    then = now - datetime.timedelta(days=1)
    p1 = browse.PageSpecifier('mode',
                              start_value=now,
                              account=test_utils.Generic(id='account'),
                              context='context',
                             )
    p2 = p1.copy()
    assert p1.encode() == p2.encode()
    params = dict(start_value=then,
                  offset=1,
                  size=2,
                  reversed=True,
                  account=test_utils.Generic(id='account2'),
                  context='context2',
                 )
    p2 = p1.copy(mode='mode2', **params)
    p3 = browse.PageSpecifier('mode2', **params)
    assert p2.encode() == p3.encode()

  def test_encode_and_decode(self):
    p1 = browse.PageSpecifier('mode')
    p2 = browse.PageSpecifier.decode(p1.encode())
    assert p1.encode() == p2.encode()

    account = accounts.Account.createIq('name', 'email', 'password')

    p1 = browse.PageSpecifier('mode',
                              start_value=datetime.datetime.now(),
                              offset=123,
                              reversed=True,
                              account=account,
                              context='context',
                             )
    p2 = browse.PageSpecifier.decode(p1.encode())
    assert p1.encode() == p2.encode()

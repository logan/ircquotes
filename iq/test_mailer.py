import mailer
import test_utils

def test_TestingModeMailer():
  m = mailer.TestingModeMailer()
  assert m.getLastSentEmail() is None
  m.send('account', 'subject', 'body')
  assert m.getLastSentEmail() == 'To: account\nSubject: subject\n\nbody'
  account = test_utils.Generic(email='email')
  m.send(account, 'subject', 'body')
  assert m.getLastSentEmail() == 'To: email\nSubject: subject\n\nbody'

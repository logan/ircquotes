from google.appengine.api import mail

import provider

class IMailer(provider.Interface):
  def send(self, account, subject, body): pass


class TestingModeMailer:
  provider.implements(IMailer)

  def __init__(self):
    self.last_email = None

  def send(self, account, subject, body):
    if hasattr(account, 'email'):
      account = account.email
    self.last_email = 'To: %s\nSubject: %s\n\n%s' % (account, subject, body)

  def getLastSentEmail(self):
    return self.last_email


@provider.adapter(type(None), IMailer)
def test_mailer(_):
  return TestingModeMailer()


class ProductionModeMailer:
  provider.implements(IMailer)

  def send(self, account, subject, body):
    mail.send_mail(sender='IrcQuotes Adminstration <logan@ircquotes.com>',
                   to=account.email,
                   subject=subject,
                   body=body,
                  )

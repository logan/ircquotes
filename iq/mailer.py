from google.appengine.api import mail

class AbstractMailer:
  def send(self, account, subject, body):
    raise NotImplementedError


class TestingModeMailer(AbstractMailer):
  def send(self, account, subject, body):
    self.account = account
    self.subject = subject
    self.body = body

  def getLastSentEmail(self):
    return 'To: %s\nSubject: %s\n\n%s' % (
        self.account, self.subject, self.body)


class ProductionModeMailer(AbstractMailer):
  def send(self, account, subject, body):
    mail.send_mail(sender='IrcQuotes Adminstration <logan.hanks@gmail.com>',
                   to=account.email,
                   subject=subject,
                   body=body,
                  )

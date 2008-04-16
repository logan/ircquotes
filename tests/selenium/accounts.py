from iq import selenium

class CreateAccount(selenium.TestCase):
  def setUp(self):
    self.constants(name='testCreateAccount',
                   email='testCreateAccount@domain.invalid',
                   continueUrl='/?test=1',
                   createAccountLink='Create a new account',
                   createFormEmail='email',
                   createFormName='name',
                   createFormButton='Create Account',
                  )
    self.open('/testing/delete-account?name=${name}')
    self.verifyTextPresent('ok')
    self.open('/logout?url=${continueUrl}')
    self.clickAndWait('link=${createAccountLink}')

  def testCreateForm(self):
    def assertError(text):
      self.verifyTextPresent(text)

    def submit():
      self.clickAndWait("//input[@value='${createFormButton}']")

    def setName(value):
      self.type('${createFormName}', value)

    def setEmail(value):
      self.type('${createFormEmail}', value)

    MAX_NAME_LEN = 20
    MAX_EMAIL_LEN = 32

    self.constants(nameMissing=
                     'You must choose a name for this account.',
                   invalidEmail=
                     "This doesn't look like a valid email address.",
                   badCharInName=
                     "An account name may only contain letters, numerals,"
                     " apostrophes, spaces, and other characters acceptable"
                     " in IRC nicks.",
                   emailMissing=
	                   "You must provide a working email address in order to"
                     " create an account.",
                   nameTooLong=
                     "An account name may only be at most 20 characters in"
                     " length.",
                   emailTooLong=
                     "We only support email addresses up to 32 characters"
                     " long.",
                   nameMissingLetter=
                     "An account name must contain at least one letter.",
                  )

    setEmail('test')
    submit()
    assertError('${nameMissing}')
    assertError('${invalidEmail}')

    setEmail('')
    setName('test"ing')
    submit()
    assertError('${badCharInName}')
    assertError('${emailMissing}')

    setName('a' * (MAX_NAME_LEN + 1))
    setEmail('%s@x.invalid' % ('a' * (MAX_EMAIL_LEN - 9)))
    submit()
    assertError('${nameTooLong}')
    assertError('${emailTooLong}')

    setName('a' * MAX_NAME_LEN)
    submit()
    self.verifyTextNotPresent('${nameTooLong}')

    setName('a' * (MAX_NAME_LEN + 1))
    setEmail('%s@x.invalid' % ('a' * (MAX_EMAIL_LEN - 10)))
    submit()
    self.verifyTextNotPresent('${emailTooLong}')

    setName('{}')
    submit()
    assertError('${nameMissingLetter}')

    setName('${name}')
    submit()
    self.verifyElementPresent('activation_code')

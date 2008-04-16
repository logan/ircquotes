from iq import selenium

class CreateAccount(selenium.TestCase):
  def setUp(self):
    self.constants(name='testCreateAccount',
                   uname='TESTCREATEACCOUNT',
                   email='testCreateAccount@domain.invalid',
                   password='test',
                   badname='testCreateAccount|bad',
                   badnameError='invalid account name',
                   badpassError='password incorrect',
                   continueUrl='/?test=1',
                   createAccountLink='Create a new account',
                   createFormEmail='email',
                   createFormName='name',
                   createFormButton='Create Account',
                   passwordFormButton='Set Password',
                   signinFormButton='Login',
                   success=
                     'Congratuations, ${name}, your account has been activated!'
                     ' Continue.',
                   hello='Hello, ${name}',
                   signin='Sign In',
                  )
    self.deleteCookie('session')
    self.open('/testing/delete-account?name=${name}')
    self.assertTextPresent('ok')
    self.open('${continueUrl}')
    self.clickAndWait('link=${createAccountLink}')

  def createAccount(self, name='${name}', email='${email}'):
    self.type('${createFormName}', name)
    self.type('${createFormEmail}', email)
    self.clickAndWait("//input[@value='${createFormButton}']")
    self.assertElementPresent('activation_code')
    self.storeText("//div[@id='activation_code']", 'activationCode')

  def setPassword(self, skip_open=False):
    if not skip_open:
      self.open('/activate?name=${name}&activation=${activationCode}')
    self.type('password', '${password}')
    self.type('password2', '${password}')
    self.clickAndWait("//input[@value='${passwordFormButton}']")
    self.assertTextPresent('${success}')

  def testCreateForm(self):
    def assertError(text):
      self.assertTextPresent(text)

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
    self.assertTextNotPresent('${nameTooLong}')

    setName('a' * (MAX_NAME_LEN + 1))
    setEmail('%s@x.invalid' % ('a' * (MAX_EMAIL_LEN - 10)))
    submit()
    self.assertTextNotPresent('${emailTooLong}')

    setName('{}')
    submit()
    assertError('${nameMissingLetter}')

    setName('${name}')
    submit()
    self.assertElementPresent('activation_code')

  def testPasswordForm(self):
    self.constants(passwordMismatch='Passwords did not match',
                  )
    self.createAccount()
    self.open('/activate?name=${name}&activation=${activationCode}')
    self.type('password', 'test1')
    self.type('password', 'test2')
    self.clickAndWait("//input[@value='${passwordFormButton}']")
    self.assertTextPresent('${passwordMismatch}')
    self.setPassword(skip_open=True)

  def testContinuation(self):
    self.createAccount()
    self.setPassword()
    self.clickAndWait('link=Continue')
    self.assertTextPresent('${hello}')
    self.assertLocation('${baseUrl}${continueUrl}')

  def testSignin(self):
    self.createAccount()
    self.setPassword()
    self.open('/logout?url=/')
    self.open('/testing/delete-account?name=${badname}')
    self.open('/login?url=${continueUrl}')
    self.type('name', '${badname}')
    self.clickAndWait("//input[@value='${signinFormButton}']")
    self.assertTextPresent('${badnameError}')
    self.type('name', '${uname}')
    self.clickAndWait("//input[@value='${signinFormButton}']")
    self.assertTextPresent('${badpassError}')
    self.type('name', '${name}')
    self.type('password', '${password}')
    self.clickAndWait("//input[@value='${signinFormButton}']")
    self.assertTextPresent('${hello}')
    self.assertLocation('${baseUrl}${continueUrl}')

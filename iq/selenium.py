import logging
import os

ACTIONS = [
  'addSelection',
  'answerOnNextPrompt',
  'check',
  'chooseCancelOnNextConfirmation',
  'click',
  'clickAndWait',
  'clickAt',
  'close',
  'createCookie',
  'deleteCookie',
  'dragdrop',
  'fireEvent',
  'goBack()',
  'keyDown',
  'keyPress',
  'keyUp',
  'mouseDown',
  'mouseDownAt',
  'mouseMove',
  'mouseMoveAt',
  'mouseOut',
  'mouseOver',
  'mouseUp',
  'mouseUpAt',
  'open',
  'refresh',
  'removeSelection',
  'select',
  'selectFrame',
  'selectWindow',
  'setContext',
  'setCursorPosition',
  'setTimeout',
  'submit',
  'type',
  'uncheck',
  'waitForCondition',
  'waitForPageToLoad',
  'waitForPopUp',
  'windowFocus',
  'windowMaximize',
]

ASSERTION_MODES = [
  'store',
  'assert',
  'assertNot',
  'verify',
  'verifyNot',
  'waitFor',
  'waitForNot',
]

ACCESSORS = [
  'Alert',
  'AllButtons',
  'AllFields',
  'AllLinks',
  'AllWindowIds',
  'AllWindowNames',
  'AllWindowTitles',
  'Attribute',
  'AttributeFromAllWindows',
  'BodyText',
  'Confirmation',
  'Cookie',
  'CursorPosition',
  'ElementHeight',
  'ElementIndex',
  'ElementPositionLeft',
  'ElementPositionTop',
  'ElementWidth',
  'Eval',
  'Expression',
  'HtmlSource',
  'Location',
  'LogMessages',
  'Prompt',
  'SelectedId',
  'SelectedIds',
  'SelectedIndex',
  'SelectedIndexes',
  'SelectedLabel',
  'SelectedLabels',
  'SelectedValue',
  'SelectedValues',
  'SelectOptions',
  'Table',
  'Text',
  'Title',
  'Value',
  'WhetherThisFrameMatchFrameExpression',
  'AlertPresent',
  'Checked',
  'ConfirmationPresent',
  'Editable',
  'ElementPresent',
  'Ordered',
  'PromptPresent',
  'SomethingSelected',
  'TextPresent',
  'TextNotPresent',
  'Visible',
]


class TestCaseClass(type):
  def __new__(cls, *args, **kwargs):
    instance = type.__new__(cls, *args, **kwargs)
    def createEmitter(name):
      setattr(instance, name, lambda self, *args: self.emit(name, *args))
    for action in ACTIONS:
      createEmitter(action)
    for mode in ASSERTION_MODES:
      for accessor in ACCESSORS:
        createEmitter('%s%s' % (mode, accessor))
    return instance


class TestCase(object):
  __metaclass__ = TestCaseClass

  def __init__(self):
    self.table = []

  def setUp(self):
    pass

  def constants(self, **kwargs):
    for name, value in kwargs.iteritems():
      self.emit('store', name, value)

  def emit(self, *args):
    args = list(args)[:3]
    while len(args) < 3:
      args.append('')
    self.table.append(args)

  def emitCommand(self, cmd, args):
    self.emit(cmd, *args)


class TestSuite:
  def __init__(self):
    self.cases = []

  def addModule(self, mod):
    logging.debug('adding module: %s', mod)
    for name, value in mod.__dict__.iteritems():
      if isinstance(value, type) and issubclass(value, TestCase):
        self.addClass(value)
      else:
        if isinstance(value, type):
          logging.debug('issubclass(%s, %s) = %s', value, TestCase, issubclass(value, TestCase))

  def addClass(self, klass):
    logging.debug('adding class: %s', klass)
    for name, value in klass.__dict__.iteritems():
      if callable(value) and name.startswith('test'):
        logging.info('Found test case: %s.%s',
                     klass.__name__, name[len('test'):])
        self.cases.append((klass, name[len('test'):], value))

  def output(self, path):
    if not os.path.exists(path):
      os.makedirs(path)
    rows = []
    for case in self.cases:
      rows.append(self.outputTestCase(path, *case))

    f = self.startXhtml(path, 'suite.xml', 'Test Suite')
    print >> f, '<table id="suiteTable" cellpadding="1" cellspacing="1" border="1" class="selenium">'
    print >> f, '<tbody><tr><td><b>Test Suite</b></td></tr>'
    for row in rows:
      print >> f, row
    print >> f, '</tbody></table></body></html>'
    f.close()

  def outputTestCase(self, path, klass, name, case):
    instance = klass()
    instance.setUp()
    case(instance)
    qname = '%s.%s' % (klass.__name__, name)
    f = self.startXhtml(path, '%s.xml' % qname, qname)
    print >> f, 'table cellpadding="1" cellspacing="1" border="1">'
    print >> f, '<thead><tr><td colspan="3">%s</td></tr></thead>' % qname
    print >> f, '<tbody>'
    for row in instance.table:
      print >> f, '<tr>'
      for col in row:
        print >> f, '  <td>%s</td>' % self.escape(col)
      print >> f, '</tr>'
    print >> f, '</tbody></table></body></html>'
    f.close()
    return '<tr><td><a href="%s.xml">%s</a></td></tr>' % (qname, qname)

  def startXhtml(self, path, name, title):
    f = file(os.path.join(path, name), 'w')
    print >> f, '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" />
  <link rel="selenium.base" href="" />
  <title>%s</title>
</head>
<body>''' % title
    return f

  def escape(self, value):
    return (value.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
           )

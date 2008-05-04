import logging
import os
import py
import sys

logging.basicConfig(level=logging.DEBUG)

Option = py.test.config.Option

option = py.test.config.addoptions('iq options',
    Option('-G', '--googlebase', dest='googlebase',
           help='Path to the Google SDK.  If not given, will be determined'
                ' by looking at dev_appserver.py in PATH.'),
)

GOOGLE_DEPENDENCIES = ['', 'lib/yaml/lib']

if False and option.googlebase:
  base = option.googlebase
else:
  for path in os.environ['PATH'].split(os.pathsep):
    bin = os.path.join(path, 'dev_appserver.py')
    if os.path.exists(bin):
      logging.debug('Found dev_appserver.py at %s', bin)
      base = os.path.dirname(os.path.abspath(os.path.realpath(bin)))
      break
logging.debug('base = %r', base)
if base and os.path.isdir(base):
  logging.info('Located Google SDK at %s', base)
  for entry in GOOGLE_DEPENDENCIES:
    logging.debug('Adding Google dependency to PYTHONPATH: %s', entry)
    path = os.path.join(base, entry)
    if not os.path.isdir(path):
      logging.error('Expected to be a directory: %s', path)
      break
    if path not in sys.path:
      sys.path.append(path)

 
class IqDirectory(py.test.collect.Directory):
  def recfilter(self, path):
    # Disable recursion to force only top-level tests to be collected.
    return False

Directory = IqDirectory

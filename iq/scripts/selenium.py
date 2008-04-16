#!/usr/bin/env PYTHONPATH=. python

import imp
import logging
from optparse import OptionParser
import os
import sys

from iq import selenium

def loadModule(path, name):
  logging.debug('attempting to load module %s from %s', name, path)
  try:
    f, pathname, desc = imp.find_module(name, [path])
    logging.debug('found module, attempting to load')
    return imp.load_module(name, f, pathname, desc)
  except ImportError:
    logging.exception('Failed to import module: %s.py',
                      os.path.join(name, path))


def generateTestSuite(src_path, output_path, appbase):
  suite = selenium.TestSuite(baseUrl=appbase)
  logging.info('Building test suite from modules in %s', src_path)
  for root, dirs, files in os.walk(src_path):
    for name in files:
      if name.endswith('.py'):
        logging.debug('module candidate: %s/%s', root, name)
        mod = loadModule(root, name[:-len('.py')])
        if mod:
          suite.addModule(mod)
        else:
          logging.warn('failed to load module')
  suite.output(output_path)
  return suite
  

def main():
  parser = OptionParser(usage='usage: %prog [options] TESTPATH')
  parser.add_option('-a', '--appbase', dest='appbase',
                    default='http://iq-test.appspot.com',
                    help="URL of application to test.")
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                    help="Enable debug logging.")
  options, args = parser.parse_args()
  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug('verbose logging ON')
  if len(args) < 2:
    parser.error("Path to selenium test cases and output directory must be"
                 " provided.")
  generateTestSuite(args[0], args[1], options.appbase)


if __name__ == '__main__':
  main()

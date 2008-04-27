#!/usr/bin/env PYTHONPATH=. /usr/bin/python

import logging
from optparse import OptionParser
import MySQLdb

from iq.client import client
from iq.client import migrator

def main():
  parser = OptionParser(usage='usage: %prog [OPTIONS] [accounts|quotes]...')
  parser.add_option('-H', '--dbhost', dest='dbhost', default='localhost')
  parser.add_option('-p', '--dbpasswd', dest='dbpasswd', default='iq')
  parser.add_option('-u', '--dbuser', dest='dbuser', default='iq')
  parser.add_option('-d', '--dbname', dest='dbname', default='iq')
  parser.add_option('-a', '--appbase', dest='appbase',
                    default='http://localhost:8080')
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                    help="Enable debug logging.")
  parser.add_option('-t', '--threads', action='store', type='int',
                    dest='threads', help='Degree of parallelization.')
  parser.add_option('-A', '--all', action='store_true', dest='all',
                    help="Migrate everything.")
  parser.add_option('-U', '--userid', dest='userid', default='migrator')
  parser.add_option('-S', '--secret', dest='secret')
  parser.add_option('-r', '--rewrite', action='store_true', dest='rewrite')

  options, args = parser.parse_args()

  if not options.secret:
    parser.error('Specify API client secret with -S or --secret.')

  if options.all:
    targets = ['accounts', 'quotes']
  elif not args:
    parser.error('Specify migration targets in the command line, or use -A.')
  else:
    targets = args

  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.INFO)

  conn = MySQLdb.connect(host=options.dbhost,
                         user=options.dbuser,
                         passwd=options.dbpasswd,
                         db=options.dbname,
                        )

  c = client.IqJsonClient(options.userid, options.secret,
                          host=options.appbase,
                          baseuri='/json',
                          use_pickle=True,
                         )

  for target in targets:
    if target == 'accounts':
      migrator.MigrateAccounts(conn, c, options.rewrite)
    elif target == 'quotes':
      migrator.MigrateQuotes(conn, c, options.rewrite)
    else:
      parser.error('Invalid migration target specified.')
    print 'Done with %s!' % target
  print 'Done!'
  return 0

if __name__ == '__main__':
  main()

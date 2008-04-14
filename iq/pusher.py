#!/usr/bin/python

import logging
from optparse import OptionParser
import MySQLdb
import pickle
import urllib

class Pusher:
  def __init__(self, conn, appbase):
    self.conn = conn
    self.appbase = appbase

  def cursor(self):
    return self.conn.cursor()

  def post(self, uri, **params):
    ps = []
    for key, value in params.iteritems():
      if isinstance(value, (tuple, list)):
        for subvalue in value:
          ps.append((key, subvalue))
      else:
        ps.append((key, value))
    ps = urllib.urlencode(ps)
    f = urllib.urlopen('%s%s' % (self.appbase, uri), ps)
    return pickle.load(f)


def MigrateRatings(pusher):
  cursor = pusher.cursor()
  cursor.execute("SELECT user_id FROM users")
  for i, (user_id,) in enumerate(cursor.fetchall()):
    logging.info('Migrating ratings for user %d/%d', i + 1, cursor.rowcount)
    cursor.execute("SELECT quote_id, rating, UNIX_TIMESTAMP(rate_time)"
                   " FROM ratings WHERE user_id = %s", user_id)
    legacy_quote_ids = []
    values = []
    submitted = []
    for quote_id, rating, rate_time in cursor.fetchall():
      legacy_quote_ids.append(quote_id)
      values.append(rating)
      submitted.append(rate_time)
    logging.info('Clearing for %d', user_id)
    result = pusher.post('/rating', legacy_user_id=user_id, clear=1)
    if not result['ok']:
      print 'Error!  %s' % result['error']
      break
    if values:
      logging.info('Uploading %d ratings...', len(values))
      batch_size = 100
      for j in xrange(0, len(values), batch_size):
        logging.info('Posting %d-%d...', j + 1, j + batch_size)
        result = pusher.post('/rating',
                             legacy_user_id=user_id,
                             legacy_quote_id=legacy_quote_ids[j:j+batch_size],
                             value=values[j:j+batch_size],
                             submitted=submitted[j:j+batch_size],
                            )
        if not result['ok']:
          print 'Error!  %s' % result['error']
          break
    else:
      logging.info('No ratings to migrate')


def MigrateAccounts(pusher):
  cursor = pusher.cursor()
  cursor.execute("SELECT user_id, name, email, UNIX_TIMESTAMP(creation_time)"
                 " FROM users WHERE activation IS NULL")
  rows = cursor.fetchall()
  batch_size = 100
  for start in xrange(0, len(rows), batch_size):
    params = {}
    for i, (legacy_id, name, email, created) in enumerate(rows[start:start+batch_size]):
      params['legacy_id%d' % i] = legacy_id
      params['name%d' % i] = name
      params['email%d' % i] = email
      params['created%d' % i] = created
    print "Uploading %d accounts..." % (i + 1)
    result = pusher.post('/account', **params)
    if not result['ok']:
      print "Error!  %s" % result['error']
      break


def MigrateQuotes(pusher):
  print "Clearing all quotes!!!"
  result = pusher.post('/quote', clear=1)
  cursor = pusher.cursor()
  cursor.execute("SELECT quote_id, user_id, UNIX_TIMESTAMP(submit_time), quote"
                 ", network, server, channel, note"
                 ", UNIX_TIMESTAMP(modify_time)"
                 " FROM quotes")
  rows = cursor.fetchall()
  batch_size = 1
  for start in xrange(0, len(rows), batch_size):
    params = {}
    for i, quote in enumerate(rows[start:start+batch_size]):
      (legacy_id, legacy_user_id, submitted, source, network, server, channel,
       note, modified) = quote
      params['legacy_id%d' % i] = legacy_id
      params['legacy_user_id%d' % i] = legacy_user_id
      params['submitted%d' % i] = submitted
      params['source%d' % i] = source
      params['network%d' % i] = network
      params['server%d' % i] = server
      params['channel%d' % i] = channel
      params['note%d' % i] = note
      if modified:
        params['modified%d' % i] = modified
    print "Uploading %d quotes..." % (i + 1)
    result = pusher.post('/quote', **params)
    if not result['ok']:
      print "Error!  %s" % result['error']
      break


def main():
  parser = OptionParser()
  parser.add_option('-H', '--dbhost', dest='dbhost', default='localhost')
  parser.add_option('-p', '--dbpasswd', dest='dbpasswd', default='iq')
  parser.add_option('-u', '--dbuser', dest='dbuser', default='iq')
  parser.add_option('-d', '--dbname', dest='dbname', default='iq')
  parser.add_option('-a', '--appbase', dest='appbase',
                    default='http://localhost:8080/legacy')

  options, args = parser.parse_args()

  conn = MySQLdb.connect(host=options.dbhost,
                         user=options.dbuser,
                         passwd=options.dbpasswd,
                         db=options.dbname,
                        )

  pusher = Pusher(conn, options.appbase)

  #MigrateAccounts(pusher)
  #MigrateQuotes(pusher)
  MigrateRatings(pusher)


if __name__ == '__main__':
  main()

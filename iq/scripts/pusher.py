#!/usr/bin/python

import logging
from optparse import OptionParser
import MySQLdb
import pickle
import threading
import urllib

class Pusher:
  def __init__(self, conn, appbase, thread_count):
    self.conn = conn
    self.appbase = appbase
    self.thread_count = thread_count

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
    logging.debug('%s%s ? %s', self.appbase, uri, ps)
    f = urllib.urlopen('%s%s' % (self.appbase, uri), ps)
    return pickle.load(f)


class Worker(threading.Thread):
  def __init__(self, pusher, uri, work, id):
    threading.Thread.__init__(self)
    self.pusher = pusher
    self.uri = uri
    self.work = work
    self.id = id

  def run(self):
    for i in xrange(self.id, len(self.work), self.pusher.thread_count):
      logging.info('worker %d taking item %d', self.id, i)
      result = self.pusher.post(self.uri, **self.work[i])
      if not result['ok']:
        logging.error(result['error'])
        break
      logging.debug('worker %d on item %d: %s', self.id, i, result)
    logging.info('worker %d finished', self.id)


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
      logging.error(result['error'])
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
          logging.error(result['error'])
          break
    else:
      logging.info('No ratings to migrate')


def MigrateAccounts(pusher):
  cursor = pusher.cursor()
  cursor.execute("SELECT user_id, name, email, password"
                 ", UNIX_TIMESTAMP(creation_time)"
                 " FROM users WHERE activation IS NULL"
                 " ORDER BY user_id")
  work = []
  rows = cursor.fetchall()
  for row in rows:
    params = {}
    legacy_id, name, email, password, created = row
    params['legacy_id'] = legacy_id
    params['name'] = name
    params['email'] = email
    params['password'] = password
    params['created'] = created
    work.append(params)

  logging.info('Creating %d threads', pusher.thread_count)
  threads = [Worker(pusher, '/account', work, i) for i in xrange(pusher.thread_count)]
  logging.info('Starting %d threads', pusher.thread_count)
  for thread in threads:
    thread.start()
  logging.info('Waiting on %d threads', pusher.thread_count)
  for thread in threads:
    thread.join()
  logging.info('All threads completed!')


def MigrateQuotes(pusher, first=0):
  cursor = pusher.cursor()
  cursor.execute("SELECT quote_id, user_id, UNIX_TIMESTAMP(submit_time), quote"
                 ", network, server, channel, note"
                 ", UNIX_TIMESTAMP(modify_time)"
                 " FROM quotes WHERE quote_id > %s ORDER BY user_id, quote_id",
                 first)
  rows = cursor.fetchall()
  work = []
  for quote in rows:
    (legacy_id, legacy_user_id, submitted, source, network, server, channel,
     note, modified) = quote
    params = {}
    params['legacy_id'] = legacy_id
    params['legacy_user_id'] = legacy_user_id
    params['submitted'] = submitted
    params['source'] = source
    params['network'] = network
    params['server'] = server
    params['channel'] = channel
    params['note'] = note
    if modified:
      params['modified'] = modified
    work.append(params)

  logging.info('Creating %d threads', pusher.thread_count)
  threads = [Worker(pusher, '/quote', work, i) for i in xrange(pusher.thread_count)]
  logging.info('Starting %d threads', pusher.thread_count)
  for thread in threads:
    thread.start()
  logging.info('Waiting on %d threads', pusher.thread_count)
  for thread in threads:
    thread.join()
  logging.info('All threads completed!')


def main():
  parser = OptionParser()
  parser.add_option('-H', '--dbhost', dest='dbhost', default='localhost')
  parser.add_option('-p', '--dbpasswd', dest='dbpasswd', default='iq')
  parser.add_option('-u', '--dbuser', dest='dbuser', default='iq')
  parser.add_option('-d', '--dbname', dest='dbname', default='iq')
  parser.add_option('-a', '--appbase', dest='appbase',
                    default='http://localhost:8080/legacy')
  parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                    help="Enable debug logging.")
  parser.add_option('-t', '--threads', action='store', type='int',
                    dest='threads', help='Degree of parallelization.')

  options, args = parser.parse_args()
  if options.verbose:
    logging.basicConfig(level=logging.DEBUG)

  conn = MySQLdb.connect(host=options.dbhost,
                         user=options.dbuser,
                         passwd=options.dbpasswd,
                         db=options.dbname,
                        )

  pusher = Pusher(conn, options.appbase, options.threads)

  #MigrateAccounts(pusher)
  MigrateQuotes(pusher, 1283)
  #MigrateRatings(pusher)


if __name__ == '__main__':
  main()

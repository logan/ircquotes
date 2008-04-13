#!/usr/bin/python

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
    params = urllib.urlencode(params)
    f = urllib.urlopen('%s%s' % (self.appbase, uri), params)
    return pickle.load(f)


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

  MigrateAccounts(pusher)


if __name__ == '__main__':
  main()

import logging
import MySQLdb

from louie import dispatcher

def MigrateAccounts(db, client, rewrite=False):
  cursor = db.cursor()
  cursor.execute("SELECT user_id, name, email, password"
                 ", UNIX_TIMESTAMP(creation_time)"
                 " FROM users WHERE activation IS NULL"
                 " ORDER BY user_id")
  rows = cursor.fetchall()
  for i, row in enumerate(rows):
    params = {}
    user_id, name, email, password, created = row
    response = client.call_migrate_account(user_id=user_id,
                                           name=name,
                                           email=email,
                                           password=password,
                                           created=created,
                                           rewrite=rewrite and 1 or 0,
                                          )
    if response.status == 'saved':
      print '[Account: %3d/%d] Saved: %s' % (i + 1, len(rows), response.key)
    elif response.status.startswith('skipped'):
      print '[Account: %3d/%d] Skipped' % (i + 1, len(rows))
    else:
      logging.fatal('[Account: %3d/%d] Error: %s', i + 1, len(rows),
                    response.status)
      raise RuntimeError


def MigrateQuotes(db, client, rewrite=False):
  cursor = db.cursor()
  cursor.execute("SELECT quote_id, user_id, UNIX_TIMESTAMP(submit_time), quote"
                 ", network, server, channel, note"
                 ", UNIX_TIMESTAMP(modify_time)"
                 " FROM quotes ORDER BY user_id, quote_id")
  rows = cursor.fetchall()
  for i, quote in enumerate(rows):
    (quote_id, user_id, submitted, source, network, server, channel,
     note, modified) = quote
    response = client.call_migrate_quote(quote_id=quote_id,
                                         user_id=user_id,
                                         network=network,
                                         server=server,
                                         channel=channel,
                                         source=source,
                                         note=note,
                                         modified=modified,
                                         submitted=submitted,
                                         rewrite=rewrite and 1 or 0,
                                         anonymize_as_needed=1,
                                        )
    if response.status == 'saved':
      print '[Quote: %3d/%d] Saved: %s' % (i + 1, len(rows), response.key)
    elif response.status.startswith('skipped'):
      print '[Quote: %3d/%d] Skipped' % (i + 1, len(rows))
    else:
      logging.fatal('[Quote: %3d/%d] Error: %s', i + 1, len(rows),
                    response.status)
      raise RuntimeError


def MigrateRatings(db, client, offset=0):
  dead_users = [
    126,
    232,
    327,
    472,
    604,
    761,
  ]

  cursor = db.cursor()
  while True:
    cursor.execute("SELECT quote_id, user_id, rating FROM ratings"
                   " ORDER BY quote_id, user_id LIMIT %d,100"
                   % offset)
    rows = cursor.fetchall()
    if not rows:
      break
    for quote_id, user_id, rating in rows:
      if user_id not in dead_users:
        response = client.call_migrate_rating(quote_id=quote_id,
                                              user_id=user_id,
                                              value=rating,
                                             )
        if not response.ok:
          raise RuntimeError('Died with offset=%d: %s' % (offset, response.details))
      offset += 1
      print "Counter: %d" % offset

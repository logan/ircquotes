import client
import logging

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  c = client.IqJsonClient('http://localhost:8080', use_pickle=False)
  start = None
  offset = 0
  limit = 10
  response = c.call_rebuild_quotes(start=start, offset=offset, limit=limit, ignore_build_time=True)
  while response.quotes:
    for qid in response.quotes:
      print qid
    start = ','.join(map(str, response.start))
    offset = response.offset
    response = c.call_rebuild_quotes(start=start, offset=offset, limit=limit, ignore_build_time=True)
  print "Completed!"

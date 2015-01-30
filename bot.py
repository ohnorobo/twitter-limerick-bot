#!/usr/local/bin/python3

import tweepy
import os
import postgresql
from pprint import pprint
from keys import *

def log_error(msg):
  timestamp = time.strftime('%Y%m%d:%H%M:%S')
  sys.stderr.write("%s: %s\n" % (timestamp,msg))

def is_ascii(s):
  return all(ord(c) < 128 for c in s)

class StreamWatcherListener(tweepy.StreamListener):
  def on_status(self, status):

      # potentially add to db
      db.potential_add(status)

      # potentially tweet

  def on_error(self, status_code):
    log_error("Status code: %s." % status_code)
    time.sleep(3)
    return True  # keep stream alive

  def on_timeout(self):
    log_error("Timeout.")


class Database():
  def potential_add(self, tweet):

    if (is_ascii(tweet.text) and tweet.lang == "en"):
      pprint(tweet.text)
      pprint(tweet.id)


#main
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
db = Database()

listener = StreamWatcherListener()
stream = tweepy.Stream(auth, listener)
stream.sample()



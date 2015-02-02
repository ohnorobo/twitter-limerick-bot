#!/usr/local/bin/python3

import os, time, sys
import tweepy
import postgresql
from pprint import pprint
from keys import *

def log_error(msg):
  timestamp = time.strftime('%Y%m%d:%H%M:%S')
  sys.stderr.write("%s: %s\n" % (timestamp,msg))

def is_ascii(s):
  return all(ord(c) < 128 for c in s)

def contains_digit(string):
  return any(char.isdigit() for char in string)

# turns a list if lists into a single list
def flatten(l):
  return [item for sublist in l for item in sublist]




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

  def __init__(self):
    self.mr = MeterReader()

  def potential_add(self, tweet):

    if self.validate(tweet):
      if (self.mr.valid_meter(tweet.text)):
        pprint(tweet.text)
        pprint(tweet.id)

  # meets some strict list of criteria for inclusion
  # ascii only
  # english only
  # no retweets
  # no included links
  def validate(self, tweet):
    return is_ascii(tweet.text) and \
           tweet.lang == "en"



class MeterReader():

  # 0    — No stress
  # 1    — Primary stress
  # 2    — Secondary stress

  def __init__(self):
    self.dic = CMUDict()

  def valid_meter(self, text):
    text = text.split(' ')

    try:
      num = self.num_sylls(text)
      print(num)
    except KeyError:
      return False

    if 8 <= num <= 10:
      if self.matchlong(text, num):
        return "long"

    if 5 <= num <= 7:
      if self.matchshort(text, num):
        return "short"

    return False

  # return the number of sylls in a text
  def num_sylls(self, text):
    return sum(map(self.dic.sylls, text))

  # match the pattern 
  # + ˘ / ˘ ˘ / ˘ ˘ / +
  # where single-syll words match either way
  # and +s are optional ˘
  def matchlong(self, text, num_sylls):

    stresses = self.stresses(text)
    single_syll_words = self.single_syll_words(text)

    # possible options
    #  ./../../   8
    #  ./../../.  9
    # ../../../   9
    # ../../../.  10

    if num_sylls == 8:
      return self.match_pattern(stresses, single_sylls, [1, 0, 1, 1, 0])
    else if num_sylls == 9:
      return self.match_pattern(stresses, single_sylls, [1, 0, 1, 1, 0, 1]) or
             self.match_pattern(stresses, single_sylls, [1, 1, 0, 1, 1, 0])
    else if num_sylls == 10:
      return self.match_pattern(stresses, single_sylls, [1, 1, 0, 1, 1, 0, 1])

    #pprint(stresses)
    #pprint(single_syll_words)

  # match the pattern 
  # + ˘ / ˘ ˘ / +
  # where single sylls count either way
  # and +s are optional ˘
  def matchshort(self, text, num_sylls):

    stresses = self.stresses(text)
    single_syll_words = self.single_syll_words(text)

    # possible options
    #  ./../   5
    #  ./../.  6
    # ../../   6
    # ../../.  7

    if num_sylls == 5:
      return self.match_pattern(stresses, single_sylls, [1, 0, 1, 1, 0])
    else if num_sylls == 6:
      return self.match_pattern(stresses, single_sylls, [1, 0, 1, 1, 0, 1]) or
             self.match_pattern(stresses, single_sylls, [1, 1, 0, 1, 1, 0])
    else if num_sylls == 7:
      return self.match_pattern(stresses, single_sylls, [1, 1, 0, 1, 1, 0, 1])

    #pprint(stresses)
    #pprint(single_syll_words)


  #the stress corrosponding th each syllable
  def stresses(self, text):
    return flatten(map(self.dic.stresses, text))

  # whether each syllable is a single word
  def single_syll_words(self, text):
    return flatten(map(self.dic.single_syll, text))


  def match_pattern(self, stresses, single_sylls, pattern):
    # stresses is a list of 0-1-2s
    # single sylls is a list of true-falses
    # patterns is a list of 0-1s




class CMUDict():

  def __init__(self):

    f = open("./cmudict/cmudict-0.7b")

    d = {}
    for line in f:
      word, syllbit = line.split("  ") # two spaces
      sylls = syllbit.strip().split(' ') # one space
      d[word]=(self.parse_stresses(sylls),
               self.parse_rhyme(sylls),
               self.parse_num_sylls(sylls))

      #pprint((line, d))
    self.dic = d

  # returns the number of sylls in a word
  def parse_num_sylls(self, sylls):
    return len(list(filter(contains_digit, sylls)))

  # returns a list of 0s 1s and 2s, 
  # corrosponding to the stresses in the given syllables
  def parse_stresses(self, sylls):
    stresses = []
    for syll in sylls:
      if '0' in syll:
        stresses.append(0)
      if '1' in syll:
        stresses.append(1)
      if '2' in syll:
        stresses.append(2)

    return stresses

  # returns a string which represents the rhyme for the word
  def parse_rhyme(self, sylls):
    return sylls[-1]
    #TODO how many strings are best?

  def sylls(self, word):
    return self.dic[word.upper()][2]

  def stresses(self, word):
    return self.dic[word.upper()][0]

  def rhyme(self, word):
    return self.dic[word.upper()][1]

  # returns [True] if it's a single syll word
  # returns [False False ...] for any multi-syll word
  # number of falses matches number of sylls
  def single_syll(self, word):
    sylls = self.dic[word.upper()][2]

    if sylls == 1:
      return [True]
    else:
      return [False]*sylls





#main
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
db = Database()

listener = StreamWatcherListener()
stream = tweepy.Stream(auth, listener)

# stream.filter(languages=["en"])
# this doesn't seem to work at the moment
# https://github.com/tweepy/tweepy/issues/291

stream.sample()



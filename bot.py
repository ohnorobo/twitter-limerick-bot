#!/usr/local/bin/python3

import os, time, sys
import tweepy
import postgresql
from pprint import pprint
from keys import *


VOWELS = ['A', 'E', 'I', 'O', 'U'] # vowels parts in the CMU phone schema

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
    db = postgresql.open(user='slaplante', password='',
                         database='limerickdb',
                         host='localhost', port=5432)
    self.add = db.prepare("INSERT INTO limericks VALUES ($1, $2, $3, $4)")


    self.mr = MeterReader()


  def potential_add(self, tweet):

    if self.validate(tweet):
      # Valid is one of "long" "short" False
      valid = self.mr.valid_meter(tweet.text)

      if (valid):
        pprint(tweet.text)
        pprint(tweet.id)
        pprint(valid)
        rhyme = self.mr.rhyme(tweet.text)

        self.add(tweet.id, tweet.text, rhyme,
                 self.long_not_short(valid))

  # long or short is stored in the db as a boolean
  # T = long
  # F = short
  def long_not_short(self, lors):
    if lors == "long":
      return True
    elif lors == "short":
      return False
    else:
      print("AAAHHH")


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

  def rhyme(self, text):
    text = text.split(' ')
    # get last 2 words for the rhyme
    final_sylls = flatten([self.dic.sound_sylls(word) for word in text[-2:]])

    for i, syll in enumerate(reversed(final_sylls)):
      if any(vowel in syll for vowel in VOWELS):
        break

    # TODO, this includes the consonant before the last vowel
    # is that really what we want?
    # maybe it should just be core+ryme
    # or head+core if there's no ryme
    # tho -> DH-OW
    # family -> L-IY
    rhyme_sylls = final_sylls[-1*(i+2):]
    st = "-".join(rhyme_sylls)
    print(st)
    return st;



  def valid_meter(self, text):
    text = text.split(' ')

    try:
      num = self.num_sylls(text)
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
    return sum(map(self.dic.num_sylls, text))

  # match the pattern 
  # + ˘ / ˘ ˘ / ˘ ˘ / +
  # where single-syll words match either way
  # and +s are optional ˘
  def matchlong(self, text, num_sylls):

    stresses = self.stresses(text)
    single_sylls = self.single_syll_words(text)

    #pprint(stresses)
    #pprint(single_syll_words)

    # possible options
    #  ./../../   8
    #  ./../../.  9
    # ../../../   9
    # ../../../.  10

    if (num_sylls == 8):
      return self.match_pattern(text, stresses, single_sylls, [1,0,1,1,0,1,1,0])
    elif (num_sylls == 9):
      return self.match_pattern(text, stresses, single_sylls, [1,0,1,1,0,1,1,0,1]) or \
             self.match_pattern(text, stresses, single_sylls, [1,1,0,1,1,0,1,1,0])
    elif (num_sylls == 10):
      return self.match_pattern(text, stresses, single_sylls, [1,1,0,1,1,0,1,1,0,1])

  # match the pattern 
  # + ˘ / ˘ ˘ / +
  # where single sylls count either way
  # and +s are optional ˘
  def matchshort(self, text, num_sylls):

    stresses = self.stresses(text)
    single_sylls = self.single_syll_words(text)

    #pprint(stresses)
    #pprint(single_syll_words)

    # possible options
    #  ./../   5
    #  ./../.  6
    # ../../   6
    # ../../.  7

    if (num_sylls == 5):
      return self.match_pattern(text, stresses, single_sylls, [1,0,1,1,0])
    elif (num_sylls == 6):
      return self.match_pattern(text, stresses, single_sylls, [1,0,1,1,0,1]) or \
             self.match_pattern(text, stresses, single_sylls, [1,1,0,1,1,0])
    elif (num_sylls == 7):
      return self.match_pattern(text, stresses, single_sylls, [1,1,0,1,1,0,1])

  #the stress corrosponding th each syllable
  def stresses(self, text):
    return flatten(map(self.dic.stresses, text))

  # whether each syllable is a single word
  def single_syll_words(self, text):
    return flatten(map(self.dic.single_syll, text))


  def match_pattern(self, text, stresses, single_sylls, pattern):
    # stresses is a list of 0-1-2s
    # single sylls is a list of true-falses
    # patterns is a list of 0-1s
    # all lists must be the same length

    for tex, stress, single_syll, patt in zip(text, stresses, single_sylls, pattern):
      if stress == patt:
        pass
      elif stress == 2: # secondary stress can be either off or on
        pass
      elif single_syll == True:
        # TODO this is probably to permissive a condition
        # figure out something more restrained
        # maybe don't allow stress on single-syll stop words
        # http://xpo6.com/list-of-english-stop-words/
        if tex.lower() in STOPWORDS:
          if patt == 1:
            pass
          else:
            return False
        else:
          if patt == 0:
            pass
          else:
            return False

      else:
        return False

    print(pattern)
    return True

STOPWORDS = ["a", "the", "for", "am", "an", "are", "as", "at", "be", "but",
             "he", "her", "i", "if", "in", "is", "it", "it's", "my", "of", "on",
             "or", "and", "our", "his", "her", "out", "so", "such", "than", "these",
             "this", "that", "those", "to", "too"]


class CMUDict():

  # dic is a dicitonary of 
  # { words : [stresses, syllable_sounds, number_of_sylls] }

  def __init__(self):

    f = open("./cmudict/cmudict-0.7b")

    d = {}
    for line in f:
      word, syllbit = line.split("  ") # two spaces
      sylls = syllbit.strip().split(' ') # one space
      d[word]=(self.parse_stresses(sylls),
               self.parse_syll_sounds(sylls),
               self.parse_num_sylls(sylls))
    self.dic = d

  # returns the number of sylls in a word
  def parse_num_sylls(self, sylls):
    return len(list(filter(contains_digit, sylls)))

  def parse_syll_sounds(self, sylls):
    return [self.remove_num(syll) for syll in sylls]

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
  #def parse_rhyme(self, sylls):
  #  return sylls[-1]
  #  #TODO how many strings are best?

  def num_sylls(self, word):
    return self.dic[word.upper()][2]

  # like sylls, but removes stress #s in syllables
  def sound_sylls(self, word):
    #print((word, self.dic[word.upper()]))
    return [self.remove_num(syll) for syll in self.dic[word.upper()][1]]

  def remove_num(self, syll):
    if '0' in syll or '1' in syll or '2' in syll:
      return syll[:-1]
    else:
      return syll

  def stresses(self, word):
    return self.dic[word.upper()][0]

  #def rhyme(self, word):
  #  return self.dic[word.upper()][1]

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



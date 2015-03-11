#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import os, time, sys, re, traceback
import tweepy
from pprint import pprint
from keys import *  #this is another python file that defines your twitter/db credentials
from offensive import offensive


VOWELS = ['A', 'E', 'I', 'O', 'U'] # vowels parts in the CMU phone schema

# http://www.noswearing.com/
BLACKLIST = ["arse", "ass", "asshole", "bastard", "bitch", "bloody", "bollocks", "boner",
             "chode", "choad", "clusterfuck", "cock", "cooch", "cooter", "cunt", "cum",
             "damn", "dick", "douche", "dumbass", "dumbfuck", "fuck", "fuckface", #"fucking",
             "fuckup", "goddamn", "goddamnit", "hell", "jackass", "motherfucker", "motherfucking",
             "piss", "pissed", "poon", "prick", "pussy", "queef", "schlong", "shit", "smeg",
             "smegma", "splooge", "tit", "tits", "twat", "vag", "wank"]




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
    # pprint(status.text)
    db.potential_add(status)


  def on_error(self, status_code):
    log_error("Status code: %s." % status_code)
    if status_code == 420:
      pprint("Enhance your calm")
      time.sleep(120)
    else:
      time.sleep(3)
    return True  # keep stream alive

  def on_exception(self, exception):
    pprint(exception)
    time.sleep(3)
    return True

  def on_timeout(self):
    log_error("Timeout.")

  def try_to_tweet(self):
    # TODO look for a pair and a triple
    # tweet if you can
    pass

  # given 5 tweet ids that form a tweet
  def tweet(self, long_ids, short_ids):
    tweepy.retweet(long_ids[0])
    tweepy.retweet(long_ids[1])
    tweepy.retweet(short_ids[0])
    tweepy.retweet(short_ids[1])
    tweepy.retweet(long_ids[2])

    db.deletepair(long_ids[0], long_ids[1])
    db.deletetriple(long_ids[0], long_ids[1], long_ids[2])





class Database():

  def __init__(self):
    import postgresql # importing this earlier messes up nosetests

    db = postgresql.open(user='slaplante', password='',
                         database='limerickdb',
                         host='localhost', port=5432)

    self.addtweet = db.prepare("INSERT INTO lines VALUES ($1, $2, $3, $4)")
    self.deletetweet = db.prepare("DELETE FROM lines WHERE id=$1")
    self.search = db.prepare("SELECT id, tweet FROM lines WHERE length=$1 AND rhyme=$2")

    self.addpair = db.prepare("INSERT INTO pairs VALUES ($1, $2, $3, $4)")
    self.addtriple = db.prepare("INSERT INTO triples VALUES ($1, $2, $3, $4, $5, $6)")

    self.deletepair = db.prepare("DELETE FROM pairs WHERE id_a=$1 AND id_b=$2")
    self.deletepair = db.prepare("DELETE FROM triples WHERE id_a=$1 AND id_b=$2 AND id_c=$3")

    self.mr = MeterReader()

  # add a tweet to the db if it is valid
  def potential_add(self, tweet):

    if self.validate(tweet):
      #pprint(tweet.text)
      # Valid is one of "long", "short", or False
      valid, pattern = self.mr.valid_meter(tweet.text)

      if (valid):
        pprint("VALID PATTERN")
        pprint(pattern)
        pprint(tweet.text)
        pprint(tweet.id)
        pprint(valid)
        rhyme = self.mr.rhyme(tweet.text)
        self.addtweet(tweet.id, tweet.text, rhyme, self.long_not_short(valid))

        if valid == 'long':
          self.potential_triple(rhyme)
        elif valid == 'short':
          self.potential_pair(rhyme)


  # moved short tweets from db to pair table if possible
  def potential_pair(self, rhyme):
    search = self.search(self.long_not_short("short"), rhyme)
    ids, texts, final_words, wordset = self.get_elements(search)

    if len(wordset) == 2:
      indexes = [final_words.index(word) for word in wordset]
      print(("IDS pair", ids, texts))
      self.addpair(ids[indexes[0]], ids[indexes[1]],
                   texts[indexes[0]], texts[indexes[1]])
      for ida in ids:
        self.deletetweet(ida)

  # given a db search returns
  #  - list of ids
  #  - list of texts
  #  - list of final words in thos texts
  #  - set (uniq) of final words in those texts
  #  TODO move indexing into this method
  def get_elements(self, search):
    ids = [x[0] for x in search]
    texts = [x[1] for x in search]
    final_words = [text.split(" ")[-1].upper() for text in texts]
    wordset = list(set(final_words))

    return ids, texts, final_words, wordset


  # moved long tweets from db to triple table if possible
  def potential_triple(self, rhyme):
    search = self.search(self.long_not_short("long"), rhyme)
    ids, texts, final_words, wordset = self.get_elements(search)

    if len(wordset) == 3:
      indexes = [final_words.index(word) for word in wordset]
      print(("IDS triple", ids, texts))
      self.addtriple(ids[indexes[0]], ids[indexes[1]], ids[indexes[2]],
                     texts[indexes[0]], texts[indexes[1]], texts[indexes[2]])
      for ida in ids:
        self.deletetweet(ida)


  # long or short is stored in the db as a boolean
  # T = long
  # F = short
  def long_not_short(self, lors):
    if lors == "long":
      return True
    elif lors == "short":
      return False
    else:
      raise Exception("lors value is illegal", lors)


  # meets some strict list of criteria for inclusion
  # ascii only
  # no retweets
  # no included links
  # nothing really terrible
  def validate(self, tweet):
    return is_ascii(tweet.text) and self.tact(tweet.text)

  def tact(self, text):
    return re.search(offensive, text) is None



class MeterReader():

  # 0    — No stress
  # 1    — Primary stress
  # 2    — Secondary stress

  def __init__(self):
    self.dic = CMUDict()

  # return a string representing the rhyme for a text
  # "march at dawm" -> "AW-N"
  def rhyme(self, text):
    text = text.split(' ')
    # get last 2 words for the rhyme
    final_sylls = flatten([self.dic.sound_sylls(word) for word in text[-2:]])

    for i, syll in enumerate(reversed(final_sylls)):
      if any(vowel in syll for vowel in VOWELS):
        break

    # this is the ryme of the last syllable
    # family -> y
    # cats -> ats
    # boo -> oo
    rhyme_sylls = final_sylls[-1*(i+1):]
    st = "-".join(rhyme_sylls)
    print(st)
    return st;


  # checks if meter is valid for a limerick
  # and returns 'long' or 'short' if valid, False otherwise
  # and the matched pattern or [] if there is no pattern
  def valid_meter(self, text):
    text = text.split(' ')

    try:
      num = self.num_sylls(text)
    except KeyError:
      return False, []

    if 8 <= num <= 10:
      match, pattern = self.matchlong(text, num)
      if match:
        return "long", pattern

    if 5 <= num <= 7:
      match, pattern = self.matchshort(text, num)
      if match:
        return "short", pattern

    return False, []

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
    tex = self.get_syllables(text)

    #pprint(stresses)
    #pprint(single_syll_words)

    # possible options
    #  ./../../   8
    #  ./../../.  9
    # ../../../   9
    # ../../../.  10

    if (num_sylls == 8):
      return self.match_pattern(tex, stresses, single_sylls, [0,1,0,0,1,0,0,1])
    elif (num_sylls == 9):
      return self.match_pattern(tex, stresses, single_sylls, [0,1,0,0,1,0,0,1,0]) or \
             self.match_pattern(tex, stresses, single_sylls, [0,0,1,0,0,1,0,0,1])
    elif (num_sylls == 10):
      return self.match_pattern(tex, stresses, single_sylls, [0,0,1,0,0,1,0,0,1,0])

  # match the pattern 
  # + ˘ / ˘ ˘ / +
  # where single sylls count either way
  # and +s are optional ˘
  def matchshort(self, text, num_sylls):

    stresses = self.stresses(text)
    single_sylls = self.single_syll_words(text)
    tex = self.get_syllables(text)

    #pprint(stresses)
    #pprint(single_syll_words)

    # possible options
    #  ./../   5
    #  ./../.  6
    # ../../   6
    # ../../.  7

    if (num_sylls == 5):
      return self.match_pattern(tex, stresses, single_sylls, [0,1,0,0,1])
    elif (num_sylls == 6):
      return self.match_pattern(tex, stresses, single_sylls, [0,1,0,0,1,0]) or \
             self.match_pattern(tex, stresses, single_sylls, [0,0,1,0,0,1])
    elif (num_sylls == 7):
      return self.match_pattern(tex, stresses, single_sylls, [0,0,1,0,0,1,0])

  #the stress corrosponding th each syllable
  def stresses(self, text):
    return flatten(map(self.dic.stresses, text))

  # whether each syllable is a single word
  def single_syll_words(self, text):
    return flatten(map(self.dic.single_syll, text))

  # returns syllables for a list of words
  # ["see", "you", "later"] -> ["EE", "OU", "AY", "ER"]
  def get_syllables(self, text):
    return flatten(map(self.dic.vowel_sound_sylls, text))

  # does the text match the given stress pattern?
  def match_pattern(self, text, stresses, single_sylls, pattern):
    # stresses is a list of 0-1-2s
    # single sylls is a list of true-falses
    # patterns is a list of 0-1s
    # all lists must be the same length

    if not (len(text) == len(stresses) == len(single_sylls) == len(pattern)):
      pprint("ABORT")
      pprint((text, stresses, single_sylls, pattern))
      return Exception("unequal pattern lengths")

    for tex, stress, single_syll, patt in zip(text, stresses, single_sylls, pattern):
      #pprint((tex, stress, single_syll, patt))
      #if stress == patt:
      #  pass
      #elif stress == 2: # secondary stress can be either off or on
      #  pass
      #elif single_syll == True:
      is_stopword = tex.lower() in STOPWORDS

      # no stress
      if patt == 0:
        #print("weak")
        pass
      # non-stopwords and stress
      elif patt in [1,2] and not is_stopword and not single_syll:
        #pprint("strong")
        pass
        # TODO use textblob to do pos tagging here?
      else:
        #pprint("failed")
        return False, pattern

      #else:
      #  #pprint("failed")
      #  return False, pattern

    print(pattern)
    return True, pattern

# TODO this is probably too permissive a condition
# figure out something more restrained
# maybe don't allow stress on single-syll stop words
# http://xpo6.com/list-of-english-stop-words/
STOPWORDS = ["a", "the", "for", "am", "an", "are", "as", "at", "be", "but",
             "he", "her", "i", "is", "if", "in", "is", "it", "it's", "my", "of", "on",
             "or", "and", "our", "his", "her", "out", "so", "such", "than", "these",
             "this", "that", "those", "there", "to", "too"]


class CMUDict():

  # dic is a dicitonary of 
  # { words : [stresses, syllable_sounds, number_of_sylls] }
  #   - stresses is a list of numbers, [1, 0, 0, 2, 1]
  #   - syllable sounds is a list of words, ['D', 'AW', 'N']
  #   - number of sylls is a number, 4

  # Stresses are
  # 0    — No stress
  # 1    — Primary stress
  # 2    — Secondary stress

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

  # returns syllables for a word but removes numbers
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

  # returns number of syllables in a word
  def num_sylls(self, word):
    return self.dic[word.upper()][2]

  # like sylls, but removes stress #s in syllables
  def sound_sylls(self, word):
    return [self.remove_num(syll) for syll in self.dic[word.upper()][1]]

  # like sylls, but removes stress #s in syllables
  # and onlt returns syll cores
  def vowel_sound_sylls(self, word):
    sylls = self.sound_sylls(word)
    return filter(lambda syll: any([vowel in syll for vowel in VOWELS]), sylls)



  # DH -> DH
  # AY1 -> AY
  def remove_num(self, syll):
    if contains_digit(syll):
      return syll[:-1]
    else:
      return syll

  # returns the stress pattern a a list of numbers
  # [0, 1, 0, 2, 1]
  def stresses(self, word):
    return self.dic[word.upper()][0]

  # returns [True] if it's a single syll word
  # returns [False False ...] for any multi-syll word
  # number of falses matches number of sylls
  def single_syll(self, word):
    sylls = self.dic[word.upper()][2]

    if sylls == 1:
      return [True]
    else:
      return [False]*sylls



import unittest

class TestCMU(unittest.TestCase):

  dic = CMUDict()

  def TestVowelSylls(self):
    self.assertEqual(self.dic.vowel_sound_sylls('Allergies'), ['AE', 'ER', 'IY'])



class TestMeter(unittest.TestCase):

  # only set this up once, it's expensive
  mr = MeterReader()

  def TestMatchLong(self):
                                      #   .        /    .      .       /   .     .       /    .
    self.assertTrue(self.mr.matchlong(["There", "was", "a", "young", "sailor", "from", "Brighton"], 9))
                                      #   .     /      .      .      /        .       .      /       .
    self.assertTrue(self.mr.matchlong(["Who", "said", "to", "his", "girl", "you're", "a", "tight", "one"], 9))

                                       # .      /   .     .    .     /      .   /   .      /
    self.assertFalse(self.mr.matchlong(["A", "blender", "is", "a", "good", "investment", "right"], 10)[0])


  def TestMatchShort(self):
                                       #   .     .   /       .       .      /
    self.assertTrue(self.mr.matchshort(["She", "replied", "bless", "my", "soul"], 6))
                                    #   .        /    .        .        /
    # self.assertTrue(mr.matchshort(["You're", "in", "the", "wrong", "hole"], 5))
    # fails to put stress on the 'in'


  def TestMatchSingleSylls(self):
                                       #    .     .      /     .      .      /
    self.assertTrue(self.mr.matchshort(["The", "cat", "sat", "on", "the", "mat"], 6))

  def TestMatchPattern1(self):
           # .    /  .  .  /
    text = "That son of a bitch".split()
    stresses = self.mr.stresses(text)
    single_sylls = self.mr.single_syll_words(text)
    tex = self.mr.get_syllables(text)

    self.assertTrue(self.mr.match_pattern(tex, stresses, single_sylls, [0, 1, 0, 0, 1]))

  def TestMatchPattern2(self):
           # .   /  .   .  .  /
    text = "My brother is a douche".split()
    stresses = self.mr.stresses(text)
    single_sylls = self.mr.single_syll_words(text)
    tex = self.mr.get_syllables(text)

    self.assertFalse(self.mr.match_pattern(tex, stresses, single_sylls, [0, 1, 0, 0, 1, 0])[0])


  def TestMatchPattern3(self):
           # .   /  .   .  /   .    /
    text = "But damn do I love my friends".split()
    stresses = self.mr.stresses(text)
    single_sylls = self.mr.single_syll_words(text)
    tex = self.mr.get_syllables(text)

    self.assertFalse(self.mr.match_pattern(tex, stresses, single_sylls, [0, 0, 1, 0, 0, 1, 0])[0])


  def TestMatchPattern4(self):
           # /  .  .   /   .    .  /
    text = "Allergies can suck my ass".split()
    stresses = self.mr.stresses(text)
    single_sylls = self.mr.single_syll_words(text)
    tex = self.mr.get_syllables(text)

    self.assertFalse(self.mr.match_pattern(tex, stresses, single_sylls, [0, 0, 1, 0, 0, 1, 0])[0])

  def TestMatchPattern5(self):
           # .   /  .   .  /  .
    text = "My brother is silly".split()
    stresses = self.mr.stresses(text)
    single_sylls = self.mr.single_syll_words(text)
    tex = self.mr.get_syllables(text)

    self.assertTrue(self.mr.match_pattern(tex, stresses, single_sylls, [0, 1, 0, 0, 1, 0])[0])







if __name__ == "__main__":

  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(access_token, access_token_secret)
  db = Database()

  listener = StreamWatcherListener()
  stream = tweepy.Stream(auth, listener, timeout=35)

  while True:
    try:
      print("trying to sample")
      #stream.sample()
      stream.filter(track=BLACKLIST, languages=["en"])
    except Exception as e:
      #pprint(e)
      pprint("Restarting")
      time.sleep(5)
      continue



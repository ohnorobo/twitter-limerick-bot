
##Under construction


####twitter

reads in from the twitter firehose
sends tweets to meter

retweets 5 tweets at a time when directed by db



####meter-checker

reads a tweet, determines if it is 
 anapestic and the right number of syllables

sends a save message to db if it is
  save message includes a rime key and an indication of which db to save to


####db

saves tweets when directed, 

2 tables
  one for 5-6 syllable lines, indexed by rime
  one for 7-9 syllable lines, indexed on rime

when adding new entries to the table check for existing entries with that rime/syllable count (slightly different syllable counts for different lines in the same limrick seem to be okay)
of there are 2 entries for short lines, or three entries for longer lines, add them to a queue of matches

when there is a set of matches for both short and long lines then retweet all 5 in order long-long-short-short-long, evict those 5 entries from the db


˘ = weak

/ = strong


anapestic = ˘ ˘ /



limerick form:

5 anapestic lines,·

˘ ˘ / ˘ ˘ / ˘ ˘ /

˘ ˘ / ˘ ˘ / ˘ ˘ /

˘ ˘ / ˘ ˘ /

˘ ˘ / ˘ ˘ /

˘ ˘ / ˘ ˘ / ˘ ˘ /

The first ˘ on any line can usually be dropped without trouble

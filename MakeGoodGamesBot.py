# -*- coding: utf-8 -*-
#MakeGoodGamesBot

#Requiered libraries
from twitter import *
from collections import Counter
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler, API
from tweepy import Stream
import time
import pandas as pd
import matplotlib.pyplot as plt
import json
import random as rd
#import seaborn as sns

#Auth keys and tokens.   
ds = pd.read_pickle('dogge_secret')
consumer_key        = ds[0]
consumer_secret     = ds[1]
access_token        = ds[2]
access_token_secret = ds[3]

#Initially exploring to Python APIs sixohsix and Tweepy. Now the bot uses both for different purposes.
#Probably going to modify soon for only one.

#Twitter (sixohsix) client
t  =  Twitter(auth=OAuth(access_token, access_token_secret, consumer_key, consumer_secret))

#Tweepy client
auth_handler = OAuthHandler(consumer_key, consumer_secret)
auth_handler.set_access_token(access_token, access_token_secret)
twitter_client = API(auth_handler)


#Date and data
def get_date():
    today = time.localtime()
    date = str(today[0])+'-'+str(today[1])+'-'+str(today[2])
    return date

try:
    banRT = list(pd.read_pickle('ban_RT'))
    banTXT = list(pd.read_pickle('ban_TXT'))
except:
    banRT,banTXT = [],[]


#Schedule for a day. Default time between RT's set to 3 minutes.
#Steps: 1) First follow or unfollow according to tit_for_tat(),
#       2) RT followers, 
#       3) RT highest ratio of number_of_RT/number_of_followers of previous day Statuses.
    
def run_schedule(dt=get_date(),ky='#indiedev',mx=150,clean=False,folow=False):
    if clean: tit_for_tat()
    if folow: RT_followers(key_=ky,max_=mx)
    RT_last_day(dt,key_=ky)

    
def loop_schedule(date):
    while True:
        for ky in ['#indiedev','#indiegame']:
            print 'Day '+str(date)+' and keyword '+str(ky)
            run_schedule(dt=date,ky=ky)
            d = get_date()        
            if date != d:
                date = d
                break

#Main Functions for 'run_schedule()'

#Keeps track of who doesn't follow back. If an ID appears twice in this category then it
#unfollows. Bot follows ALL followers. Filter for undesirable accounts will be implemented soon.
def tit_for_tat():
    print 'Tit for Tat!'
    follow_me = twitter_client.followers_ids() #who follows me
    follow_you = twitter_client.friends_ids()  #who do I follow
    erros_ids = []
    fol_len = len([1 for id_ in follow_me if id_ not in follow_you])
    print 'Following '+str(fol_len)+' new users.'
    for id_ in follow_me:
        if id_ not in follow_you:
            try:
                twitter_client.create_friendship(id_)
                time.sleep(5)
            except:
                erros_ids.append(id_)
    unfollow,rem_len = remember_follow()
    print 'Unfollowing '+str(len(unfollow))+'. Remembering '+str(rem_len)+'.'
    for id_ in follow_you:
        if id_ in unfollow:
            try:
                twitter_client.destroy_friendship(id_)
                time.sleep(5)
            except:
                erros_ids.append(id_)

#Take previous day tweets. Rank by higher RT of smaller accounts. Try to RT the underdog!
def RT_last_day(date,key_='#indiedev'):
    print 'RT '+str(key_)+' most relevant tweets from yesterday!'
    d = latest_tweets(date=date,key_=key_)
    d = rank_sort(d)
    plot_distro(d[:5000])
    a = RT_this(d[:10000],sleep_t=180)
    return a

#Take timelines from followers and looks for keyword (default: #indiedev. RTs top tweets (default=2).
def RT_followers(key_='#indiedev',max_=150,rts_=2): #900/1500 Rate limit
    print 'RT '+str(key_)+' within followers!'
    clct,twtn = [],0
    friends = twitter_client.followers_ids()
    #Get collection of tweets of followers.
    for f in friends:
        c=[]
        try:
            c = twitter_client.user_timeline(f,count=100)
        except:
            print 'Cant retweet follower.'
        tcl = [ci for ci in c if '#indiedev' in ci.text and ci.in_reply_to_status_id == None]
        if len(tcl) > 0:
            dc = {str(i.id):int(i.retweet_count) for i in tcl}
            dfc = pd.DataFrame.from_dict(dc,orient='index')
            dfc = dfc.sort(0,ascending=False)
            #Final collection of RTs considers only top statuses
            clct = clct + list(dfc.index[:rts_])
    
    #After selection of most desirable RTs, we randomly RT them.
    rd.shuffle(clct)
    print 'Going for '+str(len(clct[:max_]))+' tweets.'
    for id_ in clct:
        if twtn >= max_:    break
        try:
            twtn+=1
            twitter_client.retweet(id_)
            print 'Tweeted '+str(twtn)
            time.sleep(120)
            twitter_client.create_favorite(id_)
        except:
            pass

#RT statuses from a given DataFrame d.
def RT_this(d,sleep_t=60,stop_at=500,allow_like=False,checkmedia=False):
    err,twts,iters=0,0,0
    for tweet in d.values:
        if twts == stop_at:
            print 'Got '+str(stop_at)+' tweets. Stopping.'
            break
        try:
            like,publish,i = True,True,0
            if type(tweet[11]) != None:
                try:
                    if tweet[11] in banRT: like,publish = False,False
                except:
                    pass
            i=1
            if len(tweet[27]) > 14:
                if tweet[27][:15] in banTXT: like,publish = False,False
            i=2
            like = False
            if like and rd.random() < 0.05:
                twitter_client.create_favorite(tweet[8])
                print 'Liked '+tweet[27]
                if publish == False:
                    time.sleep(60)
            i=3
            if checkmedia and publish:
                    publish = filter_gif(tweet)
            if publish:
                try:
                    twitter_client.retweet(tweet[8])
                    i,twts=4,twts+1
                    print 'RTed : '+str(twts)+' at '+str(time.ctime())
                    time.sleep(sleep_t)
                    i=5
                    if type(tweet[11]) != None:
                        banRT.append(tweet[11])
                    if len(tweet[27]) > 14:
                        banTXT.append(tweet[27][:15])
                except:
                    pass
                
                try:
                    u_fol,u_fri=tweet[29]['followers_count'],tweet[29]['friends_count']
                    if (u_fol > 500 and u_fol < 10000) or (u_fol > 1.5*u_fri):
                        if i==4:
                            time.sleep(sleep_t)
                        i=6
                        twitter_client.create_friendship(tweet[29]['id'])
                except:
                    pass
                
                if like and allow_like:
                    try:
                        twitter_client.create_favorite(tweet[8])
                        print 'Liked '+tweet[27]
                        time.sleep(sleep_t/3)
                    except:
                        print 'Couldnt like'
                save_banDF()
            iters+=1
        except:
            err+=1

#StreamListener: DoggoListener is not currently on use as RTs of previous day and followers
#use most of the bot's daytime.

#List of words to avoid and possible tweet lexic
banword = ["porn","pron","p0rn","pr0n"]
doggolex = ['*doggehyped*']

class DoggoListener(StreamListener):
    def on_data(self, data):        
        tweet = json.loads(data)
        i,like,publish = 0,True,True
        try:
            for word in banword:
                if word in tweet['text'].lower(): like,publish = False,False
            i=1
            if tweet.get('lang') and tweet.get('lang') != 'en': like,publish = False,False
            i=2
            try:
                if type(tweet['user']['description']) != None:
                        if 'indie' not in tweet['user']['description'] or 'dev' not in tweet['user']['description'] or 'developer' not in tweet['user']['description']:
                            like = False
                            if tweet['user']['followers_count'] < 1000: publish = False
                else:
                    like,publish = False,False
            except:
                like,publish = False,False
            i=3
            if type(tweet['in_reply_to_status_id']) != None:            
                if tweet['in_reply_to_status_id'] in banRT:
                    like,publish = False,False
            i=4
            if len(tweet['text']) > 14:
                if tweet['text'][:15] in banTXT:
                    like,publish = False,False
            i=5 
            if like:
                twitter_client.create_favorite(tweet['id'])
                print 'Liked '+tweet['text']
                if publish == False:
                    time.sleep(10)
            i=6
            if publish:
                twitter_client.retweet(tweet['id'])
                #Some console output to check if stream is RTweeting.
                try:
                    print 'RTd: '+str(tweet['text'])
                except:
                    print '*Woof*'
                i='t'
                if type(tweet['in_reply_to_status_id']) != None:
                    i=7
                    banRT.append(tweet['in_reply_to_status_id'])
                if len(tweet['text']) > 14:
                    i=8
                    banTXT.append(tweet['text'][:15])
                save_banDF()
                time.sleep(60)
        except:
            print i #For debugging purposes
            
        return True
  
def run_doggo_run(): #Streams the doggolistener()
    if __name__ == '__main__':
        listener = DoggoListener()
        stream = Stream(auth_handler, listener)
        stream.filter(track=['indie game', 'indie games','gamedev','game dev','#indiedev',
                             '#gamedev','#indiegame','#steamNewRelease','#nintendoswitch'])



    
#From here you will find other useful functions that support Run_schedule and Run_doggo_run.

def save_banDF():
    df = pd.Series(banRT)
    df.to_pickle('ban_RT')
    df = pd.Series(banTXT)
    df.to_pickle('ban_TXT')    
    
#Based on sixohsix
def latest_tweets(date=get_date(),key_="#indiedev #indiegame #gamedev"):
    print "Search for "+str(date)
    tweets = t.search.tweets(q=key_,count=5000,until=date)
    dftwt = pd.DataFrame(tweets['statuses'])
    while True:
        try:
            tweets = t.search.tweets(q=key_,max_id=min(list(dftwt.id)),count=5000,until=date)
            tempdf = pd.DataFrame(tweets['statuses'])
            dftwt = dftwt.append(tempdf)
        except:
            break
    date = str(list(dftwt.created_at)[0][:3])
    print "Check for only TODAYS ONLY!!!"
    dftwt = only_with_date(date,dftwt)
    return dftwt

def only_with_date(str_,df):
    valid = []
    for date in df.created_at:
        if str_ in date[:3]:
            valid.append(1)
        else:
            valid.append(0)
    df['valid'] = valid
    return df[df.valid == 1]
             
def plot_distro(d):
    for column in ['favorite_count','retweet_count']:
        t = list(d[column])
        t.sort()
        plt.title(column)
        plt.plot(t)
        plt.show()
    a = [i[29]['followers_count'] for i in d.values]
    a.sort()
    plt.title('followers_count')
    plt.plot(a)
    plt.show()

def rank_sort(d):
    d['follow'] = [i[29]['followers_count'] for i in d.values]
    da = d[d.follow > 100]
    a = [float(i[23])/float(i[29]['followers_count']) for i in da.values]
    da['rank'] = list(a)
    dd = da.sort_values(by='rank',ascending=False)
    #ban,keep=[],[]
    #for i in d.values:
    #    if i[27][:15] in ban:
    #        keep.append(0)
    #    else:
    #        keep.append(1)
    #        ban.append(i[27][:15])
    #d['ktxt'] = keep
    #d = d[d.ktxt == 1]
    return dd

def remember_follow():
    try:
        rem = list(pd.read_pickle('remember'))
    except:
        rem = []
    follow_me = twitter_client.followers_ids() #who follows me
    follow_you = twitter_client.friends_ids()  #who do I follow
    remember = [id_ for id_ in follow_you if id_ not in follow_me and id_ not in rem]
    unfollow = [id_ for id_ in follow_you if id_ not in follow_me and id_ in rem ]
    rdf = pd.Series(remember)
    rdf.to_pickle('remember')
    return unfollow,len(rdf)

def unfollow_this(ids_):
    for id_ in ids_:
        twitter_client.destroy_friendship(id_)
        time.sleep(10)
        
def filter_gif(tweet,v=False):
    try:
        if len(tweet[4]['media']) > 0: v=True
    except:
        pass
    return v
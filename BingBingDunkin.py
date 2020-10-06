from random import randint, sample
from time import sleep
from os import getcwd
from urllib.parse import quote_plus
import configparser
from pytrends.request import TrendReq
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

endpoints = {"news/search", "videos/search", "images/search", "shop", "search"}  # no leading /
GECKO_DRIVER = 'geckodriver.exe'  # CHANGE ME (path to downloaded web-driver)

"""
 ____  __  __ _   ___    ____  __  __ _   ___    ____  _  _  __ _  __ _  __  __ _   _  
(  _ \(  )(  ( \ / __)  (  _ \(  )(  ( \ / __)  (    \/ )( \(  ( \(  / )(  )(  ( \ (/  
 ) _ ( )( /    /( (_ \   ) _ ( )( /    /( (_ \   ) D () \/ (/    / )  (  )( /    /    
(____/(__)\_)__) \___/  (____/(__)\_)__) \___/  (____/\____/\_)__)(__\_)(__)\_)__)    

BingBingDunkin' is a program which automates getting search points for multiple accounts.
"""


def wait_for(sec=2, jitter=True):
    """
    A function which is provided a minimum amount of time and then adds a random amount
    to make the delay unpredictable.
    :param sec: The minimum amount of time
    :param jitter: If you want jitter
    """
    if jitter:
        sleep(sec + randint(3,95))
    else:
        sleep(sec)


def google_trends() -> list:
    """
    google_trends will use the google trends api to generate a list of hundreds of popular
    search phrases being used today.
    :return: A list of search phrases
    """
    pytrend = TrendReq()  # Initiating the google trends object
    all_trendin_phrases = []
    while True:
        try:
            #  Returns about top 20 trending phrases
            list_of_trending = pytrend.trending_searches(pn='united_states')[0].to_list()
            print(list_of_trending)
            break
        except Exception as e:
            print(e)
            wait_for(2, jitter=False)

    #  Iterate through each search phrase
    for phrase in list_of_trending:
        #  Getting rid of symbols since they mess up column names in a dataframe
        phrase = ''.join( c for c in phrase if c not in "~`|\\!@#$%^&*()_+-=;:[]{}'\",./<>?" )
        pytrend.build_payload(kw_list=[phrase])
        while True:
            try:
                #  Will use google trends to find related queries to the phrase
                df = pytrend.related_queries()
                #  Check if no related phrases returned
                if df[phrase]['top'] is None:
                    break
                #  Grab the related queries from the column and convert to a list
                related_queries = df[phrase]['top']['query'].to_list()
                all_trendin_phrases.extend(related_queries)
                break
            except Exception as e:
                print(phrase)
                print(e)
                wait_for(2, jitter=False)
    #  A list of all trend words as well as their related searches
    return all_trendin_phrases


def start(all_trending_topics: list, user_agent: str, NUM_WORDS: int):
    """
    Start will compile a dictionary from all credentials stored in credentials.ini. For each account
    a browser will be started with the provided user agent and NUM_WORDS will be used to randomly select
    an amount of phrases from all_trending_topics.
    :param all_trending_topics: A list of strings which have search phrases
    :param user_agent: String which represents the browser
    """

    #  Creates a parser for the credentials
    config = configparser.ConfigParser()
    config.read("credentials.ini")
    accounts = {}
    #  Create a dict of email:pass
    for key in config['DEFAULT']:
        if 'email' in key:
            accounts[config['DEFAULT'][key]] = config['DEFAULT']['password' + key.split("email")[1]]

    #  Iterates over each account credentials
    for email in accounts.keys():
        #  Set up the driver profile
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", user_agent) # Sets user agent
        profile.set_preference("dom.disable_beforeunload", True) # Disables firefox popups
        driver = webdriver.Firefox(firefox_profile=profile, executable_path=getcwd() + "/{}".format(GECKO_DRIVER))

        password = accounts[email]
        print("Account: ", email, password)
        words_list = sample(all_trending_topics, NUM_WORDS)

        #  Login
        driver.get("https://login.live.com/")
        wait_for(5, jitter=False)
        elem = driver.find_element_by_name('loginfmt')
        elem.clear()
        elem.send_keys(email) # add your login email id
        elem.send_keys(Keys.RETURN)
        wait_for(4, jitter=False)
        elem1 = driver.find_element_by_name('passwd')
        elem1.clear()
        elem1.send_keys(str(password)) # add your password
        elem1.send_keys(Keys.ENTER)
        wait_for(9, jitter=False)

        #  Once logged in search using the random words
        for num, phrase in enumerate(words_list):
            url_base = 'https://www.bing.com/{}?q='.format(sample(endpoints, 1)[0])
            print('{0}. URL : {1}'.format(str(num + 1), url_base + quote_plus(phrase)))
            #  Try the request until you get a response
            while True:
                try:
                    driver.get(url_base + quote_plus(phrase))
                    break
                except Exception as e1:
                    print(e1)
                    wait_for(1)
            wait_for(90, jitter=True)
        #  Delete cookies
        driver.delete_all_cookies()
        driver.quit()
        print()


if __name__ == '__main__':
    #  Don't change. This user agent represents an edge browser which will give you 600 more points per month
    DESKTOP_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36 Edg/85.0.564.68"
    MOBILE_USERAGENT = "Mozilla/5.0 (Android 6.0.1; Mobile; rv:77.0) Gecko/77.0 Firefox/77.0"
    #  Don't change. More != better. There is a maximum amount of points you can get per day
    NUM_WORDS_DESKTOP = 32  # the amount of searches per account (1 search = 5 pts)
    NUM_WORDS_MOBILE = 22  # the amount of searches per account (1 search = 5 pts)

    print("Generating Trending Topics")
    all_trending_topics = google_trends()

    print("Starting Desktop")
    start(all_trending_topics, DESKTOP_USERAGENT, NUM_WORDS_DESKTOP)

    print("Finished Desktop")
    wait_for(60)

    print("Starting Mobile\n")
    start(all_trending_topics, MOBILE_USERAGENT, NUM_WORDS_MOBILE)

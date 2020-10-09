from random import randint, choices, sample
from time import sleep
from os import getcwd, path
from urllib.parse import quote_plus
import configparser
from pytrends.request import TrendReq
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.keys import Keys

endpoints = ["news/search", "videos/search", "images/search", "shop", "search"]  # no leading /
distribution = [.2, .05, .1, .05, .6]  # Probability distribution for the above endpoints
GECKO_DRIVER = 'geckodriver'  # CHANGE ME (path to downloaded web-driver)

"""
 ____  __  __ _   ___    ____  __  __ _   ___    ____  _  _  __ _  __ _  __  __ _   _  
(  _ \(  )(  ( \ / __)  (  _ \(  )(  ( \ / __)  (    \/ )( \(  ( \(  / )(  )(  ( \ (/     ( (
 ) _ ( )( /    /( (_ \   ) _ ( )( /    /( (_ \   ) D () \/ (/    / )  (  )( /    /         ) )
(____/(__)\_)__) \___/  (____/(__)\_)__) \___/  (____/\____/\_)__)(__\_)(__)\_)__)       ........
                                                                                         |      |]
                                                                                         \      /
                                                                                          `----'
BingBingDunkin' is a program which automates getting search points for multiple accounts.
"""

ASCII_ART = """
 ____  __  __ _   ___    ____  __  __ _   ___    ____  _  _  __ _  __ _  __  __ _   _  
(  _ \(  )(  ( \ / __)  (  _ \(  )(  ( \ / __)  (    \/ )( \(  ( \(  / )(  )(  ( \ (/     ( (
 ) _ ( )( /    /( (_ \   ) _ ( )( /    /( (_ \   ) D () \/ (/    / )  (  )( /    /         ) )
(____/(__)\_)__) \___/  (____/(__)\_)__) \___/  (____/\____/\_)__)(__\_)(__)\_)__)       ........
                                                                                         |      |]
                                                                                         \      /
                                                                                          `----'
"""
def wait_for(sec=2, jitter=True, min=3, max=100):
    """
    A function which is provided a minimum amount of time and then adds a random amount
    to make the delay unpredictable.
    :param max: The highest amount of jitter
    :param min: The lowest amount of jitter
    :param sec: The minimum amount of time
    :param jitter: If you want jitter
    """
    if jitter:
        sleep(sec + randint(min, max))
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
            #  Returns about top 20 trending words
            list_of_trending = pytrend.trending_searches(pn='united_states')[0].to_list()
            print(list_of_trending)
            break
        except Exception as e:
            print(e)
            wait_for(2, jitter=False)

    #  Iterate through each search word
    for word in list_of_trending:
        #  Getting rid of symbols since they mess up column names in a dataframe
        phrase = ''.join(c for c in word if c not in "~`|\\!@#$%^&*()_+-=;:[]{}'\",./<>?")
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


def start(all_trending_topics: list, user_agent: str, NUM_WORDS: int, mobile=False):
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
        profile.set_preference("dom.disable_beforeunload", True)  # Disables firefox popups
        try:
            driver = webdriver.Firefox(firefox_profile=profile, executable_path=getcwd() + "/{}".format(GECKO_DRIVER))
            driver.set_page_load_timeout(15)  # Sets a timeout at 15 seconds
        except Exception as e:
            print('\nERROR:', e)
            exit(1)

        password = accounts[email]
        print("Account: ", email, password)
        words_list = sample(all_trending_topics, min(NUM_WORDS, len(all_trending_topics)))

        #  Login
        driver.get("https://login.live.com/")
        wait_for(5, jitter=False)
        elem = driver.find_element_by_name('loginfmt')
        elem.clear()
        elem.send_keys(email)
        elem.send_keys(Keys.RETURN)
        wait_for(4, jitter=False)
        elem1 = driver.find_element_by_name('passwd')
        elem1.clear()
        elem1.send_keys(str(password))
        elem1.send_keys(Keys.ENTER)
        wait_for(9, jitter=False)

        #  Once logged in search using the random phrases
        for num, phrase in enumerate(words_list):
            endpoint = choices(endpoints, weights=distribution, k=1)[0]
            url_base = 'https://www.bing.com/{}?q='.format(endpoint)
            print('{0}. URL : {1}'.format(str(num + 1), url_base + quote_plus(phrase)))
            #  Try the request until you get a response
            while True:
                try:
                    driver.get(url_base + quote_plus(phrase))
                    if not mobile:  # Doesn't work for mobile
                        #  Mimic human interaction by clicking on links on the page
                        if endpoint == 'search':
                            # The b_algo class hold the results
                            link_elements = driver.find_elements_by_class_name("b_algo")
                            returned_links = {}
                            for el in link_elements:
                                try:
                                    h2 = el.find_element_by_tag_name('h2')
                                except Exception:
                                    continue
                                a = h2.find_element_by_tag_name('a')
                                href = a.get_attribute('href')
                                #  Filter out anything that isn't a url
                                if "bing" not in href and href != '':
                                    returned_links[href] = a
                            #  Choose between 0-3 links to click on
                            amt = randint(0, min(len(returned_links), 3))
                            for site in sample(returned_links.keys(), amt):
                                wait_for(sec=1, jitter=True, min=3, max=8)
                                print('\t\tClicking : {}'.format(site))
                                try:
                                    returned_links[site].click()
                                #  The DOM is different sometimes clicking the link will error
                                except exceptions.StaleElementReferenceException:
                                    driver.get(site.split("#")[0])
                                wait_for(sec=1, jitter=True, min=3, max=8)
                                while "bing.com" not in driver.current_url:
                                    driver.back()
                    break  # While

                except Exception as e1:
                    print(e1)
                    wait_for(1, jitter=True, min=2, max=10)

            wait_for(3, jitter=True, min=0, max=100)
        #  Delete cookies
        driver.delete_all_cookies()
        driver.quit()
        print()


def output_points(user_agent):
    print("\n\n\n")
    print("POINTS REPORT")
    config = configparser.ConfigParser()
    config.read("credentials.ini")
    accounts = {}
    #  Create a dict of email:pass
    for key in config['DEFAULT']:
        if 'email' in key:
            accounts[config['DEFAULT'][key]] = config['DEFAULT']['password' + key.split("email")[1]]

    for email in accounts.keys():
        #  Set up the driver profile
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", user_agent)  # Sets user agent
        profile.set_preference("dom.disable_beforeunload", True)  # Disables firefox popups
        try:
            driver = webdriver.Firefox(firefox_profile=profile, executable_path=getcwd() + "/{}".format(GECKO_DRIVER))
            driver.set_page_load_timeout(15)  # Sets a timeout at 15 seconds
        except Exception as e:
            print('\nERROR:', e)
            exit(1)

        password = accounts[email]

        driver.get("https://login.live.com/")
        wait_for(5, jitter=False)
        elem = driver.find_element_by_name('loginfmt')
        elem.clear()
        elem.send_keys(email)
        elem.send_keys(Keys.RETURN)
        wait_for(4, jitter=False)
        elem1 = driver.find_element_by_name('passwd')
        elem1.clear()
        elem1.send_keys(str(password))
        elem1.send_keys(Keys.ENTER)
        wait_for(9, jitter=False)

        driver.get("https://www.bing.com/")
        points = driver.find_element_by_id("id_rc")
        wait_for(9, jitter=False)
        points.click()
        wait_for(9, jitter=False)
        points.click()
        wait_for(9, jitter=False)
        points.click()
        wait_for(9, jitter=False)
        print(email)
        points_num = int(points.text)
        print("\tTotal points: ", points_num)
        if points_num >= 6500:
            print("Time to cash in $$$")
        wait_for(60, jitter=False)

def daily_set(user_agent):
    config = configparser.ConfigParser()
    config.read("credentials.ini")
    accounts = {}
    #  Create a dict of email:pass
    for key in config['DEFAULT']:
        if 'email' in key:
            accounts[config['DEFAULT'][key]] = config['DEFAULT']['password' + key.split("email")[1]]


    for email in accounts.keys():
        print("Daily set for ", email)
        #  Set up the driver profile
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", user_agent)  # Sets user agent
        profile.set_preference("dom.disable_beforeunload", True)  # Disables firefox popups
        try:
            driver = webdriver.Firefox(firefox_profile=profile, executable_path=getcwd() + "/{}".format(GECKO_DRIVER))
            driver.set_page_load_timeout(15)  # Sets a timeout at 15 seconds
        except Exception as e:
            print('\nERROR:', e)
            exit(1)

        # daily set 1
        driver.get("https://www.bing.com/")
        points = driver.find_element_by_id("id_rc")
        wait_for(9, jitter=False)
        points.click()
        wait_for(9, jitter=False)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        elem = driver.find_element_by_xpath("/html/body")
        flyout = elem.find_element_by_id("modern-flyout")
        free_ten_points = flyout.find_element_by_class_name("promo_cont")
        free_ten_points.click()
        wait_for(9, jitter=False)

        # complete the bing quiz
        count = 0
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        driver.get("https://www.bing.com/")
        wait_for(9, jitter=False)
        points = driver.find_element_by_id("id_rc")
        points.click()
        wait_for(9, jitter=False)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        elem = driver.find_element_by_xpath("/html/body")
        flyout = elem.find_element_by_id("modern-flyout")
        quiz = flyout.find_elements_by_class_name("promo_cont")[1]
        wait_for(9, jitter=False)
        quiz.click()
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        for i in range(0,10):
            question = "QuestionPane" + str(i)
            answer = "AnswerPane" + str(i)

            content= driver.find_element_by_id("b_content")
            olist = content.find_element_by_id("b_results")
            canvas = olist.find_element_by_id("wkCanvas")
            qa = canvas.find_element_by_id("ListOfQuestionAndAnswerPanes")
            q1 = qa.find_element_by_id(question)
            a = q1.find_element_by_class_name("wk_Circle")
            a.click()
            wait_for(9, jitter=False)

            content= driver.find_element_by_id("b_content")
            olist = content.find_element_by_id("b_results")
            canvas = olist.find_element_by_id("wkCanvas")
            qa = canvas.find_element_by_id("ListOfQuestionAndAnswerPanes")
            a1 = qa.find_element_by_id(answer)
            next = a1.find_element_by_class_name("wk_buttons")
            button = next.find_element_by_class_name("wk_button")
            button.click()
            wait_for(9, jitter=False)


        # complete the poll
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        driver.get("https://www.bing.com/")
        wait_for(9, jitter=False)
        points = driver.find_element_by_id("id_rc")
        points.click()
        wait_for(9, jitter=False)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        elem = driver.find_element_by_xpath("/html/body")
        flyout = elem.find_element_by_id("modern-flyout")
        poll = flyout.find_elements_by_class_name("promo_cont")[2]
        poll.click()
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        trivia_overlay = driver.find_element_by_id("b_TriviaOverlay")
        wrapper= trivia_overlay.find_element_by_id("overlayWrapper")
        button_overlay = wrapper.find_element_by_id("btOverlay")
        overlay_panel = button_overlay.find_element_by_id("overlayPanel")
        trivia_overlay_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
        poll_overlay = trivia_overlay_data.find_element_by_id("btPollOverlay")
        poll = poll_overlay.find_element_by_class_name("bt_poll")
        options = poll.find_element_by_css_selector(".btOptions2.bt_pollOptions")
        choice = options.find_element_by_id("btoption0")
        choice.click()
        wait_for(9, jitter=False)
        driver.close()



if __name__ == '__main__':
    #  Don't change. This user agent represents an edge browser which will give you 600 more points per month
    DESKTOP_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36 Edg/85.0.564.68"
    MOBILE_USERAGENT = "Mozilla/5.0 (Android 6.0.1; Mobile; rv:77.0) Gecko/77.0 Firefox/77.0"
    #  Don't change. More != better. There is a maximum amount of points you can get per day
    # the amount of searches per account (1 search = 5 pts)
    NUM_WORDS_DESKTOP = 35  # 30 searches for 150 Desktop pts; 4 searches for 20 Edge pts; 1 extra
    NUM_WORDS_MOBILE = 21  # 20 searches for 100 Mobile pts; 1 extra

    try:
        assert path.isfile(GECKO_DRIVER)
    except AssertionError as e:
        print('\nERROR: {} NOT FOUND'.format(GECKO_DRIVER))
        exit(1)

    print(ASCII_ART)

    print("Generating Trending Topics")
    all_trending_topics = google_trends()

    print("Starting Desktop")
    start(all_trending_topics, DESKTOP_USERAGENT, NUM_WORDS_DESKTOP)

    print("Finished Desktop")
    wait_for(60, jitter=False)

    print("Starting Mobile\n")
    start(all_trending_topics, MOBILE_USERAGENT, NUM_WORDS_MOBILE, mobile=True)

    print("Finished Mobile")
    wait_for(60, jitter=False)

    print("Running Daily Set")
    daily_set(DESKTOP_USERAGENT)


    print("Getting Points")
    output_points(DESKTOP_USERAGENT)
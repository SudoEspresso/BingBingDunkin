from random import randint, choices, sample
from time import sleep, time, gmtime, strftime
from os import getcwd, path
from urllib.parse import quote_plus
import configparser
from pytrends.request import TrendReq
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.keys import Keys
from requests.exceptions import Timeout
from tqdm import tqdm

all_enpoints = ["news/search", "videos/search", "images/search", "shop", "search"]  # no leading /
distribution = [.2, .05, .1, .05, .6]  # Probability distribution for the above endpoints
GECKO_DRIVER = 'geckodriver'  # CHANGE ME (path to downloaded web-driver)
FINAL_REPORT = {}

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
    assert min <= max
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
    for word in tqdm(list_of_trending):
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
                wait_for(1, jitter=False)
                break
            except Timeout as e:
                print(phrase)
                print(e)
                wait_for(2, jitter=False)
    print("\n\n")
    #  A list of all trend words as well as their related searches
    return all_trendin_phrases


def start(all_trending_topics: list, user_agent: str, NUM_WORDS: int, mimicDesktop=False, find_points=False):
    """
    Start will compile a dictionary from all credentials stored in credentials.ini. For each account
    a browser will be started with the provided user agent and NUM_WORDS will be used to randomly select
    an amount of phrases from all_trending_topics.
    :param NUM_WORDS: The number of search phrases to randomly select from the google trending searches
    :param mimicDesktop: if True will mimic user interaction by clicking on results (only for desktop)
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
        profile.set_preference("general.useragent.override", user_agent)  # Sets user agent
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
        wait_for(5, jitter=False)
        elem.send_keys(Keys.RETURN)
        wait_for(10, jitter=False)
        elem1 = driver.find_element_by_name('passwd')
        elem1.clear()
        elem1.send_keys(str(password))
        wait_for(5, jitter=False)
        elem1.send_keys(Keys.ENTER)
        wait_for(10, jitter=False)
        if not find_points:
            #  Once logged in search using the random google trending phrases
            for num, phrase in enumerate(words_list):
                #  Select a endpoint to use (search/ has the highest probability)
                endpoint = choices(all_enpoints, weights=distribution, k=1)[0]
                url_base = 'https://www.bing.com/{}?q='.format(endpoint)
                print('{0}. URL : {1}'.format(str(num + 1), url_base + quote_plus(phrase)))
                #  Try the request until you get a response
                while True:
                    try:
                        driver.get(url_base + quote_plus(phrase))
                        if mimicDesktop and endpoint == 'search':  # Doesn't work for mobile
                            #  Mimic human interaction by clicking on links on the page
                            mimic_desktop_interaction(driver)
                        break  # While

                    except Exception as e1:
                        print(e1)
                        wait_for(1, jitter=True, min=2, max=10)

                wait_for(3, jitter=True, min=0, max=60)
            if mimicDesktop:  # if Desktop
                #  This condition hits when the desktop searches have finished
                print("Starting Daily Set")
                daily_set(driver)
                print("Finished Daily Set")
        if find_points:  # if mobile
            #  This means that this account has finished collecting points
            find_account_points(email, driver)

        driver.quit()
        print()


def mimic_desktop_interaction(driver: webdriver.Firefox):
    """
    After a search using bing.com/search this function will go through the page and find
    any clickable search results. A number between 0 - 3 will be chosen and that will be
    how many of the links are clicked and loaded.
    :param driver: The web driver used to interact with the browser
    """
    # The b_algo class hold the results
    link_elements = driver.find_elements_by_class_name("b_algo")
    returned_links = {}
    for el in link_elements:
        try:
            h2 = el.find_element_by_tag_name('h2')
        except Exception:
            #  Some times h2 can't be found in this case just skip to the
            #  next element since there should be plenty to choose from
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


def find_account_points(email: str, driver: webdriver.Firefox):
    """
    Will collect and store the account points corresponding to the given email
    :param email: The email address
    :param driver: The web driver used to interact with the browser
    """
    driver.get("https://www.bing.com/")
    wait_for(4, jitter=False)
    points = driver.find_element_by_id("id_rc")
    wait_for(4, jitter=False)
    points.click()
    wait_for(4, jitter=False)
    points.click()
    wait_for(4, jitter=False)
    points.click()
    wait_for(8, jitter=True, min=5, max=13)
    points_num = int(points.text)

    global FINAL_REPORT
    #  Modify the global var and add the account with its pts
    FINAL_REPORT[email] = points_num


def daily_set(driver: webdriver.Firefox):
    """
    The daily set is composed of 3 items, the first being a simple click search, the
    second being a 10 question quiz and the last being a poll. All three of these tasks
    are automated when completed multiple days in a row Microsoft Rewards provides bonus pts.
    :param driver: The web driver used to interact with the browser
    """
    try:
        # Daily set 1
        # Just clicks the link 10 pts
        while True:
            try:
                driver.get("https://www.bing.com/")
                break
            except Exception:
                wait_for(1, jitter=False)
        points = driver.find_element_by_id("id_rc")
        wait_for(9, jitter=False)
        points.click()
        wait_for(9, jitter=False)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        elem = driver.find_element_by_xpath("/html/body")
        flyout = elem.find_element_by_id("modern-flyout")
        free_ten_points = flyout.find_element_by_class_name("promo_cont")
        free_ten_points.click()
        wait_for(3, jitter=True, min=1, max=5)
        print("Daily set 1")
    except (exceptions.ElementNotInteractableException, exceptions.NoSuchElementException, IndexError) as e:
        #  Either the user interacted with the screen or the daily set is already done
        pass

    try:
        # Daily set 2
        # Complete the bing quiz 10 pts
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        while True:
            try:
                driver.get("https://www.bing.com/")
                break
            except Exception:
                wait_for(1, jitter=False)
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
        for i in range(0, 10):
            question = "QuestionPane" + str(i)
            answer = "AnswerPane" + str(i)
            content = driver.find_element_by_id("b_content")
            olist = content.find_element_by_id("b_results")
            canvas = olist.find_element_by_id("wkCanvas")
            qa = canvas.find_element_by_id("ListOfQuestionAndAnswerPanes")
            q1 = qa.find_element_by_id(question)
            a = q1.find_element_by_class_name("wk_Circle")
            a.click()
            wait_for(9, jitter=False)

            content = driver.find_element_by_id("b_content")
            olist = content.find_element_by_id("b_results")
            canvas = olist.find_element_by_id("wkCanvas")
            qa = canvas.find_element_by_id("ListOfQuestionAndAnswerPanes")
            a1 = qa.find_element_by_id(answer)
            next = a1.find_element_by_class_name("wk_buttons")
            button = next.find_element_by_class_name("wk_button")
            button.click()
            wait_for(9, jitter=False)
        print("Daily set 2")
    except (exceptions.ElementNotInteractableException, exceptions.NoSuchElementException, IndexError) as e:
        #  Either the user interacted with the screen or the daily set is already done
        pass

    try:
        # Daily set 3
        # Complete the poll
        driver.switch_to.default_content()
        wait_for(9, jitter=False)
        while True:
            try:
                driver.get("https://www.bing.com/")
                break
            except Exception:
                wait_for(1, jitter=False)
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
        wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
        button_overlay = wrapper.find_element_by_id("btOverlay")
        overlay_panel = button_overlay.find_element_by_id("overlayPanel")
        trivia_overlay_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
        poll_overlay = trivia_overlay_data.find_element_by_id("btPollOverlay")
        poll = poll_overlay.find_element_by_class_name("bt_poll")
        options = poll.find_element_by_css_selector(".btOptions2.bt_pollOptions")
        choice = options.find_element_by_id("btoption0")
        choice.click()
        print("Daily set 3")
        wait_for(9, jitter=False)
    except (exceptions.ElementNotInteractableException, exceptions.NoSuchElementException, IndexError) as e:
        #  Either the user interacted with the screen or the daily set is already done
        pass


def print_report(time_taken):
    """
    Once everything is complete the resulting points will be output
    :param time_taken: The amount of time taken to complete all searching
    """
    global FINAL_REPORT
    print("POINTS REPORT")
    ty_res = gmtime(time_taken)
    res = strftime("%H:%M:%S", ty_res)

    print("Total Time: ", res)
    for email in FINAL_REPORT.keys():
        points = FINAL_REPORT[email]
        print("\tTotal points: ", points)
        if points >= 6500:
            print("Time to cash in $$$")


if __name__ == '__main__':
    #  Don't change. This user agent represents an edge browser which will give you 600 more points per month
    DESKTOP_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36 Edg/85.0.564.68"
    MOBILE_USERAGENT = "Mozilla/5.0 (Android 6.0.1; Mobile; rv:77.0) Gecko/77.0 Firefox/77.0"
    #  Don't change. More != better. There is a maximum amount of points you can get per day
    #  the amount of searches per account (1 search = 5 pts)
    NUM_WORDS_DESKTOP = 35 # 30 searches for 150 Desktop pts; 4 searches for 20 Edge pts; 1 extra
    NUM_WORDS_MOBILE = 25 # 20 searches for 100 Mobile pts; 5 extra

    try:
        assert path.isfile(GECKO_DRIVER)
    except AssertionError as e:
        print('\nERROR: {} NOT FOUND'.format(GECKO_DRIVER))
        exit(1)

    print(ASCII_ART)

    print("Google Trending Topics")
    all_trending_topics = google_trends()

    START_TIME = time()
    print("Starting Desktop")
    start(all_trending_topics, DESKTOP_USERAGENT, NUM_WORDS_DESKTOP, mimicDesktop=True)
    print("Finished Desktop")

    wait_for(60, jitter=False)

    print("Starting Mobile\n")
    start(all_trending_topics, MOBILE_USERAGENT, NUM_WORDS_MOBILE)
    print("Finished Mobile")

    print("Getting Points\n")
    start(all_trending_topics, DESKTOP_USERAGENT, 0, find_points=True)
    STOP_TIME = time()

    difference_in_time = STOP_TIME - START_TIME

    print_report(difference_in_time)

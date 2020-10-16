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
GECKO_DRIVER = 'geckodriver.exe'  # CHANGE ME (path to downloaded web-driver)
INITIAL_POINTS = {}
FINAL_POINTS = {}
#  Colors
GREEN = "\033[32m"
RED = "\033[91m"
END = "\033[0m"
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
            break
        except Exception as e:
            print(e)
            wait_for(2, jitter=False)

    #  Iterate through each search word
    for word in tqdm(list_of_trending):
        #  Getting rid of symbols since they mess up column names in a dataframe
        phrase = ''.join(c for c in word if c not in "~`|\\!@#$%^&*()_+-=;:[]{}'\",./<>?")
        while True:
            try:
                pytrend.build_payload(kw_list=[phrase])
                break
            except Exception as e:
                wait_for(1, jitter=False)
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
                wait_for(2, jitter=False)
    print("\r")  # To prevent the loading bar from going on two lines
    #  A list of all trend words as well as their related searches
    return all_trendin_phrases


def login(driver: webdriver.Firefox, email: str, password: str) -> bool:
    """
    Logs the driver into Bing.com and determines if there was a sucessful login
    of if the account is blocked by Microsoft
    :param driver: The web driver used to interact with the browser
    :param email: The email address to be logged in
    :param password: The password to be logged in
    :return: True if successful False if account is blocked
    """
    while True:
        try:
            driver.get("https://login.live.com/")
            break
        except Exception:
            wait_for(1, jitter=False)
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
    wait_for(9, jitter=False)
    #  Grabs the text after the login. Either blocked or asks to stay signed in
    while True:
        try:
            login_result = driver.find_element_by_class_name("text-title").text
            break
        except exceptions.NoSuchElementException:
            #  .text-title is always there but sometimes doesn't load all the way
            wait_for(1, jitter=False)

    if "Stay signed in?" not in login_result:  # Blocked
        print(RED + "ACCOUNT BLOCKED\n" + END)
        global FINAL_POINTS
        FINAL_POINTS[email] = "BLOCKED"
        INITIAL_POINTS[email] = "BLOCKED"
        return False
    else:  # Not Blocked
        print(GREEN + "Successful Login" + END)
        return True


def start(all_trending_topics: list, user_agent: str, NUM_WORDS: int, mimicDesktop=False):
    """
    Start will compile a dictionary from all credentials stored in credentials.ini. For each account
    a browser will be started with the provided user agent and NUM_WORDS will be used to randomly select
    an amount of phrases from all_trending_topics.
    :param all_trending_topics: A list of strings which have search phrases
    :param user_agent: String which represents the browser
    :param NUM_WORDS: The number of search phrases to randomly select from the google trending searches
    :param mimicDesktop: if True will mimic user interaction by clicking on results (only for desktop)
    """
    #  Creates a parser for the credentials
    config = configparser.ConfigParser()
    config.read("credentials.ini")
    accounts = {}
    #  Create a dict of email:pass
    for key in config['DEFAULT']:
        if 'email' in key:
            #  accounts[email] = password
            accounts[config['DEFAULT'][key]] = config['DEFAULT']['password' + key.split("email")[1]]

    #  Iterates over each account credentials
    for email in accounts.keys():
        #  Set up the driver profile
        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", user_agent)  # Sets user agent
        profile.set_preference("dom.disable_beforeunload", True)  # Disables "data you have entered may not be saved" popup
        profile.set_preference("dom.webnotifications.enabled", False)  # Disables "Asking for location" popup
        try:
            driver = webdriver.Firefox(firefox_profile=profile, executable_path=getcwd() + "/{}".format(GECKO_DRIVER))
            driver.set_page_load_timeout(15)  # Sets a timeout at 15 seconds
        except Exception as e:
            print('\nERROR:', e)
            exit(1)

        password = accounts[email]
        print("Account: ", email, password)
        #  Logs in and returns a boolean if successful or not
        isSuccessful = login(driver, email, password)

        if not isSuccessful:
            driver.quit()
            continue  # Go to next credentials, skip searches

        if not mimicDesktop:  # if Mobile
            #  Grab the initial amount of point the account has
            points = find_account_points(driver)
            INITIAL_POINTS[email] = points

        words_list = sample(all_trending_topics, min(NUM_WORDS, len(all_trending_topics)))

        #  Once logged in search using the random google trending phrases
        for num, phrase in enumerate(words_list):
            #  Select a endpoint to use (search/ has the highest probability)
            endpoint = choices(all_enpoints, weights=distribution, k=1)[0]
            url_base = 'https://www.bing.com/{}?q='.format(endpoint)
            print('{:4s}. URL : {}'.format(str(num + 1), url_base + quote_plus(phrase)))
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
            print("\nStarting Daily Set")
            daily_set(driver)
            print("Finished Daily Set")
            #  This means that this account has finished collecting points
            #  Grab the final amount of points the account has
            points = find_account_points(driver)
            global FINAL_POINTS
            #  Modify the global var and add the account with its pts
            FINAL_POINTS[email] = points

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
            a = h2.find_element_by_tag_name('a')
        except Exception:
            #  Some times h2 can't be found in this case just skip to the
            #  next element since there should be plenty to choose from
            continue
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
            driver.get(site.split("#")[0])  # removes the DOM part from the URL

        wait_for(sec=1, jitter=True, min=3, max=8)
        while "bing.com" not in driver.current_url:
            driver.back()


def find_account_points(driver: webdriver.Firefox) -> int:
    """
    Will collect and store the account points using the provided driver
    :param driver: The web driver used to interact with the browser
    """
    points = None
    wait = 20
    while points is None:  # If the page doesn't load it will set points=None
        try:
            driver.get("https://account.microsoft.com/rewards/")
            wait_for(wait, jitter=False)
            body = driver.find_element_by_tag_name("mee-rewards-user-status-balance")
            points = int(body.find_element_by_tag_name("span").text.replace(",", ""))
            wait += 5
        except Exception:
            wait_for(1, jitter=False)
    return points


def lightspeed_quiz(driver: webdriver.Firefox):
    """
    Completes the "lightning speed" quiz
    :param driver: The web driver used to interact with the browser
    """
    # get the number of points
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    container = welcome_container.find_element_by_class_name("rqWcHeader")
    points = container.find_element_by_class_name("rqWcpoints")
    points = points.text
    points = points.split(" ")[0]
    num_questions = int(points) / 10

    num_questions = int(num_questions)
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    button = welcome_container.find_element_by_id("rqStartQuiz")
    button.click()
    wait_for(7, jitter=True, min=0, max=2)
    #  Iterate over each question
    for question in range(0, num_questions):
        #  Iterate over each answer until correct
        for i in range(0, 4):
            button_overlay_panel = driver.find_element_by_id("overlayPanel")
            trivia_overlay_data = button_overlay_panel.find_element_by_class_name("TriviaOverlayData")
            current_question_container = trivia_overlay_data.find_element_by_id("currentQuestionContainer")
            text = current_question_container.find_element_by_class_name("textBasedMultiChoice")
            answers = text.find_elements_by_class_name("rq_button")
            answer = answers[i]
            answer.click()
            wait_for(5, jitter=True, min=0, max=2)


def thisorthat_quiz(driver: webdriver.Firefox):
    """
    Completes the "This Or That?" quiz
    :param driver: The web driver used to interact with the browser
    """
    # get the number of points
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    container = welcome_container.find_element_by_class_name("rqWcHeader")
    points = container.find_element_by_class_name("rqWcpoints")
    points = points.text
    points = points.split(" ")[0]
    num_questions = int(points) / 5

    num_questions = int(num_questions)
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    button = welcome_container.find_element_by_id("rqStartQuiz")
    button.click()
    wait_for(7, jitter=True, min=0, max=2)

    for _ in range(0, num_questions):
        button_overlay_panel = driver.find_element_by_id("overlayPanel")
        trivia_overlay_data = button_overlay_panel.find_element_by_class_name("TriviaOverlayData")
        current_question_container = trivia_overlay_data.find_element_by_id("currentQuestionContainer")
        question = current_question_container.find_element_by_class_name("rqQuestion")
        options = question.find_element_by_class_name("btOptions")
        option = options.find_element_by_id("rqAnswerOption0")
        option.click()
        wait_for(7, jitter=True, min=0, max=2)


def supersonic_quiz(driver: webdriver.Firefox):
    """
    Completes the "super-sonic" quiz
    :param driver: The web driver used to interact with the browser
    """
    # get the number of points
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    container = welcome_container.find_element_by_class_name("rqWcHeader")
    points = container.find_element_by_class_name("rqWcpoints")
    points = points.text
    points = points.split(" ")[0]
    num_questions = int(points) / 10

    num_questions = int(num_questions)
    quiz = driver.find_element_by_id("QuizContainerWrapper")
    trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
    wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
    button_overlay = wrapper.find_element_by_id("btOverlay")
    overlay_panel = button_overlay.find_element_by_id("overlayPanel")
    trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
    welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
    button = welcome_container.find_element_by_id("rqStartQuiz")
    button.click()
    wait_for(7, jitter=True, min=0, max=2)

    for _ in range(0, num_questions):
        for i in range(0, 8):
            quiz = driver.find_element_by_id("QuizContainerWrapper")
            trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
            wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
            button_overlay = wrapper.find_element_by_id("btOverlay")
            overlay_panel = button_overlay.find_element_by_id("overlayPanel")
            trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
            question_container = trivia_data.find_element_by_id("currentQuestionContainer")
            all_options = question_container.find_element_by_class_name("b_slideexp")
            overlay = all_options.find_element_by_class_name("b_overlay")
            viewport = overlay.find_element_by_css_selector(".b_viewport.scrollbar")
            slidebar = viewport.find_element_by_class_name("b_slidebar")
            buttons = slidebar.find_element_by_class_name("btOptions")
            options = buttons.find_elements_by_class_name("slide")
            option = options[i]
            option.click()
            wait_for(7, jitter=True, min=0, max=2)


def daily_set(driver: webdriver.Firefox):
    """
    The daily set is composed of 3 items, the first being a simple click search, the
    second being a quiz and the last being a poll. All three of these tasks are automated
    when completed multiple days in a row Microsoft Rewards provides bonus pts.
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
    except Exception as e:
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
        wait_for(9, jitter=True)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        elem = driver.find_element_by_xpath("/html/body")
        flyout = elem.find_element_by_id("modern-flyout")
        wait_for(9, jitter=False)
        quiz = flyout.find_elements_by_class_name("promo_cont")[1]
        wait_for(9, jitter=False)
        quiz.click()
        driver.switch_to.default_content()
        wait_for(9, jitter=False)

        #  Grabs the name of the quiz (1 of 4 options)
        quiz = driver.find_element_by_id("QuizContainerWrapper")
        trivia_overlay = quiz.find_element_by_id("b_TriviaOverlay")
        wrapper = trivia_overlay.find_element_by_id("overlayWrapper")
        button_overlay = wrapper.find_element_by_id("btOverlay")
        overlay_panel = button_overlay.find_element_by_id("overlayPanel")
        trivia_data = overlay_panel.find_element_by_class_name("TriviaOverlayData")
        welcome_container = trivia_data.find_element_by_id("quizWelcomeContainer")
        title_class = welcome_container.find_element_by_class_name("rqTitle")
        title = title_class.find_element_by_class_name("b_topTitle")
        print(title.text)

        if title.text == "Lightspeed quiz":
            lightspeed_quiz(driver)
        elif title.text == "This or That?":
            thisorthat_quiz(driver)
        elif title.text == "Supersonic quiz":
            supersonic_quiz(driver)
        else:  # Normal quiz
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
    except Exception as e:
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
        wait_for(5, jitter=True, min=0, max=2)
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
    except Exception as e:
        #  Either the user interacted with the screen or the daily set is already done
        pass


def print_report(time_taken: int):
    """
    Once everything is complete the resulting points will be output
    :param time_taken: The amount of time taken to complete all searching (in seconds)
    """
    global FINAL_POINTS
    global INITIAL_POINTS
    print("""
 ____  ____  ____   __  ____  ____ 
(  _ \(  __)(  _ \ /  \(  _ \(_  _)
 )   / ) _)  ) __/(  O ))   /  )(  
(__\_)(____)(__)   \__/(__\_) (__)
""")
    ty_res = gmtime(time_taken)
    res = strftime("%H:%M:%S", ty_res)

    print("Total Time: ", res)
    for email in FINAL_POINTS.keys():
        points = FINAL_POINTS[email]
        if points == "BLOCKED":
            print(RED + "\t{} IS BLOCKED".format(email) + END)
            print()
            continue
        if FINAL_POINTS[email] is None or INITIAL_POINTS[email] is None:
            print(RED + "\tERROR Collecting {} Points".format(email) + END + "\n")
            continue
        print("\t{} Total points:  {}".format(email, points))
        print("\t{} Earned points: {}".format(" " * len(email), FINAL_POINTS[email] - INITIAL_POINTS[email]))
        if points >= 6500:
            print(GREEN + "\tTime to cash in $$$" + END)
        print()


if __name__ == '__main__':
    #  Don't change. This user agent represents an edge browser which will give you 600 more points per month
    DESKTOP_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36 Edg/85.0.564.68"
    MOBILE_USERAGENT = "Mozilla/5.0 (Android 6.0.1; Mobile; rv:77.0) Gecko/77.0 Firefox/77.0"
    #  Don't change. More != better. There is a maximum amount of points you can get per day
    #  the amount of searches per account (1 search = 5 pts)
    NUM_WORDS_DESKTOP = 35  # 30 searches for 150 Desktop pts; 4 searches for 20 Edge pts; 1 extra
    NUM_WORDS_MOBILE = 25  # 20 searches for 100 Mobile pts; 5 extra

    try:
        assert path.isfile(GECKO_DRIVER)
    except AssertionError as e:
        print('\nERROR: {} NOT FOUND'.format(GECKO_DRIVER))
        exit(1)

    print(ASCII_ART)

    print("Google Trending Topics")
    all_trending_topics = google_trends()

    START_TIME = time()
    print("""
 _  _   __  ____  __  __    ____ 
( \/ ) /  \(  _ \(  )(  )  (  __)
/ \/ \(  O )) _ ( )( / (_/\ ) _) 
\_)(_/ \__/(____/(__)\____/(____)

\n""")
    start(all_trending_topics, MOBILE_USERAGENT, NUM_WORDS_MOBILE, mimicDesktop=False)

    wait_for(60, jitter=False)

    print("""
 ____  ____  ____  __ _  ____  __  ____ 
(    \(  __)/ ___)(  / )(_  _)/  \(  _ \\
 ) D ( ) _) \___ \ )  (   )( (  O )) __/
(____/(____)(____/(__\_) (__) \__/(__)  
\n""")
    start(all_trending_topics, DESKTOP_USERAGENT, NUM_WORDS_DESKTOP, mimicDesktop=True)
    STOP_TIME = time()

    difference_in_time = STOP_TIME - START_TIME

    print_report(difference_in_time)

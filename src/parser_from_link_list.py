import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import time
import re

USER_LOGIN = ''
USER_PASSWORD = ''
JOB_TITLE = ''
POSTS_URL_SUFFIX = 'recent-activity/all/'
POSTS_URL_PREFIX = 'https://www.linkedin.com/feed/update/'
NUM_PAGES_TO_PARSE = 17
NUM_SCROLLS = 4


def gen_search_query(JOB_TITLE):
    return f'https://www.linkedin.com/search/results/people/?currentCompany=%5B%2212611%22%2C%2225880%22%2C%2210718%22%2C%2277009034%22%2C%22579461%22%2C%2276092120%22%2C%2219201%22%2C%226132%22%2C%228979%22%2C%22111769%22%2C%222223110%22%2C%2232642%22%2C%223275554%22%2C%2235639643%22%2C%2237181095%22%2C%2277366986%22%2C%2280856181%22%2C%228699%22%2C%2297007097%22%2C%2297279296%22%2C%2297345934%22%5D&keywords={JOB_TITLE}&origin=FACETED_SEARCH&sid=_yf'

# to randomize time before scrolling posts
def calc_cooldown(left=1.5, right=3.0):
    return np.random.uniform(left, right)

def get_profile_info(driver, profile_url):
    driver.get(profile_url)     # this will open the link
    
    time.sleep(4.5) # extratime for loading
    
    # Extracting data from page with BeautifulSoup
    cur_profile_url = driver.current_url
    src = driver.page_source

    # Now using beautiful soup
    soup = BeautifulSoup(src, 'lxml')

    # Extracting the HTML of the complete introduction box
    # that contains the name, company name, and the location
    intro = soup.find('div', {'class': 'pv-text-details__left-panel'})

    # In case of an error, try changing the tags used here.
    name_loc = intro.find("h1")

    # Extracting the Name
    name = name_loc.get_text().strip() # strip() is used to remove any extra blank spaces
    
    works_at_loc = intro.find("div", {'class': 'text-body-medium'})

    # this gives us the HTML of the tag in which the Company Name is present
    # Extracting the Company Name
    works_at = works_at_loc.get_text().strip()
    
    # find work experience and scroll to it
    experience = driver.find_element(By.CLASS_NAME, 'pvs-list__outer-container')
    actions = ActionChains(driver)
    actions.scroll_to_element(experience).scroll_by_amount(0, 600).perform()
    
    # create variable and find experience
    exp = soup.find_all(lambda tag: tag.name == 'span' and
                                   tag.get('class') == ['visually-hidden'])

    # convert experience to text
    exp_list = []
    for el in exp:
        exp_list.append(el.get_text())

    
    try:# clean data from unnecessary information ('None' like a flag for deleting)   
        exp_list = exp_list[exp_list.index('Опыт работы')+1:exp_list.index('Образование')]
        exp_list = list(map(lambda x: None if x.__contains__(',') or x.__contains__('Навыки') else x, exp_list))
        exp_list = list(map(lambda x: None if x == None or len(x) > 100 else x, exp_list))
    except: 
        exp_list = ['experience parsing error']

    # create list with first 3 rows (last work), but we can change length
    exp_list = [i for i in exp_list if i != None]
    # exp_list = exp_list[:3]  # uncomment this row to reduce exp1
    
    return [cur_profile_url, name, works_at, exp_list]

def grab_reactions(post_src):
    reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__reactions-count'})

    # If number of reactions is written as text
    # It has different class name
    if reaction_cnt is None:
        reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__social-proof-text'})

    if reaction_cnt is not None:
        reaction_cnt = reaction_cnt.get_text().strip()
    
    return reaction_cnt

def grab_comments(post_src):
    comment_cnt = post_src.find(text=re.compile('[^"]*?комментар[^"]*?'))

    # If number of reactions is written as text
    # It has different class name
    if comment_cnt is None:
        return 0
    else:
        comment_cnt = comment_cnt.get_text().strip()
    
    return comment_cnt

def get_and_print_user_posts(driver, posts_url):
    driver.get(posts_url)

#     #Simulate scrolling to capture all posts
#     SCROLL_PAUSE_TIME = 1.5

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    # We can adjust this number to get more posts
#     NUM_SCROLLS = 1

    for i in range(NUM_SCROLLS):
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
#         time.sleep(SCROLL_PAUSE_TIME)
        time.sleep(calc_cooldown())

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        
        # Wait to try to click on the show more results button
        time.sleep(calc_cooldown())

        # Try clicking on the show more results button
        try: driver.find_element(By.XPATH, "//button[@class='artdeco-button artdeco-button--muted artdeco-button--1 artdeco-button--full artdeco-button--secondary ember-view scaffold-finite-scroll__load-button']").click()
        except: continue

    # Parsing posts
    src = driver.page_source

    # Now using beautiful soup
    soup = BeautifulSoup(src, 'lxml')
    # soup.prettify()
    
    name = soup.find('h3', class_='single-line-truncate t-16 t-black t-bold mt2').get_text().strip()
    posts = soup.find_all('li', class_='profile-creator-shared-feed-update__container')
    # print(posts)
    
    post_texts = []
    post_reactions = []
    post_comments = []
    post_urls = []

#     print(f'Number of posts: {len(posts)}')
#     for post_src in posts:
# #         post_text_div = post_src.find('div', {'class': 'feed-shared-update-v2__description-wrapper mr2'})
#         post_text_div = post_src.find('div', {'class': re.compile("^feed-shared-update-v2__description-wrapper")})

#         # if post_text_div is None:
#         #     print(post_src)

#         if post_text_div is not None:
#             post_text = post_text_div.find('span', {'dir': 'ltr'})
#         else:
#             post_text = None

#         # If post text is found
#         if post_text is not None:
#             post_text = post_text.get_text().strip()
#             print(f'Post text: {post_text}')

#         reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__reactions-count'})

#         # If number of reactions is written as text
#         # It has different class name
#         if reaction_cnt is None:
#             reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__social-proof-text'})

#         if reaction_cnt is not None:
#             reaction_cnt = reaction_cnt.get_text().strip()
#             print(f'Reactions: {reaction_cnt}')

#     return

    for post_src in posts:
        grab = False
        texts = post_src.find_all("span", {"dir":"ltr"})
        if len(texts) > 1 and texts[0].get_text().strip() == name and texts[1] is not None:
            try: grab = texts[1].parent['class'] == ['break-words']
            except: 
                try: grab = texts[1].parent.parent['class'] == ['break-words']
                except: pass
        if grab:
            post_urls.append(POSTS_URL_PREFIX + post_src.find('div', {'data-urn': re.compile('^urn:li:activity:')})['data-urn']) 
            post_texts.append(texts[1].get_text().strip())
            post_reactions.append(grab_reactions(post_src))
            post_comments.append(grab_comments(post_src))
                
    return [post_texts, post_reactions, post_comments, post_urls]

if __name__ == '__main__':
    # start Chrome browser
    caps = DesiredCapabilities().CHROME

    caps['pageLoadStrategy'] = 'eager'

    driver = webdriver.Chrome()

    # Opening linkedIn's login page
    # NOTE: We need to turn of 2 step authentification
    driver.get("https://linkedin.com/uas/login")

    input('Enter your login and password on webpage and press "Enter"')


    profile_urls = pd.read_csv('D:/Data_Science/mentoring/src/Senior_Developer_links.csv')
    profile_urls = profile_urls['0'].tolist()
    #profile_urls = list(set(profile_urls))

    #pd.Series(profile_urls).to_csv(f'{JOB_TITLE}_links.csv')

#     print(profile_urls)

    # Parse profile urls
    profile_info = []
    
    for i, profile_url in enumerate(profile_urls, start = 1):
        profile_data = get_profile_info(driver, profile_url)
        cur_profile_url = driver.current_url
        profile_data_2 = get_and_print_user_posts(driver, cur_profile_url + POSTS_URL_SUFFIX)
        profile_info.append(profile_data + profile_data_2)
        if i % 5 == 0:
            profile_info_df = pd.DataFrame(profile_info, columns=['profile_url', 'name', 'works_at', 'exp_list', 'posts', 'reactions', 'comments', 'post_url'])
            profile_info_df.to_csv('profile_info.csv')
            
        time.sleep(2)    
        
    profile_info_df = pd.DataFrame(profile_info, columns=['profile_url', 'name', 'works_at', 'exp_list', 'posts', 'reactions', 'comments', 'post_url'])
    profile_info_df.to_csv('profile_info.csv')
    
    # close the Chrome browser
    driver.quit()

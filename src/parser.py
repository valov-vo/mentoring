# импорт и загрузка библиотек

# общие
import re
import time
import numpy as np
import pandas as pd

# парсинг
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# настройки работы парсера
JOB_TITLE               = '<JOB TITLE>' # профессия для поиска профилей
USER_LOGIN              = '<LINKEDIN LOGIN>'
USER_PASSWORD           = '<LINKEDIN PASSWORD>'
POSTS_URL_SUFFIX        = 'recent-activity/all/'
POSTS_URL_PREFIX        = 'https://www.linkedin.com/feed/update/'
NUM_PAGES_TO_PARSE      = 30
NUM_SCROLLS             = 4
CONTINUE_PARSING        = False # если продолжаем парсинг по ранее сохраненным ссылкам на профили
CONTINUE_FROM_PROFILE_N = 0 # порядковый номер профиля для продолжения парсинга
PROFILE_URLS_PATH       = '<PROFILE URLS PATH>' # адрес для загрузки файла со ссылками на профили для продолжения парсинга 
PROFILE_INFO_PATH       = '<PROFILE INFO PATH>' # адрес для загрузки файла со спарсенными данными для продолжения парсинга 

# создание функции gen_search_query
def gen_search_query(job_title: str) -> str:
    '''
    Функция генерирует и возваращает ссылку с результатами выдачи поиска на LinkedIn по вакансии людей, 
    в настоящее время работающих в целевых компаниях, полученных от рекрутера:
    - Bell Integrator;
    - Beeline;
    - Innotech;
    - Gazprombank
    - LANIT;
    - Kaspresky;
    - Megafon;
    - MTS (включая MTS Digital);
    - Rambler&Co;
    - Sberbank (включая СберТех);
    - Tinkoff;
    - VK;
    - VTB;
    - Yandex.
    
    Аргументы:
    - job_title - название вакансии, для которой необходимо сгенерировать результаты выдачи поиска.
    '''
    
    return f'https://www.linkedin.com/search/results/people/?currentCompany=%5B%2212611%22%2C%2225880%22%2C%2210718%22%2C%2277009034%22%2C%22579461%22%2C%2276092120%22%2C%2219201%22%2C%226132%22%2C%228979%22%2C%22111769%22%2C%222223110%22%2C%2232642%22%2C%223275554%22%2C%2235639643%22%2C%2237181095%22%2C%2277366986%22%2C%2280856181%22%2C%228699%22%2C%2297007097%22%2C%2297279296%22%2C%2297345934%22%5D&keywords={job_title}&origin=FACETED_SEARCH&sid=_yf'

# создание функции calc_cooldown
def calc_cooldown(left  = 1.5: float, 
                  right = 3.0: float) -> float:
    '''
    Функция генерирует и возвращает число из непрерывного равномерного распределения.
    Результат используется для рандомизации пауз в работе парсера.
    
    Аргументы:
    - left, right - левая и правая границы распределения.
    '''
    
    return np.random.uniform(left, right)

def get_profile_info(driver, profile_url: str):
    '''
    Функция собирает и сохраняет информацию из профиля на LinkedIn:
    - имя и фамилию;
    - текущие должность и место работы;
    - предыдущий опыт.
    
    Аргументы:
    - driver      - объект webdriver библиотеки selenium;
    - profile_url - ссылка профиля для парсинга.
    '''
    
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
    
    # Extracting the HTML of the box
    # that contains the company name and job titlw
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

    exp_list = [i for i in exp_list if i != None]
    
    return [cur_profile_url, name, works_at, exp_list]

# создание функции grab_comments_cnt
def grab_comments_cnt(post_src):
    '''
    Функиця находит и возвращает количество комментариев к посту.
    
    Аргументы:
    - post_src - html код поста.
    '''
        
    comment_cnt = post_src.find(text=re.compile('[^"]*?комментар[^"]*?'))
    
    if comment_cnt is None:
        return 0
    else:
        comment_cnt = comment_cnt.get_text().strip()
    
    return comment_cnt

# создание функций grab_reactions_cnt
def grab_reactions_cnt(post_src):
    '''
    Функиця находит и возвращает количество реакций к посту.
    
    Аргументы:
    - post_src - html код поста.
    '''
    
    reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__reactions-count'})

    # If number of reactions is written as text
    # It has different class name
    if reaction_cnt is None:
        reaction_cnt = post_src.find('span', {'class': 'social-details-social-counts__social-proof-text'})

    if reaction_cnt is not None:
        reaction_cnt = reaction_cnt.get_text().strip()
    
    return reaction_cnt

# создание функций get_user_posts
def get_user_posts(driver, posts_url):
    '''
    Функиця находит и возвращает список, содержащий текст поста, ссылки на пост, количества реакций и комментариев. 
    Если пост является репостом без текста, написанного автором анкеты, такой пост игнорируется.
    
    Аргументы:
    - driver   - объект webdriver библиотеки selenium;
    - post_src - html код поста.
    '''    
    
    
    driver.get(posts_url)

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(NUM_SCROLLS):
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
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
    
    # сохранение имени и фамилии в отдельную переменную 
    name = soup.find('h3', class_='single-line-truncate t-16 t-black t-bold mt2').get_text().strip()
    
    # поиск и сохранение постов владельца анкеты    
    posts = soup.find_all('li', class_='profile-creator-shared-feed-update__container')
    
    # создание списков для сохранения текстов постов, количества реакций и комментариев и ссылок на посты
    post_texts     = []
    post_reactions = []
    post_comments  = []
    post_urls      = []
    
    # по каждому посту     
    for post_src in posts:
        
        # создание индикатора, есть ли в посте текст, написанный владельцем анкеты 
        grab = False
         
        # поиск текстовых блоков 
        texts = post_src.find_all("span", {"dir":"ltr"})
        
        # проверка, содержит ли пост текст владельца анкеты 
        if len(texts) > 1 and texts[0].get_text().strip() == name and texts[1] is not None:
            try: grab = texts[1].parent['class'] == ['break-words']
            except: 
                try: grab = texts[1].parent.parent['class'] == ['break-words']
                except: pass
        
        # если пост содержит текст, написанный владельцем анкеты          
        if grab:
            
            # сохранение текста поста, количества реакций и комментариев и ссылки на пост
            post_urls.append(POSTS_URL_PREFIX + post_src.find('div', {'data-urn': re.compile('^urn:li:activity:')})['data-urn']) 
            post_texts.append(texts[1].get_text().strip())
            post_reactions.append(grab_reactions_cnt(post_src))
            post_comments.append(grab_comments_cnt(post_src))
                
    return [post_texts, post_reactions, post_comments, post_urls]

if __name__ == '__main__':
    
    # start Chrome browser
    caps = DesiredCapabilities().CHROME

    caps['pageLoadStrategy'] = 'eager'

    driver = webdriver.Chrome()

    # Opening linkedIn's login page
    # NOTE: We need to turn of 2 step authentification
    driver.get("https://linkedin.com/uas/login")

    # waiting for the page to load
    time.sleep(calc_cooldown())

    # entering username
    username = driver.find_element(By.ID, "username")

    # In case of an error, try changing the element
    # tag used here.

    # Enter Your Email Address
    username.send_keys(USER_LOGIN)

    # entering password
    pword = driver.find_element(By.ID, "password")
    # In case of an error, try changing the element
    # tag used here.

    # Enter Your Password
    pword.send_keys(USER_PASSWORD)

    # Clicking on the log in button
    # Format (syntax) of writing XPath -->
    # //tagname[@attribute='value']
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # если начинаем парсинг с начала    
    if not CONTINUE_PARSING:
    
        # Open search page
        driver.get(gen_search_query(JOB_TITLE))

        profile_urls = []

        # Iterate over pages of search results
        # to collect profile urls
        for i in range(NUM_PAGES_TO_PARSE):
            search_result_links = driver.find_elements(By.CSS_SELECTOR, "div.entity-result__item a.app-aware-link")

            for link in search_result_links:
                href = link.get_attribute("href")
                if 'linkedin.com/in' in href:
                    profile_urls.append(href)

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(calc_cooldown())
            next_button = driver.find_element(By.CLASS_NAME,'artdeco-pagination__button--next')
            next_button.click()
            time.sleep(calc_cooldown())
         
        profile_urls = list(set(profile_urls)) # удаляем дубликаты в собранных ссылках на профили
        pd.Series(profile_urls).to_csv(f'{JOB_TITLE}_links.csv') # сохраняем собранные ссылки на профили
        
        profile_info = [] # создаем список для сохранения результатов парсинга по профилю
    
    # если продолжаем парсинг по ранее сохраненным ссылкам на профили
    else:
        profile_urls = pd.read_csv(PROFILE_URLS_PATH)['0'].to_list() # загружаем ранее собранные ссылки на профили
        profile_info = pd.read_csv(PROFILE_INFO_PATH, index_col=0).values.tolist() # загружаем ранее собранную информацию с профилей

    # Parse profile urls    
    for i, profile_url in enumerate(profile_urls[CONTINUE_FROM_PROFILE_N:], start = 1):
        profile_data = get_profile_info(driver, profile_url) # вызов функции get_profile_info
        cur_profile_url = driver.current_url
        profile_data_2 = get_user_posts(driver, cur_profile_url + POSTS_URL_SUFFIX) # вызов функции get_user_posts
        profile_info.append(profile_data + profile_data_2) # объединение и сохранение результатов парсинга по странице польззователя
        
        # save parsed data after each 10 profiles
        if i % 10 == 0:
            profile_info_df = pd.DataFrame(profile_info, columns=['profile_url', 'name', 'works_at', 'exp_list', 'posts', 'reactions', 'comments', 'post_url'])
            profile_info_df.to_csv(f'{JOB_TITLE}_profile_info.csv')
            
        time.sleep(calc_cooldown())    
    
    # save parsed data
    profile_info_df = pd.DataFrame(profile_info, columns=['profile_url', 'name', 'works_at', 'exp_list', 'posts', 'reactions', 'comments', 'post_url'])
    profile_info_df.to_csv(f'{JOB_TITLE}_profile_info.csv')
    
    # close the Chrome browser
    driver.quit()

#!/usr/bin/env python
# coding: utf-8

# In[19]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import visibility_of_element_located, presence_of_element_located
from selenium.webdriver.chrome.service import Service
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import time


# In[2]:


# Webdriver settings
def driver_init():
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--headless=new")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Akagami/170.0.0.0"
    options.add_argument("user-agent=" + user_agent)
    driver = webdriver.Chrome(service=Service("C:/chromedriver/chromedriver.exe"), options=options)
    driver.set_window_size(800, 2000)
    return driver


# In[18]:


# Get href_list
def href_list_content(current_url, href_content):
    lider_link = "https://www.lider.cl"
    channel = current_url.split('/')[-1]
    href_list = [
        lider_link + href['href'].replace(f"/{channel}/{lider_link}", "")
        if lider_link in href['href'] else lider_link + href['href']
        for href in href_content
    ]
    return href_list


# In[4]:


# Por si se encuentra una caluga con time sales
def cal1_url(browser, url):
    try:
        browser.execute_script("window.open('');")
        browser.switch_to.window(browser.window_handles[-1])
        browser.get(url)
        banner_element = "//div[@class='limited-time-sales__sale-banner' and @role='presentation']"
        WebDriverWait(driver=browser, timeout=15).until(visibility_of_element_located((By.XPATH, banner_element)))
        button = browser.find_element(By.XPATH, banner_element)
        button.click()
        WebDriverWait(driver=browser, timeout=15).until(visibility_of_element_located((By.CLASS_NAME, 'ais-Pagination-list')))
        href_list = [ browser.current_url ]
        print(f'url limited time sales encontrada {href_list[0]}')
    except Exception as e:
        href_list = []
        print(href_list)
        print(f'No se pudo obtener la url de la Caluga 1. {str(e)}')
    return href_list
        


# In[5]:


def slides_banners_href(url):
    browser = driver_init()
    browser.get(url)
    try:
        WebDriverWait(driver=browser, timeout=15).until(visibility_of_element_located((By.XPATH, "//div[@class='slick-slider slick-initialized' and @dir='ltr']")))
        ul_tag = browser.find_element(By.XPATH, "//ul[@class='slick-dots']")
        li_tags = ul_tag.find_elements(By.TAG_NAME, "li")
        count_dots = len(li_tags)

        for _ in range(count_dots):
            next_button = browser.find_element(By.XPATH, "//button[@type='button' and @class='slick-arrow slick-next']")
            next_button.click()
            time.sleep(1)

        current_url = browser.current_url

        content = browser.page_source
        soup = BeautifulSoup(content, "html.parser")
        slides_href_content = set(soup.find_all('a', class_='banners-home__banner'))
        slides_href_list = href_list_content(current_url, slides_href_content)

        while True:
            current_scroll_pos = browser.execute_script("return window.pageYOffset;")
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)
            new_scroll_pos = browser.execute_script("return window.pageYOffset;")
            if new_scroll_pos == current_scroll_pos:
                break
        
        WebDriverWait(driver=browser, timeout=15).until(visibility_of_element_located((By.ID, 'corporate_footer_lider_bci')))
        banners_href_content = soup.find_all('a', href=True, attrs={"data-testid": "advertising-slot-test-id"})
        banners_href_list = href_list_content(current_url, banners_href_content)

        for cal in banners_href_list:
            if 'Cal1' in cal or 'Caluga_1' in cal:
                print('Caluga 1 no se encuentra en "limited time sales"')
                return slides_href_list, banners_href_list
            else:
                cal1_limited = cal1_url(browser, url)
                banners_href_list.extend(cal1_limited)
                return slides_href_list, banners_href_list
    except Exception as e:
        print(f'Se produjo un error: {str(e)}')
    finally:
        browser.close()


# In[6]:


# Gettins soup content
def get_soup_item_content(browser, url):
    try:
        browser.get(url)
        WebDriverWait(driver=browser, timeout=20).until(visibility_of_element_located((By.CLASS_NAME, 'ais-Hits')))
        browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        content = browser.page_source
        soup = BeautifulSoup(content, "html.parser")
        return soup
    except Exception as e:
        print(f'No se pudo obtener el contenido soup en la url {url}. {str(e)}')
        return None

def scrap_item_content_from_url(url, soup, pages_dict):
    try:
        query_params = parse_qs(urlparse(url).query)
        items_soup = soup.find_all('li', class_='ais-Hits-item')
        lista = []

        ads_name = query_params['ads_name'][0]
        ads_position = query_params['ads_position'][0]
        ads_id = query_params['ads_id'][0]

        for item in items_soup:
            href = item.find('a')['href']
            product_nbr = item.find('div', class_='product-card__image-area overlay-wrap overflow-hidden bg-white')['id']
            lista.append({
                'url': url,
                'products_quantity': pages_dict['n_products'],
                'ads_name': ads_name,
                'ads_position': ads_position,
                'ads_id': ads_id,
                'href': href,
                'products_nbr': product_nbr
            })
        return lista
    except Exception as e:
        print(f'Atributos de item NO scrapeados en url {url}. {str(e)}')
        return []
        


# In[15]:


def products_scraper(url):
    try:
        browser = driver_init()
        url = url.replace("hitsPerPage=16", '').replace("page=1", '').replace("ads", '&ads')
        soup = get_soup_item_content(browser, url)
        n_products = int(soup.find('div', class_='products-qantity-and-order-desktop__quantity-shown').string.split(' ')[-2])
        pages_dict = {'n_products': n_products, 'max_pages': 1 if n_products < 100 else int(soup.find('ul', class_='ais-Pagination-list').find_all('a', class_='ais-Pagination-link')[-1].string)}
        
        lista = scrap_item_content_from_url(url, soup, pages_dict)
        for page in range(1, pages_dict['max_pages'] + 1):
            url_parts = urlparse(url)
            query_params = parse_qs(url_parts.query)
            query_params['page'] = page
            new_query_string = urlencode(query_params, doseq=True)
            new_url_parts = url_parts._replace(query=new_query_string)
            url = urlunparse(new_url_parts)
            soup = get_soup_item_content(browser, url)
            lista.extend(scrap_item_content_from_url(url, soup, pages_dict))
            print(f"Pagina {page} de {pages_dict['max_pages']} scrapeadas de {query_params['ads_position'][0]}")
        browser.close()
        df = pd.DataFrame(lista)
        return df
    except Exception as e:
        print(f'Error en la url {url}. {str(e)}')
        return []


# In[16]:


def process_cycle(url):
    slides, banners = slides_banners_href(url)
    url_list = []
    url_list.extend(slides)
    url_list.extend(banners)
    print(f'slides {len(slides)} = {slides}')
    print(f'banners {len(banners)} = {banners}')
    list_df = []
    for url in url_list:
        try:
            list_df.append(products_scraper(url))
        except Exception as e:
            print(str(e))
            pass
    return pd.DataFrame.concat(list_df)


# In[17]:


if __name__ == '__main__':
    catex_url = 'https://www.lider.cl/catalogo'
    sod_url = 'https://www.lider.cl/supermercado'
    catex_df = process_cycle(catex_url)
    sod_df = process_cycle(sod_url)


    if catex_url is not None:
        print(f'Scraper catex terminado:\n{catex_df}')
    if sod_url is not None:
        print(f'Scraper sod terminado:\n{sod_df}')


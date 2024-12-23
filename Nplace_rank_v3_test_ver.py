from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from bs4 import BeautifulSoup
from threading import Thread, Event
 
from time import sleep
 
from selenium import webdriver
 
options = webdriver.ChromeOptions()
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
options.add_argument('window-size=1380,900')
#options.add_argument('headless=new')
#options.add_argument("disable-gpu")
driver = webdriver.Chrome(options=options)
 
# 대기 시간
driver.implicitly_wait(time_to_wait=3)
 
# 반복 종료 조건
keyword = "사상터미널 맛집"
업체_ID = '1220246922'
URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
driver.get(url=URL)

result_placeid = []

class ThreadWithReturnValue(Thread):
    
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return
    
def split_url(url):
    first_split = url.split('/')
    last_split = first_split[-1].split('?')
    
    return last_split[0]

def get_naver_rank(keyword, 업체_ID) :
#def get_naver_rank(keyword) :
    
    try:
        place_or_loc = driver.find_element(By.ID, 'place-app-root').find_element(By.XPATH, './div[last()]').get_attribute('id')
        펼쳐서_더보기 = driver.find_element(By.CLASS_NAME, 'place_section.Owktn').find_element(By.XPATH, './div[last()]').get_attribute('class')

        if place_or_loc == 'place-main-section-root':
            if 펼쳐서_더보기 == 'rdX0R':
                펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R > div > a"
            elif 펼쳐서_더보기 == 'rdX0R POx9H':
                펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R.POx9H > div > a"
        elif place_or_loc == 'loc-main-section-root':
            if 펼쳐서_더보기 == 'rdX0R':
                펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R > div > a"
            elif 펼쳐서_더보기 == 'rdX0R POx9H':
                펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R.POx9H > div > a"
        else:
            driver.quit()
            return '플레이스 조회와 관련이 없는 키워드 또는 업체'

        펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
        )
        펼쳐서_더보기_엘리먼트.click()

        if place_or_loc == 'place-main-section-root':
            더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
        elif place_or_loc == 'loc-main-section-root':
            더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"
        
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()

        전체_엘리먼트들 = []
        타겟_업체_인덱스 = -1

        while True:
            for _ in range(9):
                ActionChains(driver).send_keys(u'\ue004').perform()
            for _ in range(6):
                ActionChains(driver).send_keys(u'\ue010').perform()
                sleep(0.4)
            
            엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
            엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')
            
            if 엘리먼트_클래스2[0] != '':
                엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
            else:
                엘리먼트들 = []
                driver.quit()
                return "잘못된 키워드"
            
            for 엘리먼트 in 엘리먼트들:
                if len(엘리먼트_클래스2) > 1:
                    if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
                        전체_엘리먼트들.append(엘리먼트)
                        if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                            타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
                else:
                    전체_엘리먼트들.append(엘리먼트)
                    if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                        타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
            
            # for 엘리먼트 in 엘리먼트들:
            #     if len(엘리먼트_클래스2) > 1:
            #         if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
            #             전체_엘리먼트들.append(엘리먼트)
            #     else:
            #         전체_엘리먼트들.append(엘리먼트)
            
            if 타겟_업체_인덱스 == -1:
                print(keyword + " // 순위권 외")
                result = '-'
                driver.quit()
                return result
            
            for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
                place_url = 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href")
                result_url = split_url(place_url)
                result_placeid.append(result_url)
            
            if 타겟_업체_인덱스 != -1:
                rank = 타겟_업체_인덱스 + 1
                result = f"{rank}위"
                break
            
            if not 엘리먼트들:
                driver.quit()
                return f"-"
            
            print("1", result, result_placeid, len(result_placeid))
            return result_placeid

    except Exception as e:
        driver.quit()
        print({e})
        return f"오류 발생 : 관리자 문의"
        
#result_thread = ThreadWithReturnValue(target=get_naver_rank, args=keyword)
#result_thread.start()

get_naver_rank(keyword, 업체_ID)
    
#result_fin = result_thread.join()
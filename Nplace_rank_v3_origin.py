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
keyword = "마린시티 카페"
업체_ID = '1615812977'
URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
driver.get(url=URL)

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

def get_naver_rank(keyword, 업체_ID) :
    
    # 플레이스 필터에 해당하는지, 해당하지 않는지 체크
    # 해당하면 place-main-section-root 반환
    # 해당하지 않으면 loc-main-section-root 반환함
    place_or_loc = driver.find_element(By.ID, 'place-app-root').find_element(By.XPATH,'./div[last()]').get_attribute('id')
    
    펼쳐서_더보기 = driver.find_element(By.CLASS_NAME, 'place_section.Owktn').find_element(By.XPATH, './div[last()]').get_attribute('class')

    ##### 명확한 키워드가 아니면 m.place.naver.com 뒤 카테고리 종류가 붙지 않음
    ##### 가급적 본인의 가게명을 집어넣는 키워드는 지양할 것
  
    if place_or_loc in 'place-main-section-root' :
        
        #펜션, 네일 더보기 버튼 셀렉터
        if 펼쳐서_더보기 == 'rdX0R' :
                                 #place-main-section-root > div > div.rdX0R > div > a
            펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R > div > a"
        #맛집 더보기 버튼 셀렉터
        elif 펼쳐서_더보기 == 'rdX0R POx9H' :
            펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R.POx9H > div > a"
                
    elif place_or_loc in 'loc-main-section-root' :     
        #플레이스 조회에 해당하지 않는 키워드들의 더보기 버튼 셀렉터
        if 펼쳐서_더보기 == 'rdX0R' :
            펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R > div > a"
        #맛집 더보기 버튼 셀렉터
        elif 펼쳐서_더보기 == 'rdX0R POx9H' :
            펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R.POx9H > div > a"
    
    else :
        print('플레이스 조회와 관련이 없는 키워드 또는 업체')
        펼쳐서_더보기_셀렉터 = 'null'
    
    # 2.펼쳐서 더보기 탭을 클릭하기
    try:
        펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
        )
        펼쳐서_더보기_엘리먼트.click()
    except:
        print(f"검색어 {keyword}의 '펼쳐서 더보기' 버튼을 찾을 수 없음")
        # [x] Todo 여기서 함수 종료해야함

    # "XX 더보기" 버튼이 로드될 때까지 대기
    # 대분류 카테고리에 들어가지 않는 검색 키워드 입력 시, loc-main-section-root로 진입하게 됨.
    try:
        if place_or_loc in 'place-main-section-root' :
            더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
        elif place_or_loc in 'loc-main-section-root' :
            더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()
    except Exception as e:
        print(f"더보기 버튼을 찾을 수 없음: {e}")
        driver.quit()

    전체_엘리먼트들 = []
    result_test = ""
    타겟_업체_인덱스 = -1

    # 스크롤을 내리면서 class="UEzoS"인 엘리먼트 찾기
    while True:
        for _ in range (7) : # 하단 list_scroll_container로 포커싱 자동 이동
            ActionChains(driver).send_keys(u'\ue004').perform()
        for _ in range(8) :
            ActionChains(driver).send_keys(u'\ue010').perform()
            sleep(0.2)
        
        엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
        엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')
        
        if 엘리먼트_클래스2[0] != '' :
            엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
        else :
            엘리먼트들 = ''
            print("해당 엘리먼트가 없음")
        
        for 엘리먼트 in 엘리먼트들:
            if len(엘리먼트_클래스2) > 1 :
                if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
                    전체_엘리먼트들.append(엘리먼트)
                    if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                        타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
                        
            else :
                전체_엘리먼트들.append(엘리먼트)
                if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                    타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
        
        if 타겟_업체_인덱스 == -1:
            print(keyword + " // 순위권 외")
            result = '-'
            driver.quit()
            return result
        
        ## 100개 ~ 300개 업체 전체 리스트 추출 구문.
        
        for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
            company_name = 엘리먼트.find_element(By.CLASS_NAME, "place_bluelink").text
            result_test += f"{i}. {company_name}\n"
        
        rank = 타겟_업체_인덱스 + 1
        
        ## 입력한 가게 상호 출력 구문
        store_name = 전체_엘리먼트들[타겟_업체_인덱스].find_element(By.CLASS_NAME, "place_bluelink").text

        result = f"{keyword} // {rank}위"
        print(result_test)
        print(result)
        driver.quit()
        return result
        
result_thread = ThreadWithReturnValue(target=get_naver_rank, args=(keyword,업체_ID))
result_thread.start()
    
result_fin = result_thread.join()
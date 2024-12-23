from dotenv import load_dotenv
import os
import lxml
load_dotenv()

DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from threading import Thread
from selenium import webdriver
import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from apscheduler.executors.pool import ThreadPoolExecutor as APSchedulerThreadPoolExecutor
from time import sleep, strftime, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import random
import threading

from requests.exceptions import HTTPError

import mysql.connector
from flask_caching import Cache

from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.secret_key = 'nplace_rank_secret_key'

# MySQL 데이터베이스 연결 내용 명시
conn = mysql.connector.connect(
        # host='192.168.0.26',
        host='localhost',
        user='test',
        password='tpals0430',
        database='nplace_rank_db',
        ssl_disabled=True,
)

# MySQL 데이터베이스 연결 내용 함수화
def get_db_connection():
    # 새로운 데이터베이스 커넥션을 생성합니다.
    return mysql.connector.connect(
        # host='192.168.0.26',
        host='localhost',
        user='test',
        password='tpals0430',
        database='nplace_rank_db',
        ssl_disabled=True
    )

############## APScheduler 함수 실행 부 (지정 시간마다 자동 실행)
scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Seoul')

scheduler.start()

# 플레이스 URL로 플레이스ID 추출하는 함수
def split_url(url):
    first_split = url.split('/')
    last_split = first_split[-1].split('?')
    
    return last_split[0]


cursor = conn.cursor()

# 쓰레드를 사용한 병렬 실행용 구문
class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


###################################################### 네이버 키워드별 전체 순위 검색 코드 시작 ###################################################### 

def get_naver_rank(keyword, 업체_ID, max_retries=2):
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    options.add_argument('window-size=1380,900')
    options.add_argument('headless=new')
    options.add_argument("disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})  # 이미지 비활성화
    
    retry_count = 0
    result = None

    # retry_count 변수 -> 재시도 횟수
    # max_retries 변수 -> 최대 재시도 횟수
    while retry_count < max_retries:
        sleep(random.uniform(0.5, 2))
        driver = None
        try:
            if driver is None:
                driver = webdriver.Chrome(options=options)
                
            # 접속하고자 하는 URL, 변경 X
            URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
            driver.get(url=URL)
            
            sleep(1)

            # place-app-root 부분이 나올때까지 시스템 대기
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'place-app-root')))

            # place_or_loc 변수 -> 확인 필요
            place_or_loc = driver.find_element(By.ID, 'place-app-root').find_element(By.XPATH, './div[last()]').get_attribute('id')
            
            # 펼쳐서_더보기 변수 -> 모바일 네이버에서 키워드(OOO 맛집, OOO역 피자 등) 검색 시 가게 목록 보여주는 '펼처서 더보기' 버튼의 선택자를 찾는 변수
            펼쳐서_더보기 = driver.find_element(By.CLASS_NAME, 'place_section.Owktn').find_element(By.XPATH, './div[last()]').get_attribute('class')

            # 펼처서_더보기 변수 -> rdX0R , rdX0R POx9H 2개만 확인됨. 각각 값에 따라 분기 처리함.
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
                return '플레이스 조회와 관련이 없는 키워드 또는 업체'
            
            # 위에서 찾은 펼쳐서_더보기_셀렉터가 로딩된 후, 클릭이 가능할때까지 대기.
            펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
            )
            
            # 펼쳐서 더보기 버튼 클릭 명령
            펼쳐서_더보기_엘리먼트.click()

            # 펼쳐서 더보기를 누르면 가게 목록이 추가적으로 더 나오게 됨.
            # 전체 가게 목록을 크롤링하기 위해 전체 목록을 보여주는 '더보기' 버튼을 눌러야 함.
            if place_or_loc == 'place-main-section-root':
                더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
            elif place_or_loc == 'loc-main-section-root':
                더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"

            # 펼쳐서 더보기 기능에 사용한 로직과 동일함.
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()

            # 더보기 버튼을 누르면 네이버 플레이스 페이지로 이동합니다.
            # 일반적인 크롤링이 불가능한 동적 웹페이지라 약간의 꼼수를 코드로 구성했어요.
            # 키보드의 TAB 키를 9번 누르는 액션 명령, 무한 스크롤을 뚫기 위해 End 키로 제일 최하단으로 이동하는 꼼수에요.


            # 전체_엘리먼트들 변수 -> 전체 가게 목록을 담을 리스트 변수
            전체_엘리먼트들 = []
            # 타겟_업체_인덱스 변수 -> 매개변수로 받은 업체_ID를 가진 업체의 위치(몇 등인지)를 가리키는 변수
            타겟_업체_인덱스 = -1

            while True:
                for _ in range(9):  # 키 입력 횟수 최소화
                    ActionChains(driver).send_keys(u'\ue004').perform()
                for _ in range(6):  # 키 입력 횟수 최소화
                    ActionChains(driver).send_keys(u'\ue010').perform()
                    sleep(0.4)

                # 엘리먼트_클래스 변수 -> 네이버 플레이스 페이지에서 가게 목록을 담고 있는 CSS 부분
                엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
                
                # 엘리먼트_클래스2 변수 -> '광고' 라고 붙은 가게를 제거하기 위한 리스트 변수
                # 네이버 유료 광고를 쓰는 가게는 'eDFz9 ooooo'의 클래스 이름을, 유료 광고를 안쓰는 가게는 'eDFz9' 의 클래스 이름을 씁니다.
                # 광고 업체 순서는 접속할때마다 바뀌기 때문에 랭킹에서 제외해야 합니다.
                
                #'eDFz9 ooooo' 를 split 하면 [eDFz9, ooooo] 2개로 나뉘고, 'eDFz9'를 split하면 [eDFz9]로 나뉘게 됩니다.
                엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')

                # 전체 업체 리스트를 올바르게 가져왔는지 체크하는 로직
                if 엘리먼트_클래스2[0] != '':
                    엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
                else:
                    return "잘못된 키워드"

                # 전체 업체 리스트('엘리먼트들' 변수) 에 있는 각각의 업체('엘리먼트' 변수)를 반복문으로 확인
                for 엘리먼트 in 엘리먼트들:
                    # 엘리먼트_클래스2 변수의 요소가 2개인 경우
                    if len(엘리먼트_클래스2) > 1:
                        # 분리된 [eDFz9, ooooo]에서 ooooo 이 없는 업체가 진짜 업체들이므로, 없는 ��체들만 전체_엘리먼트들 변수에 추가(append)
                        if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
                            전체_엘리먼트들.append(엘리먼트)
                            # 가져온 가게 정보 중 <a href="">에 랭킹 체크할 업체 ID가 포함된 경우 순위 산정
                            if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                                타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
                                
                    # 엘리먼트_클래스2 변수의 요소가 1개인 경우
                    else:
                        전체_엘리먼트들.append(엘리먼트)
                        if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
                            타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
                
                # 타겟_업체_인덱스 변수 -> 순위 넣는 변수, 이 변수가 -1 그대로라는건 해당 업체가 없다는 뜻
                if 타겟_업체_인덱스 == -1:
                    result = '-'
                    driver.quit()
                    return result

                # 타겟_업체_인덱스는 리스트 형식이라 0번, 1번.. 으로 시작함.
                # 따라서 제대로 랭킹을 가져온 경우, 1을 플러스해서 정상적인 랭킹으로 출력해줌.
                if 타겟_업체_인덱스 != -1:
                    rank = 타겟_업체_인덱스 + 1
                    result = f"{rank}위"
                    break
                
                # 가져온 업체 목록이 아무것도 없거나 에러일 경우 처리하는 조건문.
                if not 엘리먼트들:
                    result = '-'
                    break

            break  # 성공 시 루프 탈출

        # 해당 부분은 거의 사용하지 않으나, 랭킹을 못가져온 경우 2-3번 재실행하는 함수.
        except (selenium.common.TimeoutException, selenium.common.WebDriverException, HTTPError) as e:
            retry_count += 1
            
            if "429" in str(e):
                backoff_time = 2 ** retry_count
                print(f"429 Error: Waiting for keyword: {keyword}, 업체_ID: {업체_ID}, {backoff_time} seconds before retrying...")
                sleep(backoff_time)
                
            print(f"Error occurred for keyword: {keyword}, 업체_ID: {업체_ID}. Retry {retry_count}/{max_retries}. Exception: {e}")
            
            if retry_count == max_retries:
                result = f"Failed after {max_retries} retries"
            print(f"Unexpected error: {e}")
            
            result = f"오류 발생 : 관리자 문의"
            break

        # 최종적으로 크롬 웹 드라이버를 종료함.
        finally:
            if driver:
                driver.quit()

    # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
    if retry_count == max_retries and result is None:
        result = "TimeoutException: Max retries reached"

    return result


## 병렬 실행을 위한 코드 부분입니다.

# max_worker는 각 작업을 수행할 일꾼의 수 입니다.

# update_keyword_results_in_batches 함수는 아래 update_keyword_results 함수의 결과값을 DB에 입력/수정 요청하는 예약(batches) 기능 함수입니다.
# 아래 코드 기준으로, 말로 해석하자면 이렇게 됩니다.

# 1개의 배치(batch) = 30개의 업체+키워드 구성으로 되어있어요.
# DB에 있는 전체 업체+키워드를 중복없이 가져와서, 1 배치 단위(30개)로 N개의 배치로 쪼갭니다.
# 순서대로 1개 배치를 15개의 쓰레드가 각각 실행, 총 2번 실행하고 결과값이 나와야 1개의 배치가 종료됩니다.
# 전체 배치가 끝날때까지 해당 작업(쓰레드로 랭킹 체크 함수 실행)이 진행됩니다.

def update_keyword_results_in_batches(batch, batch_number):
    start_time = time()  # 시작 시간 기록

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_keyword = {executor.submit(get_naver_rank, keyword, place_id): (user_id, place_id, keyword) for user_id, place_id, keyword in batch}

        for future in as_completed(future_to_keyword):
            user_id, place_id, keyword = future_to_keyword[future]
            try:
                result = future.result()
                cursor.execute('INSERT INTO keyword_result (user_id, place_id, keyword, search_date, result) VALUES (%s, %s, %s, %s, %s)',
                               (user_id, place_id, keyword, strftime('%Y-%m-%d'), result))
            except Exception as e:
                cursor.execute('UPDATE keyword_result SET result = %s WHERE user_id = %s AND place_id = %s AND keyword = %s AND search_date = %s',
                               (result, user_id, place_id, keyword, strftime('%Y-%m-%d')))
                print(f"Error processing keyword {keyword}, {result}: {e}")

    conn.commit()

    end_time = time()  # 종료 시간 기록
    elapsed_time = end_time - start_time
    print(f"Batch {batch_number} processed in {elapsed_time:.2f} seconds")
    
# update_keyword_results 함수는 위에서 말한 전체 업체+키워드에 대해 쪼개는 기능을 하는 함수입니다.
# 30개씩 쪼개서 여러개의 배치를 만들고, 스케쥴러(예약 실행)에 5분마다 1 배치(30개)씩 돌아가도록 작업을 예약합니다.
# 모든 배치 작업이 끝난 후, 제대로 랭킹이 체크되지 않은 업체+키워드의 재검사를 위한 함수(start_retry_failed_keywords_job) 실행을 예약합니다.
# start_retry_failed_keywords_job 함수 설명은 다음 문단에 써두었습니다.

def update_keyword_results():
    cursor.execute('SELECT DISTINCT user_id, place_id, keyword FROM keyword_result ORDER BY user_id ASC')
    unique_keywords = cursor.fetchall()

    # 키워드 리스트를 30개씩 분할
    batches = [unique_keywords[i:i + 30] for i in range(0, len(unique_keywords), 30)]

    # 5분 간격으로 각 배치를 실행
    for index, batch in enumerate(batches):
        scheduler.add_job(update_keyword_results_in_batches, args=[batch, index + 1], trigger='date', next_run_time=datetime.now() + timedelta(minutes=5 * index))

    # 모든 배치가 완료된 후 스케줄러 종료 및 retry_failed_keywords_job 시작 예약
    final_run_time = datetime.now() + timedelta(minutes=5 * (len(batches) - 1))
    scheduler.add_job(start_retry_failed_keywords_job, trigger='date', next_run_time=final_run_time + timedelta(minutes=10))

# 주기적 작업 추가 (매일 정해진 시간에 실행하도록 설정)
scheduler = BackgroundScheduler()
scheduler.add_job(id='update_keyword_results_job', func=update_keyword_results, trigger='cron', minute="46", second='10', misfire_grace_time=60)

scheduler.start()

###################################################### 네이버 키워드별 전체 순위 검색 코드 끝끝 ###################################################### 


###################################################### 오류 키워드들 전체 순위 검색 재실행 코드 시작 ###################################################### 

# DB에 등록된 모든 업체, 모든 키워드에 대해 랭킹 체크 함수가 돌아간 다음에 실행되는 병렬 실행 함수 부분입니다.

# start_retry_failed_keywords_job 함수는 retry_failed_keywords 함수를 예약 실행하기 위한 예약 함수입니다.
def start_retry_failed_keywords_job():
    print("Starting retry_failed_keywords_job after update_keyword_results completion.")

    # 8시간 동안 10분 간격으로 retry_failed_keywords_job 실행
    end_time = datetime.now() + timedelta(hours=8)
    scheduler.add_job(retry_failed_keywords, id='retry_failed_keywords_job', trigger='interval', minutes=10, start_date=datetime.now(), end_date=end_time)

### 랭킹 체크를 실패한 키워드를 재시도하는 함수
# '~위'처럼 정상적인 결과값이 아닌 값(오류 관리자문의, TimeoutException 등)이 들어간 업체 + 키워드를 대상으로 다시 실행합니다.
# 돌아가는 시간은 차후 조절이 필요합니다.

# 모든 함수의 내용을 다 알지 않아도 괜찮아요. 어차피 챗GPT가 짜준거라 물어보면 됩니다.
def retry_failed_keywords():
    today = datetime.now().strftime('%Y-%m-%d')

    # '오류'텍스트를 포함한 result 레코드들 가져오기
    cursor.execute('SELECT place_id, keyword FROM keyword_result WHERE search_date = %s AND result LIKE %s', (today, '%오류%'))
    failed_keywords = cursor.fetchall()
    
    print(f"Found {len(failed_keywords)} failed keywords.")
    
    if not failed_keywords:
        print("No failed keywords found.")
        return

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_keyword = {
            executor.submit(get_naver_rank, keyword, place_id): (place_id, keyword) for place_id, keyword in failed_keywords
        }

        for future in as_completed(future_to_keyword):
            place_id, keyword = future_to_keyword[future]
            try:
                result = future.result()
                # 결과 업데이트
                cursor.execute(
                    'UPDATE keyword_result SET result = %s WHERE place_id = %s AND keyword = %s AND search_date = %s',
                    (result, place_id, keyword, today)
                )
            except Exception as e:
                print(f"Error processing keyword {keyword} for place_id {place_id}: {e}")

    # 변경사항을 커밋
    conn.commit()

# 스케줄러 설정 및 초기 실행
scheduler = BackgroundScheduler(executors={'default': APSchedulerThreadPoolExecutor(20)})

# update_keyword_results 작업을 매일 정해진 시간에 실행하도록 설정
scheduler.add_job(id='update_keyword_results_job', func=update_keyword_results, trigger='cron', minute="41", second='10', misfire_grace_time=60)

# 스케줄러 시작
scheduler.start()
###################################################### 오류 키워드들 전체 순위 검색 재실행 코드 끝끝 ###################################################### 


## TOP100 키워드 구문 실행 부분은 나중에 추가할 기능이에요. 지금 당장은 X
## 한번에 여러번 실행하는 부담을 줄이기 위해서 여러번 등록된 키워드들을 대상으로 먼저 실행해주는 함수라고 보심 됩니다.

####################################################### 24 08 28 TOP 100 키워드 실행 구문 테스트 시작 ###################################################### 

# # 0. get_place_rank 함수 부분, TOP 100개 키워드를 기준으로 키워드별 업체 플레이스 ID 리스트 형식으로 산출

# def get_keyword_rank(keyword):
#     options = webdriver.ChromeOptions()
#     options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
#     options.add_argument('window-size=1380,900')
#     options.add_argument('headless=new')
#     options.add_argument("disable-gpu")
#     driver = webdriver.Chrome(options=options)
    
#     result_placeid = []

#     URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
#     driver.get(url=URL)

#     sleep(1)

#     try:
#         place_or_loc = driver.find_element(By.ID, 'place-app-root').find_element(By.XPATH, './div[last()]').get_attribute('id')
#         펼쳐서_더보기 = driver.find_element(By.CLASS_NAME, 'place_section.Owktn').find_element(By.XPATH, './div[last()]').get_attribute('class')

#         if place_or_loc == 'place-main-section-root':
#             if 펼쳐서_더보기 == 'rdX0R':
#                 펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R > div > a"
#             elif 펼쳐서_더보기 == 'rdX0R POx9H':
#                 펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R.POx9H > div > a"
#         elif place_or_loc == 'loc-main-section-root':
#             if 펼쳐서_더보기 == 'rdX0R':
#                 펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R > div > a"
#             elif 펼쳐서_더보기 == 'rdX0R POx9H':
#                 펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R.POx9H > div > a"
#         else:
#             driver.quit()
#             return '플레이스 조회와 관련이 없는 키워드 또는 업체'

#         펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
#             EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
#         )
#         펼쳐서_더보기_엘리먼트.click()

#         if place_or_loc == 'place-main-section-root':
#             더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
#         elif place_or_loc == 'loc-main-section-root':
#             더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"
        
#         WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()


#         ##### 위에 설명했던 내용들과 비슷한 기능 부분입니다.
#         전체_엘리먼트들 = []
#         
#         #최종 전체 가게 목록
#         result_store_list_fin = []
#         result_company_list = []
#         
#         # 몇 등인지 체크하는 변수
#         타겟_업체_인덱스 = -1

#         while True:
#             for _ in range(7):
#                 # 구글 크롬(selenium)에서 TAB 키를 누르는 액션, 7번 반복 실행
#                 ActionChains(driver).send_keys(u'\ue004').perform()
#             for _ in range(6):
#                 # 구글 크롬(selenium)에서 END 키를 누르는 액션, 6번 반복 실행
#                 ActionChains(driver).send_keys(u'\ue010').perform()
#                 sleep(0.3)
#             
#             엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
#             엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')
#             
#             if 엘리먼트_클래스2[0] != '':
#                 엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
#             else:
#                 엘리먼트들 = []
#                 driver.quit()
#                 return "잘못된 키워드"
#             
#             for 엘리먼트 in 엘리먼트들:
#                 if len(엘리먼트_클래스2) > 1:
#                     if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
#                         전체_엘리먼트들.append(엘리먼트)
#                         if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
#                             타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
#                 else:
#                     전체_엘리먼트들.append(엘리먼트)
#                     if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
#                         타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
#             
#             ## 100개 ~ 300개 업체 전체 리스트 추출 구문.
#             for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
#                 company_name = 엘리먼트.find_element(By.CLASS_NAME, "YwYLL").text
#                 result_store_list = f"{i}. {company_name}\n"
#                 result_company_list.append(company_name)
#                 result_store_list_fin.append(result_store_list)
#             
#             print(result_store_list_fin)
#             rank = 타겟_업체_인덱스 + 1
#             
#            
#             if 타겟_업체_인덱스 != -1:
#                 rank = 타겟_업체_인덱스 + 1
#                  ## 입력한 가게 상호 출력 구문
#                 store_name = 전체_엘리먼트들[타겟_업체_인덱스].find_element(By.CLASS_NAME, "YwYLL").text
#                 result = f"{rank}위"
#                 driver.quit()
#                 end_time = time()
#                 elapsed_time = end_time - start_time
#                 print(elapsed_time)
#                 return result, store_name, result_store_list_fin, result_company_list, keyword
#             
#             elif 타겟_업체_인덱스 == -1:
#                 result = '-'
#                  ## 입력한 가게 상호 출력 구문
#                 store_name = "키워드 가게 목록에 없는 상호명"
#                 driver.quit()
#                 return result, store_name, result_store_list_fin, result_company_list, keyword
#                 
#             if not 엘리먼트들:
#                 driver.quit()
#                 return f"-"
#             
#             bs 변수 -> 로딩된 전체 HTML 코드를 가져옵니다
#             bs = BeautifulSoup(driver.page_source, 'html.parser')
#             # 엘리먼트들 변수 -> 전체 가게 목록이 담긴 상위 코드 부분만 가져옵니다  
#             엘리먼트들 = bs.select("ul.eDFz9 li.VLTHu")
#             
#             # 가져온 전체 가게 목록에 대해 반복문을 돌립니다.
#             for 엘리먼트 in 엘리먼트들:
#                 # tivan 단어가 들어간 업체 주소는 네이버에서 유료 광고를 사용한 흔적이니까 제외해야 합니다.
#                 if "tivan" in 엘리먼트.find("a", class_="P7gyV")["href"] :
#                     continue
#                 # 네이버 유료 광고를 사용하지 않은 업체들 추려내는 부분입니다.
#                 else :
#                     전체_엘리먼트들.append(엘리먼트)
#                     if 업체_ID in 엘리먼트.find("a", class_="P7gyV")["href"]:
#                         타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
#             
#             ## 100개 ~ 300개 업체 전체 리스트 추출 구문.
#             for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
#                 company_name_element = 엘리먼트.find("span", class_="YwYLL")
#                 company_name = company_name_element.get_text(strip=True)
#                 
#                 result_store_list = f"{i}. {company_name}\n"
#                 result_company_list.append(company_name)
#                 result_store_list_fin.append(result_store_list)
#             
#             print(result_store_list_fin)
#             rank = 타겟_업체_인덱스 + 1
#             print(타겟_업체_인덱스)
#             
#             if 타겟_업체_인덱스 != -1:
#                 rank = 타겟_업체_인덱스 + 1
#                  ## 입력한 가게 상호 출력 구문
#                 store_name_fin = 전체_엘리먼트들[타겟_업체_인덱스].find("span", class_="YwYLL")
#                 # store_name_fin 만 가져와서 출력할 경우 불필요한 HTML 소스 <p>, <div> 등이 따라나옵니다.
#                 # 따라서 아래처럼 get_text 함수로 HTML 코드에서 필요한 글자 부분만 가져와야 합니다.
#                 store_name = store_name_fin.get_text(strip=True)
#                 result = f"{rank}위"
#                 driver.quit()
#                 end_time = time()
#                 elapsed_time = end_time - start_time
#                 print(elapsed_time)
#                 return result, store_name, result_store_list_fin, result_company_list, keyword
#             
#             
#             # 이건 설명 안해도 아시겠져????????????
#             # 검색한 업체가 목록에 없을 때 경우입니다.
#             elif 타겟_업체_인덱스 == -1:
#                 result = '-'
#                  ## 입력한 가게 상호 출력 구문
#                 store_name = "키워드 가게 목록에 없는 상호명"
#                 driver.quit()
#                 return result, store_name, result_store_list_fin, result_company_list, keyword
#                 
#             if not 엘리먼트들:
#                 driver.quit()
#                 return f"-"
#     
#         except Exception as e:
#             driver.quit()
#             print({e})
#             return f"오류 발생 : 관리자 문의"


#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result


#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result


#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#         result = "TimeoutException: Max retries reached"

#     return result

#     # 여러번 시도해도 결과값을 못 가져온 경우의 조건문.
#     if retry_count == max_retries and result is None:
#     except Exception as e:
#         driver.quit()
#         print({e})
#         return f"오류 발생 : 관리자 문의"

# # 1. keyword_result 테이블에서 상위 100개의 키워드를 추출하여 반환
# def get_top_keywords():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT DISTINCT keyword FROM keyword_result LIMIT 100
#     """)
#     top_keywords = [row[0] for row in cursor.fetchall()]
#     print(top_keywords)
#     conn.close()
#     return top_keywords

# # 3. place_id를 비교하고 keyword_result 테이블을 갱신하는 함수
# def update_keyword_result(cursor, place_id, keyword, result):
#     today_date = datetime.now().strftime("%Y-%m-%d")
#     result_rank = str(result) + '위'

#     # users 테이블에서 user_id 가져오기
#     cursor.execute("SELECT id FROM users WHERE place_id = ?", (place_id,))
#     user_id_row = cursor.fetchone()

#     if not user_id_row:
#         raise ValueError(f"User with place_id {place_id} not found.")
    
#     user_id = user_id_row[0]

#     # Check if the record exists for the given place_id and keyword
#     cursor.execute("""
#         SELECT search_date FROM keyword_result 
#         WHERE place_id = ? AND keyword = ? ORDER BY search_date DESC LIMIT 1
#     """, (place_id, keyword))
#     row = cursor.fetchone()

#     if row:
#         current_search_date = row[0]
        
#         # Only update if search_date is today, otherwise insert new
#         if str(current_search_date) == str(today_date):
#             cursor.execute("""
#                 UPDATE keyword_result
#                 SET result = ?
#                 WHERE place_id = ? AND keyword = ? AND search_date = ?
#             """, (result_rank, place_id, keyword, today_date))
#         else:
#             cursor.execute("""
#                 INSERT INTO keyword_result (user_id, place_id, keyword, search_date, result)
#                 VALUES (?, ?, ?, ?, ?)
#             """, (user_id, place_id, keyword, today_date, result_rank))
#     else:
#         cursor.execute("""
#             INSERT INTO keyword_result (user_id, place_id, keyword, search_date, result)
#             VALUES (?, ?, ?, ?, ?)
#         """, (user_id, place_id, keyword, today_date, result_rank))


# # 2. 각 키워드를 이용하여 get_keyword_rank 함수를 병렬로 호출하고 결과 처리
# def process_keyword(keyword):
#     conn = get_db_connection()
#     cursor = conn.cursor(prepared=True)
#     try:
#         # keyword_result 테이블에서 해당 키워드에 대한 중복 없는 place_id를 가져옴
#         cursor.execute("""
#             SELECT DISTINCT place_id FROM keyword_result WHERE keyword = ?
#         """, (keyword,))
#         existing_place_ids = set(row[0] for row in cursor.fetchall())
#     except Exception as e:
#         print(f"Error fetching place_ids from the database: {e}")
#         conn.close()
#         return

#     # get_keyword_rank 함수를 호출하여 각 키워드에 대해 place_ids 리스트 반환
#     place_ids = []
#     place_ids = get_keyword_rank(keyword)
#     print(f"Place IDs from get_keyword_rank for {keyword}: {len(place_ids)}")

#     # 반환된 place_ids와 기존의 place_ids를 비교하여 업데이트 수행
#     try:
#         for index, place_id in enumerate(place_ids):
#             if place_id in existing_place_ids:
#                 # 각 place_id에 대해 업데이트 수행
#                 update_keyword_result(cursor, place_id, keyword, index + 1)
                
#     except Exception as e:
#         print(f"Error during updating keyword result: {e}")
    
#     conn.commit()
#     conn.close()

# # 메인 함수: 상위 키워드를 병렬로 처리
# def process_keywords():
#     top_keywords = get_top_keywords()

#     # 병렬로 process_keyword 함수를 실행
#     with ThreadPoolExecutor(max_workers=10) as executor:
#         executor.map(process_keyword, top_keywords)

# 4. 스케줄러 설정 - 매일 오후 2시에 실행
#scheduler = BackgroundScheduler()
#scheduler.add_job(func=process_keywords, trigger='cron', hour=14)
#scheduler.add_job(id='update_top100_results_job', func=process_keywords, trigger='cron', minute="10", second='10', misfire_grace_time=60)
#scheduler.start()
###################################################### 24 08 28 TOP 100 키워드 실행 구문 테스트 끝 ###################################################### 


# 일회성으로 내 업체가 어떤 키워드에서 몇등에 위치해 있는지 체크하는 함수 기능부 입니다.
# public-check.html과 연관이 있어용
# 요청사항.txt에 적어둔 내용대로,
# 기존 크롤링해서 일일히 정보 가져오는 방법보다 BeautifulSoup4로 HTML 소스를 한번에 다 긁어오고,
# 긁어온 전체 소스에서 필요한 부분만 정리해서 결과값 전달하는 방식으로 개선된 부분이에요.
# 기존 방법 (10초) 에서 4초 정도 줄어드는 개선이 있긴 합니다만 복잡해요 ㅠ.

def get_naver_rank_public(keyword, 업체_ID):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from bs4 import BeautifulSoup
    from time import time, sleep

    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    options.add_argument('window-size=1380,900')
    # options.add_argument('headless=new')
    options.add_argument('--headless')
    options.add_argument("disable-gpu")
    options.add_argument('--no-sandbox')  
    options.add_argument('--disable-dev-shm-usage') 
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,       # 이미지 비활성화
        "profile.managed_default_content_settings.stylesheets": 2,  # CSS 비활성화
        "profile.managed_default_content_settings.javascript": 1    # JS 허용
    })

    driver = webdriver.Chrome(options=options)
    start_time = time()

    # 네이버 플레이스 검색 결과 페이지 (좌표는 임의 값)
    URL = f"https://m.place.naver.com/place/list?query={keyword}&x=126.9783882&y=37.5666103"
    driver.get(URL)
    print("퍼블릭")

    try:
        # 기본적으로 업체 리스트가 로딩될 때까지 대기
        # ul.eDFz9 li.VLTHu 구조로 업체 리스트를 담고 있음
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.eDFz9 li.VLTHu"))
        )

        # 결과를 담을 리스트
        전체_엘리먼트들 = []
        result_store_list_fin = []
        result_company_list = []
        타겟_업체_인덱스 = -1

        # 일정 횟수(예: 3회) 정도 스크롤을 반복하며 더 많은 업체를 로딩
        # 필요에 따라 횟수 조절 가능
        scroll_attempts = 3

        for _ in range(scroll_attempts):
            # 자바스크립트로 화면 최하단까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(0.5)  # 로딩 시간 약간 대기

            # HTML 다시 파싱
            bs = BeautifulSoup(driver.page_source, 'lxml')
            엘리먼트들 = bs.select("ul.eDFz9 li.VLTHu")

            # 업체 목록 파싱
            # a.P7gyV: 업체 링크 / span.YwYLL: 업체명 / tivan 포함 링크는 광고
            새_엘리먼트들 = []
            for 엘리먼트 in 엘리먼트들:
                a_tag = 엘리먼트.select_one("a.P7gyV")
                if not a_tag:
                    continue
                href = a_tag.get('href', '')
                # 광고 제외
                if "tivan" in href:
                    continue
                # 실제 업체 리스트에 추가
                새_엘리먼트들.append(엘리먼트)

            # 이미 추가된 업체를 포함한 전체 리스트를 업데이트
            # 중복 업체가 있을 수 있으므로 set 등을 고려할 수 있지만 여기서는 그냥 누적
            이전_길이 = len(전체_엘리먼트들)
            for 엘 in 새_엘리먼트들:
                if 엘 not in 전체_엘리먼트들:
                    전체_엘리먼트들.append(엘)

            # 타겟 업체 인덱스 갱신
            for idx, 엘 in enumerate(전체_엘리먼트들):
                a_tag = 엘.select_one("a.P7gyV")
                if a_tag and 업체_ID in a_tag.get('href', ''):
                    타겟_업체_인덱스 = idx
                    break

            # 타겟 업체를 찾았으면 더 이상 스크롤할 필요 없이 종료
            if 타겟_업체_인덱스 != -1:
                break

        # 모든 업체 리스트를 바탕으로 순위 목록 만들기
        for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
            name_tag = 엘리먼트.select_one("span.YwYLL")
            company_name = name_tag.get_text(strip=True) if name_tag else "Unknown"
            result_store_list = f"{i}. {company_name}\n"
            result_company_list.append(company_name)
            result_store_list_fin.append(result_store_list)

        # 결과 판단
        if 타겟_업체_인덱스 != -1:
            rank = 타겟_업체_인덱스 + 1
            store_name_tag = 전체_엘리먼트들[타겟_업체_인덱스].select_one("span.YwYLL")
            store_name = store_name_tag.get_text(strip=True) if store_name_tag else "Unknown"
            result = f"{rank}위"
        else:
            result = '-'
            store_name = "키워드 가게 목록에 없는 상호명"

        end_time = time()
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time:.2f}s")

        return result, store_name, result_store_list_fin, result_company_list, keyword

    except Exception as e:
        print(e)
        return "오류 발생 : 관리자 문의", "Unknown", [], [], keyword
    finally:
        driver.quit()




def get_naver_rank_public22(keyword, 업체_ID):
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    options.add_argument('window-size=1380,900')
    # options.add_argument('headless=new')
    options.add_argument("disable-gpu")
    options.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2,  # 이미지 비활성화
    "profile.managed_default_content_settings.stylesheets": 2,  # CSS 비활성화
    "profile.managed_default_content_settings.javascript": 1  # JS 허용 (기본값)
})
    driver = webdriver.Chrome(options=options)
    start_time = time()
    #URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
    
    # 네이버 플레이스에 다이렉트로 접속하는 URL입니다.
    # x 좌표, y 좌표를 없애버리면 정상적으로 접근이 안되서 아무거나 써넣은 좌표에요.
    URL = f"https://m.place.naver.com/place/list?query={keyword}&x=126.9783882&y=37.5666103"
    driver.get(url=URL)
    print("퍼블릭")
    #sleep(1)

    try:
        # place_or_loc = driver.find_element(By.ID, 'place-app-root').find_element(By.XPATH, './div[last()]').get_attribute('id')
        # 펼쳐서_더보기 = driver.find_element(By.CLASS_NAME, 'place_section.Owktn').find_element(By.XPATH, './div[last()]').get_attribute('class')

        # if place_or_loc == 'place-main-section-root':
        #     if 펼쳐서_더보기 == 'rdX0R':
        #         펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R > div > a"
        #     elif 펼쳐서_더보기 == 'rdX0R POx9H':
        #         펼쳐서_더보기_셀렉터 = "#place-main-section-root > div > div.rdX0R.POx9H > div > a"
        # elif place_or_loc == 'loc-main-section-root':
        #     if 펼쳐서_더보기 == 'rdX0R':
        #         펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R > div > a"
        #     elif 펼쳐서_더보기 == 'rdX0R POx9H':
        #         펼쳐서_더보기_셀렉터 = "#loc-main-section-root > div > div.rdX0R.POx9H > div > a"
        # else:
        #     driver.quit()
        #     return '플레이스 조회와 관련이 없는 키워드 또는 업체'

        # 펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
        # )
        # 펼쳐서_더보기_엘리먼트.click()

        # if place_or_loc == 'place-main-section-root':
        #     더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
        # elif place_or_loc == 'loc-main-section-root':
        #     더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"
        
        # WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()


        ##### 위에 설명했던 내용들과 비슷한 기능 부분입니다.
        전체_엘리먼트들 = []
        
        #최종 전체 가게 목록
        result_store_list_fin = []
        result_company_list = []
        
        # 몇 등인지 체크하는 변수
        타겟_업체_인덱스 = -1

        while True:
            for _ in range(7):
                # 구글 크롬(selenium)에서 TAB 키를 누르는 액션, 7번 반복 실행
                ActionChains(driver).send_keys(u'\ue004').perform()
            for _ in range(6):
                # 구글 크롬(selenium)에서 END 키를 누르는 액션, 6번 반복 실행
                ActionChains(driver).send_keys(u'\ue010').perform()
                sleep(0.3)
            
            # 엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
            # 엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')
            
            # if 엘리먼트_클래스2[0] != '':
            #     엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
            # else:
            #     엘리먼트들 = []
            #     driver.quit()
            #     return "잘못된 키워드"
            
            # for 엘리먼트 in 엘리먼트들:
            #     if len(엘리먼트_클래스2) > 1:
            #         if 엘리먼트_클래스2[1] not in 엘리먼트.get_attribute("class"):
            #             전체_엘리먼트들.append(엘리먼트)
            #             if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
            #                 타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
            #     else:
            #         전체_엘리먼트들.append(엘리먼트)
            #         if 업체_ID in 엘리먼트.find_element(By.TAG_NAME, "a").get_attribute("href"):
            #             타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
            
            # ## 100개 ~ 300개 업체 전체 리스트 추출 구문.
            # for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
            #     company_name = 엘리먼트.find_element(By.CLASS_NAME, "YwYLL").text
            #     result_store_list = f"{i}. {company_name}\n"
            #     result_company_list.append(company_name)
            #     result_store_list_fin.append(result_store_list)
            
            # print(result_store_list_fin)
            # rank = 타겟_업체_인덱스 + 1
            
           
            # if 타겟_업체_인덱스 != -1:
            #     rank = 타겟_업체_인덱스 + 1
            #      ## 입력한 가게 상호 출력 구문
            #     store_name = 전체_엘리먼트들[타겟_업체_인덱스].find_element(By.CLASS_NAME, "YwYLL").text
            #     result = f"{rank}위"
            #     driver.quit()
            #     end_time = time()
            #     elapsed_time = end_time - start_time
            #     print(elapsed_time)
            #     return result, store_name, result_store_list_fin, result_company_list, keyword
            
            # elif 타겟_업체_인덱스 == -1:
            #     result = '-'
            #      ## 입력한 가게 상호 출력 구문
            #     store_name = "키워드 가게 목록에 없는 상호명"
            #     driver.quit()
            #     return result, store_name, result_store_list_fin, result_company_list, keyword
                
            # if not 엘리먼트들:
            #     driver.quit()
            #     return f"-"
            
            # bs 변수 -> 로딩된 전체 HTML 코드를 가져옵니다
            bs = BeautifulSoup(driver.page_source, 'html.parser')
            # 엘리먼트들 변수 -> 전체 가게 목록이 담긴 상위 코드 부분만 가져옵니다  
            엘리먼트들 = bs.select("ul.eDFz9 li.VLTHu")
            
            # 가져온 전체 가게 목록에 대해 반복문을 돌립니다.
            for 엘리먼트 in 엘리먼트들:
                # tivan 단어가 들어간 업체 주소는 네이버에서 유료 광고를 사용한 흔적이니까 제외해야 합니다.
                if "tivan" in 엘리먼트.find("a", class_="P7gyV")["href"] :
                    continue
                # 네이버 유료 광고를 사용하지 않은 업체들 추려내는 부분입니다.
                else :
                    전체_엘리먼트들.append(엘리먼트)
                    if 업체_ID in 엘리먼트.find("a", class_="P7gyV")["href"]:
                        타겟_업체_인덱스 = len(전체_엘리먼트들) - 1
            
            ## 100개 ~ 300개 업체 전체 리스트 추출 구문.
            for i, 엘리먼트 in enumerate(전체_엘리먼트들, start=1):
                company_name_element = 엘리먼트.find("span", class_="YwYLL")
                company_name = company_name_element.get_text(strip=True)
                
                result_store_list = f"{i}. {company_name}\n"
                result_company_list.append(company_name)
                result_store_list_fin.append(result_store_list)
            
            print(result_store_list_fin)
            rank = 타겟_업체_인덱스 + 1
            print(타겟_업체_인덱스)
           
            if 타겟_업체_인덱스 != -1:
                rank = 타겟_업체_인덱스 + 1
                 ## 입력한 가게 상호 출력 구문
                store_name_fin = 전체_엘리먼트들[타겟_업체_인덱스].find("span", class_="YwYLL")
                # store_name_fin 만 가져와서 출력할 경우 불필요한 HTML 소스 <p>, <div> 등이 따라나옵니다.
                # 따라서 아래처럼 get_text 함수로 HTML 코드에서 필요한 글자 부분만 가져와야 합니다.
                store_name = store_name_fin.get_text(strip=True)
                result = f"{rank}위"
                driver.quit()
                end_time = time()
                elapsed_time = end_time - start_time
                print(elapsed_time)
                return result, store_name, result_store_list_fin, result_company_list, keyword
            
            
            # 이건 설명 안해도 아시겠져????????????
            # 검색한 업체가 목록에 없을 때 경우입니다.
            elif 타겟_업체_인덱스 == -1:
                result = '-'
                 ## 입력한 가게 상호 출력 구문
                store_name = "키워드 가게 목록에 없는 상호명"
                driver.quit()
                return result, store_name, result_store_list_fin, result_company_list, keyword
                
            if not 엘리먼트들:
                driver.quit()
                return f"-"
    
    except Exception as e:
        driver.quit()
        print({e})
        return f"오류 발생 : 관리자 문의"


##### 여기서부터는 파이썬 Flask 코드입니다.
##### 한번씩 살펴보시고 모르는 부분이 있으면 디코나 카톡으로 알려드릴게요.

@app.route('/')
def index():
    if 'id' in session:
        return redirect(url_for('Nplace-rank-check'))
    else:
        return redirect(url_for('login'))

# 메인 페이지 홈    
@app.route('/home')
def home():
    return render_template('home.html')

# 유저 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute('SELECT * FROM users WHERE id = %s AND password = %s', (username, password))
        account = cursor.fetchone()

        if account:
            session['user_id'] = account[1]
            session['place_id'] = account[4]
            session['username'] = account[3]
            return redirect(url_for('home'))
        else:
            error = 'Invalid Credentials. Please try again.'
            return render_template('login.html', error=error)
    return render_template('login.html')

# 유저 로그아웃
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('id', None)
    return redirect(url_for('home'))

# (유저 전용) 내 업체의 키워드 날짜별 랭킹
@app.route('/Nplace-rank-check', methods=['GET', 'POST'])
def Nplace_rank_check():
    if 'username' not in session:
        return redirect(url_for('login'))

    # 데이터베이스 연결 열기
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = session['user_id']
        cursor.execute('SELECT * FROM users WHERE id = %s', [user_id])
        user_info = cursor.fetchone()

        place_id = user_info[4]
        
        if user_info[5] is None: 
            user_info[5] = datetime(2020,1,1)

        vip_date = datetime.strptime(str(user_info[5]), "%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        today = datetime.strptime(str(today), "%Y-%m-%d")
        day_check = vip_date - today

        if day_check.days < 0:
            max_keywords = 3
            error = (
                "VIP 멤버쉽이 종료되어 3개의 키워드의 순위만 노출됩니다. "
                "연장 관련 문의는 아래 카카오톡 채널을 통해 문의해주세요."
            )
        else:
            max_keywords = 10

        keywords = []

        if request.method == 'POST':

            if 'add_keyword' in request.form:
                new_keyword = request.form['new_keyword']
                result_fin = '-'
                cursor.execute(
                    'SELECT COUNT(*) AS count FROM (SELECT keyword FROM keyword_result WHERE user_id = %s AND place_id = %s GROUP BY keyword) as keyword_count', 
                    (user_id, place_id)
                )
                keyword_count = cursor.fetchone()
                
                if keyword_count[0] < max_keywords:
                    cursor.execute(
                        'INSERT INTO keyword_result (user_id, place_id, keyword, search_date) VALUES (%s, %s, %s, %s)',
                        (user_id, place_id, new_keyword, datetime.now().strftime('%Y-%m-%d'))
                    )
                    conn.commit()
                    keywords.append({'keyword': new_keyword, 'result': result_fin})
                else:
                    error = f'Maximum of {max_keywords} keywords reached.'
                    return render_template('Nplace-rank-check.html', username=session['username'], user_info=user_info, keywords=keywords, max_keywords=max_keywords, error=error)
            
            elif 'search' in request.form:
                keyword_id = request.form['keyword_id']
                result_thread = ThreadWithReturnValue(target=get_naver_rank, args=(keyword_id, place_id))
                result_thread.start()
                result_fin = result_thread.join()
                keywords.append({'keyword': keyword_id, 'result': result_fin})
            
            elif 'delete_keyword' in request.form:
                keyword_id = request.form['keyword_id']
                cursor.execute('DELETE FROM keyword_result WHERE user_id = %s AND place_id = %s AND keyword = %s',
                               (user_id, place_id, keyword_id))
                conn.commit()

        if user_info:
            cursor.execute('SELECT keyword, search_date, result FROM keyword_result WHERE user_id = %s AND place_id = %s ORDER BY search_date DESC', 
                           (user_id, place_id))
            keyword_results = cursor.fetchall()
            keywords_dict = {}
            for result in keyword_results:
                if result[0] not in keywords_dict:
                    keywords_dict[result[0]] = []
                keywords_dict[result[0]].append({'search_date': result[1], 'result': result[2]})

            keywords = [{'keyword': key, 'results': value} for key, value in keywords_dict.items()]

            if day_check.days < 0:
                keywords = keywords[:3]

        return render_template('Nplace-rank-check.html', username=session['username'], user_info=user_info, keywords=keywords, max_keywords=max_keywords, error=error if day_check.days < 0 else None)
    
    finally:
        # 데이터베이스 연결 닫기
        cursor.close()
        conn.close()


## 유저가 아니어도 사용 가능, 단 IP당 24시간마다 3회 조회 가능
@app.route('/public-check', methods=['GET', 'POST'])
def search():
    error = None
    result = None

    # Get client IP address
    client_ip = request.remote_addr

    # Get IP-related search data from session
    ip_search_data = session.get('ip_search_data', {})

    if request.method == 'POST':
        now = datetime.now()

        # If this IP has a record in session
        if client_ip in ip_search_data:
            ip_info = ip_search_data[client_ip]
            search_times = ip_info.get('search_times', [])
            last_search_time = search_times[-1] if search_times else None

            # Ensure all times are offset-naive by converting to naive datetime
            search_times = [time.replace(tzinfo=None) for time in search_times]

            # Filter out searches older than 24 hours
            search_times = [time for time in search_times if now - time < timedelta(hours=24)]
            ip_info['search_times'] = search_times

            if len(search_times) > 100:
                error = 'IP당 24시간마다 최대 3회 조회가 가능합니다.'
            else:
                keyword = request.form['keyword']
                place_id = request.form['place_id']
                result = get_naver_rank_public(keyword, place_id)
                ip_info['search_times'].append(now)
                session['ip_search_data'] = ip_search_data
        else:
            # First search from this IP within 24 hours
            keyword = request.form['keyword']
            place_id = request.form['place_id']
            result = get_naver_rank_public(keyword, place_id)
            ip_search_data[client_ip] = {'search_times': [now]}
            session['ip_search_data'] = ip_search_data

    return render_template('public-check.html', result=result, error=error)

keyword_last_run = {}

# public-check 실행 시 접근하는 페이지, 3회 제한 횟수 검사 및 결과 갱신
@app.route('/run-now', methods=['POST'])
def run_now():
    main_conn = get_db_connection()
    cursor = main_conn.cursor()
    
    keyword_id = request.json.get('keyword_id')
    place_id = request.json.get('place_id')
    user_id = session['user_id']
    
    last_run = keyword_last_run.get(keyword_id)
    current_time = datetime.now()

    if last_run and (current_time - last_run) < timedelta(hours=8):
        time_left = timedelta(hours=8) - (current_time - last_run)
        return jsonify(success=False, message=f'이 키워드는 {time_left.seconds // 3600}시간 {time_left.seconds % 3600 // 60}분 후에 다시 실행할 수 있습니다.')

    try:
        result = get_naver_rank(keyword_id, place_id)
        keyword_last_run[keyword_id] = current_time
        cursor.execute(
            'INSERT INTO keyword_result (user_id, place_id, keyword, search_date, result) VALUES (%s, %s, %s, %s, %s)',
            (user_id, place_id, keyword_id, current_time.strftime('%Y-%m-%d'), result)
        )
        print('try 커밋')
        main_conn.commit()
        return jsonify(success=True, result=result)
    except Exception as e:
        cursor.execute(
            'UPDATE keyword_result SET result = %s WHERE user_id = %s AND place_id = %s AND keyword = %s AND search_date = %s',
            (result, user_id, place_id, keyword_id, current_time.strftime('%Y-%m-%d'))
        )
        print('except 커밋')
        main_conn.commit()
        return jsonify(success=True, result=result)  # Update success response here
    finally:
        cursor.close()
        main_conn.close()

if __name__ == '__main__':
    app.run(port=8080,debug=True,use_reloader=False, host='0.0.0.0', threaded=True)
    # flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080})
    # flask_thread.start()

    # # 스케줄러는 백그라운드에서 실행되도록 설정했으므로, 별도 처리 없이 정상 동작
    # flask_thread.join()  # Flask 웹 애플리케이션이 종료되지 않도록 유지
    # flask_thread.join()  # Flask 웹 애플리케이션이 종료되지 않도록 유지
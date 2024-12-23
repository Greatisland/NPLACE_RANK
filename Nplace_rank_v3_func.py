
from threading import Thread
from selenium import webdriver
import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep, strftime, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import random

from requests.exceptions import HTTPError

import mysql.connector
from flask_caching import Cache

from apscheduler.schedulers.background import BackgroundScheduler

conn = mysql.connector.connect(
        # host='192.168.0.26',
        host='localhost',
        user='test',
        password='tpals0430',
        database='nplace_rank_db'
)

def get_db_connection():
    # 새로운 데이터베이스 커넥션을 생성합니다.
    return mysql.connector.connect(
        # host='192.168.0.26',
        host='localhost',
        user='test',
        password='tpals0430',
        database='nplace_rank_db'
    )

############## APScheduler 함수 실행 부분


scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Seoul')

scheduler.start()

# 플레이스 URL로 플레이스ID 추출하는 함수
def split_url(url):
    first_split = url.split('/')
    last_split = first_split[-1].split('?')
    
    return last_split[0]


cursor = conn.cursor()

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

    while retry_count < max_retries:
        sleep(random.uniform(0.5, 2))
        driver = None
        try:
            if driver is None:
                driver = webdriver.Chrome(options=options)

            URL = f"https://m.search.naver.com/search.naver?where=m&sm=top_sly.hst&fbm=0&acr=1&ie=utf8&query={keyword}"
            driver.get(url=URL)
            
            sleep(1)

            # sleep 제거 또는 최소화
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'place-app-root')))

            # 기존 로직 실행
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
                return '플레이스 조회와 관련이 없는 키워드 또는 업체'

            펼쳐서_더보기_엘리먼트 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 펼쳐서_더보기_셀렉터))
            )
            펼쳐서_더보기_엘리먼트.click()

            if place_or_loc == 'place-main-section-root':
                더보기_셀렉터 = "#place-main-section-root > div > div.M7vfr > a"
            elif place_or_loc == 'loc-main-section-root':
                더보기_셀렉터 = "#loc-main-section-root > div > div.M7vfr > a"

            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 더보기_셀렉터))).click()

            전체_엘리먼트들 = []
            타겟_업체_인덱스 = -1

            while True:
                for _ in range(9):  # 키 입력 횟수 최소화
                    ActionChains(driver).send_keys(u'\ue004').perform()
                for _ in range(6):  # 키 입력 횟수 최소화
                    ActionChains(driver).send_keys(u'\ue010').perform()
                    sleep(0.4)

                엘리먼트_클래스 = driver.find_element(By.CLASS_NAME, 'eDFz9').find_element(By.XPATH, './/li').get_attribute('class')
                엘리먼트_클래스2 = 엘리먼트_클래스.split(' ')

                if 엘리먼트_클래스2[0] != '':
                    엘리먼트들 = driver.find_elements(By.CLASS_NAME, 엘리먼트_클래스2[0])
                else:
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
                
                if 타겟_업체_인덱스 == -1:
                    result = '-'
                    driver.quit()
                    return result
            
                if 타겟_업체_인덱스 != -1:
                    rank = 타겟_업체_인덱스 + 1
                    result = f"{rank}위"
                    break

                if not 엘리먼트들:
                    result = '-'
                    break

            break  # 성공 시 루프 탈출

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

        finally:
            if driver:
                driver.quit()

    if retry_count == max_retries and result is None:
        result = "TimeoutException: Max retries reached"

    return result

### 키워드 30개씩 분할하여 순차적으로 실행하고, 처리 시간을 기록하는 코드

def update_keyword_results_in_batches(batch, batch_number):
    start_time = time()  # 시작 시간 기록

    with ThreadPoolExecutor(max_workers=10) as executor:
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
scheduler.add_job(id='update_keyword_results_job', func=update_keyword_results, trigger='cron', minute="29", second='10', misfire_grace_time=60)

scheduler.start()

###################################################### 네이버 키워드별 전체 순위 검색 코드 끝끝 ###################################################### 


###################################################### 오류 키워드들 전체 순위 검색 재실행 코드 ###################################################### 

def start_retry_failed_keywords_job():
    print("Starting retry_failed_keywords_job after update_keyword_results completion.")

    # 8시간 동안 10분 간격으로 retry_failed_keywords_job 실행
    end_time = datetime.now() + timedelta(hours=8)
    scheduler.add_job(retry_failed_keywords, id='retry_failed_keywords_job', trigger='interval', minutes=10, start_date=datetime.now(), end_date=end_time)

### 실패한 키워드를 재시도하는 함수

def retry_failed_keywords():
    today = datetime.now().strftime('%Y-%m-%d')

    # '오류'가 발생한 레코드들 가져오기
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
scheduler = BackgroundScheduler()

# update_keyword_results 작업을 매일 정해진 시간에 실행하도록 설정
scheduler.add_job(id='update_keyword_results_job', func=update_keyword_results, trigger='cron', minute="02", second='10', misfire_grace_time=60)

scheduler.start()

# 실행 중단을 방지하기 위해 계속 실행
try:
    while scheduler.running:
        sleep(2)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
###################################################### 오류 키워드들 전체 순위 검색 재실행 코드 ###################################################### 
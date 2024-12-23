from time import time, sleep
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup

# WebDriver 설정
options = webdriver.ChromeOptions()
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
options.add_argument('window-size=1380,900')
options.add_argument('headless=new')
options.add_argument("disable-gpu")
driver = webdriver.Chrome(options=options)

# URL 설정
url = "https://m.place.naver.com/place/list?query=경성대%20맛집&x=126.9783880&y=37.5666107"
driver.get(url)

# 타이머 시작
start_time = time()

# 스크롤 동작 실행
for _ in range(7):
    ActionChains(driver).send_keys(u'\ue004').perform()  # 아래 화살표
for _ in range(6):
    ActionChains(driver).send_keys(u'\ue010').perform()  # 페이지 아래
    sleep(0.3)

# 페이지 소스를 BeautifulSoup로 파싱
bs = BeautifulSoup(driver.page_source, 'html.parser')

li_elements = bs.select("ul.eDFz9 li.VLTHu")
i = 1

store_list = []

for li in li_elements:
    # 'span' 태그의 텍스트를 추출
    # li 요소 내에 특정 클래스의 a 태그가 있는지 확인
    gubv_link = li.find("a", class_="P7gyV")["href"]
    print(gubv_link)
    
    # 특정 클래스의 a 태그가 있으면 다음 li로 넘어가기
    if gubv_link:
        continue
        
    span_ywyl_text = li.find("span", class_="YwYLL")
    span_yzbg_text = li.find("span", class_="YzBgS")

    # 각각의 span에서 텍스트만 추출, 존재하지 않으면 None 반환
    store_name = span_ywyl_text.get_text(strip=True)
    store_category = span_yzbg_text.get_text(strip=True)

    # 검색된 전체 업체 결과 출력
    store_name_fin = f"{i}. {store_name}"
    store_list.append(store_name_fin)
    
    # 입력한 업체의 키워드, 업체명, 순위
    store_category
    
    i = i+1

driver.quit()
end_time = time()
elapsed_time = end_time - start_time

# 결과 출력
print("Total elapsed time:", elapsed_time, "seconds")

# test_api_response.py

import json
from datetime import date

from api.endpoints.crawler.court_crawler import CourtNameCrawler

crawler = CourtNameCrawler()

# 2008-01-01 서울 남자 데이터 조회
data = crawler.fetch_data_by_date(
    target_date=date(2008, 1, 2), city_code="41", gender_code="2"
)

if data and "data" in data:
    print(f"총 {len(data['data'])}개 이름")
    print("\n전체 데이터:")
    for item in data["data"]:
        print(f"  {item['순위']}위: {item['이름']} ({item['건수']}건)")

    # "기타" 있는지 확인
    etc_items = [item for item in data["data"] if "기타" in item["이름"]]
    if etc_items:
        print(f"\n✅ '기타' 발견: {etc_items}")
    else:
        print(f"\n❌ '기타' 없음")
else:
    print("데이터 없음")

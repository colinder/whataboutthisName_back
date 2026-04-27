# crawler/court_crawler.py

import json
import time
from datetime import date
from typing import Dict, Optional

import requests


class CourtNameCrawler:
    """대법원 출생신고 통계 크롤러"""

    def __init__(self):
        self.base_url = "https://stfamily.scourt.go.kr/ds/report/query.do"
        self.session = requests.Session()

        # ✅ 재시도 설정
        self.max_retries = 3  # 최대 3번 재시도
        self.retry_delay = 5  # 5초 대기
        self.failed_items: list[dict] = []  # ← 추가
        # 24개 시도 코드 (현재 17개 + 구 명칭 7개)
        self.all_city_codes = [
            "11",
            "26",
            "27",
            "28",
            "29",
            "30",
            "31",
            "36",
            "41",
            "51",
            "43",
            "44",
            "52",
            "46",
            "47",
            "48",
            "50",
            "21",
            "22",
            "23",
            "24",
            "25",
            "42",
            "45",
        ]

    def fetch_data_by_date(
        self, target_date: date, city_code: str, gender_code: str
    ) -> Optional[Dict]:
        """
        일자별 시도별 데이터 조회

        Args:
            target_date: 조회 날짜
            city_code: 시도 코드 (예: "11")
            gender_code: 성별 코드 ("1"=남자, "2"=여자)

        Returns:
            {"mapid": "...", "data": [...]} 또는 None
        """
        date_str = target_date.strftime("%Y%m%d")

        data = {
            "pid": "1811",
            "uid": "999999",
            "dsid": "1261",
            "dstype": "DS",
            "mapid": "7cbe6546-89a8-4378-b7d6-16f4bcd93d36",
            "sqlid": "1811-0",
            "params": self._build_params_daily(date_str, city_code, gender_code),
        }

        result = self._request(data)

        # ← 추가: 실패 시 기록
        if result is None:
            self.failed_items.append({
                "date": str(target_date),
                "city_code": city_code,
                "gender_code": gender_code,
                "type": "daily",
            })

        return result


    def fetch_data_by_month(
        self,
        year: int,
        month: int,
        gender_code: str,
    ) -> Optional[Dict]:
        """
        월별 전체 데이터 조회 (모든 시도 포함)

        Args:
            year: 연도
            month: 월
            gender_code: 성별 코드 ("0"=전체, "1"=남자, "2"=여자)

        Returns:
            {"mapid": "...", "data": [...]} 또는 None
        """
        year_month = f"{year}{month:02d}"

        data = {
            "pid": "1811",
            "uid": "999999",
            "dsid": "1261",
            "dstype": "DS",
            "mapid": "7cbe6546-89a8-4378-b7d6-16f4bcd93d36",
            "sqlid": "1811-0",
            "params": self._build_params_monthly(year_month, gender_code),
        }

        result = self._request(data)

        # ← 추가: 실패 시 기록
        if result is None:
            self.failed_items.append({
                "date": f"{year}-{month:02d}",
                "city_code": "전체",
                "gender_code": gender_code,
                "type": "monthly",
            })

        return result

    def _build_params_daily(
        self, date_str: str, city_code: str, gender_code: str
    ) -> str:
        """일자별 조회 params 생성"""
        params = {
            "@MultiCandType": {"value": ["DT"], "type": "STRING", "defaultValue": ""},
            "@MultiCandStDt": {
                "value": [date_str],
                "type": "STRING",
                "defaultValue": "",
            },
            "@MultiCandEdDt": {
                "value": [date_str],
                "type": "STRING",
                "defaultValue": "",
            },
            "@SidoCd": {
                "value": [city_code],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "C.SIDO_CD",
            },
            "@CggCd": {
                "value": ["_EMPTY_VALUE_"],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "D.CGG_CD",
            },
            "@UmdCd": {
                "value": ["_EMPTY_VALUE_"],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "E.UMD_CD",
            },
            "@GenderCd": {
                "value": [gender_code],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "F.GENDER_CD",
            },
        }

        return json.dumps(params)

    def _build_params_monthly(
        self,
        year_month: str,
        gender_code: str,
    ) -> str:
        """월별 전체 조회 params 생성 (24개 시도 모두 포함)"""

        gender_value = ["_EMPTY_VALUE_"] if gender_code == "0" else [gender_code]

        params = {
            "@MultiCandType": {"value": ["YM"], "type": "STRING", "defaultValue": ""},
            "@MultiCandStDt": {
                "value": [year_month],
                "type": "STRING",
                "defaultValue": "",
            },
            "@MultiCandEdDt": {
                "value": [year_month],
                "type": "STRING",
                "defaultValue": "",
            },
            "@SidoCd": {
                "value": self.all_city_codes,  # ✅ 24개 모두
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "C.SIDO_CD",
            },
            "@CggCd": {
                "value": ["_EMPTY_VALUE_"],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "D.CGG_CD",
            },
            "@UmdCd": {
                "value": ["_EMPTY_VALUE_"],
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "E.UMD_CD",
            },
            "@GenderCd": {
                "value": gender_value,
                "type": "STRING",
                "defaultValue": "[All]",
                "whereClause": "F.GENDER_CD",
            },
        }

        return json.dumps(params)

    def _request(self, data: dict) -> Optional[Dict]:
        """API 요청 실행"""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://stfamily.scourt.go.kr/ds/report/view.do",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        # ✅ 재시도 루프
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    self.base_url, data=data, headers=headers, timeout=30
                )
                response.raise_for_status()

                # Rate limiting (서버 부하 방지)
                time.sleep(1.5)

                return response.json()

            except requests.exceptions.HTTPError as e:
                # HTTP 에러 (502, 503 등)
                if attempt < self.max_retries - 1:
                    print(
                        f"    ⚠️ HTTP 에러 ({e.response.status_code}), {self.retry_delay}초 후 재시도 ({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"    ❌ API 요청 실패 (최대 재시도 초과): {e}")
                    return None

            except requests.exceptions.Timeout:
                # 타임아웃
                if attempt < self.max_retries - 1:
                    print(
                        f"    ⚠️ 타임아웃, {self.retry_delay}초 후 재시도 ({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print("    ❌ API 요청 실패 (타임아웃)")
                    return None

            except Exception as e:
                # 기타 에러
                if attempt < self.max_retries - 1:
                    print(
                        f"    ⚠️ 에러 발생: {e}, {self.retry_delay}초 후 재시도 ({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"    ❌ API 요청 실패: {e}")
                    return None

        return None

    def print_failed_summary(self):
        """모든 크롤링 완료 후 호출"""
        if not self.failed_items:
            print("\n✅ 모든 항목 크롤링 성공")
            return

        print(f"\n❌ 실패 항목 {len(self.failed_items)}개 (재크롤링 필요):")
        print("=" * 60)
        for item in self.failed_items:
            print(
                f"  날짜: {item['date']:<12} "
                f"| 지역코드: {item['city_code']:<6} "
                f"| 성별코드: {item['gender_code']} "
                f"| 타입: {item['type']}"
            )
        print("=" * 60)

        # 재크롤링용 날짜만 따로 출력 (API target_date 형식)
        failed_dates = sorted(set(item["date"] for item in self.failed_items))
        print(f"\n📋 재크롤링 target_date:\n{failed_dates}")
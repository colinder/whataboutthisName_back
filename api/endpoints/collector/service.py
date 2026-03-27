import asyncio
import platform
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from models.Enums import GenderEnum

SAVE_DIR = Path("data")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class CollectorService:
    @staticmethod
    def _set_gender(driver, id: str, gender_name: str):
        driver.find_element(By.ID, "param_GenderCd").click()

        result = driver.execute_script(
            """
            var key = Object.keys(window).find(k => k.startsWith('param_GenderCd_'));
            var obj = window[key];

            obj.SetSelectText(arguments[0]);

            return {
                success: true,
                text: obj.GetSelectText(),
                code: obj.GetSelectCode()
            };
        """,
            gender_name,
        )

        print("성별 선택 결과:", result)
        time.sleep(0.5)
        return

    @staticmethod
    def _set_city(driver, id: str, city_name: str):
        driver.find_element(By.ID, "param_SidoCd").click()

        result = driver.execute_script(
            """
            var key = Object.keys(window).find(k => k.startsWith('param_SidoCd_'));
            var obj = window[key];
            var data = obj.viewport.options.data;

            var target = data.find(d => d.dataFull === arguments[0]);
            if (!target) return { success: false, message: '항목을 찾을 수 없음' };

            // SetSelectText로 직접 선택
            obj.SetSelectText(target.text);

            return { 
                success: true,
                text: obj.GetSelectText(),
                code: obj.GetSelectCode()
            };
        """,
            city_name,
        )

        print("선택 결과:", result)
        time.sleep(0.5)

    @staticmethod
    def _set_date(driver, cal_img_id: str, year: int, month: int, day: int):
        # 캘린더 아이콘 클릭
        driver.find_element(By.ID, cal_img_id).click()
        time.sleep(0.5)

        # JS로 년/월/일 설정 후 닫기
        driver.execute_script(f"""
            yearSelected = {year};
            monthSelected = {month - 1};
            dateSelected = {day};
            constructCalendar();
            closeCalendar();
        """)
        time.sleep(0.3)

    @staticmethod
    def _get_driver() -> webdriver.Chrome:
        if platform.system() == "Windows":
            # Windows: 엣지 사용
            options = EdgeOptions()
            # options.add_argument("--headless")  # 개발 시 주석
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            service = EdgeService(
                executable_path=str(BASE_DIR / "drivers" / "msedgedriver.exe")
            )
            return webdriver.Edge(service=service, options=options)
        else:
            # Linux: 크롬 사용 (headless 필수)
            options = ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            service = ChromeService(executable_path="/usr/bin/chromedriver")
            return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _sync_crawl(
        start_date_str: str,
        end_date_str: str,
        city: str,
        gender: GenderEnum,
    ):
        url = "https://stfamily.scourt.go.kr/st/StFrrStatcsView.do?pgmId=090000000025"
        driver = CollectorService._get_driver()
        wait = WebDriverWait(driver, 10)

        start = datetime.strptime(start_date_str, "%Y%m%d")
        end = datetime.strptime(end_date_str, "%Y%m%d")

        try:
            driver.get(url)

            # 페이지 완전 로드 대기
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))

            # iframe 전환
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            driver.switch_to.frame(iframes[0])

            # 캘린더 아이콘이 나타날 때까지 대기
            wait.until(
                EC.presence_of_element_located(
                    (By.ID, "param_MultiCandType_stdt_elem_cal")
                )
            )

            # 시작일 설정
            CollectorService._set_date(
                driver,
                cal_img_id="param_MultiCandType_stdt_elem_cal",
                year=start.year,
                month=start.month,
                day=start.day,
            )
            print(
                "시작일:",
                driver.find_element(
                    By.ID, "param_MultiCandType_stdt_elem"
                ).get_attribute("value"),
            )

            # 종료일 설정 (ID 확인 필요)
            CollectorService._set_date(
                driver,
                cal_img_id="param_MultiCandType_eddt_elem_cal",
                year=end.year,
                month=end.month,
                day=end.day,
            )
            print(
                "종료일:",
                driver.find_element(
                    By.ID, "param_MultiCandType_eddt_elem"
                ).get_attribute("value"),
            )

            # 시도 선택
            CollectorService._set_city(
                driver,
                id="param_SidoCd_1774502844314_selectedContainer",
                city_name="서울특별시",
            )

            # 성별 선택
            CollectorService._set_gender(
                driver,
                id="param_SidoCd_1774502844314_selectedContainer",
                gender_name="남자",
            )

            # 검색 클릭
            driver.find_element(By.ID, "btn_query").click()
            # GMNoDataRow가 사라질 때까지 대기
            wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".GMNoDataRow"))
            )

            # GMBodyMid가 보일 때까지 대기
            wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".GMBodyMid"))
            )

            time.sleep(1)
            # 데이터 추출
            rows = driver.find_elements(By.CSS_SELECTOR, ".GMDataRow")

            # 데이터 존재 여부 확인 (기타 행 기준)
            has_data = any(
                row.find_elements(By.CSS_SELECTOR, "td[class*='GMCell']")[
                    1
                ].text.strip()
                == "기타"
                for row in rows
                if len(row.find_elements(By.CSS_SELECTOR, "td[class*='GMCell']")) >= 4
            )

            data = []
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td[class*='GMCell']")
                if len(cells) >= 4:
                    rank = cells[0].text.strip()
                    name = cells[1].text.strip()

                    # 합계, 기타 행 제외
                    if rank == "합계" or name == "기타":
                        continue

                    data.append(
                        {
                            "name": re.sub(r"\(.*?\)", "", name).strip(),
                            "count": cells[3].text.strip(),
                        }
                    )

            result = {
                "data": data,
                "check": {
                    "is_success": has_data,  # 정상 수집 여부
                    "has_result": len(data) > 0,  # 실제 데이터 존재 여부
                },
            }

            print(result)

        except Exception as e:
            print(f"에러 발생: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
        finally:
            driver.quit()

    @staticmethod
    async def crawl(
        start_date: date,
        end_date: date,
        city: str,
        gender: GenderEnum = GenderEnum.ALL,
    ):
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        # 셀레니움은 동기 라이브러리라 run_in_executor로 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: CollectorService._sync_crawl(
                start_date_str, end_date_str, city, gender
            ),
        )

        return {"message": "ok"}

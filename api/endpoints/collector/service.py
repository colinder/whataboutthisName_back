import asyncio
import platform
import re
import time
from datetime import date, datetime
from pathlib import Path

from models.Enums import GenderEnum
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

SAVE_DIR = Path("data")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class CollectorService:
    @staticmethod
    def _dismiss_alert(driver):
        """30일 초과 팝업이 뜨면 확인 클릭"""
        try:
            confirm_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "apprise-btn-confirm"))
            )
            confirm_btn.click()
            time.sleep(0.3)
        except:
            pass

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
        element = driver.find_element(By.ID, cal_img_id)
        driver.execute_script("arguments[0].click();", element)

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
            options = EdgeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)
        else:
            options = ChromeOptions()
            # options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _sync_crawl(
        dates: list[date],
        city: str,
        gender: GenderEnum,
    ):
        url = "https://stfamily.scourt.go.kr/st/StFrrStatcsView.do?pgmId=090000000025"
        driver = CollectorService._get_driver()
        wait = WebDriverWait(driver, 10)

        try:
            driver.get(url)

            # 1. iframe 로드 대기 후 전환
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)

            # 2. iframe 내부 요소 대기
            wait.until(EC.visibility_of_element_located((By.ID, "btn_query")))

            dates.sort(reverse=True)
            for target_date in dates:
                # 시작일 설정
                CollectorService._set_date(
                    driver,
                    cal_img_id="param_MultiCandType_stdt_elem_cal",
                    year=target_date.year,
                    month=target_date.month,
                    day=target_date.day,
                )
                CollectorService._dismiss_alert(driver)
                # print(
                #     "시작일:",
                #     driver.find_element(
                #         By.ID, "param_MultiCandType_stdt_elem"
                #     ).get_attribute("value"),
                # )

                time.sleep(3)

                # 종료일 설정
                CollectorService._set_date(
                    driver,
                    cal_img_id="param_MultiCandType_eddt_elem_cal",
                    year=target_date.year,
                    month=target_date.month,
                    day=target_date.day,
                )
                CollectorService._dismiss_alert(driver)
                # print(
                #     "종료일:",
                #     driver.find_element(
                #         By.ID, "param_MultiCandType_eddt_elem"
                #     ).get_attribute("value"),
                # )

                # 시도 선택
                CollectorService._set_city(
                    driver,
                    id="param_SidoCd_1774502844314_selectedContainer",
                    city_name=city,
                )

                # 성별 선택
                CollectorService._set_gender(
                    driver,
                    id="param_SidoCd_1774502844314_selectedContainer",
                    gender_name=gender.value
                    if isinstance(gender, GenderEnum)
                    else gender,
                )

                # 검색 클릭
                driver.find_element(By.ID, "btn_query").click()

                # 결과 대기: 데이터 또는 "조회된 데이터가 없습니다"
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: (
                            d.find_elements(By.CSS_SELECTOR, ".GMDataRow")
                            or "조회된 데이터가 없습니다" in d.page_source
                        )
                    )
                except:
                    pass

                time.sleep(1)

                # 데이터 없는 경우
                if "조회된 데이터가 없습니다" in driver.page_source:
                    print(f"{target_date} - 조회 결과 없음 (정상)")
                    result = {
                        "data": [],
                        "check": {
                            "is_success": True,
                            "has_result": False,
                        },
                    }
                    print(result)
                    continue

                # 데이터 추출
                rows = driver.find_elements(By.CSS_SELECTOR, ".GMDataRow")

                data = []
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td[class*='GMCell']")
                    if len(cells) >= 4:
                        rank = cells[0].text.strip()
                        name = cells[1].text.strip()

                        # 합계, 빈 행 제외 (기타는 수집)
                        if rank == "합계" or not name:
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
                        "is_success": True,
                        "has_result": len(data) > 0,
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
        dates: list[date],
        city: str,
        gender: GenderEnum,
    ):

        # 셀레니움은 동기 라이브러리라 run_in_executor로 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: CollectorService._sync_crawl(dates, city, gender),
        )

        return {"message": "ok"}

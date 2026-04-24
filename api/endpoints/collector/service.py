import asyncio
import platform
import re
import time
from datetime import date
from itertools import product

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import select
from webdriver_manager.chrome import ChromeDriverManager

from database import SessionLocal
from models.enums import CityEnum, GenderEnum
from models.name import Name
from models.record import Record

from .db_service import save_crawl_results, save_empty_crawl_log


class CollectorService:
    @staticmethod
    def _dismiss_alert(driver):
        """팝업 + 오버레이 닫기"""
        try:
            confirm_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "apprise-btn-confirm"))
            )
            confirm_btn.click()
            time.sleep(0.3)
        except:
            pass

        # 오버레이가 남아있으면 강제 제거
        try:
            driver.execute_script("""
                var overlay = document.querySelector('.apprise-overlay');
                if (overlay) overlay.style.display = 'none';
                var apprise = document.querySelector('.apprise');
                if (apprise) apprise.style.display = 'none';
            """)
        except:
            pass

    @staticmethod
    def _save_to_db(results: list[dict]):
        db = SessionLocal()
        try:
            # 이름 캐시 (DB 조회 최소화)
            name_cache = {}

            for item in results:
                name_str = item["name"]
                count = int(item["count"]) if item["count"] else 0

                # 이름 조회/생성 (캐시 활용)
                if name_str not in name_cache:
                    stmt = select(Name).where(Name.name == name_str)
                    name_obj = db.execute(stmt).scalar_one_or_none()

                    if not name_obj:
                        name_obj = Name(name=name_str, count=0)
                        db.add(name_obj)
                        db.flush()

                    name_cache[name_str] = name_obj

                name_obj = name_cache[name_str]
                name_obj.count += count

                # records 중복 체크 후 저장
                stmt = select(Record).where(
                    Record.name_id == name_obj.id,
                    Record.city == item["city"],
                    Record.record_date == item["record_date"],
                    Record.gender == item["gender"],
                )
                existing = db.execute(stmt).scalar_one_or_none()

                if not existing:
                    db.add(
                        Record(
                            name_id=name_obj.id,
                            city=item["city"],
                            record_date=item["record_date"],
                            gender=item["gender"],
                            count=count,
                        )
                    )
                else:
                    existing.count = count

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"DB 저장 실패: {e}")
        finally:
            db.close()

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
        options = ChromeOptions()
        # options.add_argument("--headless=new")
        options.add_argument("--window-size=1000,900")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        if platform.system() == "Linux":
            # Docker 환경
            options.binary_location = "/usr/bin/chromium"
            service = ChromeService(executable_path="/usr/bin/chromedriver")
        else:
            # 로컬 개발 (Mac/Windows)
            service = ChromeService(ChromeDriverManager().install())

        return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _reset_and_set_city(driver, city_name: str):
        """이전 시도 선택 초기화 후 새로 선택"""
        if city_name == "전체":
            # 모든 도시 체크
            driver.execute_script("""
                var key = Object.keys(window).find(k => k.startsWith('param_SidoCd_'));
                var obj = window[key];
                var data = obj.viewport.options.data;
                
                for (var i = 0; i < data.length; i++) {
                    obj.SetItemCheck(i, true);
                }
            """)
            time.sleep(0.5)
        else:
            # 전체 해제 후 단일 도시 선택
            driver.execute_script("""
                var key = Object.keys(window).find(k => k.startsWith('param_SidoCd_'));
                var obj = window[key];
                var data = obj.viewport.options.data;
                
                for (var i = 0; i < data.length; i++) {
                    obj.SetItemCheck(i, false);
                }
            """)
            time.sleep(0.3)

            CollectorService._set_city(
                driver,
                id="param_SidoCd_1774502844314_selectedContainer",
                city_name=city_name,
            )

    @staticmethod
    def _reset_and_set_gender(driver, gender_name: str):
        """이전 성별 선택 초기화 후 새로 선택"""
        driver.execute_script("""
            var key = Object.keys(window).find(k => k.startsWith('param_GenderCd_'));
            var obj = window[key];
            obj.SetSelectText('');
        """)
        time.sleep(0.3)

        CollectorService._set_gender(
            driver,
            id="param_GenderCd",
            gender_name=gender_name,
        )

    @staticmethod
    def _sync_crawl(
        dates: list[date],
        cities: list[CityEnum],
        genders: list[GenderEnum],
    ):
        # 시간 종합
        from datetime import datetime

        start_time = datetime.now()
        print(f"\n>>> 크롤링 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        url = "https://stfamily.scourt.go.kr/st/StFrrStatcsView.do?pgmId=090000000025"
        driver = CollectorService._get_driver()
        wait = WebDriverWait(driver, 10)

        all_results = []

        try:
            driver.get(url)

            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
            wait.until(EC.visibility_of_element_located((By.ID, "btn_query")))

            dates.sort(reverse=True)

            prev_city = None
            prev_gender = None

            for city, gender in product(cities, genders):
                print(f"\n=== {city.value} / {gender.value} 수집 시작 ===")

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
                    time.sleep(0.3)

                    # 종료일 설정
                    CollectorService._set_date(
                        driver,
                        cal_img_id="param_MultiCandType_eddt_elem_cal",
                        year=target_date.year,
                        month=target_date.month,
                        day=target_date.day,
                    )
                    CollectorService._dismiss_alert(driver)

                    # 도시가 바뀔 때만 재설정
                    if city != prev_city:
                        CollectorService._reset_and_set_city(driver, city.value)
                        prev_city = city

                    # 성별이 바뀔 때만 재설정
                    if gender != prev_gender:
                        CollectorService._reset_and_set_gender(driver, gender.value)
                        # 전체 선택 시 팝업 처리
                        if gender.value == "전체":
                            CollectorService._dismiss_alert(driver)
                        prev_gender = gender

                    # 검색 클릭
                    driver.find_element(By.ID, "btn_query").click()

                    # 결과 대기
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: (
                                d.find_elements(By.CSS_SELECTOR, ".GMDataRow")
                                or "조회된 데이터가 없습니다" in d.page_source
                            )
                        )
                    except:
                        pass

                    time.sleep(0.5)

                    # 데이터 없는 경우
                    if "조회된 데이터가 없습니다" in driver.page_source:
                        print(f"  {target_date} - 조회 결과 없음 (정상)")
                        save_empty_crawl_log(target_date, city.value, gender.value)
                        continue

                    # 그리드 데이터 직접 추출
                    grid_data = driver.execute_script("""
                        var grid = Grids[0];
                        if (!grid) return null;
                        
                        var result = [];
                        var rows = grid.Rows;
                        
                        for (var key in rows) {
                            if (key === 'Header' || key === 'SumRow') continue;
                            var row = rows[key];
                            if (!row || !row.C2) continue;
                            
                            var name = row.C2;
                            var count = row.C4;
                            
                            if (name && name !== '합계') {
                                result.push({
                                    rank: row.C1 || '',
                                    name: name,
                                    count: String(count || '0')
                                });
                            }
                        }
                        
                        return {total: result.length, data: result};
                    """)

                    # 그리드 방식 실패 시 DOM 파싱으로 폴백
                    if not grid_data or not grid_data.get("data"):
                        rows = driver.find_elements(By.CSS_SELECTOR, ".GMDataRow")
                        data = []
                        for row in rows:
                            cells = row.find_elements(
                                By.CSS_SELECTOR, "td[class*='GMCell']"
                            )
                            if len(cells) >= 4:
                                rank = cells[0].text.strip()
                                name = cells[1].text.strip()
                                if rank == "합계" or not name:
                                    continue
                                data.append(
                                    {
                                        "name": re.sub(r"\(.*?\)", "", name).strip(),
                                        "count": cells[3].text.strip(),
                                    }
                                )
                    else:
                        data = []
                        for item in grid_data["data"]:
                            name = item["name"].strip()
                            if not name:
                                continue
                            data.append(
                                {
                                    "name": re.sub(r"\(.*?\)", "", name).strip(),
                                    "count": item["count"].strip()
                                    if item["count"]
                                    else "0",
                                }
                            )

                    # all_results에 추가
                    for item in data:
                        all_results.append(
                            {
                                "name": item["name"],
                                "count": item["count"],
                                "city": city.value,
                                "gender": gender.value,
                                "record_date": target_date,
                            }
                        )

                    total = sum(int(item["count"]) for item in data if item["count"])
                    print(f"  {target_date} - {len(data)}개 이름, 총 {total}명 수집")

        except Exception as e:
            print(f"에러 발생: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
        finally:
            driver.quit()

        # 진행시간 출력
        end_time = datetime.now()
        elapsed = end_time - start_time
        minutes = elapsed.total_seconds() / 60
        print(f"\n>>> 크롤링 종료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f">>> 소요 시간: {int(minutes)}분 {int(elapsed.total_seconds() % 60)}초")

        # 전체 수집 완료 후 한 번에 저장
        if all_results:
            save_crawl_results(all_results)
            print(f"\n=== 총 {len(all_results)}건 DB 저장 완료 ===")

    @staticmethod
    async def crawl(
        dates: list[date],
        cities: list[CityEnum] | None = None,
        genders: list[GenderEnum] | None = None,
    ):
        if cities is None:
            # cities = [city for city in CityEnum if "구)" not in city.value]
            cities = list(CityEnum)
        if genders is None:
            genders = list(GenderEnum)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: CollectorService._sync_crawl(dates, cities, genders),
        )

        return {
            "message": f"{len(cities)}개 도시 x {len(genders)}개 성별 x {len(dates)}일 수집 완료"
        }

    @staticmethod
    def run_crawl(
        dates: list[date],
        cities: list[CityEnum] | None = None,
        genders: list[GenderEnum] | None = None,
    ):
        """BackgroundTask용 동기 메서드"""
        if cities is None:
            cities = list(CityEnum)
        if genders is None:
            genders = list(GenderEnum)

        CollectorService._sync_crawl(dates, cities, genders)

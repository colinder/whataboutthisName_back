# ruff: noqa: F401
import enum


class GenderEnum(str, enum.Enum):
    ALL = "전체"
    MALE = "남자"
    FEMALE = "여자"


class CityEnum(str, enum.Enum):
    ALL = "전체"

    # 특별시/광역시/특별자치시
    SEOUL = "서울특별시"
    BUSAN = "부산광역시"
    DAEGU = "대구광역시"
    INCHEON = "인천광역시"
    GWANGJU = "광주광역시"
    DAEJEON = "대전광역시"
    ULSAN = "울산광역시"
    SEJONG = "세종특별자치시"

    # 도
    GYEONGGI = "경기도"
    CHUNGBUK = "충청북도"
    CHUNGNAM = "충청남도"
    JEONNAM = "전라남도"
    GYEONGBUK = "경상북도"
    GYEONGNAM = "경상남도"
    JEJU = "제주특별자치도"
    GANGWON = "강원특별자치도"
    JEONBUK = "전북특별자치도"

    # 구 명칭 (폐지된 행정구역)
    BUSAN_OLD = "부산직할시(구)"
    DAEGU_OLD = "대구직할시(구)"
    INCHEON_OLD = "인천직할시(구)"
    GWANGJU_OLD = "광주직할시(구)"
    DAEJEON_OLD = "대전직할시(구)"
    GANGWON_OLD = "강원도(구)"
    JEONBUK_OLD = "전라북도(구)"


# 시도 코드 매핑 (24개)
CITY_CODE_MAP = {
    # 현재 행정구역 (17개)
    CityEnum.SEOUL: "11",
    CityEnum.BUSAN: "26",
    CityEnum.DAEGU: "27",
    CityEnum.INCHEON: "28",
    CityEnum.GWANGJU: "29",
    CityEnum.DAEJEON: "30",
    CityEnum.ULSAN: "31",
    CityEnum.SEJONG: "36",
    CityEnum.GYEONGGI: "41",
    CityEnum.GANGWON: "51",
    CityEnum.CHUNGBUK: "43",
    CityEnum.CHUNGNAM: "44",
    CityEnum.JEONBUK: "52",
    CityEnum.JEONNAM: "46",
    CityEnum.GYEONGBUK: "47",
    CityEnum.GYEONGNAM: "48",
    CityEnum.JEJU: "50",
    # 구 명칭 (7개)
    CityEnum.BUSAN_OLD: "21",
    CityEnum.DAEGU_OLD: "22",
    CityEnum.INCHEON_OLD: "23",
    CityEnum.GWANGJU_OLD: "24",
    CityEnum.DAEJEON_OLD: "25",
    CityEnum.GANGWON_OLD: "42",
    CityEnum.JEONBUK_OLD: "45",
}


# 전체 시도 코드 리스트 (24개)
ALL_CITY_CODES = [
    # 현재 행정구역 (17개)
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
    # 구 명칭 (7개) - 절대 제외 금지!
    "21",
    "22",
    "23",
    "24",
    "25",
    "42",
    "45",
]


def get_all_city_codes():
    """전체 시도 코드 (24개) - 절대 수정 금지"""
    return ALL_CITY_CODES


def get_current_city_codes():
    """현재 행정구역 코드만 (17개)"""
    return [
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
    ]


def get_old_city_codes():
    """구 명칭 코드만 (7개)"""
    return ["21", "22", "23", "24", "25", "42", "45"]


def get_city_name_by_code(code: str) -> str:
    """코드로 시도명 찾기"""
    for city_enum, city_code in CITY_CODE_MAP.items():
        if city_code == code:
            return city_enum.value
    return None


def get_city_code_by_name(name: str) -> str:
    """시도명으로 코드 찾기"""
    for city_enum, city_code in CITY_CODE_MAP.items():
        if city_enum.value == name:
            return city_code
    return None

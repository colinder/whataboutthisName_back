# ruff: noqa: F401
import enum


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


class GenderEnum(str, enum.Enum):
    ALL = "전체"
    MALE = "남자"
    FEMALE = "여자"

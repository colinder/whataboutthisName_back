-- ============================================================
-- Neon 테이블 생성 SQL (v2 - 크롤링 이력 관리)
-- 기존 테이블을 삭제하고 새로 생성합니다
-- Neon 대시보드 → SQL Editor에서 실행하세요
-- ============================================================

-- 기존 테이블 삭제 (순서 중요: FK 참조 순서 역순)
DROP TABLE IF EXISTS records CASCADE;
DROP TABLE IF EXISTS crawl_logs CASCADE;
DROP TABLE IF EXISTS names CASCADE;

-- ============================================================
-- 1. crawl_logs 테이블 (크롤링 이력)
-- ============================================================
CREATE TABLE crawl_logs (
    id          SERIAL PRIMARY KEY,
    record_date DATE NOT NULL,
    city        VARCHAR(255) NOT NULL,
    gender      VARCHAR(255) NOT NULL,
    is_success  BOOLEAN NOT NULL DEFAULT FALSE,
    has_result  BOOLEAN NOT NULL DEFAULT FALSE,
    total_count INTEGER NOT NULL DEFAULT 0,
    crawled_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE crawl_logs IS '크롤링 수집 이력';
COMMENT ON COLUMN crawl_logs.record_date IS '수집 대상 날짜';
COMMENT ON COLUMN crawl_logs.city IS '도시';
COMMENT ON COLUMN crawl_logs.gender IS '성별';
COMMENT ON COLUMN crawl_logs.is_success IS '수집 성공 여부';
COMMENT ON COLUMN crawl_logs.has_result IS '데이터 존재 여부';
COMMENT ON COLUMN crawl_logs.total_count IS '수집 건수';
COMMENT ON COLUMN crawl_logs.crawled_at IS '수집 실행 시각';

-- 중복 수집 방지 (같은 날짜+도시+성별은 1건만)
CREATE UNIQUE INDEX idx_crawl_logs_unique
    ON crawl_logs(record_date, city, gender);

CREATE INDEX idx_crawl_logs_date ON crawl_logs(record_date);
CREATE INDEX idx_crawl_logs_city ON crawl_logs(city);
CREATE INDEX idx_crawl_logs_gender ON crawl_logs(gender);

-- ============================================================
-- 2. names 테이블 (이름 마스터)
-- ============================================================
CREATE TABLE names (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE names IS '아기 이름 마스터';
COMMENT ON COLUMN names.name IS '이름';

CREATE INDEX idx_names_name ON names(name);

-- ============================================================
-- 3. records 테이블 (수집 데이터)
-- ============================================================
CREATE TABLE records (
    id            SERIAL PRIMARY KEY,
    crawl_log_id  INTEGER NOT NULL REFERENCES crawl_logs(id) ON DELETE CASCADE,
    name_id       INTEGER NOT NULL REFERENCES names(id) ON DELETE CASCADE,
    count         INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE records IS '수집된 출생신고 데이터';
COMMENT ON COLUMN records.crawl_log_id IS '크롤링 로그 FK';
COMMENT ON COLUMN records.name_id IS '이름 FK';
COMMENT ON COLUMN records.count IS '출생 건수';

CREATE INDEX idx_records_crawl_log_id ON records(crawl_log_id);
CREATE INDEX idx_records_name_id ON records(name_id);

-- 같은 크롤링 로그에서 같은 이름은 1건만
CREATE UNIQUE INDEX idx_records_unique
    ON records(crawl_log_id, name_id);

-- ============================================================
-- 4. updated_at 자동 갱신 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER names_updated_at
    BEFORE UPDATE ON names
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

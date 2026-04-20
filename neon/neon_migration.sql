-- ============================================================
-- Neon 테이블 생성 SQL (Auto Increment ID)
-- Neon 대시보드 → SQL Editor에서 실행하세요
-- ============================================================

-- ============================================================
-- 1. names 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS names (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE names IS '출생신고 아기 이름 목록';
COMMENT ON COLUMN names.name IS '이름 항목';
COMMENT ON COLUMN names.count IS '건수';

-- ============================================================
-- 2. records 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS records (
    id          SERIAL PRIMARY KEY,
    name_id     INTEGER NOT NULL REFERENCES names(id) ON DELETE CASCADE,
    city        VARCHAR(255) NOT NULL,
    record_date DATE NOT NULL,
    gender      VARCHAR(255) NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

COMMENT ON TABLE records IS '일별/도시별/성별 출생신고 기록';
COMMENT ON COLUMN records.name_id IS '이름 FK';
COMMENT ON COLUMN records.city IS '도시';
COMMENT ON COLUMN records.record_date IS '기록일자';
COMMENT ON COLUMN records.gender IS '성별';
COMMENT ON COLUMN records.count IS '성별 전체 건수';

-- ============================================================
-- 3. 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_records_name_id ON records(name_id);
CREATE INDEX IF NOT EXISTS idx_records_date ON records(record_date);
CREATE INDEX IF NOT EXISTS idx_records_city ON records(city);
CREATE INDEX IF NOT EXISTS idx_records_gender ON records(gender);

CREATE INDEX IF NOT EXISTS idx_records_date_gender_city
    ON records(record_date, gender, city);

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

CREATE TRIGGER records_updated_at
    BEFORE UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

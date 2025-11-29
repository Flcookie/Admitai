-- 创建申请管理表
-- 在Supabase中执行此SQL脚本

CREATE TABLE IF NOT EXISTS applications (
    id BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(255) NOT NULL,
    program_id INTEGER NOT NULL,
    program_name VARCHAR(500) NOT NULL,
    university VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'planned',
    priority INTEGER NOT NULL DEFAULT 0,
    application_deadline DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_applications_student_id ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_program_id ON applications(program_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- 添加注释
COMMENT ON TABLE applications IS '学生申请管理表';
COMMENT ON COLUMN applications.student_id IS '学生ID（可以用用户名或邮箱）';
COMMENT ON COLUMN applications.program_id IS '项目ID（关联programs表）';
COMMENT ON COLUMN applications.status IS '状态: planned(计划中), in_progress(申请中), submitted(已提交), accepted(已录取), rejected(已拒绝), waitlisted(候补)';
COMMENT ON COLUMN applications.priority IS '优先级: 0=低, 1=中, 2=高';


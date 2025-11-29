# 申请管理模块数据库设置

在使用申请管理功能之前，需要在 Supabase 中创建 `applications` 表。

## 创建数据库表

1. 登录你的 Supabase 项目
2. 进入 SQL Editor
3. 复制并执行 `create_applications_table.sql` 中的 SQL 脚本

或者直接在 SQL Editor 中执行：

```sql
-- 创建申请管理表
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
```

## 表结构说明

- `id`: 主键，自增
- `student_id`: 学生ID（使用localStorage自动生成）
- `program_id`: 项目ID（关联programs表）
- `program_name`: 项目名称（冗余存储，便于查询）
- `university`: 学校名称（冗余存储）
- `status`: 申请状态（planned/in_progress/submitted/accepted/rejected/waitlisted）
- `priority`: 优先级（0=低, 1=中, 2=高）
- `application_deadline`: 申请截止日期
- `notes`: 备注信息
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 验证

执行完成后，可以：
1. 在 Supabase 的 Table Editor 中查看 `applications` 表
2. 尝试在前端添加一个项目到申请列表
3. 查看申请管理页面是否能正常显示

如果遇到错误，请检查：
- Supabase 连接配置是否正确
- 表是否成功创建
- 后端服务是否正常运行


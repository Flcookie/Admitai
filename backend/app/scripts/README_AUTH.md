# 用户认证模块设置说明

## 数据库表创建

在 Supabase 中执行以下 SQL 脚本来创建用户表：

1. 登录 Supabase 项目
2. 进入 SQL Editor
3. 执行 `backend/app/scripts/create_users_table.sql` 中的 SQL 脚本

或者直接执行：

```sql
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

## 功能说明

### 后端 API

- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/verify` - 验证token（简化版本）
- `GET /auth/me` - 获取当前用户信息（需要完善）

### 前端功能

- 登录/注册模态框
- 认证状态管理（localStorage）
- 路由保护（dashboard页面需要登录）

## 注意事项

1. **密码安全**：当前使用简单的 SHA256 哈希，生产环境应使用 bcrypt 等更安全的算法
2. **Token管理**：当前token存储在localStorage，生产环境应使用httpOnly cookie
3. **Token验证**：当前token验证逻辑简化，生产环境应使用JWT并实现完整的验证流程

## 使用示例

### 注册用户
```typescript
import { register } from "@/lib/api";

await register({
  email: "user@example.com",
  password: "password123",
  name: "用户名"
});
```

### 登录
```typescript
import { login } from "@/lib/api";

const data = await login({
  email: "user@example.com",
  password: "password123"
});

// 登录成功后，token和用户信息会自动保存到localStorage
```

### 检查登录状态
```typescript
import { isAuthenticated, getCurrentUser } from "@/lib/api";

if (isAuthenticated()) {
  const user = getCurrentUser();
  console.log("当前用户:", user);
}
```

### 退出登录
```typescript
import { logout } from "@/lib/api";

logout();
```


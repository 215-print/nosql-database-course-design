from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import redis_client

SESSION_PREFIX = "auth:session:"  # 登录会话在 Redis 中的键前缀
SESSION_EXPIRE_SECONDS = 43200  # 登录会话有效期为 12 小时

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer Token",
)  # 使用标准 Bearer Token 认证


# 创建并保存登录会话，返回访问令牌。
def create_session(subject_id: str, role: str) -> str:
    import secrets

    token = secrets.token_urlsafe(32)  # 生成随机登录 Token
    session_key = f"{SESSION_PREFIX}{token}"  # 构造会话 Redis 键

    with redis_client.pipeline(transaction=True) as pipe:
        pipe.hset(session_key, mapping={"subject_id": subject_id, "role": role})
        pipe.expire(session_key, SESSION_EXPIRE_SECONDS)
        pipe.execute()

    return token  # 返回 Token


def revoke_user_sessions(user_id: str) -> None:
    """修改密码或拉黑用户后，使该用户已有的登录会话失效。"""
    for key in redis_client.scan_iter(f"{SESSION_PREFIX}*"):
        session = redis_client.hgetall(key)
        if session.get("subject_id") == user_id and session.get("role") == "用户":
            redis_client.delete(key)


# 从 Bearer Token 中解析当前登录身份。
def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")

    token = credentials.credentials  # 提取 Token
    session_key = f"{SESSION_PREFIX}{token}"  # 构造会话 Key
    session = redis_client.hgetall(session_key)  # 查询登录会话

    if not session:
        raise HTTPException(
            status_code=401,
            detail="登录已失效，请重新登录",
        )

    return session  # 返回当前登录身份


# 校验当前请求是否具有管理员身份。
def require_admin(
    principal: dict = Depends(get_principal),
) -> dict:
    if principal.get("role") != "管理员":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return principal  # 返回管理员身份


# 校验当前请求是否为有效且未被拉黑的用户。
def require_user(
    principal: dict = Depends(get_principal),
) -> dict:
    if principal.get("role") != "用户":
        raise HTTPException(status_code=403, detail="需要用户权限")

    from app.services import get_user_raw
    user = get_user_raw(principal.get('subject_id', ''))
    if not user:
        raise HTTPException(status_code=401, detail="用户账号不存在，请重新登录")
    if user.get("blacklist") == "true":
        raise HTTPException(status_code=403, detail="该用户已被管理员拉黑")

    return principal  # 返回普通用户身份

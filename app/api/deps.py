"""FastAPI 依赖注入：OpenID 头部 + JWT 鉴权。"""
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Header, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logging import logger

# 密码哈希上下文（虽然演示主要用 openid 登录，但保留以支持真实密码登录）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT access token。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_openid(x_openid: Optional[str] = Header(None)) -> str:
    """从请求头提取用户标识。未提供时使用默认值。"""
    if not x_openid:
        logger.warning("请求缺少 X-OpenID 头，使用默认用户 default_user")
        return "default_user"
    return x_openid


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_openid: Optional[str] = Header(None),
) -> str:
    """
    获取当前认证用户。
    优先使用 Bearer JWT；若无 JWT，则回退到 X-OpenID 头部（兼容旧客户端与 Streamlit 演示）。
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            openid: str = payload.get("sub")
            if openid is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的凭据",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return openid
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或过期的凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 回退：X-OpenID 头部（兼容 Streamlit 前端与内部调用）
    if x_openid:
        return x_openid

    logger.warning("请求缺少鉴权信息，使用默认用户 default_user")
    return "default_user"


def get_current_active_user(current_user: str = Depends(get_current_user)) -> str:
    """获取当前激活用户（演示版全部视为激活）。"""
    return current_user

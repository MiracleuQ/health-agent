"""认证接口：基于 OpenID 的简易登录（生产环境应接入真实用户系统）。"""
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta
from app.api.deps import create_access_token, settings, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    openid: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    openid: str


@router.post("/login", summary="简易登录（基于 OpenID）", response_model=LoginResponse)
def login(req: LoginRequest):
    """根据 openid 生成 JWT。生产环境应校验密码/手机验证码等。"""
    access_token = create_access_token(data={"sub": req.openid})
    return {"access_token": access_token, "openid": req.openid}


@router.get("/me", summary="查询当前用户")
def get_me(current_user: str = Depends(get_current_user)):
    return {"openid": current_user, "authenticated": True}

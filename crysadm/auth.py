# API 权限管理
__author__ = 'powergx'
from util import hash_password
import json

from flask import Response, request, session, redirect, url_for
from functools import wraps
from crysadm import r_session

# 将当前用户添加到在线用户列表当中
def __handshake():
    user = session.get('user_info')
    username = user.get('username')
    if username is None or not username:
        username = ''
    key = 'user:%s:is_online' % username
    # SETEX(KEY_NAME TIMEOUT VALUE)
    r_session.setex(key, '1', 120)
    r_session.sadd('global:online.users', username)

# 需要管理员权限
def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_info') is None:
            return redirect(url_for('login'))
        if session.get('user_info').get('is_admin') is None or not session.get('user_info').get('is_admin'):
            return redirect(url_for('dashboard'))
        __handshake()
        return f(*args, **kwargs)

    return decorated

# 需要用户权限
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_info') is None:
            return redirect(url_for('login'))
        __handshake()
        return f(*args, **kwargs)

    return decorated
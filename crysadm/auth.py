# API 权限管理
__author__ = 'powergx'
from util import hash_password
import json

from flask import Response, request, session, redirect, url_for
from functools import wraps
from crysadm import r_session

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

def __handshake():
    user = session.get('user_info')
    username = user.get('username') if user.get('username') is not None else ''
    key = 'user:%s:is_online' % username
    r_session.setex(key, '1', 120)
    r_session.sadd('global:online.users', username)
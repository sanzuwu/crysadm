__author__ = 'powergx'
import hashlib
from flask import session

# 生成hash密码
def hash_password(pwd):
    """
        :param pwd: input password
        :return: return hash md5 password
        """
    from crysadm import app

    return hashlib.md5(str("%s%s" % (app.config.get("PASSWORD_PREFIX"), pwd)).encode('utf-8')).hexdigest()

# 生成 md5 16位小写密码
def md5(s):
    import hashlib

    return hashlib.md5(s.encode('utf-8')).hexdigest().lower()

# 提取错误信息
def get_message():
    err_msg = None
    if session.get('error_message') is not None:
        err_msg = session.get('error_message')
        session['error_message'] = None
    return err_msg

# 设置信息
def set_message(message,type='error'):
    if type == 'error':
        session['error_message'] = message
    elif type == 'info':
        session['info_message'] = message
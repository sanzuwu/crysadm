__author__ = 'powergx'
from flask import request, Response, render_template, session, url_for, redirect
from crysadm import app, r_session
from auth import requires_admin, requires_auth
import json
from util import hash_password
import uuid
import re
from datetime import datetime

@app.route('/user/login', methods=['POST'])
def user_login():
    username = request.values.get('username')
    password = request.values.get('password')

    hashed_password = hash_password(password)

    user_info = r_session.get('%s:%s' % ('user', username))
    if user_info is None:
        session['error_message'] = '用户不存在'
        return redirect(url_for('login'))

    user = json.loads(user_info.decode('utf-8'))

    if user.get('password') != hashed_password:
        session['error_message'] = '密码错误'
        return redirect(url_for('login'))

    if not user.get('active'):
        session['error_message'] = '您的账号已被禁用.'
        return redirect(url_for('login'))

    if user.get('log_as_body') is not None:
        if len(user.get('log_as_body')) > 0:
            r_session.set('%s:%s' % ('record', username), json.dumps(dict(diary=user.get('log_as_body')))) # 创建新通道,转移原本日记
            user['log_as_body'] = []

    user['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 记录登陆时间
    r_session.set('%s:%s' % ('user', username), json.dumps(user)) # 修正数据

    if r_session.get('%s:%s' % ('record', username)) is None:
        r_session.set('%s:%s' % ('record', username), json.dumps(dict(diary=[]))) # 创建缺失的日记

    session['user_info'] = user

    return redirect(url_for('dashboard'))


@app.route('/login')
def login():
    if session.get('user_info') is not None:
        return redirect(url_for('dashboard'))

    err_msg = None
    if session.get('error_message') is not None:
        err_msg = session.get('error_message')
        session['error_message'] = None

    return render_template('login.html', err_msg=err_msg)


@app.route('/invitations')
def public_invitation():
    inv_codes = r_session.smembers('public_invitation_codes')

    return render_template('public_invitation.html', inv_codes=inv_codes)



@app.route('/user/logout')
@requires_auth
def logout():
    if session.get('admin_user_info') is not None:
        session['user_info'] = session.get('admin_user_info')
        del session['admin_user_info']
        return redirect(url_for('admin_user'))

    session.clear()
    return redirect(url_for('login'))


@app.route('/log')
@requires_auth
def user_log():
    log_as = []
    user = session.get('user_info')

    record_key = '%s:%s' % ('record', user.get('username'))
    record_info = json.loads(r_session.get(record_key).decode('utf-8'))

    for row in record_info.get('diary'):
        if (datetime.now() - datetime.strptime(row.get('time'), '%Y-%m-%d %H:%M:%S')).days < 7:
            log_as.append(row)
    log_as.reverse()

    return render_template('log.html', log_user=log_as)


@app.route('/log/delete')
@requires_auth
def user_log_delete():
    user = session.get('user_info')

    record_key = '%s:%s' % ('record', user.get('username'))
    record_info = json.loads(r_session.get(record_key).decode('utf-8'))

    record_info['diary'] = []

    r_session.set(record_key, json.dumps(record_info))

    return redirect(url_for('user_log'))


@app.route('/user/profile')
@requires_auth
def user_profile():
    user = session.get('user_info')

    user_key = '%s:%s' % ('user', user.get('username'))
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))

    err_msg = None
    if session.get('error_message') is not None:
        err_msg = session.get('error_message')
        session['error_message'] = None
    action = None
    if session.get('action') is not None:
        action = session.get('action')
        session['action'] = None

    return render_template('profile.html', user_info=user_info, err_msg=err_msg, action=action)


@app.route('/user/change_info', methods=['POST'])
@requires_auth
def user_change_info():
    user = session.get('user_info')
    email = request.values.get('email')
    session['action'] = 'info'
    r = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

    if re.match(r, email) is None:
        session['error_message'] = '邮箱地址格式不正确.'

        return redirect(url_for('user_profile'))

    user_key = '%s:%s' % ('user', user.get('username'))
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))

    user_info['email'] = email
    r_session.set(user_key, json.dumps(user_info))

    return redirect(url_for('user_profile'))


@app.route('/user/change_property/<field>/<value>', methods=['POST'])
@requires_auth
def user_change_property(field, value):
    user = session.get('user_info')
    user_key = '%s:%s' % ('user', user.get('username'))

    user_info = json.loads(r_session.get(user_key).decode('utf-8'))

    if field == 'auto_column':
        user_info['auto_column'] = True if value == '1' else False
    if field == 'auto_collect':
        user_info['auto_collect'] = True if value == '1' else False
    if field == 'auto_drawcash':
        user_info['auto_drawcash'] = True if value == '1' else False
    if field == 'auto_giftbox':
        user_info['auto_giftbox'] = True if value == '1' else False
    if field == 'auto_searcht':
        user_info['auto_searcht'] = True if value == '1' else False
    if field == 'auto_revenge':
        user_info['auto_revenge'] = True if value == '1' else False
    if field == 'auto_getaward':
        user_info['auto_getaward'] = True if value == '1' else False

    r_session.set(user_key, json.dumps(user_info))

    return redirect(url_for('user_profile'))


@app.route('/user/change_password', methods=['POST'])
@requires_auth
def user_change_password():
    user = session.get('user_info')
    o_password = request.values.get('old_password')
    n_password = request.values.get('new_password')
    n2_password = request.values.get('new2_password')
    session['action'] = 'password'

    if n_password != n2_password:
        session['error_message'] = '新密码输入不一致.'
        return redirect(url_for('user_profile'))

    if len(n_password) < 8:
        session['error_message'] = '密码必须8位及以上.'
        return redirect(url_for('user_profile'))

    user_key = '%s:%s' % ('user', user.get('username'))
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))

    hashed_password = hash_password(o_password)

    if user_info.get('password') != hashed_password:
        session['error_message'] = '原密码错误'
        return redirect(url_for('user_profile'))

    user_info['password'] = hash_password(n_password)
    r_session.set(user_key, json.dumps(user_info))

    return redirect(url_for('user_profile'))


@app.route('/register')
def register():
    if session.get('user_info') is not None:
        return redirect(url_for('dashboard'))

    err_msg = None
    if session.get('error_message') is not None:
        err_msg = session.get('error_message')
        session['error_message'] = None

    info_msg = None
    if session.get('info_message') is not None:
        info_msg = session.get('info_message')
        session['info_message'] = None

    invitation_code = ''
    if request.values.get('inv_code') is not None and len(request.values.get('inv_code')) > 0 :
        invitation_code = request.values.get('inv_code')
        if not r_session.sismember('invitation_codes', invitation_code) and \
                not r_session.sismember('public_invitation_codes', invitation_code):
            session['error_message'] = '无效的邀请码。'

    return render_template('register.html', err_msg=err_msg, info_msg=info_msg, invitation_code=invitation_code)


@app.route('/user/register', methods=['POST'])
def user_register():
    invitation_code = request.values.get('invitation_code')
    username = request.values.get('username')
    password = request.values.get('password')
    re_password = request.values.get('re_password')

    if not r_session.sismember('invitation_codes', invitation_code) and \
            not r_session.sismember('public_invitation_codes', invitation_code):
        session['error_message'] = '无效的邀请码。'
        return redirect(url_for('register'))

    if username == '':
        session['error_message'] = '账号名不能为空。'
        return redirect(url_for('register'))

    if r_session.get('%s:%s' % ('user', username)) is not None:
        session['error_message'] = '该账号名已存在。'
        return redirect(url_for('register'))

    if password != re_password:
        session['error_message'] = '新密码输入不一致.'
        return redirect(url_for('register'))

    if len(password) < 8:
        session['error_message'] = '密码必须8位及以上.'
        return redirect(url_for('register'))

    r_session.srem('invitation_codes', invitation_code)
    r_session.srem('public_invitation_codes', invitation_code)

    user = dict(username=username, password=hash_password(password), id=str(uuid.uuid1()),
                active=True, is_admin=False, max_account_no=20,
                created_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    r_session.set('%s:%s' % ('user', username), json.dumps(user))
    r_session.set('%s:%s' % ('record', username), json.dumps(dict(diary=[])))
    r_session.sadd('users', username)

    session['info_message'] = '恭喜你，注册成功.'
    return redirect(url_for('register'))

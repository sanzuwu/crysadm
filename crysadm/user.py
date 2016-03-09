__author__ = 'powergx'
from flask import request, Response, render_template, session, url_for, redirect
from crysadm import app, r_session
from auth import requires_admin, requires_auth
import json
from util import hash_password
import uuid
import re
from datetime import datetime

#Crysadm 用户登录
@app.route('/user/login', methods=['POST'])
def user_login():
    try:
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
        session['user_info'] = user

        return redirect(url_for('dashboard'))
    except Exception as e:
        return  

# 主页登录
@app.route('/login')
def login():
    if session.get('user_info') is not None: return redirect(url_for('dashboard'))
    err_msg = session.get('error_message')
    session['error_message'] = None
    return render_template('index.html', err_msg=err_msg)

# 邀请管理
@app.route('/invitations')
def public_invitation():
    inv_codes = r_session.smembers('public_invitation_codes')
    return render_template('public_invitation.html', inv_codes=inv_codes)

# 注销登录
@app.route('/user/logout')
@requires_auth
def logout():
    if session.get('admin_user_info') is not None:
        session['user_info'] = session.get('admin_user_info')
        del session['admin_user_info']
        return redirect(url_for('admin_user'))
    session.clear()
    return redirect(url_for('login'))

# 用户个人资料
@app.route('/user/profile')
@requires_auth
def user_profile():
    user = session.get('user_info')
    user_key = 'user:%s' % user.get('username')
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))
    
    err_msg = session.get('error_message')
    session['error_message'] = None
    
    action = session.get('action')
    session['action']=None
    
    return render_template('profile.html', user_info=user_info, err_msg=err_msg, action=action)

# 修改个人资料
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

# 修改自动属性
@app.route('/user/change_property/<field>/<value>', methods=['POST'])
@requires_auth
def user_change_property(field, value):
    user = session.get('user_info')
    user_key = 'user:%s' % user.get('username')
    user_info = json.loads(r_session.get(user_key).decode('utf-8'))
    
    if field == 'auto_collect': # 自动收集
        user_info['auto_collect'] = True if value =='1' else False
    if field == 'auto_drawcash':  # 自动提现
        user_info['auto_drawcash'] = True if value =='1' else False
    if field == 'auto_giftbox':  # 开免费宝箱
        user_info['auto_giftbox'] = True if value =='1' else False
    if field == 'auto_cashbox': # 开收费宝箱
        user_info['auto_cashbox'] = True if value =='1' else False
    if field == 'auto_stealattack': # 水晶进攻与复仇
        user_info['auto_stealattack'] = True if value =='1' else False
    r_session.set(user_key, json.dumps(user_info))

    return redirect(url_for('user_profile'))
   

# 修改密码
@app.route('/user/change_password', methods=['POST'])
@requires_auth
def user_change_password():
    try:
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
    except Exception as e:
        return

# 用户注册（后台程序）
@app.route('/register')
def register():
    if session.get('user_info') is not None:
        return redirect(url_for('dashboard'))

    err_msg = None
    if session.get('error_message') is not None:
        err_msg = session.get('error_message')
        session['error_message'] = None

    invitation_code = ''
    if request.values.get('inv_code') is not None and len(request.values.get('inv_code')) > 0 :
        invitation_code = request.values.get('inv_code')
        if not r_session.sismember('invitation_codes', invitation_code) and \
                    not r_session.sismember('public_invitation_codes', invitation_code):
            session['error_message'] = '无效的邀请码。'

    return render_template('register.html', err_msg=err_msg,invitation_code=invitation_code)

# 用户注册(web界面)
@app.route('/user/register', methods=['POST'])
def user_register():
    try:
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
                active=True, is_admin=False, max_account_no=5,
                created_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        r_session.set('%s:%s' % ('user', username), json.dumps(user))
        r_session.sadd('users', username)
        return redirect(url_for('login'))
    except Exception as e:
        return
    

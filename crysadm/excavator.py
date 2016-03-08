# Html － 我的矿机
__author__ = 'powergx'
from flask import request, Response, render_template, session, url_for, redirect
from crysadm import app, r_session
from auth import requires_admin, requires_auth
import json
import requests
from urllib.parse import urlparse, parse_qs
import time
from api import xunlei_api_exec_collect, ubus_cd, xunlei_api_exec_getCash, DEBUG_MODE

# 收集水晶函数
def func_collect_crystal(USERID=None):    
    if DEBUG_MODE:
        print('func_collect_crystal() incoming USERID = %s' % USERID)
    try:
        user = session.get('user_info')
        username = user.get('username')
        err_msg = ''
        info_msg = ''

        for b_user_id in r_session.smembers('accounts:%s' % username):
            account_key = 'account:%s:%s' % (username, b_user_id.decode("utf-8"))
            if DEBUG_MODE:
                print('collect_crystal() : account_key=%s' % account_key)
            account_info = json.loads(r_session.get(account_key).decode("utf-8"))
            if DEBUG_MODE:
                print('collect_crystal() : account_info=%s' % account_info)
            user_id = account_info.get('user_id')
            if DEBUG_MODE:
                print('collect_crystal() : user_id=%s' % user_id)
            if USERID is not None and user_id != USERID:
                if DEBUG_MODE:
                    print('collect_crystal() : Specify user_id is %s, current id is %s, do not collected!' % (USERID, user_id))
                continue

            cookies = dict(sessionid=account_info.get('session_id'), userid=str(user_id))
            r = xunlei_api_exec_collect(cookies)
            if r.get('r') != 0:
                err_msg += '  %s : %s <br />' % (user_id, r['rd'])
            else:
                info_msg += '  %s : 收取水晶成功 <br />' % user_id
                account_data_key = account_key + ':data'
                account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
                account_data_value.get('mine_info')['td_not_in_a'] = 0
                r_session.set(account_data_key, json.dumps(account_data_value))
                time.sleep(5)

        if len(info_msg) > 0:
            session['info_message'] = info_msg
        if len(err_msg) > 0:
            session['error_message'] = err_msg
    
        return redirect(url_for('excavators'))
    except Exception as e:
        return

# 提现函数
def func_exec_drawcash(USERID=None):
    if DEBUG_MODE:
        print('func_exec_drawcash() : incomingID = %s' % USERID)
    try:
        user = session.get('user_info')
        username = user.get('username')
        err_msg = ''
        info_msg = ''

        for b_user_id in r_session.smembers('accounts:%s' % username):
            account_key = 'account:%s:%s' % (username, b_user_id.decode("utf-8"))
            if DEBUG_MODE:
                print(account_key)
            account_info = json.loads(r_session.get(account_key).decode("utf-8"))
            if DEBUG_MODE:
                print(account_info)
            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')

            if USERID is not None and user_id != USERID:
                if DEBUG_MODE:
                    print('func_exec_drawcash() : Specify user_id is %s, current id is %s, do not cash!' % (USERID, user_id))
                continue

            cookies = dict(sessionid=session_id, userid=str(user_id))

            r = xunlei_api_exec_getCash(cookies=cookies, limits=10)
            if DEBUG_MODE:
                print('xunlei_api_exec_getCash(%s) : %s' % (cookies, r))
            if r.get('r') != 0:
                err_msg += '  %s : %s <br />' % (user_id, r['rd'])
            else:
                info_msg += '  %s : %s <br />' % (user_id, r['rd'])            
                account_data_key = account_key + ':data'
                account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
                account_data_value.get('income')['r_can_use'] = 0
                r_session.set(account_data_key, json.dumps(account_data_value))
                time.sleep(100)

        if len(info_msg) > 0:
            session['info_message'] = info_msg
        if len(err_msg) > 0:
            session['error_message'] = err_msg
        return redirect(url_for('excavators'))
    except Exception as e:
        return

# 加载矿机主页面
@app.route('/excavators')
@requires_auth
def excavators():
    try:
        user = session.get('user_info')
        err_msg = None
        if session.get('error_message') is not None:
            err_msg = session.get('error_message')
            session['error_message'] = None

        info_msg = None
        if session.get('info_message') is not None:
            info_msg = session.get('info_message')
            session['info_message'] = None

        accounts_key = 'accounts:%s' % user.get('username')
        accounts = list()

        for acct in sorted(r_session.smembers(accounts_key)):
            account_key = 'account:%s:%s' % (user.get('username'), acct.decode("utf-8"))
            account_data_key = account_key + ':data'
            account_data_value = r_session.get(account_data_key)
            account_info = json.loads(r_session.get(account_key).decode("utf-8"))
            if account_data_value is not None:
                account_info['data'] = json.loads(account_data_value.decode("utf-8"))

            accounts.append(account_info)

        show_drawcash = not (r_session.get('can_drawcash') is None or
                         r_session.get('can_drawcash').decode('utf-8') == '0')

    
        return render_template('excavators.html', err_msg=err_msg, info_msg=info_msg, accounts=accounts,
                           show_drawcash=show_drawcash)
    except Exception as e:
        return
    

# 收集所有ID水晶
@app.route('/collect/all', methods=['POST'])
@requires_auth
def collect_all_crystal():
    if DEBUG_MODE:
        print('start collect all users crystals')   
    return func_collect_crystal(USERID=None)

# 收集单个ID水晶
@app.route('/collect/<user_id>', methods=['POST'])
@requires_auth
def collect_one_crystal(user_id):
    if DEBUG_MODE:
        print('start collect with user_id %s' % user_id)
    return func_collect_crystal(USERID=user_id)


# 对用户绑定的所有迅雷ID进行提现操作
@app.route('/drawcash/all', methods=['POST'])
@requires_auth
def drawcash_all():
    if DEBUG_MODE:
        print('start drawcash with all ids')
    return func_exec_drawcash(USERID=None)

# 单用户ID提现
@app.route('/drawcash/<user_id>', methods=['POST'])
@requires_auth
def drawcash(user_id):
    if DEBUG_MODE:
        print('start drawcash with user_id %s' % user_id)
    return func_exec_drawcash(USERID=user_id)

# 重启设备按钮
@app.route('/reboot_device', methods=['POST'])
@requires_auth
def reboot_device():
    try:
        device_id = request.values.get('device_id')
        session_id = request.values.get('session_id')
        account_id = request.values.get('account_id')
        ubus_cd(session_id, account_id, 'reboot', ["mnt", "reboot", {}], '&device_id=%s' % device_id)
        return redirect(url_for('excavators'))        
    except Exception as e:
        return    

# 设置设备名称
@app.route('/set_device_name', methods=['POST'])
@requires_auth
def set_device_name():
    try:
        setting_url = request.values.get('url')
        new_name = request.values.get('name')
        query_s = parse_qs(urlparse(setting_url).query, keep_blank_values=True)

        device_id = query_s['device_id'][0]
        session_id = query_s['session_id'][0]
        account_id = query_s['user_id'][0]

        ubus_cd(session_id, account_id, 'set_device_name',
            ["server", "set_device_name", {"device_name": new_name, "device_id": device_id}])
        return json.dumps(dict(status='success'))
    except Exception as e:
        return
    
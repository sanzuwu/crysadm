# Html － 我的矿机
__author__ = 'powergx'
from flask import request, Response, render_template, session, url_for, redirect
from crysadm import app, r_session
from auth import requires_admin, requires_auth
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote
import time
from api import collect, ubus_cd, api_searcht_steal, api_searcht_collect, api_getaward, collect, api_summary_steal

# 加载矿机主页面
@app.route('/excavators')
@requires_auth
def excavators():
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

# 收取水晶[ID]
@app.route('/collect/<user_id>', methods=['POST'])
@requires_auth
def collect_all(user_id):
    user = session.get('user_info')
    account_key = 'account:%s:%s' % (user.get('username'), user_id)
    account_info = json.loads(r_session.get(account_key).decode("utf-8"))

    session_id = account_info.get('session_id')
    user_id = account_info.get('user_id')

    cookies = dict(sessionid=session_id, userid=str(user_id))
    t = collect(cookies)
    session['info_message'] = '收取水晶成功'
    account_data_key = account_key + ':data'
    account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
    account_data_value.get('mine_info')['td_not_in_a'] = 0
    r_session.set(account_data_key, json.dumps(account_data_value))

    return redirect(url_for('excavators'))

# 幸运转盘[ID]
@app.route('/getaward/<user_id>', methods=['POST'])
@requires_auth
def getaward_all(user_id):
    user = session.get('user_info')
    account_key = 'account:%s:%s' % (user.get('username'), user_id)
    account_info = json.loads(r_session.get(account_key).decode("utf-8"))

    session_id = account_info.get('session_id')
    user_id = account_info.get('user_id')

    cookies = dict(sessionid=session_id, userid=str(user_id))
    t = api_getaward(cookies)
    if t.get('rd') != 'ok':
        session['error_message'] = '%s' % t.get('rd')
    else:
        session['info_message'] = '转盘成功,获得:%s  下次转需要:%s秘银.<br />' % (unquote(t.get('tip')), t.get('cost'))
        account_data_key = account_key + ':data'
        account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
        account_data_value.get('mine_info')['td_not_in_a'] = 0
        r_session.set(account_data_key, json.dumps(account_data_value))

    return redirect(url_for('excavators'))

# 秘银进攻[ID]
@app.route('/searcht/<user_id>', methods=['POST'])
@requires_auth
def searcht_all(user_id):
    user = session.get('user_info')
    account_key = 'account:%s:%s' % (user.get('username'), user_id)
    account_info = json.loads(r_session.get(account_key).decode("utf-8"))

    session_id = account_info.get('session_id')
    user_id = account_info.get('user_id')

    cookies = dict(sessionid=session_id, userid=str(user_id))
    t = check_cashbox_collect(cookies)
    if t.get('r') != 0:
        session['error_message'] = '进攻失败,%s' % unquote(t.get('rd'))
    else:
        session['info_message'] = '进攻成功,获得:%s秘银' % t.get('s')
        account_data_key = account_key + ':data'
        account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
        account_data_value.get('mine_info')['td_not_in_a'] = 0
        r_session.set(account_data_key, json.dumps(account_data_value))

    return redirect(url_for('excavators'))

# 执行进攻函数
def check_cashbox_collect(cookies):
    box_info = api_searcht_steal(cookies)
    if box_info.get('r') != 0:
        r = box_info
    else:
        time.sleep(2)
        r = api_searcht_collect(cookies=cookies, searcht_id=box_info.get('sid'))
        time.sleep(1)
        api_summary_steal(cookies=cookies, searcht_id=box_info.get('sid'))
    return r

# 收集所有水晶
@app.route('/collect/all', methods=['POST'])
@requires_auth
def collect_all_crystal():
    user = session.get('user_info')
    username = user.get('username')

    error_message = ''
    success_message = ''
    for b_user_id in r_session.smembers('accounts:%s' % username):

        account_key = 'account:%s:%s' % (username, b_user_id.decode("utf-8"))
        account_info = json.loads(r_session.get(account_key).decode("utf-8"))

        session_id = account_info.get('session_id')
        user_id = account_info.get('user_id')

        cookies = dict(sessionid=session_id, userid=str(user_id))
        r = collect(cookies)
        if r.get('r') != 0:
            error_message += 'Id:%s : %s<br />' % (user_id, r.get('rd'))
        else:
            success_message += 'Id:%s : 收取水晶成功.<br />' % user_id
            account_data_key = account_key + ':data'
            account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
            account_data_value.get('mine_info')['td_not_in_a'] = 0
            r_session.set(account_data_key, json.dumps(account_data_value))

    if len(success_message) > 0:
        session['info_message'] = success_message

    if len(error_message) > 0:
        session['error_message'] = error_message

    return redirect(url_for('excavators'))

# 所有账号进攻
@app.route('/searcht/all', methods=['POST'])
@requires_auth
def searcht_all_crystal():
    user = session.get('user_info')
    username = user.get('username')

    error_message = ''
    success_message = ''
    for b_user_id in r_session.smembers('accounts:%s' % username):

        account_key = 'account:%s:%s' % (username, b_user_id.decode("utf-8"))
        account_info = json.loads(r_session.get(account_key).decode("utf-8"))

        session_id = account_info.get('session_id')
        user_id = account_info.get('user_id')

        cookies = dict(sessionid=session_id, userid=str(user_id))
        t = check_cashbox_collect(cookies)
        if t.get('r') != 0:
            error_message += 'Id:%s 进攻失败,%s<br />' % (user_id, unquote(t.get('rd')))
        else:
            success_message += 'Id:%s : 进攻成功,获得:%s秘银.<br />' % (user_id, t.get('s'))
            account_data_key = account_key + ':data'
            account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
            account_data_value.get('mine_info')['td_not_in_a'] = 0
            r_session.set(account_data_key, json.dumps(account_data_value))
    if len(success_message) > 0:
        session['info_message'] = success_message

    if len(error_message) > 0:
        session['error_message'] = error_message

    return redirect(url_for('excavators'))

# 所有账号转盘
@app.route('/getaward/all', methods=['POST'])
@requires_auth
def getaward_all_crystal():
    user = session.get('user_info')
    username = user.get('username')

    error_message = ''
    success_message = ''
    for b_user_id in r_session.smembers('accounts:%s' % username):

        account_key = 'account:%s:%s' % (username, b_user_id.decode("utf-8"))
        account_info = json.loads(r_session.get(account_key).decode("utf-8"))

        session_id = account_info.get('session_id')
        user_id = account_info.get('user_id')

        cookies = dict(sessionid=session_id, userid=str(user_id))
        t = api_getaward(cookies)
        if t.get('rd') != 'ok':
            error_message += 'Id:%s %s<br />' % (user_id, t.get('rd')) 
        else:
            success_message += 'Id:%s 转盘成功,获得:%s  下次转需要:%s 秘银.<br />' % (user_id, unquote(t.get('tip')), t.get('cost'))
            account_data_key = account_key + ':data'
            account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
            account_data_value.get('mine_info')['td_not_in_a'] = 0
            r_session.set(account_data_key, json.dumps(account_data_value))
    if len(success_message) > 0:
        session['info_message'] = success_message

    if len(error_message) > 0:
        session['error_message'] = error_message

    return redirect(url_for('excavators'))

# 生成用户收益
@app.route('/drawcash/<user_id>', methods=['POST'])
@requires_auth
def drawcash(user_id):
    user = session.get('user_info')
    account_key = 'account:%s:%s' % (user.get('username'), user_id)
    account_info = json.loads(r_session.get(account_key).decode("utf-8"))

    session_id = account_info.get('session_id')
    user_id = account_info.get('user_id')

    cookies = dict(sessionid=session_id, userid=str(user_id))
    from api import exec_draw_cash

    r = exec_draw_cash(cookies)
    if r.get('r') != 0:
        session['error_message'] = r.get('rd')
        return redirect(url_for('excavators'))
    else:
        session['info_message'] = r.get('rd')
    account_data_key = account_key + ':data'
    account_data_value = json.loads(r_session.get(account_data_key).decode("utf-8"))
    account_data_value.get('income')['r_can_use'] = 0
    r_session.set(account_data_key, json.dumps(account_data_value))

    return redirect(url_for('excavators'))

# 重启设备按钮
@app.route('/reboot_device', methods=['POST'])
@requires_auth
def reboot_device():
    device_id = request.values.get('device_id')
    session_id = request.values.get('session_id')
    account_id = request.values.get('account_id')

    ubus_cd(session_id, account_id, 'reboot', ["mnt", "reboot", {}], '&device_id=%s' % device_id)

    return redirect(url_for('excavators'))

# 升级设备按钮
@app.route('/progress_device', methods=['POST'])
@requires_auth
def progress_device():
    device_id = request.values.get('device_id')
    session_id = request.values.get('session_id')
    account_id = request.values.get('account_id')
    ubus_cd(session_id, account_id, 'get_progress', ["upgrade", "start", {}], '&device_id=%s' % device_id)
    ubus_cd(session_id, account_id, 'get_progress', ["upgrade", "get_progress", {}], '&device_id=%s' % device_id)

    return redirect(url_for('excavators'))

# 生成设备名称
@app.route('/set_device_name', methods=['POST'])
@requires_auth
def set_device_name():
    setting_url = request.values.get('url')
    new_name = request.values.get('name')
    query_s = parse_qs(urlparse(setting_url).query, keep_blank_values=True)

    device_id = query_s['device_id'][0]
    session_id = query_s['session_id'][0]
    account_id = query_s['user_id'][0]

    ubus_cd(session_id, account_id, 'set_device_name',
            ["server", "set_device_name", {"device_name": new_name, "device_id": device_id}])

    return json.dumps(dict(status='success'))
__author__ = 'powergx'
import json
import requests
from crysadm_helper import r_session
from requests.adapters import HTTPAdapter
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

requests.packages.urllib3.disable_warnings()

# 迅雷API接口
server_address = 'http://2-api-red.xunlei.com'
agent_header = {'user-agent': "RedCrystal/2.0.0 (iPhone; iOS 8.4; Scale/2.00)"}

#server_address = 'http://1-api-red.xunlei.com/index.php'
#agent_header = {'user-agent': "RedCrystal/2.0.0 (iPhone; iOS 8.4; Scale/2.00)"}

DEBUG_MODE = False

# 提交链接给迅雷，获取返回信息
def xunlei_api_posttoxunlei(cookies, url, data, verify=False, headers=agent_header, timeout=60):
    address = server_address + url
    if DEBUG_MODE:
        print('Call from xunlei_api_posttoxunlei(cookies=%s,url=%s,data=%s,verify=%s,headers=%s' % (cookies, address, data, verify, headers))
    try:
        r = requests.post(url=address, data=data, verify=verify, headers=headers, cookies=cookies, timeout=timeout)        
    except requests.exceptions.RequestException as e:
        return __handle_exception(e=e)

    if r.status_code != 200: 
        return __handle_exception(rd=r.reason)

    if DEBUG_MODE: print('  Result = %s' % r.text)    
    return json.loads(r.text)

# 获取输入的cookies信息
def xunlei_api_get_IncomeInfo(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(hand='0', v='1', ver='1')
    return xunlei_api_posttoxunlei(url='/?r=usr/getinfo&v=1', data=body, cookies=cookies)

# 获取MINE信息
def xunlei_api_get_mine_info(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(hand='0', v='2', ver='1')
    return xunlei_api_posttoxunlei(url='/?r=mine/info', data=body, cookies=cookies)


# 检测用户是否有可提现的金额（周二 11:00~18:00）
def xunlei_api_isCashDay(cookies=None): 
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '2'
    body = dict(hand='0', v='1', ver='1')
    return xunlei_api_posttoxunlei(url='/?r=usr/drawcashInfo', data=body, cookies=cookies)

# 获取帐户余额
def xunlei_api_get_balance_inof(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '2'
    body = dict(hand='0', v='2', ver='1')
    return xunlei_api_posttoxunlei(url='/?r=usr/asset', data=body, cookies=cookies)

# 向迅雷提交提现请求
# cookies = 用户信息
# money = 提现金额（元）
def xunlei_api_require_cash(cookies, money):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '2'
    body = dict(hand='0', m=str(money), v='3', ver='1')
    if DEBUG_MODE:
        print('call from xunlei_api_require_cask(%s, %s)' % (cookies, money))
    return xunlei_api_posttoxunlei(url='?r=usr/drawpkg', data=body, cookies=cookies)

# 获取免费宝箱信息
def xunlei_api_get_giftbox(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '2'
    body = dict(tp='0', p='0', ps='60', t='', v='2', cmid='-1')
    return xunlei_api_posttoxunlei(url='/?r=usr/giftbox', data=body, cookies=cookies).get('ci')

# 打开宝箱
def xunlei_api_open_stone(cookies, giftbox_id, direction):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(v='1', id=str(giftbox_id), side=direction)
    return xunlei_api_posttoxunlei(url='/?r=usr/openStone', data=body, cookies=cookies).get('get')

# 向迅雷申请提现
# 增加提现下限，当可提现金额少于指定值时，不提现
# cookies = 用户信息
# limits = 提现下限值，单位元
def xunlei_api_exec_getCash(cookies, limits):
    # 检测是否可提现   
    r = xunlei_api_isCashDay(cookies)   
    if r.get('r') != 0: return r
    if r.get('is_tm') == 0: return dict(r=0, rd=r.get('tm_tip'))
    # 获取帐户可提现余额
    r = xunlei_api_get_balance_inof(cookies)    
    if r.get('r') != 0: 
        return r
    wc_pkg = r.get('wc_pkg')   
    # 如果设置了提取下限且帐户金额少于下限值，退出
    if limits is not None and wc_pkg < limits: 
        return dict(r=1, rd='帐户金额少于下限值%s元' % limits)
    # 没有设置下限，当可提现金额大于200元时，提取200元
    if wc_pkg > 200: 
        wc_pkg = 200
    # 申请提现    
    return xunlei_api_require_cash(cookies, wc_pkg)

# 收集水晶
def xunlei_api_exec_collect(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(hand='0', v='2', ver='1')
    return xunlei_api_posttoxunlei(url='/index.php?r=mine/collect', data=body, cookies=cookies)

# 获取速度状态
def xunlei_api_get_spped_stat(s_type, cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(type=s_type, hand='0', v='0', ver='1')
    try:
        r = requests.post(server_address + '/?r=mine/speed_stat', data=body, verify=False, cookies=cookies, headers=agent_header, timeout=60)        
    except requests.exceptions.RequestException as e:
        __handle_exception(e=e)
        return [0] * 24
    if r.status_code != 200:
        __handle_exception(e=e)
        return [0] * 24
    return json.loads(r.text).get('sds')

# 获取星域存储相关信息
def ubus_cd(session_id, account_id, action, out_params, url_param=None):
    url = "http://kjapi.peiluyou.com:5171/ubus_cd?account_id=%s&session_id=%s&action=%s" % (account_id, session_id, action)
    if url_param is not None:
        url += url_param
    params = ["%s" % session_id] + out_params

    data = {"jsonrpc": "2.0", "id": 1, "method": "call", "params": params}

    try:
        body = dict(data=json.dumps(data), action='onResponse%d' % int(time.time() * 1000))
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=5))
        r = s.post(url, data=body)
        result = r.text[r.text.index('{'):r.text.rindex('}')+1]
        return json.loads(result)
    except requests.exceptions.RequestException as e:
        return __handle_exception(e=e)

# 获取个人信息
def xunlei_api_get_privilege(cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(v='1', ver='6')
    return xunlei_api_posttoxunlei(url='/?r=usr/privilege', data=body, cookies=cookies)

# 获取设备状态
def xunlei_api_get_device_stat(s_type, cookies):
    cookies['origin'] = '4' if len(cookies.get('sessionid')) == 128 else '1'
    body = dict(type=s_type, hand='0', v='2', ver='1')
    return xunlei_api_posttoxunlei(url='/?r=mine/devices_stat', data=body, cookies=cookies)

# 发送设置链接
def parse_setting_url(url):
    query_s = parse_qs(urlparse(url).query, keep_blank_values=True)

    device_id = query_s['device_id'][0]
    session_id = query_s['session_id'][0]
    account_id = query_s['user_id'][0]
    return device_id, session_id, account_id

# 检测是否API错误
def is_api_error(r):
    if r.get('r') == -12345:
        return True
    return False

# 错误处理
def __handle_exception(e=None, rd='接口故障', r=-12345):
    if e is None:
        print(rd)
    else:
        print(e)

    b_err_count = r_session.get('api_error_count')
    if b_err_count is None:
        r_session.setex('api_error_count', '1', 60)
        return dict(r=r, rd=rd)

    err_count = int(b_err_count.decode('utf-8')) + 1

    if err_count > 200:
        r_session.setex('api_error_info', '迅雷矿场API故障中,攻城狮正在赶往事故现场,请耐心等待.', 60)

    err_count_ttl = r_session.ttl('api_error_count')
    if err_count_ttl is None:
        err_count_ttl = 30
    r_session.setex('api_error_count', str(err_count), err_count_ttl + 1)
    return dict(r=r, rd=rd)
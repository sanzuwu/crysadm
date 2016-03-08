__author__ = 'powergx'
import sys, os
import config, socket, redis
import time
from login import login
from datetime import datetime, timedelta
from multiprocessing import Process
from multiprocessing.dummy import Pool as ThreadPool
import threading

# from crysadm import conf, redis_conf, pool, r_session

conf = config.ProductionConfig
redis_conf = conf.REDIS_CONF
pool = redis.ConnectionPool(host=redis_conf.host, port=redis_conf.port, db=redis_conf.db, password=redis_conf.password)
r_session = redis.Redis(connection_pool=pool)

from api import *

# 获取用户数据
def get_data(username):
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_data')

    start_time = datetime.now()
    try:
        for user_id in r_session.smembers('accounts:%s' % username):
            # 如果用户状态为非启用状态，则执行下一个用户
            account_key = 'account:%s:%s' % (username, user_id.decode('utf-8'))
            account_info = json.loads(r_session.get(account_key).decode('utf-8'))
            if not account_info.get('active'): continue 

            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')
            cookies = dict(sessionid=session_id, userid=str(user_id))            
            # 获取帐户水晶状态
            mine_info = xunlei_api_get_mine_info(cookies) 
            if is_api_error(mine_info):
                print('get_data:', user_id, mine_info, 'error')
                return
            # 如果登陆已过期，则重新登录并重新获取水晶状态
            if mine_info.get('r') != 0:
                success, account_info = __relogin(account_info.get('account_name'), account_info.get('password'), account_info, account_key)
                if not success:
                    print('get_data:', user_id, 'relogin failed')
                    continue
                session_id = account_info.get('session_id')
                user_id = account_info.get('user_id')
                cookies = dict(sessionid=session_id, userid=str(user_id))
                mine_info = xunlei_api_get_mine_info(cookies)
            if mine_info.get('r') != 0:
                print('get_data:', user_id, mine_info, 'error')
                continue
            # 获取设备状态
            device_info = ubus_cd(session_id, user_id, 'get_devices', ["server", "get_devices", {}], '&action=%donResponse' % int(time.time()*1000))
            red_zqb = device_info['result'][1]

            account_data_key = account_key + ':data'
            exist_account_data = r_session.get(account_data_key)
            if exist_account_data is None:
                account_data = dict()
                account_data['privilege'] = xunlei_api_get_privilege(cookies)
            else:
                account_data = json.loads(exist_account_data.decode('utf-8'))

            if account_data.get('updated_time') is not None:
                last_updated_time = datetime.strptime(account_data.get('updated_time'), '%Y-%m-%d %H:%M:%S')
                if last_updated_time.hour != datetime.now().hour:
                    account_data['zqb_speed_stat'] = xunlei_api_get_spped_stat('1', cookies)
                    account_data['old_speed_stat'] = xunlei_api_get_spped_stat('0', cookies)
            else:
                account_data['zqb_speed_stat'] = xunlei_api_get_spped_stat('1', cookies)
                account_data['old_speed_stat'] = xunlei_api_get_spped_stat('0', cookies)

            account_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')            
            account_data['mine_info'] = mine_info            
            account_data['device_info'] = red_zqb.get('devices')            
            account_data['income'] = xunlei_api_get_IncomeInfo(cookies)

            if is_api_error(account_data.get('income')):
                print('get_data:', user_id, 'income error')
                return

            r_session.set(account_data_key, json.dumps(account_data))
            if not r_session.exists('can_drawcash'):
                r = xunlei_api_isCashDay(cookies=cookies)
                if r.get('r') == 0:
                    r_session.setex('can_drawcash', r.get('is_tm'), 60)

        if start_time.day == datetime.now().day:
            save_history(username)

        r_session.setex('user:%s:cron_queued' % username, '1', 60)
        if DEBUG_MODE:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'successed')        
    except Exception as ex:
        print(username.encode('utf-8'), 'failed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ex)

# 保存历史数据
def save_history(username):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'save_history')

    try:
        str_today = datetime.now().strftime('%Y-%m-%d')
        key = 'user_data:%s:%s' % (username, str_today)
        b_today_data = r_session.get(key)
        today_data = dict()

        if b_today_data is not None:
            today_data = json.loads(b_today_data.decode('utf-8'))

        today_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today_data['pdc'] = 0
        today_data['last_speed'] = 0
        today_data['deploy_speed'] = 0
        today_data['balance'] = 0
        today_data['income'] = 0
        today_data['speed_stat'] = list()
        today_data['pdc_detail'] = []

        for user_id in r_session.smembers('accounts:%s' % username):
            # 获取账号所有数据
            account_data_key = 'account:%s:%s:data' % (username, user_id.decode('utf-8'))
            b_data = r_session.get(account_data_key)
            if b_data is None:
                continue
            data = json.loads(b_data.decode('utf-8'))

            if datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S') + timedelta(minutes=1) < datetime.now() or \
                        datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S').day != datetime.now().day:
                continue
            today_data.get('speed_stat').append(dict(mid=data.get('privilege').get('mid'),
                                                 dev_speed=data.get('zqb_speed_stat') if data.get(
                                                     'zqb_speed_stat') is not None else [0] * 24,
                                                 pc_speed=data.get('old_speed_stat') if data.get(
                                                     'old_speed_stat') is not None else [0] * 24))
            this_pdc = data.get('mine_info').get('dev_m').get('pdc') + \
                   data.get('mine_info').get('dev_pc').get('pdc')

            today_data['pdc'] += this_pdc
            today_data.get('pdc_detail').append(dict(mid=data.get('privilege').get('mid'), pdc=this_pdc))

            today_data['balance'] += data.get('income').get('r_can_use')
            today_data['income'] += data.get('income').get('r_h_a')
            for device in data.get('device_info'):
                today_data['last_speed'] += int(int(device.get('dcdn_upload_speed')) / 1024)
                today_data['deploy_speed'] += int(device.get('dcdn_download_speed') / 1024)

        r_session.setex(key, json.dumps(today_data), 3600 * 24 * 35)
        save_income_history(username, today_data.get('pdc_detail'))
    except Exception as e:
        print(username.encode('utf-8'), 'failed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), e)
    

# 获取保存的历史数据
def save_income_history(username, pdc_detail):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'save_income_history')

    try:
        now = datetime.now()
        key = 'user_data:%s:%s' % (username, 'income.history')
        b_income_history = r_session.get(key)
        income_history = dict()

        if b_income_history is not None:
            income_history = json.loads(b_income_history.decode('utf-8'))

        if now.minute < 50:
            return

        if income_history.get(now.strftime('%Y-%m-%d')) is None:
            income_history[now.strftime('%Y-%m-%d')] = dict()

        income_history[now.strftime('%Y-%m-%d')][now.strftime('%H')] = pdc_detail

        r_session.setex(key, json.dumps(income_history), 3600 * 72)
    except Exception as e:
        print(username.encode('utf-8'), 'failed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), e)
    

# 重新登录
def __relogin(username, password, account_info, account_key):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'relogin')

    try:
        login_result = login(username, password, conf.ENCRYPT_PWD_URL)

        if login_result.get('errorCode') != 0:
            account_info['status'] = login_result.get('errorDesc')
            account_info['active'] = False
            r_session.set(account_key, json.dumps(account_info))
            return False, account_info

        account_info['session_id'] = login_result.get('sessionID')
        account_info['status'] = 'OK'
        r_session.set(account_key, json.dumps(account_info))
        return True, account_info
    except Exception as e:
        return False, account_info

# 执行自动收集的函数
def prc_background_collect(cookies):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'prc_background_collect()')
    try:
        mine_info = xunlei_api_get_mine_info(cookies)
        if mine_info.get('r') == 0 and mine_info.get('td_not_in_a') > 0:
            xunlei_api_exec_collect(cookies)            
    except requests.exceptions.RequestException as e:
        return

# 执行自动提现的函数
def prc_background_drawcash(cookies):
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'prc_background_drawcash()')    
    try:
        xunlei_api_exec_getCash(cookies=cookies, limits=10)
    except Exception as e:
        return

# 执行开免费宝箱的函数
def prc_background_giftbox(cookies):
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'prc_background_giftbox()')
    try:
        box_info = xunlei_api_get_giftbox(cookies)
        if DEBUG_MODE: print('      box_info = %s' % box_info)
        if box_info is None: return
        for box in box_info:
            #开宝箱
            #direction = 开启方向
            #   左切 = 1；竖切=2；右切=3
            #box.get('cnum') = 开宝箱的费用,0为免费宝箱
            if box.get('cnum') == 0:
                if DEBUG_MODE: print('      open box = %s' % box)
                xunlei_api_open_stone(cookies=cookies, giftbox_id=box.get('id'), direction='3')
    except Exception as e:
        return

# 执行开收费宝箱的函数
def prc_background_cashbox(cookies):
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'prc_background_giftbox()')
    try:
        box_info = xunlei_api_get_giftbox(cookies)
        if DEBUG_MODE: print('      box_info = %s' % box_info)
        if box_info is None: return
        for box in box_info:
            #开宝箱
            #direction = 开启方向
            #   左切 = 1；竖切=2；右切=3
            #box.get('cnum') = 开宝箱的费用,0为免费宝箱
            if DEBUG_MODE: print('      open box = %s' % box)
            xunlei_api_open_stone(cookies=cookies, giftbox_id=box.get('id'), direction='3')                
    except Exception as e:
        return

# 刷新在线用户数据
def background_refresh_online_user_data():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'background_refresh_online_user_data()')
    if r_session.exists('api_error_info'):
        return
    try:
        for user in r_session.smembers('global:online.users'):
            get_data(user.decode('utf-8'))
    except Exception as e:
        return

# 刷新离线用户数据
def background_refresh_offline_user_data():    
    if r_session.exists('api_error_info') or datetime.now().minute < 50:
        return
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'background_refresh_offline_user_data()')

    offline_users = []
    for b_user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in r_session.sdiff('users', *r_session.smembers('global:online.users'))]):
        user_info = json.loads(b_user.decode('utf-8'))
        username = user_info.get('username')
        if not user_info.get('active'): continue

        every_hour_key = 'user:%s:cron_queued' % username
        if r_session.exists(every_hour_key): continue
        offline_users.append(username)

    pool = ThreadPool(processes=1)
    pool.map(get_data, offline_users)
    pool.close()
    pool.join()

# 从在线用户数组中移除离线用户名称 
def background_remove_offline_user():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'background_remove_offline_user()')
    for b_username in r_session.smembers('global:online.users'):
        username = b_username.decode('utf-8')
        if not r_session.exists('user:%s:is_online' % username):
            r_session.srem('global:online.users', username)
    
# 刷新设置了自动任务的用户 
def background_update_auto_task_users():
    if DEBUG_MODE: print(' start update auto task users in db')
    collect_accounts =[] #自动收取用户
    cash_accounts = [] #自动提现用户
    giftbox_accounts = [] #开免费宝箱用户
    cashbox_accounts =[] #开收费宝箱用户    

    for user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in r_session.smembers('users')]):
        user_info = json.loads(user.decode('utf-8'))
        if not user_info.get('active'): continue
        user_name = user_info.get('username')
        account_keys = ['account:%s:%s' % (user_name, user_id.decode('utf-8')) for user_id in r_session.smembers('accounts:%s' % user_name)]
        if len(account_keys) == 0: continue
        for acc in r_session.mget(*account_keys):
            acc_info = json.loads(acc.decode('utf-8'))
            if not (acc_info.get('active')): continue
            s_id = acc_info.get('session_id')
            u_id = acc_info.get('user_id')
            cookies = json.dumps(dict(sessionid=s_id, userid=u_id))
            if user_info.get('auto_collect'): collect_accounts.append(cookies)
            if user_info.get('auto_drawcash'): cash_accounts.append(cookies)
            if user_info.get('auto_giftbox'): giftbox_accounts.append(cookies)
            if user_info.get('auto_cashbox'): cashbox_accounts.append(cookies)            
    # 自动收取
    r_session.delete('global:auto.collect.cookies')
    r_session.sadd('global:auto.collect.cookies', *collect_accounts)
    # 自动提现
    r_session.delete('global:auto.drawcash.cookies')
    r_session.sadd('global:auto.drawcash.cookies', *cash_accounts)
    # 开免费宝箱
    r_session.delete('global:auto.giftbox.cookies')
    r_session.sadd('global:auto.giftbox.cookies', *giftbox_accounts)
    # 开收费宝箱
    r_session.delete('global:auto.cashbox.cookies')
    r_session.sadd('global:auto.cashbox.cookies', *cashbox_accounts)
    
# 收集水晶
def background_collect_crystal():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'background_collect_crystal()')
    for cookie in r_session.smembers('global:auto.collect.cookies'):
        prc_background_collect(json.loads(cookie.decode('utf-8')))

# 自动开免费宝箱
def background_exec_auto_giftbox():
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'exec_auto_giftbox()')
    for cookie in r_session.smembers('global:auto.giftbox.cookies'):
        prc_background_giftbox(json.loads(cookie.decode('utf-8')))

# 自动开收费宝箱
def background_exec_auto_cashbox():
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'exec_auto_cashbox()')
    for cookie in r_session.smembers('global:auto.cashbox.cookies'):
        prc_background_cashbox(json.loads(cookie.decode('utf-8')))

# 自动提现
def background_exec_auto_drawcash():
    if DEBUG_MODE: print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'exec_auto_drawcash()')    
    #周二才能提现，weekday()返回0－6，0表示周1；isoweekday返回1-7，7代表星期天
    time_now = datetime.now()
    if int(time_now.isoweekday()) != 2:        
        return dict(r='0', rd='提现开放时间为每周二11:00-18:00(国家法定节假日除外)')
    #11:00 - 18:00才能提现
    time_hour = time_now.hour
    if int(time_hour) < 11 or int(time_hour) > 18: 
        return dict(r='0', rd='提现开放时间为每周二11:00-18:00(国家法定节假日除外)')

    for cookie in r_session.smembers('global:auto.drawcash.cookies'):
        prc_background_drawcash(json.loads(cookie.decode('utf-8')))
 
# 计时器函数，定期执行某个线程，时间单位为秒
def timer(func, seconds):
    while True:
        Process(target=func).start()
        time.sleep(seconds)

if __name__ == '__main__':
    # 刷新数据库中选择了自动任务的用户，单位为秒，默认间隔为5分钟
    # 每5分钟检测一次
    threading.Thread(target=timer, args=(background_update_auto_task_users, 5*60)).start()    
    # 刷新浏览器在线用户数据，单位为秒，默认为5秒。
    # 每15秒刷新一次在线用户数据
    threading.Thread(target=timer, args=(background_refresh_online_user_data, 15)).start()
    # 刷新离线用户数据，单位为秒，默认为30秒。
    # 每分钟刷新离线用户数据（函数内已限制该进程必须在分钟大于50以后才会运行）
    threading.Thread(target=timer, args=(background_refresh_offline_user_data, 60)).start()
    # 从在线用户列表中清除已离线的用户，单位为秒，默认为60秒。
    # 每30秒检测离线用户
    threading.Thread(target=timer, args=(background_remove_offline_user, 30)).start()
    # 收集水晶时间，单位为秒，默认为30秒。
    # 每6小时检测一次水晶收集
    threading.Thread(target=timer, args=(background_collect_crystal, 6*60*60)).start()
    # 执行自动提现函数，默认为10分钟
    # 每半小时检测一次
    threading.Thread(target=timer, args=(background_exec_auto_drawcash, 30*60)).start()
    # 执行自动开免费宝箱的函数，默认为45分钟
    # 每45分钟检测一次
    threading.Thread(target=timer, args=(background_exec_auto_giftbox, 45*60)).start()
    # 执行自动开收费宝箱的函数，默认为40分钟
    # 每45分钟检测一次
    threading.Thread(target=timer, args=(background_exec_auto_cashbox, 40*60)).start()    
    while True:
        time.sleep(1)

__author__ = 'powergx'
import requests
import random
import json
from util import md5
from base64 import b64encode
from urllib.parse import unquote, urlencode


def StrToInt(str):
    bigInteger = 0

    for char in str:
        bigInteger <<= 8
        bigInteger += ord(char)

    return bigInteger


def pow_mod(x, y, z):
    "Calculate (x ** y) % z efficiently."
    number = 1
    while y:
        if y & 1:
            number = number * x % z
        y >>= 1
        x = x * x % z
    return number


def old_login(username, md5_password):
    from api import agent_header
    exponent = int("010001", 16)
    modulus = int("AC69F5CCC8BDE47CD3D371603748378C9CFAD2938A6B021E0E191013975AD683F5CBF9ADE8BD7D46B4D2EC2D78A"
                  "F146F1DD2D50DC51446BB8880B8CE88D476694DFC60594393BEEFAA16F5DBCEBE22F89D640F5336E42F587DC4AF"
                  "EDEFEAC36CF007009CCCE5C1ACB4FF06FBA69802A8085C2C54BADD0597FC83E6870F1E36FD", 16)

    param = '{"cmdID":1,"isCompressed":0,"rsaKey":{"n":"AC69F5CCC8BDE47CD3D371603748378C9CFAD2938A6B0' \
            '21E0E191013975AD683F5CBF9ADE8BD7D46B4D2EC2D78AF146F1DD2D50DC51446BB8880B8CE88D476694DFC60594393BEEFAA16F' \
            '5DBCEBE22F89D640F5336E42F587DC4AFEDEFEAC36CF007009CCCE5C1ACB4FF06FBA69802A8085C2C54BADD0597FC83E6870F1E3' \
            '6FD","e":"010001"},"businessType":%s,"passWord":"%s","loginType":0,"platformVersion":1,' \
            '"devicesign":"div100.47aae552e03ee18cec310a66d92f08aa5b387c45c8389cce95bda8a09b2d2ab7",' \
            '"sdkVersion":177588,"protocolVersion":%s,"userName":"%s","extensionList":"","sequenceNo":%s,' \
            '"peerID":"%s","clientVersion":"1.0.0","appName":"ANDROID-com.xunlei.redcrystalandroid"}'

    hash_password = hex(pow_mod(StrToInt(md5_password), exponent, modulus))[2:].upper().zfill(256)

    _chars = "0123456789ABCDEF"

    peer_id = ''.join(random.sample(_chars, 16))

    param = param % (61, hash_password, 108, username, 1000003, peer_id)

    r = requests.post('https://login.mobile.reg2t.sandai.net', data=param, headers=agent_header, verify=False)

    login_status = json.loads(r.text)

    if login_status.get('errorCode') == 0:
        return login_status

    exponent = int("010001", 16)
    modulus = int("D6F1CFBF4D9F70710527E1B1911635460B1FF9AB7C202294D04A6F135A906E90E2398123C234340A3CEA0E5EFDC"
                  "B4BCF7C613A5A52B96F59871D8AB9D240ABD4481CCFD758EC3F2FDD54A1D4D56BFFD5C4A95810A8CA25E87FDC75"
                  "2EFA047DF4710C7D67CA025A2DC3EA59B09A9F2E3A41D4A7EFBB31C738B35FFAAA5C6F4E6F", 16)

    param = '{"cmdID":1,"isCompressed":0,"rsaKey":{"n":"D6F1CFBF4D9F70710527E1B1911635460B1FF9AB7C202' \
            '294D04A6F135A906E90E2398123C234340A3CEA0E5EFDCB4BCF7C613A5A52B96F59871D8AB9D240ABD4481CCFD758EC3F2FDD54A' \
            '1D4D56BFFD5C4A95810A8CA25E87FDC752EFA047DF4710C7D67CA025A2DC3EA59B09A9F2E3A41D4A7EFBB31C738B35FFAAA5C6F4' \
            'E6F","e":"010001"},"businessType":%s,"passWord":"%s","loginType":0,"platformVersion":1,' \
            '"verifyKey":"","sessionID":"","protocolVersion":%s,"userName":"%s","extensionList":"",' \
            '"sequenceNo":%s,"peerID":"%s","clientVersion":"1.0.0","appName":"ANDROID-com.xunlei.redcrystalandroid"}'

    hash_password = hex(pow_mod(StrToInt(md5_password), exponent, modulus))[2:].upper().zfill(256)

    _chars = "0123456789ABCDEF"

    peer_id = ''.join(random.sample(_chars, 16))

    param = param % (61, hash_password, 101, username, 10000015, peer_id)

    r = requests.post('https://login.mobile.reg2t.sandai.net', data=param, headers=agent_header, verify=False)

    login_status = json.loads(r.text)

    return login_status

def login(username, md5_password, encrypt_pwd_url=None):
    if encrypt_pwd_url is None or encrypt_pwd_url == '':
        return old_login(username, md5_password)

    xunlei_domain = 'login.xunlei.com'
    s = requests.Session()
    r = s.get('http://%s/check/?u=%s&v=100' % (xunlei_domain, username))
    if r.cookies.get('check_n') is None:
        xunlei_domain = 'login2.xunlei.com'
        r = s.get('http://%s/check/?u=%s&v=100' % (xunlei_domain, username))

    if r.cookies.get('check_n') is None:
        return old_login(username, md5_password)
    check_n = unquote(r.cookies.get('check_n'))
    check_e = unquote(r.cookies.get('check_e'))
    check_result = unquote(r.cookies.get('check_result'))

    need_captcha = check_result.split(':')[0]
    if need_captcha == '1':
        return old_login(username, md5_password)
    captcha = check_result.split(':')[1].upper()

    params = dict(password=md5_password, captcha=captcha, check_n=check_n, check_e=check_e)
    urlencode(params)
    r = requests.get(encrypt_pwd_url + '?' + urlencode(params))
    e_pwd = r.text
    if r.text == 'false':
        return old_login(username, md5_password)

    data = dict(business_type='100', login_enable='0', verifycode=captcha, v='100', e=check_e, n=check_n, u=username,
                p=e_pwd)
    r = s.post('http://%s/sec2login/' % xunlei_domain, data=data)

    cookies = r.cookies.get_dict()
    if len(cookies) < 5:
        return old_login(username, md5_password)

    return dict(errorCode=0, sessionID=cookies.get('sessionid'), nickName=cookies.get('usernick'),
                userName=cookies.get('usrname'), userID=cookies.get('userid'), userNewNo=cookies.get('usernewno'))

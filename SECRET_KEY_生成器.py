from random import Random
import time

SECRETKEY = ''

# 生成KEY,随机
def write_key():
    SECRETKEY = random_key()
    print('本次SECRET_KEY为随机生成,生成内容绝不重复:')
    print('')
    print('SECRET_KEY=%s' % (SECRETKEY))
    print('')
    print('')
    print('')
    print('')
    print('复制SECRET_KEY替换到config.py [SECRET_KEY],重启服务器即可')

# 生成FLSAK SECRET_KEY
def random_key():
    key_all = []
    key_all = ''
    key_all+=random_str(8)
    key_all+='-'+random_str(4)
    key_all+='-'+random_str(4)
    key_all+='-'+random_str(4)
    key_all+='-'+random_str(12)
    return key_all

# 生成密钥
def random_str(randomlength):
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(randomlength):
        str+=chars[random.randint(0, length)]
    return str

if __name__ == '__main__':
    write_key()
    while True:
        time.sleep(1)
#! /usr/bin/env python3.4
# -*- coding: utf-8 -*-
# config.py - configration for crysadm web and redis server
__author__ = 'powergx'

# Redis服务器配置
class RedisConfig():
    def __init__(self, host, port, db, password=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password

# Crysadm 配置
class Config(object):
    DEBUG = False  #测试模式
    TESTING = False  #测试模式
    DATABASE_URI = ''  #数据库链接
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}  #允许的后缀名
    SESSION_TYPE = 'memcached'  #缓存类型
    SECRET_KEY = '7e30485a-dd01-11e4-8abd-10ddb199c373'  #安全密钥
    REDIS_CONF = RedisConfig(host='127.0.0.1', port=6379, db=0)  #Redis服务器配置
    PASSWORD_PREFIX = "08b3db21-d120-11e4-9ttd-10ddb199c373"  #密码前缀
    ENCRYPT_PWD_URL = None  #模式
    SERVER_IP = '0.0.0.0'  #服务器IP
    SERVER_PORT =5000   #端口

# 正常运行时配置
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

# 开发者配置模式
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

# 测试模式
class TestingConfig(Config):
    DEBUG = True
    TESTING = True
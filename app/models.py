# -*- coding: utf-8 -*-
from flask import current_app
from flask.ext.login import UserMixin
from flask_security.utils import encrypt_password, verify_password

from app import db


class BaseUser(UserMixin):
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = encrypt_password(password)

    def verify_password(self, password):
        return verify_password(password, self.password_hash)


class User(BaseUser, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode(20), unique=True, nullable=False)
    password_hash = db.Column('password', db.String(120), nullable=False)
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)
    email = db.Column(db.String(64), nullable=False)
    created = db.Column(db.Integer, nullable=False)


class Producer(BaseUser, db.Model):
    __tablename__ = 'producers'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 哈希后的密码
    password_hash = db.Column('password', db.String(120), nullable=False)
    # 用于登录的手机号码
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)
    # 邮箱
    email = db.Column(db.String(64), nullable=False)
    # 注册时间
    created = db.Column(db.Integer, nullable=False)
    # 法人真实姓名
    legal_person_name = db.Column(db.Unicode(10), nullable=False)
    # 法人身份证号码
    legal_person_identity = db.Column(db.CHAR(18), nullable=False)
    # 品牌厂家名称
    name = db.Column(db.Unicode(30), unique=True, nullable=False)
    # 营业执照所在地
    license_address = db.Column(db.Unicode(30), nullable=False)
    # 营业执照期限
    license_limit = db.Column(db.Integer, nullable=False)
    # 长期印业执照
    license_long_time_limit = db.Column(db.Boolean, default=False, nullable=False)
    # 营业执照副本扫描件
    license_image = db.Column(db.String(255), nullable=False)
    # 省份 id
    province_id = db.Column(db.Integer, nullable=False)
    # 城市 id
    city_id = db.Column(db.Integer, nullable=False)
    # 区域 id
    district_id = db.Column(db.Integer, nullable=False)
    # 详细地址
    address = db.Column(db.Unicode(30), nullable=False)
    # 联系手机
    contact_mobile = db.Column(db.CHAR(11), nullable=False)
    # 联系电话
    contact_telephone = db.Column(db.CHAR(15), nullable=False)
    

class Dealer(BaseUser, db.Model):
    __tablename__ = 'dealers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode(20), unique=True, nullable=False)
    password_hash = db.Column('password', db.String(120), nullable=False)
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)
    email = db.Column(db.String(64), nullable=False)
    created = db.Column(db.Integer, nullable=False)


class Privilege(BaseUser, db.Model):
    __tablename__ = 'privileges'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), nullable=False, unique=True)
    password_hash = db.Column('password', db.String(120), nullable=False)


class Province(db.Model):
    __tablename__ = 'provinces'
    id = db.Column(db.Integer, primary_key=True)
    province = db.Column(db.Unicode(10), nullable=False)


class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.Unicode(10), nullable=False)
    province_id = db.Column(db.Integer, nullable=False)


class District(db.Model):
    __tablename__ = 'districts'
    id = db.Column(db.Integer, primary_key=True)
    district = db.Column(db.Unicode(10), nullable=False)
    city_id = db.Column(db.Integer, nullable=False)
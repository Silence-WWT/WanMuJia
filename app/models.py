# -*- coding: utf-8 -*-
import hashlib
import json
import os
import shutil
import time
import re
import random

from flask import current_app
from flask.ext.login import UserMixin
from flask.ext.cdn import url_for
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.constants import *
from app.utils.redis import redis_get, redis_set
from app.permission import privilege_id_prefix, vendor_id_prefix, distributor_id_prefix, user_id_prefix


class Property(object):
    """
    This class is used to flush property attributes.

    class UserAddress(db.Model):
        # other attributes
        user_id = db.Column(db.Integer)

    class User(db.Model, Property):
        # other attributes

        _flush = {'address': lambda x: UserAddress.query.filter_by(user_id=x.id).first()}

        @property
        def address(self):
            return self.get_or_flush('address')

    If sometime user._address is inconsistent with database
    user.flush('address')
    """

    _flush = {}

    def flush(self, *attrs):
        for attr in attrs:
            setattr(self, '_%s' % attr, self._flush[attr](self))

    def get_or_flush(self, attr):
        real_attr = '_%s' % attr
        if getattr(self, real_attr, None) is None:
            self.flush(attr)
        return getattr(self, real_attr, None)


class BaseUser(UserMixin):
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 哈希后的密码
    password_hash = db.Column('password', db.String(128), nullable=False)
    # 手机号码
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)
    # 邮箱
    email = db.Column(db.String(64), unique=True, nullable=False)
    # 邮箱是否已验证
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    # 注册时间
    created = db.Column(db.Integer, default=time.time, nullable=False)

    id_prefix = ''
    REMINDS = None

    def __init__(self, password, mobile, email):
        self.password = password
        self.mobile = mobile
        self.email = email

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return u'%s%s' % (self.id_prefix, self.id)

    @property
    def reminds(self):
        reminds = redis_get(self.REMINDS, self.id)
        if reminds:
            reminds = json.loads(reminds)
        else:
            reminds = {}
        return reminds


class User(BaseUser, db.Model):
    __tablename__ = 'users'
    # 手机号码
    mobile = db.Column(db.CHAR(11), nullable=False)
    # 邮箱
    email = db.Column(db.String(64), nullable=False)
    # 用户名
    username = db.Column(db.Unicode(30), nullable=False)
    # 用户名可修改
    username_revisable = db.Column(db.Boolean, default=True, nullable=False)

    id_prefix = user_id_prefix

    def __init__(self, password, mobile, email):
        super(User, self).__init__(password, mobile, email)
        self.username = self.generate_username()

    def item_collected(self, item_id):
        return Collection.query.filter_by(user_id=self.id, item_id=item_id).first() is not None

    @staticmethod
    def generate_fake():
        from faker import Factory
        zh_fake = Factory.create('zh-CN')
        fake = Factory.create()
        for i in range(100):
            user = User('14e1b600b1fd579f47433b88e8d85291', zh_fake.phone_number(), fake.email())
            db.session.add(user)
        db.session.commit()

    @staticmethod
    def generate_username():
        prefix = u'wmj'
        chars = 'ABCDEFGHIJKLMNPQRSTUVWXYZ123456789'
        for i in range(5):
            l = []
            md5 = hashlib.md5(str(time.time()).encode()).hexdigest()
            l.extend([random.SystemRandom().choice(md5) for _ in range(6)])
            l.extend([random.SystemRandom().choice(chars) for _ in range(4)])
            username = prefix + ''.join(l)
            if not User.query.filter_by(username=username).first():
                return username


class Collection(db.Model, Property):
    __tablename__ = 'collections'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 用户id
    user_id = db.Column(db.Integer, nullable=False, index=True)
    # 商品id
    item_id = db.Column(db.Integer, nullable=False, index=True)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)

    _flush = {
        'item': lambda x: Item.query.get(x.item_id)
    }
    _item = None

    def __init__(self, user_id, item_id):
        self.user_id = user_id
        self.item_id = item_id

    @property
    def item(self):
        return self.get_or_flush('item')


class GuideSMS(db.Model, Property):
    __tablename__ = 'guide_sms'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 用户 id
    user_id = db.Column(db.Integer, nullable=False)
    # 经销商 id
    distributor_id = db.Column(db.Integer, nullable=False)
    # 商品 id
    item_id = db.Column(db.Integer, nullable=False)
    # 手机号码
    mobile = db.Column(db.CHAR(11), nullable=False)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)

    _flush = {
        'item': lambda x: Item.query.get(x.item_id),
        'distributor': lambda x: Distributor.query.get(x.distributor_id)
    }
    _item = None
    _distributor = None

    def __init__(self, mobile, item_id, distributor_id, user_id=0):
        self.mobile = mobile
        self.item_id = item_id
        self.distributor_id = distributor_id
        self.user_id = user_id

    @property
    def item(self):
        return self.get_or_flush('item')

    @property
    def distributor(self):
        return self.get_or_flush('distributor')


class Order(db.Model):
    __tablename__ = 'orders'
    # id
    id = db.Column(db.Integer, primary_key=True)
    # 用户id
    user_id = db.Column(db.Integer, nullable=False)
    # 用户收货地址id
    user_address_id = db.Column(db.Integer, nullable=False)
    # 商家id
    distributor_id = db.Column(db.Integer, nullable=False)
    # 商品id
    item_id = db.Column(db.Integer, nullable=False)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 定金
    deposit = db.Column(db.Integer, nullable=False)
    # 定金已支付
    deposit_payed = db.Column(db.Boolean, default=False, nullable=False)
    # 价格
    price = db.Column(db.Integer, nullable=False)
    # 钱款已支付
    price_payed = db.Column(db.Boolean, default=False, nullable=False)


class Vendor(BaseUser, db.Model, Property):
    __tablename__ = 'vendors'
    # 邮箱
    email = db.Column(db.String(64), nullable=False)
    # logo图片
    logo = db.Column(db.String(255), default='', nullable=False)
    # 法人真实姓名
    agent_name = db.Column(db.Unicode(10), nullable=False)
    # 法人身份证号码
    agent_identity = db.Column(db.CHAR(18), nullable=False)
    # 法人身份证正面图片
    agent_identity_front = db.Column(db.String(255), default='', nullable=False)
    # 法人身份证反面图片
    agent_identity_back = db.Column(db.String(255), default='', nullable=False)
    # 厂家名
    name = db.Column(db.Unicode(30), nullable=False)
    # 品牌名
    brand = db.Column(db.Unicode(10), default='', nullable=False)
    # 营业执照期限
    license_limit = db.Column(db.CHAR(10), default='2035/07/19', nullable=False)
    # 营业执照副本扫描件
    license_image = db.Column(db.String(255), default='', nullable=False)
    # 联系人
    contact = db.Column(db.String(30), default=u'', nullable=False)
    # 联系电话
    telephone = db.Column(db.CHAR(15), nullable=False)
    # 简介
    introduction = db.Column(db.Unicode(30), default=u'', nullable=False)
    # 已通过审核
    confirmed = db.Column(db.Boolean, default=False, nullable=False)
    # 审核通过时间
    confirmed_time = db.Column(db.Integer, default=0, nullable=False)
    # 审核信息
    reject_message = db.Column(db.Unicode(100), default=u'', nullable=False)
    # 审核已回绝
    rejected = db.Column(db.Boolean, default=False, nullable=False)
    # 已初始化账号
    initialized = db.Column(db.Boolean, default=True, nullable=False)
    # 商品上传权限
    item_permission = db.Column(db.Boolean, default=False, nullable=False)

    id_prefix = vendor_id_prefix
    REMINDS = VENDOR_REMINDS

    _flush = {
        'address': lambda x: VendorAddress.query.filter_by(vendor_id=x.id).limit(1).first(),
        'logo': lambda x: url_for('static', filename=x.logo) if x.logo else '',
        'info_completed': lambda x: x.agent_name and x.agent_identity and x.agent_identity_front and \
        x.agent_identity_back and x.name and x.license_limit and x.license_image and x.telephone and x.address and \
        x.address.cn_id and x.address.address
    }
    _logo = None
    _address = None
    _info_completed = None

    def __init__(self, password, mobile, email, agent_name, agent_identity, name, license_limit, telephone, brand):
        super(Vendor, self).__init__(password, mobile, email)
        self.agent_name = agent_name
        self.agent_identity = agent_identity
        self.name = name
        self.license_limit = license_limit
        self.telephone = telephone
        self.brand = brand

    @property
    def address(self):
        return self.get_or_flush('address')

    @property
    def logo_url(self):
        return self.get_or_flush('logo')

    @property
    def statistic(self):
        return {
            'items': Item.query.filter_by(vendor_id=self.id, is_deleted=False, is_component=False).count(),
            'distributors': Distributor.query.filter_by(vendor_id=self.id, is_revoked=False).count()
        }

    @property
    def info_completed(self):
        if self._info_completed is None:
            self.flush('info_completed')
        return self._info_completed

    def push_confirm_reminds(self, remind_type, message=''):
        link = None
        if remind_type == VENDOR_REMINDS_SUCCESS:
            message = '您的认证信息已通过审核, 快来上传商品吧!'
            status = 'success'
        elif remind_type == VENDOR_REMINDS_PENDING:
            message = '您的认证信息将在3个工作日内审核'
            status = 'warning'
        elif remind_type == VENDOR_REMINDS_COMPLETE:
            status = 'danger'
            message = '请完善您的认证信息'
            link = {'text': '认证信息链接', 'href': '/vendor/reconfirm'}
        else:
            status = 'danger'
            message = '您的认证信息尚未能通过审核 %s' % message
            link = {'text': '重新填写', 'href': '/vendor/reconfirm'}
        reminds = {'confirm': [{'message': message, 'type': status, 'link': link}]}
        redis_set(self.REMINDS, self.id, json.dumps(reminds), 3600 * 24 * 3)

    @staticmethod
    def generate_fake(num=100):
        from faker import Factory
        from random import randint
        zh_fake = Factory.create('zh-CN')
        fake = Factory.create()
        vendors = []
        for i in range(num):
            vendor = Vendor(
                "14e1b600b1fd579f47433b88e8d85291", zh_fake.phone_number(), fake.email(), zh_fake.name(),
                zh_fake.random_number(18), '%s%s' % (zh_fake.company(), zh_fake.random_number(3)),
                zh_fake.random_number(2), zh_fake.phone_number(), zh_fake.name())
            vendor.confirmed = True if randint(0, 100) % 2 else False
            db.session.add(vendor)
            vendors.append(vendor)
        db.session.commit()
        districts = Area.query.filter(Area.level == 3).all()
        for vendor in vendors:
            vendor_address = VendorAddress(vendor.id, districts[randint(0, len(districts))].cn_id, zh_fake.address())
            db.session.add(vendor_address)
        db.session.commit()

    @staticmethod
    def generate_account(num):
        import hashlib
        import random
        vendors = []
        for i in range(num):
            password = ''.join([random.SystemRandom().choice('ABCDEFG1234567890') for _ in range(8)])
            password_hash = hashlib.md5(hashlib.md5(password.encode()).hexdigest().encode()).hexdigest()
            mobile = 'WMJ%s' % random.randint(10000000, 99999999)
            if Vendor.query.filter_by(mobile=mobile).first():
                continue
            vendors.append((mobile, password))
            vendor = Vendor(password_hash, mobile, '', '', '', '', '', '', '')
            vendor.initialized = False
            vendor.item_permission = True
            db.session.add(vendor)
            db.session.commit()
            vendor_address = VendorAddress(vendor.id, 0, '')
            db.session.add(vendor_address)
            db.session.commit()
        with open('vendor_accounts.txt', 'a') as f:
            for account in vendors:
                f.write('%s %s\n' % account)


class Distributor(BaseUser, db.Model, Property):
    __tablename__ = 'distributors'
    # 登录名
    username = db.Column(db.Unicode(20), nullable=False)
    # 生产商 id
    vendor_id = db.Column(db.Integer, nullable=False, index=True)
    # 商家名称
    name = db.Column(db.Unicode(30), nullable=False)
    # 联系电话
    contact_telephone = db.Column(db.String(30), default='', nullable=False)
    # 联系手机
    contact_mobile = db.Column(db.CHAR(11), default='', nullable=False)
    # 联系人
    contact = db.Column(db.Unicode(10), nullable=False)
    # 400分机号码
    ext_number = db.Column(db.CHAR(10), default='', nullable=False)
    # 已解约
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    # 手机号码
    mobile = None
    # 邮箱
    email = db.Column(db.String(64), default='', nullable=False)

    id_prefix = distributor_id_prefix
    REMINDS = DISTRIBUTOR_REMINDS

    _flush = {
        'vendor': lambda x: Vendor.query.get(x.vendor_id),
        'address': lambda x: DistributorAddress.query.filter_by(distributor_id=x.id).limit(1).first(),
        'revocation': lambda x: DistributorRevocation.query.filter_by(distributor_id=x.id).first()
    }
    _vendor = None
    _address = None
    _revocation = None

    def __init__(self, username, password, vendor_id, name, contact_mobile, contact_telephone, contact):
        super(Distributor, self).__init__(password, mobile='', email='')
        self.username = username
        self.vendor_id = vendor_id
        self.name = name
        self.contact_telephone = contact_telephone
        self.contact_mobile = contact_mobile
        self.contact = contact

    @property
    def vendor(self):
        return self.get_or_flush('vendor')

    @property
    def address(self):
        return self.get_or_flush('address')

    @property
    def revocation(self):
        return self.get_or_flush('revocation')

    @property
    def revocation_state(self):
        revocation = self.revocation
        if not revocation:
            return ''
        elif revocation.pending:
            return 'pending'
        elif revocation.is_revoked:
            return 'revoked'
        else:
            return 'rejected'

    def push_register_reminds(self):
        status = 'warning'
        message = '请牢记您的登录用户名: %s' % self.username
        reminds = {'confirm': [{'message': message, 'type': status, 'link': None}]}
        redis_set(self.REMINDS, self.id, json.dumps(reminds), 3600 * 24 * 3)

    @staticmethod
    def generate_username():
        from random import randint
        for i in range(10):
            username = randint(10000000, 99999999)
            if not Distributor.query.filter_by(username=username).limit(1).first():
                return username
        return False

    @staticmethod
    def add_ext_number():
        ext_numbers = (('君德益', 1245),  ('君德益四季青店', 1246),  ('劲飞红木第一楼西四环店', 1247),  ('劲飞红木西三环红木街精品店', 1248),  ('劲飞红木第一楼北四环店', 1249),  ('劲飞红木第一楼天通苑店', 1250),  ('劲飞红木第一楼东四环店', 1251),  ('东成红木广东惠州专卖店', 1252),  ('东成红木江苏南京专卖店', 1253),  ('东成红木江西赣州专卖店', 1254),  ('东成红木湖南株洲专卖店', 1255),  ('东成红木河北石家庄专卖店', 1256),  ('东成红木青海西宁专卖店', 1257),  ('东成红木北京专卖店', 1258),  ('东成红木吉林长春专卖店', 1259),  ('东成红木河北香河专卖店', 1260),  ('东成红木江苏宜兴专卖店', 1261),  ('东成红木云南玉溪专卖店', 1262),  ('东成红木广东廉江专卖店', 1263),  ('东成红木广州从化专卖店', 1264),  ('东成红木山东济南专卖店', 1265),  ('东成红木四川成都专卖店', 1266),  ('东成红木新疆乌鲁木齐专卖店', 1267),  ('东成红木广州天河专卖店', 1268),  ('东成红木广州番禺专卖店', 1269),  ('东成红木广州增城专卖店', 1270),  ('东成红木天津溏沽专卖店', 1271),  ('东成红木西安市阎良区专卖店', 1272),  ('东成红木西安临潼专卖店', 1273),  ('东成红木四川省乐山专卖店', 1274),  ('东成红木江苏江阴专卖店', 1275),  ('东成红木重庆梁平专卖店', 1276),  ('东成红木山东德州专卖店', 1277),  ('东成红木广东汕头专卖店', 1278),  ('东成红木广东珠海专卖店', 1279),  ('东成红木甘肃兰州专卖店', 1280),  ('东成红木常德专卖店', 1281),  ('东成红木唐山专卖店', 1282),  ('东成红木唐山曹妃甸店', 1283))
        for name, ext_number in ext_numbers:
            distributor = Distributor.query.filter_by(name=name).first()
            if distributor:
                distributor.ext_number = ext_number
            else:
                print(name, ext_number)
        db.session.commit()

    @staticmethod
    def generate_fake():
        from faker import Factory
        from random import randint
        from app.tasks import distributor_geo_coding
        zh_fake = Factory.create('zh-CN')
        beijing_address = ['清华大学', '北京大学', '中国人民大学', '北京交通大学', '后海公园', '圆明园', '天安门', '天坛', '北海公园', '地坛', '三里屯', '工人体育场', '国贸中心', '北京妇产医院', '宁夏大厦', '江苏大厦', '协和医院', '王府井', '全聚德', '宣武医院']
        for i in range(20):
            distributor = Distributor(
                randint(10000000, 99999999) , '14e1b600b1fd579f47433b88e8d85291', 1, beijing_address[i],
                zh_fake.phone_number(), zh_fake.phone_number(), zh_fake.name())
            db.session.add(distributor)
            db.session.commit()
            distributor_address = DistributorAddress(distributor_id=distributor.id, cn_id=110101, address=beijing_address[i])
            db.session.add(distributor_address)
            db.session.commit()
            distributor_geo_coding.delay(distributor.id, distributor_address.id)


class DistributorRevocation(db.Model, Property):
    __tablename__ = 'distributor_revocations'
    id = db.Column(db.Integer, primary_key=True)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 商家id
    distributor_id = db.Column(db.Integer, nullable=False)
    # 解约合同照片
    contract = db.Column(db.String(255), default='', nullable=False)
    # 待审核
    pending = db.Column(db.Boolean, default=True, nullable=False)
    # 已解约
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, distributor_id, contract):
        self.distributor_id = distributor_id
        self.contract = contract

    _flush = {
        'distributor': lambda x: Distributor.query.get(x.distributor_id)
    }
    _distributor = None

    @property
    def distributor(self):
        return self.get_or_flush('distributor')


class Item(db.Model, Property):
    __tablename__ = 'items'
    # 商品id
    id = db.Column(db.Integer, primary_key=True)
    # 创建时间
    created = db.Column(db.Integer, default=time.time, nullable=False)
    # 厂家id
    vendor_id = db.Column(db.Integer, nullable=False, index=True)
    # 商品名称
    item = db.Column(db.Unicode(20), nullable=False)
    # 指导价格
    price = db.Column(db.Integer, nullable=False)
    # 二级材料 id
    second_material_id = db.Column(db.Integer, nullable=False, index=True)
    # 商品分类id
    category_id = db.Column(db.Integer, nullable=False, index=True)
    # 长度 cm
    length = db.Column(db.String(10), nullable=False)
    # 宽度 cm
    width = db.Column(db.String(10), nullable=False)
    # 高度 cm
    height = db.Column(db.String(10), nullable=False)
    # 适用面积 m^2
    area = db.Column(db.String(10), nullable=False)
    # 烘干 id
    stove_id = db.Column(db.Integer, nullable=False)
    # 打磨砂纸 id
    outside_sand_id = db.Column(db.Integer, nullable=False)
    inside_sand_id = db.Column(db.Integer, nullable=False)
    # 涂饰 id
    paint_id = db.Column(db.Integer, nullable=False)
    # 装饰 id
    decoration_id = db.Column(db.Integer, nullable=False)
    # 二级场景 id
    scene_id = db.Column(db.Integer, nullable=False, index=True)
    # 风格 id
    style_id = db.Column(db.Integer, default=5, nullable=False, index=True)
    # 雕刻方式
    carve_type_id = db.Column(db.Integer, default=1, nullable=False)
    # 产品寓意
    story = db.Column(db.Unicode(5000), default=u'', nullable=False)
    # 已删除
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    # 套件id
    suite_id = db.Column(db.Integer, nullable=False)
    # 数量
    amount = db.Column(db.Integer, nullable=False)
    # 套件
    is_suite = db.Column(db.Boolean, default=False, nullable=False)
    # 组件
    is_component = db.Column(db.Boolean, default=False, nullable=False, index=True)

    _flush = {
        'vendor': lambda x: Vendor.query.get(x.vendor_id),
        'category': lambda x: [category.category if category is not None else '' for category in
                               (Category.query.get(x.category_id),)][0],
        'images': lambda x: ItemImage.query.filter_by(item_id=x.id, is_deleted=False).order_by(ItemImage.sort,
                                                                                               ItemImage.created),
        'components': lambda x: Item.query.filter_by(suite_id=x.id, is_deleted=False, is_component=True),
        'scene': lambda x: Scene.query.get(x.scene_id).scene,
        'second_material': lambda x: SecondMaterial.query.get(x.second_material_id).second_material,
        'outside_sand': lambda x: Sand.query.get(x.outside_sand_id).sand,
        'inside_sand': lambda x: Sand.query.get(x.inside_sand_id).sand if x.inside_sand_id else '——',
        'stove': lambda x: Stove.query.get(x.stove_id).stove,
        'paint': lambda x: Paint.query.get(x.paint_id).paint,
        'decoration': lambda x: Decoration.query.get(x.decoration_id).decoration,
        'style': lambda x: Style.query.get(x.style_id).style,
        'carve_type': lambda x: CarveType.query.get(x.carve_type_id).carve_type,
        'carve': lambda x: [carve.carve for carve in Carve.query.filter(Carve.id.in_(x.get_carve_id()))],
        'tenon': lambda x: [tenon.tenon for tenon in Tenon.query.filter(Tenon.id.in_(x.get_tenon_id()))]
    }
    _vendor = None
    _category = None
    _images = None
    _components = None
    _scene = None
    _second_material = None
    _outside_sand = None
    _inside_sand = None
    _stove = None
    _paint = None
    _decoration = None
    _style = None
    _carve_type = None
    _carve = None
    _tenon = None

    def __init__(self, vendor_id, item, price, second_material_id, category_id, scene_id, length, width, height, area,
                 stove_id, outside_sand_id, inside_sand_id, paint_id, decoration_id, style_id, carve_type_id, story,
                 suite_id, amount, is_suite, is_component):
        self.vendor_id = vendor_id
        self.item = item
        self.price = price
        self.second_material_id = second_material_id
        self.category_id = category_id
        self.scene_id = scene_id
        self.length = length
        self.width = width
        self.height = height
        self.area = area
        self.stove_id = stove_id
        self.outside_sand_id = outside_sand_id
        self.inside_sand_id = inside_sand_id
        self.paint_id = paint_id
        self.decoration_id = decoration_id
        self.style_id = style_id
        self.carve_type_id = carve_type_id
        self.story = story
        self.suite_id = suite_id
        self.amount = amount
        self.is_suite = is_suite
        self.is_component = is_component

    def stock_count(self):
        return sum([stock.stock for stock in Stock.query.filter(Stock.item_id == self.id, Stock.stock > 0)])

    def get_tenon_id(self):
        return [item_tenon.tenon_id for item_tenon in ItemTenon.query.filter_by(item_id=self.id)]

    def get_carve_id(self):
        return [item_carve.carve_id for item_carve in ItemCarve.query.filter_by(item_id=self.id)]

    def in_stock_distributors(self):
        distributors = db.session.query(Distributor).filter(Stock.item_id == self.id,
                                                            Stock.distributor_id == Distributor.id,
                                                            Stock.stock > 0,
                                                            Distributor.is_revoked == False)
        return distributors

    @property
    def size(self):
        if self.length and self.width and self.height:
            return '%s * %s * %s' % (self.length, self.width, self.height)
        else:
            return '——'

    @property
    def vendor(self):
        return self.get_or_flush('vendor')

    @property
    def category(self):
        return self.get_or_flush('category')

    @property
    def scene(self):
        return self.get_or_flush('scene')

    @property
    def second_material(self):
        return self.get_or_flush('second_material')

    @property
    def outside_sand(self):
        return self.get_or_flush('outside_sand')

    @property
    def inside_sand(self):
        return self.get_or_flush('inside_sand')

    @property
    def stove(self):
        return self.get_or_flush('stove')

    @property
    def paint(self):
        return self.get_or_flush('paint')

    @property
    def decoration(self):
        return self.get_or_flush('decoration')

    @property
    def style(self):
        return self.get_or_flush('style')

    @property
    def carve(self):
        return self.get_or_flush('carve')

    @property
    def carve_type(self):
        return self.get_or_flush('carve_type')

    @property
    def tenon(self):
        return self.get_or_flush('tenon')

    @property
    def images(self):
        return self.get_or_flush('images')

    @property
    def components(self):
        if self.is_suite:
            return self.get_or_flush('components')
        return []

    def update_suite_amount(self):
        if self.is_suite:
            components = self.components
            self.amount = sum([component.amount for component in components])

    def dumps(self):
        data = {}
        if not self.is_suite and not self.is_component:  # single
            attrs = ('id', 'item', 'price', 'second_material', 'category', 'scene', 'style', 'outside_sand',
                     'inside_sand', 'size', 'area', 'stove', 'paint', 'decoration', 'carve', 'carve_type',
                     'tenon', 'vendor_id', 'is_suite')
            for attr in attrs:
                data[attr] = getattr(self, attr)
            data['brand'] = self.vendor.brand
            data['images'] = [image.url for image in self.images]
        elif self.is_suite:
            attrs = ('id', 'item', 'price', 'second_material', 'scene', 'style', 'outside_sand', 'inside_sand', 'area',
                     'stove', 'carve_type', 'amount', 'vendor_id', 'is_suite')
            for attr in attrs:
                data[attr] = getattr(self, attr)
            component_dumps = []
            for component in self.components:
                component_dumps.append(component.dumps())
            data['components'] = component_dumps
            data['brand'] = self.vendor.brand
            data['images'] = [image.url for image in self.images]
        else:  # component
            attrs = ('item', 'area', 'size', 'category', 'carve', 'tenon', 'paint', 'decoration', 'amount', 'is_component')
            for attr in attrs:
                data[attr] = getattr(self, attr)
        return data

    @staticmethod
    def images_dump():
        for item in Item.query.filter_by(is_deleted=False):
            vendor_dir = os.path.join(current_app.config['IMAGE_DIR'], 'raw_images/%s_%d/' % (item.vendor.brand, item.vendor.id))
            item_dir = os.path.join(vendor_dir, '%s_%d' % (item.item.replace('/', ''), item.id))

            if not os.path.exists(vendor_dir):
                os.mkdir(vendor_dir)
            if not os.path.exists(item_dir):
                os.mkdir(item_dir)
            for image in item.images:
                src_path = os.path.join(current_app.config['IMAGE_DIR'], re.sub('.*(?=images)', '', image.url))
                image_name = image.url.rsplit('/', maxsplit=1)[-1]
                dst_path = os.path.join(item_dir, image_name)
                shutil.copyfile(src_path, dst_path)
            story_path = os.path.join(item_dir, '商品信息.txt')
            with open(story_path, 'w', encoding='utf8') as f:
                f.writelines(['寓意: %s\n' % item.story, '尺寸(cm): %s\n' % item.size, '适用面积(m^2): %s\n' % (item.area if item.area else '——')])

    @staticmethod
    def generate_fake(num=10):
        from faker import Factory
        zh_fake = Factory.create('zh-CN')
        fake = Factory.create()
        second_material_ids = [_.id for _ in SecondMaterial.query]
        category_ids = [_.id for _ in Category.query.filter_by(level=3)]
        scene_ids = [_.id for _ in Scene.query]
        stove_ids = [_.id for _ in Stove.query]
        sand_ids = [_.id for _ in Sand.query]
        paint_ids = [_.id for _ in Paint.query]
        decoration_ids = [_.id for _ in Decoration.query]
        style_ids = [_.id for _ in Style.query]
        tenon_ids = [_.id for _ in Tenon.query]
        carve_ids = [_.id for _ in Carve.query]

        def generate_fake_item():
            for i in range(num):
                item = Item(
                    vendor_id=vendor.id,
                    item=zh_fake.name(),
                    price=random.randint(0, 10000000),
                    second_material_id=random.choice(second_material_ids),
                    category_id=random.choice(category_ids),
                    scene_id=random.choice(scene_ids),
                    length=random.randint(0, 1000),
                    width=random.randint(0, 1000),
                    height=random.randint(0, 1000),
                    area=random.randint(0, 100),
                    stove_id=random.choice(stove_ids),
                    outside_sand_id=random.choice(sand_ids),
                    inside_sand_id=random.choice(sand_ids),
                    paint_id=random.choice(paint_ids),
                    decoration_id=random.choice(decoration_ids),
                    style_id=random.choice(style_ids),
                    story=fake.text(random.randint(10, 100)),
                    suite_id=0,
                    amount=0,
                    is_suite=False,
                    is_component=False
                )
                db.session.add(item)
                db.session.commit()
                generate_fake_attach(item)

        def generate_fake_suite():
            for i in range(num):
                suite = Item(
                    vendor_id=vendor.id,
                    item=zh_fake.name(),
                    price=random.randint(0, 10000000),
                    second_material_id=random.choice(second_material_ids),
                    category_id=0,
                    scene_id=random.choice(scene_ids),
                    length=0,
                    width=0,
                    height=0,
                    area=random.randint(0, 100),
                    stove_id=random.choice(stove_ids),
                    outside_sand_id=random.choice(sand_ids),
                    inside_sand_id=random.choice(sand_ids),
                    paint_id=0,
                    decoration_id=0,
                    style_id=random.choice(style_ids),
                    story=fake.text(random.randint(10, 100)),
                    suite_id=0,
                    amount=1,
                    is_suite=True,
                    is_component=False
                )
                db.session.add(suite)
                db.session.commit()
                generate_fake_component(suite)

        def generate_fake_component(suite):
            for i in range(random.randint(1, 5)):
                component = Item(
                    vendor_id=vendor.id,
                    item=zh_fake.name(),
                    price=0,
                    second_material_id=0,
                    category_id=random.choice(category_ids),
                    scene_id=0,
                    length=random.randint(0, 100),
                    width=random.randint(0, 100),
                    height=random.randint(0, 100),
                    area=random.randint(0, 100),
                    stove_id=0,
                    outside_sand_id=0,
                    inside_sand_id=0,
                    paint_id=random.choice(paint_ids),
                    decoration_id=random.choice(decoration_ids),
                    style_id=0,
                    story='',
                    suite_id=suite.id,
                    amount=random.randint(0, 10),
                    is_suite=False,
                    is_component=True
                )
                db.session.add(component)
                db.session.commit()
                generate_fake_attach(component)

        def generate_fake_attach(item):
            tenon_set = set(tenon_ids[:random.randint(1, len(tenon_ids) / 2 - 1)])
            for tenon_id in tenon_set:
                db.session.add(ItemTenon(item_id=item.id, tenon_id=tenon_id))
            carve_set = set(carve_ids[:random.randint(1, len(carve_ids) / 2 - 1)])
            for carve_id in carve_set:
                db.session.add(ItemCarve(item_id=item.id, carve_id=carve_id))
            db.session.commit()

        for vendor in Vendor.query.all():
            generate_fake_item()
            generate_fake_suite()


class ItemImage(db.Model, Property):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    path = db.Column(db.String(255), nullable=False)
    hash = db.Column(db.String(32), nullable=False)
    sort = db.Column(db.Integer, nullable=False)
    created = db.Column(db.Integer, default=time.time, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    filename = db.Column(db.Unicode(30), nullable=False)

    def __init__(self, item_id, image, image_hash, filename, sort):
        self.item_id = item_id
        self.path = image
        self.hash = image_hash
        self.filename = filename
        self.sort = sort

    _flush = {
        'item': lambda x: Item.query.get(x.item_id),
        'url': lambda x: url_for('static', filename=x.path)
    }
    _item = None
    _url = None

    @property
    def item(self):
        return self.get_or_flush('item')

    def get_vendor_id(self):
        return self.item.vendor_id

    @property
    def url(self):
        return self.get_or_flush('url')


class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False, index=True)
    distributor_id = db.Column(db.Integer, nullable=False, index=True)
    stock = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, item_id, distributor_id, stock):
        self.item_id = item_id
        self.distributor_id = distributor_id
        self.stock = stock


class Style(db.Model):
    __tablename__ = 'styles'
    id = db.Column(db.Integer, primary_key=True)
    style = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        styles = ('古典', '明式', '清式', '新中式', '其他')
        for style in styles:
            db.session.add(Style(style=style))
        db.session.commit()


class Category(db.Model, Property):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Unicode(20), nullable=False)
    father_id = db.Column(db.Integer, nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False)

    _flush = {
        'father': lambda x: Category.query.get(x.father_id) if x.level > 1 else x
    }
    _father = None

    @property
    def father(self):
        return self.get_or_flush('father')

    @staticmethod
    def generate_fake():
        categories = (('椅凳类', '10000'), ('椅', '10100'), ('靠背条椅', ''), ('交椅式躺椅', ''), ('圆后背金漆交椅', ''), ('圆后背剔红交椅', ''), ('圆后背雕花交椅', ''), ('圆后背交椅', ''), ('直后背交椅', ''), ('鹿角椅', ''), ('后背装板圈椅', ''), ('高束腰带托泥雕花圈椅', ''), ('有束腰带托泥雕花圈椅', ''), ('仿竹材圈椅', ''), ('透雕靠背圈椅', ''), ('矮素圈椅', ''), ('素圈椅', ''), ('太师椅', ''), ('官帽椅', ''), ('玫瑰椅', ''), ('背板开透光靠背椅', ''), ('一统碑木梳背椅', ''), ('一统碑椅', ''), ('小灯挂椅', ''), ('灯挂椅', ''), ('皇宫椅', ''), ('摇椅', ''), ('卷书椅', ''), ('大班椅', ''), ('长凳', '10200'), ('夹头榫春凳', ''), ('插肩榫二人凳', ''), ('夹头榫二人凳', ''), ('四面平二人凳', ''), ('有束腰二人凳', ''), ('无束腰二人凳', ''), ('门凳', ''), ('长条凳', ''), ('小条凳', ''), ('四方凳', ''), ('古凳', ''), ('坐墩', '10300'), ('瓜棱形鼓墩', ''), ('直棂式坐墩', ''), ('海棠式开光坐墩', ''), ('五开光弦纹坐墩', ''), ('四开光弦纹坐墩', ''), ('圆凳', ''), ('宝座', '10400'), ('有束腰带托泥宝座', ''), ('列屏式有束腰马蹄足宝座', ''), ('四出头官帽椅式有束腰带托泥宝座', ''), ('交杌', '10500'), ('上折式交杌', ''), ('有踏床交杌', ''), ('无踏床交杌', ''), ('小交杌', ''), ('杌凳', '10600'), ('其他形式杌凳', ''), ('有束腰杌凳', ''), ('无束腰杌凳', ''), ('四面平杌凳', ''), ('桌案类', '20000'), ('宽长桌案', '20100'), ('画案', ''), ('画桌', ''), ('书案', ''), ('书桌', ''), ('其他桌案', '20200'), ('扇面桌', ''), ('月牙桌', ''), ('琴桌', ''), ('棋桌', ''), ('供桌、供案', ''), ('抽屉桌', ''), ('圆桌（圆台）', ''), ('花几', ''), ('茶几', ''), ('高几', ''), ('翘头案', ''), ('平台案', ''), ('酒桌、半桌', '20300'), ('炕案', '20400'), ('夹头榫撇腿翘头炕案', ''), ('夹头榫炕案', ''), ('联二橱式炕案', ''), ('插肩榫炕案', ''), ('三屉大炕案', ''), ('炕桌', '20500'), ('无束腰竹节纹方炕桌', ''), ('有束腰齐牙条炕桌', ''), ('高束腰透雕炕桌', ''), ('有束腰三弯腿炕桌', ''), ('高束腰浮雕炕桌', ''), ('高束腰加矮老装绦环板炕桌', ''), ('有束腰马蹄足鼓腿彭牙炕桌', ''), ('无束腰直足井字棂格炕桌', ''), ('条形桌案', '20600'), ('条桌', ''), ('条案', ''), ('条几', ''), ('方桌', '20700'), ('麻将桌', ''), ('四方桌', ''), ('茶桌（茶台）', ''), ('长方桌（长方台）', ''), ('霸王枨餐桌', ''), ('香几', '20800'), ('四足方香几', ''), ('五足圆香几', ''), ('三足圆香几', ''), ('五足带台座圆香几', ''), ('四足高束腰小方香几', ''), ('六足高束腰香几', ''), ('四足有束腰八方香几', ''), ('五足内翻霸王枨圆香几', ''), ('高束腰五足香几', ''), ('炕几', '20900'), ('无束腰壶门牙条炕几', ''), ('无束腰罗锅枨装牙条炕几', ''), ('无束腰直枨加矮老六方材炕几', ''), ('雕云纹炕几', ''), ('黑漆素炕几', ''), ('床榻类', '30000'), ('拔步床', '30100'), ('千工拔步床', ''), ('垂花柱式拔步床', ''), ('榉木攒海棠花围拔步床', ''), ('架子床', '30200'), ('月洞式门罩架子床', ''), ('正万字门围子架子床', ''), ('十字绦环门围子架子床', ''), ('品字栏杆围子架子床', ''), ('罗汉床', '30300'), ('三屏风斗簇围子罗汉床（四簇云纹）', ''), ('三屏风攒接围子罗汉床（双笔管式）', ''), ('三屏风攒接围子罗汉床（曲尺式）', ''), ('三屏风攒接围子罗汉床（绦环加曲尺）', ''), ('三屏风攒接围子罗汉床（正卍字式）', ''), ('三屏风绦环板围子罗汉床', ''), ('五屏风攒边装板围子插屏式罗汉床', ''), ('三屏风独板围子罗汉床', ''), ('榻', '30400'), ('有束腰腰圆形脚踏', ''), ('六足折叠式榻', ''), ('无束腰直足榻', ''), ('有束腰马蹄足鼓腿彭牙榻', ''), ('有束腰直足榻', ''), ('现代床', '30500'), ('大床', ''), ('高箱床', ''), ('柜架类', '40000'), ('闷户橱', '40100'), ('柜橱', ''), ('联四橱', ''), ('联三橱', ''), ('联二橱', ''), ('方角柜', '40200'), ('大六件柜', ''), ('大四件柜', ''), ('上箱下柜', ''), ('顶箱带座小四件柜', ''), ('透格门方角柜', ''), ('方角药柜', ''), ('大方角柜', ''), ('方角炕柜', ''), ('亮格柜', '40300'), ('上格券口带栏杆万历柜', ''), ('上格双层亮格柜', ''), ('架具类', '40400'), ('火盆架', ''), ('面盆架', ''), ('书架', ''), ('衣架', ''), ('天平架', ''), ('镜架', ''), ('博古架', ''), ('花架', ''), ('圆角柜', '40500'), ('透格门圆角柜', ''), ('榉木圆角柜', ''), ('变体圆角柜', ''), ('五抹门圆角柜', ''), ('有柜膛圆角柜', ''), ('无柜膛圆角柜', ''), ('圆角炕柜', ''), ('架格', '40600'), ('直棂步步紧门透棂架格', ''), ('品字栏杆架格', ''), ('三面直棂透棂架格', ''), ('攒接十字栏杆架格', ''), ('攒接品字栏杆加卡子花架格', ''), ('透空后背架格', ''), ('四层带抽屉架格', ''), ('三面攒接棂格架格', ''), ('三层全敞带抽屉架格', ''), ('几腿式架格', ''), ('现代柜架', '40700'), ('大衣柜', ''), ('电视柜', ''), ('书柜', ''), ('多宝格', ''), ('古董柜', ''), ('酒柜', ''), ('隔厅柜', ''), ('鞋柜', ''), ('衣帽柜', ''), ('梳妆台', ''), ('其它类', '50000'), ('箱', '50100'), ('印匣', ''), ('轿箱', ''), ('小箱', ''), ('药箱', ''), ('官皮箱', ''), ('衣箱', ''), ('甘蔗床', '50200'), ('灯台', '50300'), ('提盒', '50400'), ('屏风', '50500'), ('枕凳', '50600'), ('滚凳', '50700'), ('都承盘', '50800'), ('镜台', '50900'), ('写字台', '51000'), ('大班台', '51100'), ('首饰盒', '51200'), ('工艺品', '51300'))
        first = second = None
        for category_name, str_id in categories:
            if str_id.endswith('0000'):
                first = Category(category=category_name, father_id=0, level=1)
                db.session.add(first)
                db.session.commit()
            elif str_id.endswith('00'):
                second = Category(category=category_name, father_id=first.id, level=2)
                db.session.add(second)
                db.session.commit()
            else:
                db.session.add(Category(category=category_name, father_id=second.id, level=3))
                db.session.commit()


class Scene(db.Model, Property):
    __tablename__ = 'scenes'
    id = db.Column(db.Integer, primary_key=True)
    scene = db.Column(db.Unicode(20), nullable=False)
    father_id = db.Column(db.Integer, nullable=False)
    level = db.Column(db.Integer, nullable=False)

    _flush = {
        'father': lambda x: Scene.query.get(x.father_id)
    }
    _father = None

    def __init__(self, scene, father_id, level):
        self.scene = scene
        self.father_id = father_id
        self.level = level

    @property
    def father(self):
        return self.get_or_flush('father')

    @staticmethod
    def generate_fake():
        scenes = [('家庭', ('书房', '客厅', '卧室', '厨卫', '餐厅', '儿童房')), ('办公', ('酒店', '工作室')), ('工艺品', ('工艺品',)), ('其他', ('其他', ))]
        for item in scenes:
            scene = Scene(scene=item[0], father_id=0, level=1)
            db.session.add(scene)
            db.session.commit()
            for second_scene in item[1]:
                db.session.add(Scene(scene=second_scene, father_id=scene.id, level=2))
            db.session.commit()


class FirstMaterial(db.Model):
    __tablename__ = 'first_materials'
    id = db.Column(db.Integer, primary_key=True)
    first_material = db.Column(db.Unicode(20), nullable=False)

    @staticmethod
    def generate_fake():
        materials = (u'紫檀木类', u'花梨木类', u'香枝木类', u'黑酸枝木类', u'红酸枝木类', u'鸡翅木类', u'乌木类（俗称黑檀）', u'条纹乌木类（黑檀、乌纹木、乌云木）')
        for material in materials:
            db.session.add(FirstMaterial(first_material=material))
        db.session.commit()


class SecondMaterial(db.Model):
    __tablename__ = 'second_materials'
    id = db.Column(db.Integer, primary_key=True)
    first_material_id = db.Column(db.Integer, nullable=False)
    second_material = db.Column(db.Unicode(20), nullable=False)

    @staticmethod
    def generate_fake():
        materials = ((u'紫檀木类', (u'檀香紫檀（小叶紫檀）',)), (u'花梨木类', (u'越柬紫檀（老挝花梨）', u'安达曼紫檀（非洲黄花梨）', u'刺猬紫檀（非洲花梨）', u'印度紫檀', u'大果紫檀', u'囊状紫檀', u'鸟足紫檀（东南亚花梨）')), (u'香枝木类', (u'降香黄檀（海南黄花梨）',)), (u'黑酸枝木类', (u'刀状黑黄檀（缅甸黑酸枝）', u'黑黄檀（版纳黑檀）', u'阔叶黄檀（印尼黑酸枝）', u'卢氏黑黄檀（大叶紫檀）', u'东非黑黄檀（紫光檀）', u'巴西黑黄檀', u'亚马孙黄檀', u'伯利兹黄檀（洪都拉斯玫瑰木）')), (u'红酸枝木类', (u'巴里黄檀（柬埔寨红酸枝）', u'赛州黄檀', u'交趾黄檀（大红酸枝）', u'绒毛黄檀（巴西黄檀）', u'中美洲黄檀', u'奥氏黄檀（缅甸红酸枝）', u'微凹黄檀（可可波罗）')), (u'鸡翅木类', (u'非洲崖豆木（非洲鸡翅）', u'白花崖豆木（缅甸鸡翅木）', u'铁刀木')), (u'乌木类（俗称黑檀）', (u'乌木', u'厚瓣乌木', u'毛药乌木', u'蓬赛乌木（黑檀）')), (u'条纹乌木类（黑檀、乌纹木、乌云木）', (u'苏拉威西乌木', u'菲律宾乌木')))
        for item in materials:
            first_material = FirstMaterial.query.filter_by(first_material=item[0]).first()
            for material in item[1]:
                db.session.add(SecondMaterial(first_material_id=first_material.id, second_material=material))
        db.session.commit()


class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        materials = [u'紫檀木', u'花梨木', u'香枝木', u'黑酸枝木', u'红酸枝木', u'鸡翅木', u'乌木', u'条纹乌木']
        for material in materials:
            db.session.add(Material(material=material))
        db.session.commit()


class Privilege(BaseUser, db.Model):
    __tablename__ = 'privileges'
    # 用户名
    username = db.Column(db.String(12), nullable=False, unique=True)

    mobile = None

    id_prefix = privilege_id_prefix

    def __init__(self, password, email, username):
        self.username = username
        self.email = email
        self.password = password
        super(Privilege, self).__init__(password, '', email)

    @staticmethod
    def generate_fake():
        privilege = Privilege('14e1b600b1fd579f47433b88e8d85291', 'a@a.com', 'admin')
        db.session.add(privilege)
        db.session.commit()


class Area(db.Model, Property):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False, index=True)
    area = db.Column(db.Unicode(15), nullable=False)
    father_id = db.Column(db.Integer, nullable=False, index=True)
    # level 1表示省份 2表示城市 3表示行政区
    level = db.Column(db.Integer, nullable=False)
    pinyin = db.Column(db.String(30), nullable=False)
    pinyin_index = db.Column(db.CHAR(1), nullable=False)
    distributor_amount = db.Column(db.Integer, nullable=False)

    _flush = {
        'father': lambda x: Area.query.get(x.id) if x.level > 1 else None
    }
    _father = None

    @staticmethod
    def generate_fake():
        for area in ((1,110000,'北京',0,1,'beijing','B',0),(2,110100,'北京市',1,2,'beijingshi','B',0),(3,110101,'东城区',2,3,'dongchengqu','D',0),(4,110102,'西城区',2,3,'xichengqu','X',0),(5,110105,'朝阳区',2,3,'zhaoyangqu','Z',0),(6,110106,'丰台区',2,3,'fengtaiqu','F',0),(7,110107,'石景山区',2,3,'shijingshanqu','S',0),(8,110108,'海淀区',2,3,'haidianqu','H',0),(9,110109,'门头沟区',2,3,'mentougouqu','M',0),(10,110111,'房山区',2,3,'fangshanqu','F',0),(11,110112,'通州区',2,3,'tongzhouqu','T',0),(12,110113,'顺义区',2,3,'shunyiqu','S',0),(13,110114,'昌平区',2,3,'changpingqu','C',0),(14,110115,'大兴区',2,3,'daxingqu','D',0),(15,110116,'怀柔区',2,3,'huairouqu','H',0),(16,110117,'平谷区',2,3,'pingguqu','P',0),(17,110228,'密云县',2,3,'miyunxian','M',0),(18,110229,'延庆县',2,3,'yanqingxian','Y',0),(19,120000,'天津',0,1,'tianjin','T',0),(20,120100,'天津市',19,2,'tianjinshi','T',0),(21,120101,'和平区',20,3,'hepingqu','H',0),(22,120102,'河东区',20,3,'hedongqu','H',0),(23,120103,'河西区',20,3,'hexiqu','H',0),(24,120104,'南开区',20,3,'nankaiqu','N',0),(25,120105,'河北区',20,3,'hebeiqu','H',0),(26,120106,'红桥区',20,3,'hongqiaoqu','H',0),(27,120110,'东丽区',20,3,'dongliqu','D',0),(28,120111,'西青区',20,3,'xiqingqu','X',0),(29,120112,'津南区',20,3,'jinnanqu','J',0),(30,120113,'北辰区',20,3,'beichenqu','B',0),(31,120114,'武清区',20,3,'wuqingqu','W',0),(32,120115,'宝坻区',20,3,'baodiqu','B',0),(33,120116,'滨海新区',20,3,'binhaixinqu','B',0),(34,120221,'宁河县',20,3,'ninghexian','N',0),(35,120223,'静海县',20,3,'jinghaixian','J',0),(36,120225,'蓟县',20,3,'jixian','J',0),(37,130000,'河北',0,1,'hebei','H',0),(38,130100,'石家庄市',37,2,'shijiazhuangshi','S',0),(39,130102,'长安区',38,3,'changanqu','C',0),(40,130103,'桥东区',38,3,'qiaodongqu','Q',0),(41,130104,'桥西区',38,3,'qiaoxiqu','Q',0),(42,130105,'新华区',38,3,'xinhuaqu','X',0),(43,130107,'井陉矿区',38,3,'jingxingkuangqu','J',0),(44,130108,'裕华区',38,3,'yuhuaqu','Y',0),(45,130121,'井陉县',38,3,'jingxingxian','J',0),(46,130123,'正定县',38,3,'zhengdingxian','Z',0),(47,130124,'栾城县',38,3,'luanchengxian','L',0),(48,130125,'行唐县',38,3,'hangtangxian','H',0),(49,130126,'灵寿县',38,3,'lingshouxian','L',0),(50,130127,'高邑县',38,3,'gaoyixian','G',0),(51,130128,'深泽县',38,3,'shenzexian','S',0),(52,130129,'赞皇县',38,3,'zanhuangxian','Z',0),(53,130130,'无极县',38,3,'wujixian','W',0),(54,130131,'平山县',38,3,'pingshanxian','P',0),(55,130132,'元氏县',38,3,'yuanshixian','Y',0),(56,130133,'赵县',38,3,'zhaoxian','Z',0),(57,130181,'辛集市',38,3,'xinjishi','X',0),(58,130182,'藁城市',38,3,'gaochengshi','G',0),(59,130183,'晋州市',38,3,'jinzhoushi','J',0),(60,130184,'新乐市',38,3,'xinleshi','X',0),(61,130185,'鹿泉市',38,3,'luquanshi','L',0),(62,130200,'唐山市',37,2,'tangshanshi','T',0),(63,130202,'路南区',62,3,'lunanqu','L',0),(64,130203,'路北区',62,3,'lubeiqu','L',0),(65,130204,'古冶区',62,3,'guyequ','G',0),(66,130205,'开平区',62,3,'kaipingqu','K',0),(67,130207,'丰南区',62,3,'fengnanqu','F',0),(68,130208,'丰润区',62,3,'fengrunqu','F',0),(69,130209,'曹妃甸区',62,3,'caofeidianqu','C',0),(70,130223,'滦县',62,3,'luanxian','L',0),(71,130224,'滦南县',62,3,'luannanxian','L',0),(72,130225,'乐亭县',62,3,'letingxian','L',0),(73,130227,'迁西县',62,3,'qianxixian','Q',0),(74,130229,'玉田县',62,3,'yutianxian','Y',0),(75,130281,'遵化市',62,3,'zunhuashi','Z',0),(76,130283,'迁安市',62,3,'qiananshi','Q',0),(77,130300,'秦皇岛市',37,2,'qinhuangdaoshi','Q',0),(78,130302,'海港区',77,3,'haigangqu','H',0),(79,130303,'山海关区',77,3,'shanhaiguanqu','S',0),(80,130304,'北戴河区',77,3,'beidaihequ','B',0),(81,130321,'青龙县',77,3,'qinglongxian','Q',0),(82,130322,'昌黎县',77,3,'changlixian','C',0),(83,130323,'抚宁县',77,3,'funingxian','F',0),(84,130324,'卢龙县',77,3,'lulongxian','L',0),(85,130400,'邯郸市',37,2,'handanshi','H',0),(86,130402,'邯山区',85,3,'hanshanqu','H',0),(87,130403,'丛台区',85,3,'congtaiqu','C',0),(88,130404,'复兴区',85,3,'fuxingqu','F',0),(89,130406,'峰峰矿区',85,3,'fengfengkuangqu','F',0),(90,130421,'邯郸县',85,3,'handanxian','H',0),(91,130423,'临漳县',85,3,'linzhangxian','L',0),(92,130424,'成安县',85,3,'chenganxian','C',0),(93,130425,'大名县',85,3,'damingxian','D',0),(94,130426,'涉县',85,3,'shexian','S',0),(95,130427,'磁县',85,3,'cixian','C',0),(96,130428,'肥乡县',85,3,'feixiangxian','F',0),(97,130429,'永年县',85,3,'yongnianxian','Y',0),(98,130430,'邱县',85,3,'qiuxian','Q',0),(99,130431,'鸡泽县',85,3,'jizexian','J',0),(100,130432,'广平县',85,3,'guangpingxian','G',0),(101,130433,'馆陶县',85,3,'guantaoxian','G',0),(102,130434,'魏县',85,3,'weixian','W',0),(103,130435,'曲周县',85,3,'quzhouxian','Q',0),(104,130481,'武安市',85,3,'wuanshi','W',0),(105,130500,'邢台市',37,2,'xingtaishi','X',0),(106,130502,'桥东区',105,3,'qiaodongqu','Q',0),(107,130503,'桥西区',105,3,'qiaoxiqu','Q',0),(108,130521,'邢台县',105,3,'xingtaixian','X',0),(109,130522,'临城县',105,3,'linchengxian','L',0),(110,130523,'内丘县',105,3,'neiqiuxian','N',0),(111,130524,'柏乡县',105,3,'baixiangxian','B',0),(112,130525,'隆尧县',105,3,'longyaoxian','L',0),(113,130526,'任县',105,3,'renxian','R',0),(114,130527,'南和县',105,3,'nanhexian','N',0),(115,130528,'宁晋县',105,3,'ningjinxian','N',0),(116,130529,'巨鹿县',105,3,'juluxian','J',0),(117,130530,'新河县',105,3,'xinhexian','X',0),(118,130531,'广宗县',105,3,'guangzongxian','G',0),(119,130532,'平乡县',105,3,'pingxiangxian','P',0),(120,130533,'威县',105,3,'weixian','W',0),(121,130534,'清河县',105,3,'qinghexian','Q',0),(122,130535,'临西县',105,3,'linxixian','L',0),(123,130581,'南宫市',105,3,'nangongshi','N',0),(124,130582,'沙河市',105,3,'shaheshi','S',0),(125,130600,'保定市',37,2,'baodingshi','B',0),(126,130602,'新市区',125,3,'xinshiqu','X',0),(127,130603,'北市区',125,3,'beishiqu','B',0),(128,130604,'南市区',125,3,'nanshiqu','N',0),(129,130621,'满城县',125,3,'manchengxian','M',0),(130,130622,'清苑县',125,3,'qingyuanxian','Q',0),(131,130623,'涞水县',125,3,'laishuixian','L',0),(132,130624,'阜平县',125,3,'fupingxian','F',0),(133,130625,'徐水县',125,3,'xushuixian','X',0),(134,130626,'定兴县',125,3,'dingxingxian','D',0),(135,130627,'唐县',125,3,'tangxian','T',0),(136,130628,'高阳县',125,3,'gaoyangxian','G',0),(137,130629,'容城县',125,3,'rongchengxian','R',0),(138,130630,'涞源县',125,3,'laiyuanxian','L',0),(139,130631,'望都县',125,3,'wangduxian','W',0),(140,130632,'安新县',125,3,'anxinxian','A',0),(141,130633,'易县',125,3,'yixian','Y',0),(142,130634,'曲阳县',125,3,'quyangxian','Q',0),(143,130635,'蠡县',125,3,'lixian','L',0),(144,130636,'顺平县',125,3,'shunpingxian','S',0),(145,130637,'博野县',125,3,'boyexian','B',0),(146,130638,'雄县',125,3,'xiongxian','X',0),(147,130681,'涿州市',125,3,'zhuozhoushi','Z',0),(148,130682,'定州市',125,3,'dingzhoushi','D',0),(149,130683,'安国市',125,3,'anguoshi','A',0),(150,130684,'高碑店市',125,3,'gaobeidianshi','G',0),(151,130700,'张家口市',37,2,'zhangjiakoushi','Z',0),(152,130702,'桥东区',151,3,'qiaodongqu','Q',0),(153,130703,'桥西区',151,3,'qiaoxiqu','Q',0),(154,130705,'宣化区',151,3,'xuanhuaqu','X',0),(155,130706,'下花园区',151,3,'xiahuayuanqu','X',0),(156,130721,'宣化县',151,3,'xuanhuaxian','X',0),(157,130722,'张北县',151,3,'zhangbeixian','Z',0),(158,130723,'康保县',151,3,'kangbaoxian','K',0),(159,130724,'沽源县',151,3,'guyuanxian','G',0),(160,130725,'尚义县',151,3,'shangyixian','S',0),(161,130726,'蔚县',151,3,'weixian','W',0),(162,130727,'阳原县',151,3,'yangyuanxian','Y',0),(163,130728,'怀安县',151,3,'huaianxian','H',0),(164,130729,'万全县',151,3,'wanquanxian','W',0),(165,130730,'怀来县',151,3,'huailaixian','H',0),(166,130731,'涿鹿县',151,3,'zhuoluxian','Z',0),(167,130732,'赤城县',151,3,'chichengxian','C',0),(168,130733,'崇礼县',151,3,'chonglixian','C',0),(169,130800,'承德市',37,2,'chengdeshi','C',0),(170,130802,'双桥区',169,3,'shuangqiaoqu','S',0),(171,130803,'双滦区',169,3,'shuangluanqu','S',0),(172,130804,'鹰手营子矿区',169,3,'yingshouyingzikuangqu','Y',0),(173,130821,'承德县',169,3,'chengdexian','C',0),(174,130822,'兴隆县',169,3,'xinglongxian','X',0),(175,130823,'平泉县',169,3,'pingquanxian','P',0),(176,130824,'滦平县',169,3,'luanpingxian','L',0),(177,130825,'隆化县',169,3,'longhuaxian','L',0),(178,130826,'丰宁县',169,3,'fengningxian','F',0),(179,130827,'宽城县',169,3,'kuanchengxian','K',0),(180,130828,'围场县',169,3,'weichangxian','W',0),(181,130900,'沧州市',37,2,'cangzhoushi','C',0),(182,130902,'新华区',181,3,'xinhuaqu','X',0),(183,130903,'运河区',181,3,'yunhequ','Y',0),(184,130921,'沧县',181,3,'cangxian','C',0),(185,130922,'青县',181,3,'qingxian','Q',0),(186,130923,'东光县',181,3,'dongguangxian','D',0),(187,130924,'海兴县',181,3,'haixingxian','H',0),(188,130925,'盐山县',181,3,'yanshanxian','Y',0),(189,130926,'肃宁县',181,3,'suningxian','S',0),(190,130927,'南皮县',181,3,'nanpixian','N',0),(191,130928,'吴桥县',181,3,'wuqiaoxian','W',0),(192,130929,'献县',181,3,'xianxian','X',0),(193,130930,'孟村县',181,3,'mengcunxian','M',0),(194,130981,'泊头市',181,3,'botoushi','B',0),(195,130982,'任丘市',181,3,'renqiushi','R',0),(196,130983,'黄骅市',181,3,'huanghuashi','H',0),(197,130984,'河间市',181,3,'hejianshi','H',0),(198,131000,'廊坊市',37,2,'langfangshi','L',0),(199,131002,'安次区',198,3,'anciqu','A',0),(200,131003,'广阳区',198,3,'guangyangqu','G',0),(201,131022,'固安县',198,3,'guanxian','G',0),(202,131023,'永清县',198,3,'yongqingxian','Y',0),(203,131024,'香河县',198,3,'xianghexian','X',0),(204,131025,'大城县',198,3,'dachengxian','D',0),(205,131026,'文安县',198,3,'wenanxian','W',0),(206,131028,'大厂县',198,3,'dachangxian','D',0),(207,131081,'霸州市',198,3,'bazhoushi','B',0),(208,131082,'三河市',198,3,'sanheshi','S',0),(209,131100,'衡水市',37,2,'hengshuishi','H',0),(210,131102,'桃城区',209,3,'taochengqu','T',0),(211,131121,'枣强县',209,3,'zaoqiangxian','Z',0),(212,131122,'武邑县',209,3,'wuyixian','W',0),(213,131123,'武强县',209,3,'wuqiangxian','W',0),(214,131124,'饶阳县',209,3,'raoyangxian','R',0),(215,131125,'安平县',209,3,'anpingxian','A',0),(216,131126,'故城县',209,3,'guchengxian','G',0),(217,131127,'景县',209,3,'jingxian','J',0),(218,131128,'阜城县',209,3,'fuchengxian','F',0),(219,131181,'冀州市',209,3,'jizhoushi','J',0),(220,131182,'深州市',209,3,'shenzhoushi','S',0),(221,140000,'山西',0,1,'shanxi','S',0),(222,140100,'太原市',221,2,'taiyuanshi','T',0),(223,140105,'小店区',222,3,'xiaodianqu','X',0),(224,140106,'迎泽区',222,3,'yingzequ','Y',0),(225,140107,'杏花岭区',222,3,'xinghualingqu','X',0),(226,140108,'尖草坪区',222,3,'jiancaopingqu','J',0),(227,140109,'万柏林区',222,3,'wanbailinqu','W',0),(228,140110,'晋源区',222,3,'jinyuanqu','J',0),(229,140121,'清徐县',222,3,'qingxuxian','Q',0),(230,140122,'阳曲县',222,3,'yangquxian','Y',0),(231,140123,'娄烦县',222,3,'loufanxian','L',0),(232,140181,'古交市',222,3,'gujiaoshi','G',0),(233,140200,'大同市',221,2,'datongshi','D',0),(234,140202,'城区',233,3,'chengqu','C',0),(235,140203,'矿区',233,3,'kuangqu','K',0),(236,140211,'南郊区',233,3,'nanjiaoqu','N',0),(237,140212,'新荣区',233,3,'xinrongqu','X',0),(238,140221,'阳高县',233,3,'yanggaoxian','Y',0),(239,140222,'天镇县',233,3,'tianzhenxian','T',0),(240,140223,'广灵县',233,3,'guanglingxian','G',0),(241,140224,'灵丘县',233,3,'lingqiuxian','L',0),(242,140225,'浑源县',233,3,'hunyuanxian','H',0),(243,140226,'左云县',233,3,'zuoyunxian','Z',0),(244,140227,'大同县',233,3,'datongxian','D',0),(245,140300,'阳泉市',221,2,'yangquanshi','Y',0),(246,140302,'城区',245,3,'chengqu','C',0),(247,140303,'矿区',245,3,'kuangqu','K',0),(248,140311,'郊区',245,3,'jiaoqu','J',0),(249,140321,'平定县',245,3,'pingdingxian','P',0),(250,140322,'盂县',245,3,'yuxian','Y',0),(251,140400,'长治市',221,2,'changzhishi','C',0),(252,140402,'城区',251,3,'chengqu','C',0),(253,140411,'郊区',251,3,'jiaoqu','J',0),(254,140421,'长治县',251,3,'changzhixian','C',0),(255,140423,'襄垣县',251,3,'xiangyuanxian','X',0),(256,140424,'屯留县',251,3,'tunliuxian','T',0),(257,140425,'平顺县',251,3,'pingshunxian','P',0),(258,140426,'黎城县',251,3,'lichengxian','L',0),(259,140427,'壶关县',251,3,'huguanxian','H',0),(260,140428,'长子县',251,3,'changzixian','C',0),(261,140429,'武乡县',251,3,'wuxiangxian','W',0),(262,140430,'沁县',251,3,'qinxian','Q',0),(263,140431,'沁源县',251,3,'qinyuanxian','Q',0),(264,140481,'潞城市',251,3,'luchengshi','L',0),(265,140500,'晋城市',221,2,'jinchengshi','J',0),(266,140502,'城区',265,3,'chengqu','C',0),(267,140521,'沁水县',265,3,'qinshuixian','Q',0),(268,140522,'阳城县',265,3,'yangchengxian','Y',0),(269,140524,'陵川县',265,3,'lingchuanxian','L',0),(270,140525,'泽州县',265,3,'zezhouxian','Z',0),(271,140581,'高平市',265,3,'gaopingshi','G',0),(272,140600,'朔州市',221,2,'shuozhoushi','S',0),(273,140602,'朔城区',272,3,'shuochengqu','S',0),(274,140603,'平鲁区',272,3,'pingluqu','P',0),(275,140621,'山阴县',272,3,'shanyinxian','S',0),(276,140622,'应县',272,3,'yingxian','Y',0),(277,140623,'右玉县',272,3,'youyuxian','Y',0),(278,140624,'怀仁县',272,3,'huairenxian','H',0),(279,140700,'晋中市',221,2,'jinzhongshi','J',0),(280,140702,'榆次区',279,3,'yuciqu','Y',0),(281,140721,'榆社县',279,3,'yushexian','Y',0),(282,140722,'左权县',279,3,'zuoquanxian','Z',0),(283,140723,'和顺县',279,3,'heshunxian','H',0),(284,140724,'昔阳县',279,3,'xiyangxian','X',0),(285,140725,'寿阳县',279,3,'shouyangxian','S',0),(286,140726,'太谷县',279,3,'taiguxian','T',0),(287,140727,'祁县',279,3,'qixian','Q',0),(288,140728,'平遥县',279,3,'pingyaoxian','P',0),(289,140729,'灵石县',279,3,'lingshixian','L',0),(290,140781,'介休市',279,3,'jiexiushi','J',0),(291,140800,'运城市',221,2,'yunchengshi','Y',0),(292,140802,'盐湖区',291,3,'yanhuqu','Y',0),(293,140821,'临猗县',291,3,'linyixian','L',0),(294,140822,'万荣县',291,3,'wanrongxian','W',0),(295,140823,'闻喜县',291,3,'wenxixian','W',0),(296,140824,'稷山县',291,3,'jishanxian','J',0),(297,140825,'新绛县',291,3,'xinjiangxian','X',0),(298,140826,'绛县',291,3,'jiangxian','J',0),(299,140827,'垣曲县',291,3,'yuanquxian','Y',0),(300,140828,'夏县',291,3,'xiaxian','X',0),(301,140829,'平陆县',291,3,'pingluxian','P',0),(302,140830,'芮城县',291,3,'ruichengxian','R',0),(303,140881,'永济市',291,3,'yongjishi','Y',0),(304,140882,'河津市',291,3,'hejinshi','H',0),(305,140900,'忻州市',221,2,'xinzhoushi','X',0),(306,140902,'忻府区',305,3,'xinfuqu','X',0),(307,140921,'定襄县',305,3,'dingxiangxian','D',0),(308,140922,'五台县',305,3,'wutaixian','W',0),(309,140923,'代县',305,3,'daixian','D',0),(310,140924,'繁峙县',305,3,'fanzhixian','F',0),(311,140925,'宁武县',305,3,'ningwuxian','N',0),(312,140926,'静乐县',305,3,'jinglexian','J',0),(313,140927,'神池县',305,3,'shenchixian','S',0),(314,140928,'五寨县',305,3,'wuzhaixian','W',0),(315,140929,'岢岚县',305,3,'kelanxian','K',0),(316,140930,'河曲县',305,3,'hequxian','H',0),(317,140931,'保德县',305,3,'baodexian','B',0),(318,140932,'偏关县',305,3,'pianguanxian','P',0),(319,140981,'原平市',305,3,'yuanpingshi','Y',0),(320,141000,'临汾市',221,2,'linfenshi','L',0),(321,141002,'尧都区',320,3,'yaoduqu','Y',0),(322,141021,'曲沃县',320,3,'quwoxian','Q',0),(323,141022,'翼城县',320,3,'yichengxian','Y',0),(324,141023,'襄汾县',320,3,'xiangfenxian','X',0),(325,141024,'洪洞县',320,3,'hongdongxian','H',0),(326,141025,'古县',320,3,'guxian','G',0),(327,141026,'安泽县',320,3,'anzexian','A',0),(328,141027,'浮山县',320,3,'fushanxian','F',0),(329,141028,'吉县',320,3,'jixian','J',0),(330,141029,'乡宁县',320,3,'xiangningxian','X',0),(331,141030,'大宁县',320,3,'daningxian','D',0),(332,141031,'隰县',320,3,'xixian','X',0),(333,141032,'永和县',320,3,'yonghexian','Y',0),(334,141033,'蒲县',320,3,'puxian','P',0),(335,141034,'汾西县',320,3,'fenxixian','F',0),(336,141081,'侯马市',320,3,'houmashi','H',0),(337,141082,'霍州市',320,3,'huozhoushi','H',0),(338,141100,'吕梁市',221,2,'lvliangshi','L',0),(339,141102,'离石区',338,3,'lishiqu','L',0),(340,141121,'文水县',338,3,'wenshuixian','W',0),(341,141122,'交城县',338,3,'jiaochengxian','J',0),(342,141123,'兴县',338,3,'xingxian','X',0),(343,141124,'临县',338,3,'linxian','L',0),(344,141125,'柳林县',338,3,'liulinxian','L',0),(345,141126,'石楼县',338,3,'shilouxian','S',0),(346,141127,'岚县',338,3,'lanxian','L',0),(347,141128,'方山县',338,3,'fangshanxian','F',0),(348,141129,'中阳县',338,3,'zhongyangxian','Z',0),(349,141130,'交口县',338,3,'jiaokouxian','J',0),(350,141181,'孝义市',338,3,'xiaoyishi','X',0),(351,141182,'汾阳市',338,3,'fenyangshi','F',0),(352,150000,'内蒙古',0,1,'neimenggu','N',0),(353,150100,'呼和浩特市',352,2,'huhehaoteshi','H',0),(354,150102,'新城区',353,3,'xinchengqu','X',0),(355,150103,'回民区',353,3,'huiminqu','H',0),(356,150104,'玉泉区',353,3,'yuquanqu','Y',0),(357,150105,'赛罕区',353,3,'saihanqu','S',0),(358,150121,'土默特左旗',353,3,'tumotezuoqi','T',0),(359,150122,'托克托县',353,3,'tuoketuoxian','T',0),(360,150123,'和林格尔县',353,3,'helingeerxian','H',0),(361,150124,'清水河县',353,3,'qingshuihexian','Q',0),(362,150125,'武川县',353,3,'wuchuanxian','W',0),(363,150200,'包头市',352,2,'baotoushi','B',0),(364,150202,'东河区',363,3,'donghequ','D',0),(365,150203,'昆都仑区',363,3,'kundulunqu','K',0),(366,150204,'青山区',363,3,'qingshanqu','Q',0),(367,150205,'石拐区',363,3,'shiguaiqu','S',0),(368,150206,'白云鄂博矿区',363,3,'baiyunebokuangqu','B',0),(369,150207,'九原区',363,3,'jiuyuanqu','J',0),(370,150221,'土默特右旗',363,3,'tumoteyouqi','T',0),(371,150222,'固阳县',363,3,'guyangxian','G',0),(372,150223,'达茂联合旗',363,3,'damaolianheqi','D',0),(373,150300,'乌海市',352,2,'wuhaishi','W',0),(374,150302,'海勃湾区',373,3,'haibowanqu','H',0),(375,150303,'海南区',373,3,'hainanqu','H',0),(376,150304,'乌达区',373,3,'wudaqu','W',0),(377,150400,'赤峰市',352,2,'chifengshi','C',0),(378,150402,'红山区',377,3,'hongshanqu','H',0),(379,150403,'元宝山区',377,3,'yuanbaoshanqu','Y',0),(380,150404,'松山区',377,3,'songshanqu','S',0),(381,150421,'阿鲁科尔沁旗',377,3,'alukeerqinqi','A',0),(382,150422,'巴林左旗',377,3,'balinzuoqi','B',0),(383,150423,'巴林右旗',377,3,'balinyouqi','B',0),(384,150424,'林西县',377,3,'linxixian','L',0),(385,150425,'克什克腾旗',377,3,'keshiketengqi','K',0),(386,150426,'翁牛特旗',377,3,'wengniuteqi','W',0),(387,150428,'喀喇沁旗',377,3,'kalaqinqi','K',0),(388,150429,'宁城县',377,3,'ningchengxian','N',0),(389,150430,'敖汉旗',377,3,'aohanqi','A',0),(390,150500,'通辽市',352,2,'tongliaoshi','T',0),(391,150502,'科尔沁区',390,3,'keerqinqu','K',0),(392,150521,'科尔沁左翼中旗',390,3,'keerqinzuoyizhongqi','K',0),(393,150522,'科尔沁左翼后旗',390,3,'keerqinzuoyihouqi','K',0),(394,150523,'开鲁县',390,3,'kailuxian','K',0),(395,150524,'库伦旗',390,3,'kulunqi','K',0),(396,150525,'奈曼旗',390,3,'naimanqi','N',0),(397,150526,'扎鲁特旗',390,3,'zaluteqi','Z',0),(398,150581,'霍林郭勒市',390,3,'huolinguoleshi','H',0),(399,150600,'鄂尔多斯市',352,2,'eerduosishi','E',0),(400,150602,'东胜区',399,3,'dongshengqu','D',0),(401,150621,'达拉特旗',399,3,'dalateqi','D',0),(402,150622,'准格尔旗',399,3,'zhungeerqi','Z',0),(403,150623,'鄂托克前旗',399,3,'etuokeqianqi','E',0),(404,150624,'鄂托克旗',399,3,'etuokeqi','E',0),(405,150625,'杭锦旗',399,3,'hangjinqi','H',0),(406,150626,'乌审旗',399,3,'wushenqi','W',0),(407,150627,'伊金霍洛旗',399,3,'yijinhuoluoqi','Y',0),(408,150700,'呼伦贝尔市',352,2,'hulunbeiershi','H',0),(409,150702,'海拉尔区',408,3,'hailaerqu','H',0),(410,150703,'扎赉诺尔区',408,3,'zalainuoerqu','Z',0),(411,150721,'阿荣旗',408,3,'arongqi','A',0),(412,150722,'莫力达瓦旗',408,3,'molidawaqi','M',0),(413,150723,'鄂伦春旗',408,3,'elunchunqi','E',0),(414,150724,'旗',408,3,'qi','Q',0),(415,150725,'陈巴尔虎旗',408,3,'chenbaerhuqi','C',0),(416,150726,'新巴尔虎左旗',408,3,'xinbaerhuzuoqi','X',0),(417,150727,'新巴尔虎右旗',408,3,'xinbaerhuyouqi','X',0),(418,150781,'满洲里市',408,3,'manzhoulishi','M',0),(419,150782,'牙克石市',408,3,'yakeshishi','Y',0),(420,150783,'扎兰屯市',408,3,'zalantunshi','Z',0),(421,150784,'额尔古纳市',408,3,'eergunashi','E',0),(422,150785,'根河市',408,3,'genheshi','G',0),(423,150800,'巴彦淖尔市',352,2,'bayannaoershi','B',0),(424,150802,'临河区',423,3,'linhequ','L',0),(425,150821,'五原县',423,3,'wuyuanxian','W',0),(426,150822,'磴口县',423,3,'dengkouxian','D',0),(427,150823,'乌拉特前旗',423,3,'wulateqianqi','W',0),(428,150824,'乌拉特中旗',423,3,'wulatezhongqi','W',0),(429,150825,'乌拉特后旗',423,3,'wulatehouqi','W',0),(430,150826,'杭锦后旗',423,3,'hangjinhouqi','H',0),(431,150900,'乌兰察布市',352,2,'wulanchabushi','W',0),(432,150902,'集宁区',431,3,'jiningqu','J',0),(433,150921,'卓资县',431,3,'zhuozixian','Z',0),(434,150922,'化德县',431,3,'huadexian','H',0),(435,150923,'商都县',431,3,'shangduxian','S',0),(436,150924,'兴和县',431,3,'xinghexian','X',0),(437,150925,'凉城县',431,3,'liangchengxian','L',0),(438,150926,'察哈尔右翼前旗',431,3,'chahaeryouyiqianqi','C',0),(439,150927,'察哈尔右翼中旗',431,3,'chahaeryouyizhongqi','C',0),(440,150928,'察哈尔右翼后旗',431,3,'chahaeryouyihouqi','C',0),(441,150929,'四子王旗',431,3,'siziwangqi','S',0),(442,150981,'丰镇市',431,3,'fengzhenshi','F',0),(443,152200,'兴安盟',352,2,'xinganmeng','X',0),(444,152201,'乌兰浩特市',443,3,'wulanhaoteshi','W',0),(445,152202,'阿尔山市',443,3,'aershanshi','A',0),(446,152221,'科尔沁右翼前旗',443,3,'keerqinyouyiqianqi','K',0),(447,152222,'科尔沁右翼中旗',443,3,'keerqinyouyizhongqi','K',0),(448,152223,'扎赉特旗',443,3,'zalaiteqi','Z',0),(449,152224,'突泉县',443,3,'tuquanxian','T',0),(450,152500,'锡林郭勒盟',352,2,'xilinguolemeng','X',0),(451,152501,'二连浩特市',450,3,'erlianhaoteshi','E',0),(452,152502,'锡林浩特市',450,3,'xilinhaoteshi','X',0),(453,152522,'阿巴嘎旗',450,3,'abagaqi','A',0),(454,152523,'苏尼特左旗',450,3,'sunitezuoqi','S',0),(455,152524,'苏尼特右旗',450,3,'suniteyouqi','S',0),(456,152525,'东乌珠穆沁旗',450,3,'dongwuzhumuqinqi','D',0),(457,152526,'西乌珠穆沁旗',450,3,'xiwuzhumuqinqi','X',0),(458,152527,'太仆寺旗',450,3,'taipusiqi','T',0),(459,152528,'镶黄旗',450,3,'xianghuangqi','X',0),(460,152529,'正镶白旗',450,3,'zhengxiangbaiqi','Z',0),(461,152530,'正蓝旗',450,3,'zhenglanqi','Z',0),(462,152531,'多伦县',450,3,'duolunxian','D',0),(463,152900,'阿拉善盟',352,2,'alashanmeng','A',0),(464,152921,'阿拉善左旗',463,3,'alashanzuoqi','A',0),(465,152922,'阿拉善右旗',463,3,'alashanyouqi','A',0),(466,152923,'额济纳旗',463,3,'ejinaqi','E',0),(467,210000,'辽宁',0,1,'liaoning','L',0),(468,210100,'沈阳市',467,2,'shenyangshi','S',0),(469,210102,'和平区',468,3,'hepingqu','H',0),(470,210103,'沈河区',468,3,'shenhequ','S',0),(471,210104,'大东区',468,3,'dadongqu','D',0),(472,210105,'皇姑区',468,3,'huangguqu','H',0),(473,210106,'铁西区',468,3,'tiexiqu','T',0),(474,210111,'苏家屯区',468,3,'sujiatunqu','S',0),(475,210112,'东陵区',468,3,'donglingqu','D',0),(476,210113,'沈北新区',468,3,'shenbeixinqu','S',0),(477,210114,'于洪区',468,3,'yuhongqu','Y',0),(478,210122,'辽中县',468,3,'liaozhongxian','L',0),(479,210123,'康平县',468,3,'kangpingxian','K',0),(480,210124,'法库县',468,3,'fakuxian','F',0),(481,210181,'新民市',468,3,'xinminshi','X',0),(482,210200,'大连市',467,2,'dalianshi','D',0),(483,210202,'中山区',482,3,'zhongshanqu','Z',0),(484,210203,'西岗区',482,3,'xigangqu','X',0),(485,210204,'沙河口区',482,3,'shahekouqu','S',0),(486,210211,'甘井子区',482,3,'ganjingziqu','G',0),(487,210212,'旅顺口区',482,3,'lvshunkouqu','L',0),(488,210213,'金州区',482,3,'jinzhouqu','J',0),(489,210224,'长海县',482,3,'changhaixian','C',0),(490,210281,'瓦房店市',482,3,'wafangdianshi','W',0),(491,210282,'普兰店市',482,3,'pulandianshi','P',0),(492,210283,'庄河市',482,3,'zhuangheshi','Z',0),(493,210300,'鞍山市',467,2,'anshanshi','A',0),(494,210302,'铁东区',493,3,'tiedongqu','T',0),(495,210303,'铁西区',493,3,'tiexiqu','T',0),(496,210304,'立山区',493,3,'lishanqu','L',0),(497,210311,'千山区',493,3,'qianshanqu','Q',0),(498,210321,'台安县',493,3,'taianxian','T',0),(499,210323,'岫岩县',493,3,'xiuyanxian','X',0),(500,210381,'海城市',493,3,'haichengshi','H',0),(501,210400,'抚顺市',467,2,'fushunshi','F',0),(502,210402,'新抚区',501,3,'xinfuqu','X',0),(503,210403,'东洲区',501,3,'dongzhouqu','D',0),(504,210404,'望花区',501,3,'wanghuaqu','W',0),(505,210411,'顺城区',501,3,'shunchengqu','S',0),(506,210421,'抚顺县',501,3,'fushunxian','F',0),(507,210422,'新宾县',501,3,'xinbinxian','X',0),(508,210423,'清原县',501,3,'qingyuanxian','Q',0),(509,210500,'本溪市',467,2,'benxishi','B',0),(510,210502,'平山区',509,3,'pingshanqu','P',0),(511,210503,'溪湖区',509,3,'xihuqu','X',0),(512,210504,'明山区',509,3,'mingshanqu','M',0),(513,210505,'南芬区',509,3,'nanfenqu','N',0),(514,210521,'本溪县',509,3,'benxixian','B',0),(515,210522,'桓仁县',509,3,'huanrenxian','H',0),(516,210600,'丹东市',467,2,'dandongshi','D',0),(517,210602,'元宝区',516,3,'yuanbaoqu','Y',0),(518,210603,'振兴区',516,3,'zhenxingqu','Z',0),(519,210604,'振安区',516,3,'zhenanqu','Z',0),(520,210624,'宽甸县',516,3,'kuandianxian','K',0),(521,210681,'东港市',516,3,'donggangshi','D',0),(522,210682,'凤城市',516,3,'fengchengshi','F',0),(523,210700,'锦州市',467,2,'jinzhoushi','J',0),(524,210702,'古塔区',523,3,'gutaqu','G',0),(525,210703,'凌河区',523,3,'linghequ','L',0),(526,210711,'太和区',523,3,'taihequ','T',0),(527,210726,'黑山县',523,3,'heishanxian','H',0),(528,210727,'义县',523,3,'yixian','Y',0),(529,210781,'凌海市',523,3,'linghaishi','L',0),(530,210782,'北镇市',523,3,'beizhenshi','B',0),(531,210800,'营口市',467,2,'yingkoushi','Y',0),(532,210802,'站前区',531,3,'zhanqianqu','Z',0),(533,210803,'西市区',531,3,'xishiqu','X',0),(534,210804,'鲅鱼圈区',531,3,'bayuquanqu','B',0),(535,210811,'老边区',531,3,'laobianqu','L',0),(536,210881,'盖州市',531,3,'gaizhoushi','G',0),(537,210882,'大石桥市',531,3,'dashiqiaoshi','D',0),(538,210900,'阜新市',467,2,'fuxinshi','F',0),(539,210902,'海州区',538,3,'haizhouqu','H',0),(540,210903,'新邱区',538,3,'xinqiuqu','X',0),(541,210904,'太平区',538,3,'taipingqu','T',0),(542,210905,'清河门区',538,3,'qinghemenqu','Q',0),(543,210911,'细河区',538,3,'xihequ','X',0),(544,210921,'阜新县',538,3,'fuxinxian','F',0),(545,210922,'彰武县',538,3,'zhangwuxian','Z',0),(546,211000,'辽阳市',467,2,'liaoyangshi','L',0),(547,211002,'白塔区',546,3,'baitaqu','B',0),(548,211003,'文圣区',546,3,'wenshengqu','W',0),(549,211004,'宏伟区',546,3,'hongweiqu','H',0),(550,211005,'弓长岭区',546,3,'gongchanglingqu','G',0),(551,211011,'太子河区',546,3,'taizihequ','T',0),(552,211021,'辽阳县',546,3,'liaoyangxian','L',0),(553,211081,'灯塔市',546,3,'dengtashi','D',0),(554,211100,'盘锦市',467,2,'panjinshi','P',0),(555,211102,'双台子区',554,3,'shuangtaiziqu','S',0),(556,211103,'兴隆台区',554,3,'xinglongtaiqu','X',0),(557,211121,'大洼县',554,3,'dawaxian','D',0),(558,211122,'盘山县',554,3,'panshanxian','P',0),(559,211200,'铁岭市',467,2,'tielingshi','T',0),(560,211202,'银州区',559,3,'yinzhouqu','Y',0),(561,211204,'清河区',559,3,'qinghequ','Q',0),(562,211221,'铁岭县',559,3,'tielingxian','T',0),(563,211223,'西丰县',559,3,'xifengxian','X',0),(564,211224,'昌图县',559,3,'changtuxian','C',0),(565,211281,'调兵山市',559,3,'tiaobingshanshi','T',0),(566,211282,'开原市',559,3,'kaiyuanshi','K',0),(567,211300,'朝阳市',467,2,'zhaoyangshi','Z',0),(568,211302,'双塔区',567,3,'shuangtaqu','S',0),(569,211303,'龙城区',567,3,'longchengqu','L',0),(570,211321,'朝阳县',567,3,'zhaoyangxian','Z',0),(571,211322,'建平县',567,3,'jianpingxian','J',0),(572,211324,'喀喇沁左翼县',567,3,'kalaqinzuoyizuxian','K',0),(573,211381,'北票市',567,3,'beipiaoshi','B',0),(574,211382,'凌源市',567,3,'lingyuanshi','L',0),(575,211400,'葫芦岛市',467,2,'huludaoshi','H',0),(576,211402,'连山区',575,3,'lianshanqu','L',0),(577,211403,'龙港区',575,3,'longgangqu','L',0),(578,211404,'南票区',575,3,'nanpiaoqu','N',0),(579,211421,'绥中县',575,3,'suizhongxian','S',0),(580,211422,'建昌县',575,3,'jianchangxian','J',0),(581,211481,'兴城市',575,3,'xingchengshi','X',0),(582,220000,'吉林',0,1,'jilin','J',0),(583,220100,'长春市',582,2,'changchunshi','C',0),(584,220102,'南关区',583,3,'nanguanqu','N',0),(585,220103,'宽城区',583,3,'kuanchengqu','K',0),(586,220104,'朝阳区',583,3,'zhaoyangqu','Z',0),(587,220105,'二道区',583,3,'erdaoqu','E',0),(588,220106,'绿园区',583,3,'lvyuanqu','L',0),(589,220112,'双阳区',583,3,'shuangyangqu','S',0),(590,220122,'农安县',583,3,'nonganxian','N',0),(591,220181,'九台市',583,3,'jiutaishi','J',0),(592,220182,'榆树市',583,3,'yushushi','Y',0),(593,220183,'德惠市',583,3,'dehuishi','D',0),(594,220200,'吉林市',582,2,'jilinshi','J',0),(595,220202,'昌邑区',594,3,'changyiqu','C',0),(596,220203,'龙潭区',594,3,'longtanqu','L',0),(597,220204,'船营区',594,3,'chuanyingqu','C',0),(598,220211,'丰满区',594,3,'fengmanqu','F',0),(599,220221,'永吉县',594,3,'yongjixian','Y',0),(600,220281,'蛟河市',594,3,'jiaoheshi','J',0),(601,220282,'桦甸市',594,3,'huadianshi','H',0),(602,220283,'舒兰市',594,3,'shulanshi','S',0),(603,220284,'磐石市',594,3,'panshishi','P',0),(604,220300,'四平市',582,2,'sipingshi','S',0),(605,220302,'铁西区',604,3,'tiexiqu','T',0),(606,220303,'铁东区',604,3,'tiedongqu','T',0),(607,220322,'梨树县',604,3,'lishuxian','L',0),(608,220323,'伊通县',604,3,'yitongxian','Y',0),(609,220381,'公主岭市',604,3,'gongzhulingshi','G',0),(610,220382,'双辽市',604,3,'shuangliaoshi','S',0),(611,220400,'辽源市',582,2,'liaoyuanshi','L',0),(612,220402,'龙山区',611,3,'longshanqu','L',0),(613,220403,'西安区',611,3,'xianqu','X',0),(614,220421,'东丰县',611,3,'dongfengxian','D',0),(615,220422,'东辽县',611,3,'dongliaoxian','D',0),(616,220500,'通化市',582,2,'tonghuashi','T',0),(617,220502,'东昌区',616,3,'dongchangqu','D',0),(618,220503,'二道江区',616,3,'erdaojiangqu','E',0),(619,220521,'通化县',616,3,'tonghuaxian','T',0),(620,220523,'辉南县',616,3,'huinanxian','H',0),(621,220524,'柳河县',616,3,'liuhexian','L',0),(622,220581,'梅河口市',616,3,'meihekoushi','M',0),(623,220582,'集安市',616,3,'jianshi','J',0),(624,220600,'白山市',582,2,'baishanshi','B',0),(625,220602,'浑江区',624,3,'hunjiangqu','H',0),(626,220605,'江源区',624,3,'jiangyuanqu','J',0),(627,220621,'抚松县',624,3,'fusongxian','F',0),(628,220622,'靖宇县',624,3,'jingyuxian','J',0),(629,220623,'长白县',624,3,'changbaixian','C',0),(630,220681,'临江市',624,3,'linjiangshi','L',0),(631,220700,'松原市',582,2,'songyuanshi','S',0),(632,220702,'宁江区',631,3,'ningjiangqu','N',0),(633,220721,'前郭县',631,3,'qianguoxian','Q',0),(634,220722,'长岭县',631,3,'changlingxian','C',0),(635,220723,'乾安县',631,3,'qiananxian','Q',0),(636,220781,'扶余市',631,3,'fuyushi','F',0),(637,220800,'白城市',582,2,'baichengshi','B',0),(638,220802,'洮北区',637,3,'taobeiqu','T',0),(639,220821,'镇赉县',637,3,'zhenlaixian','Z',0),(640,220822,'通榆县',637,3,'tongyuxian','T',0),(641,220881,'洮南市',637,3,'taonanshi','T',0),(642,220882,'大安市',637,3,'daanshi','D',0),(643,222400,'延边州',582,2,'yanbianzhou','Y',0),(644,222401,'延吉市',643,3,'yanjishi','Y',0),(645,222402,'图们市',643,3,'tumenshi','T',0),(646,222403,'敦化市',643,3,'dunhuashi','D',0),(647,222404,'珲春市',643,3,'hunchunshi','H',0),(648,222405,'龙井市',643,3,'longjingshi','L',0),(649,222406,'和龙市',643,3,'helongshi','H',0),(650,222424,'汪清县',643,3,'wangqingxian','W',0),(651,222426,'安图县',643,3,'antuxian','A',0),(652,230000,'黑龙江',0,1,'heilongjiang','H',0),(653,230100,'哈尔滨市',652,2,'haerbinshi','H',0),(654,230102,'道里区',653,3,'daoliqu','D',0),(655,230103,'南岗区',653,3,'nangangqu','N',0),(656,230104,'道外区',653,3,'daowaiqu','D',0),(657,230108,'平房区',653,3,'pingfangqu','P',0),(658,230109,'松北区',653,3,'songbeiqu','S',0),(659,230110,'香坊区',653,3,'xiangfangqu','X',0),(660,230111,'呼兰区',653,3,'hulanqu','H',0),(661,230112,'阿城区',653,3,'achengqu','A',0),(662,230123,'依兰县',653,3,'yilanxian','Y',0),(663,230124,'方正县',653,3,'fangzhengxian','F',0),(664,230125,'宾县',653,3,'binxian','B',0),(665,230126,'巴彦县',653,3,'bayanxian','B',0),(666,230127,'木兰县',653,3,'mulanxian','M',0),(667,230128,'通河县',653,3,'tonghexian','T',0),(668,230129,'延寿县',653,3,'yanshouxian','Y',0),(669,230182,'双城市',653,3,'shuangchengshi','S',0),(670,230183,'尚志市',653,3,'shangzhishi','S',0),(671,230184,'五常市',653,3,'wuchangshi','W',0),(672,230200,'齐齐哈尔市',652,2,'qiqihaershi','Q',0),(673,230202,'龙沙区',672,3,'longshaqu','L',0),(674,230203,'建华区',672,3,'jianhuaqu','J',0),(675,230204,'铁锋区',672,3,'tiefengqu','T',0),(676,230205,'昂昂溪区',672,3,'angangxiqu','A',0),(677,230206,'富拉尔基区',672,3,'fulaerjiqu','F',0),(678,230207,'碾子山区',672,3,'nianzishanqu','N',0),(679,230208,'梅里斯区',672,3,'meilisiqu','M',0),(680,230221,'龙江县',672,3,'longjiangxian','L',0),(681,230223,'依安县',672,3,'yianxian','Y',0),(682,230224,'泰来县',672,3,'tailaixian','T',0),(683,230225,'甘南县',672,3,'gannanxian','G',0),(684,230227,'富裕县',672,3,'fuyuxian','F',0),(685,230229,'克山县',672,3,'keshanxian','K',0),(686,230230,'克东县',672,3,'kedongxian','K',0),(687,230231,'拜泉县',672,3,'baiquanxian','B',0),(688,230281,'讷河市',672,3,'neheshi','N',0),(689,230300,'鸡西市',652,2,'jixishi','J',0),(690,230302,'鸡冠区',689,3,'jiguanqu','J',0),(691,230303,'恒山区',689,3,'hengshanqu','H',0),(692,230304,'滴道区',689,3,'didaoqu','D',0),(693,230305,'梨树区',689,3,'lishuqu','L',0),(694,230306,'城子河区',689,3,'chengzihequ','C',0),(695,230307,'麻山区',689,3,'mashanqu','M',0),(696,230321,'鸡东县',689,3,'jidongxian','J',0),(697,230381,'虎林市',689,3,'hulinshi','H',0),(698,230382,'密山市',689,3,'mishanshi','M',0),(699,230400,'鹤岗市',652,2,'hegangshi','H',0),(700,230402,'向阳区',699,3,'xiangyangqu','X',0),(701,230403,'工农区',699,3,'gongnongqu','G',0),(702,230404,'南山区',699,3,'nanshanqu','N',0),(703,230405,'兴安区',699,3,'xinganqu','X',0),(704,230406,'东山区',699,3,'dongshanqu','D',0),(705,230407,'兴山区',699,3,'xingshanqu','X',0),(706,230421,'萝北县',699,3,'luobeixian','L',0),(707,230422,'绥滨县',699,3,'suibinxian','S',0),(708,230500,'双鸭山市',652,2,'shuangyashanshi','S',0),(709,230502,'尖山区',708,3,'jianshanqu','J',0),(710,230503,'岭东区',708,3,'lingdongqu','L',0),(711,230505,'四方台区',708,3,'sifangtaiqu','S',0),(712,230506,'宝山区',708,3,'baoshanqu','B',0),(713,230521,'集贤县',708,3,'jixianxian','J',0),(714,230522,'友谊县',708,3,'youyixian','Y',0),(715,230523,'宝清县',708,3,'baoqingxian','B',0),(716,230524,'饶河县',708,3,'raohexian','R',0),(717,230600,'大庆市',652,2,'daqingshi','D',0),(718,230602,'萨尔图区',717,3,'saertuqu','S',0),(719,230603,'龙凤区',717,3,'longfengqu','L',0),(720,230604,'让胡路区',717,3,'ranghuluqu','R',0),(721,230605,'红岗区',717,3,'honggangqu','H',0),(722,230606,'大同区',717,3,'datongqu','D',0),(723,230621,'肇州县',717,3,'zhaozhouxian','Z',0),(724,230622,'肇源县',717,3,'zhaoyuanxian','Z',0),(725,230623,'林甸县',717,3,'lindianxian','L',0),(726,230624,'杜尔伯特县',717,3,'duerbotexian','D',0),(727,230700,'伊春市',652,2,'yichunshi','Y',0),(728,230702,'伊春区',727,3,'yichunqu','Y',0),(729,230703,'南岔区',727,3,'nanchaqu','N',0),(730,230704,'友好区',727,3,'youhaoqu','Y',0),(731,230705,'西林区',727,3,'xilinqu','X',0),(732,230706,'翠峦区',727,3,'cuiluanqu','C',0),(733,230707,'新青区',727,3,'xinqingqu','X',0),(734,230708,'美溪区',727,3,'meixiqu','M',0),(735,230709,'金山屯区',727,3,'jinshantunqu','J',0),(736,230710,'五营区',727,3,'wuyingqu','W',0),(737,230711,'乌马河区',727,3,'wumahequ','W',0),(738,230712,'汤旺河区',727,3,'tangwanghequ','T',0),(739,230713,'带岭区',727,3,'dailingqu','D',0),(740,230714,'乌伊岭区',727,3,'wuyilingqu','W',0),(741,230715,'红星区',727,3,'hongxingqu','H',0),(742,230716,'上甘岭区',727,3,'shangganlingqu','S',0),(743,230722,'嘉荫县',727,3,'jiayinxian','J',0),(744,230781,'铁力市',727,3,'tielishi','T',0),(745,230800,'佳木斯市',652,2,'jiamusishi','J',0),(746,230803,'向阳区',745,3,'xiangyangqu','X',0),(747,230804,'前进区',745,3,'qianjinqu','Q',0),(748,230805,'东风区',745,3,'dongfengqu','D',0),(749,230811,'郊区',745,3,'jiaoqu','J',0),(750,230822,'桦南县',745,3,'huananxian','H',0),(751,230826,'桦川县',745,3,'huachuanxian','H',0),(752,230828,'汤原县',745,3,'tangyuanxian','T',0),(753,230833,'抚远县',745,3,'fuyuanxian','F',0),(754,230881,'同江市',745,3,'tongjiangshi','T',0),(755,230882,'富锦市',745,3,'fujinshi','F',0),(756,230900,'七台河市',652,2,'qitaiheshi','Q',0),(757,230902,'新兴区',756,3,'xinxingqu','X',0),(758,230903,'桃山区',756,3,'taoshanqu','T',0),(759,230904,'茄子河区',756,3,'qiezihequ','Q',0),(760,230921,'勃利县',756,3,'bolixian','B',0),(761,231000,'牡丹江市',652,2,'mudanjiangshi','M',0),(762,231002,'东安区',761,3,'donganqu','D',0),(763,231003,'阳明区',761,3,'yangmingqu','Y',0),(764,231004,'爱民区',761,3,'aiminqu','A',0),(765,231005,'西安区',761,3,'xianqu','X',0),(766,231024,'东宁县',761,3,'dongningxian','D',0),(767,231025,'林口县',761,3,'linkouxian','L',0),(768,231081,'绥芬河市',761,3,'suifenheshi','S',0),(769,231083,'海林市',761,3,'hailinshi','H',0),(770,231084,'宁安市',761,3,'ninganshi','N',0),(771,231085,'穆棱市',761,3,'mulengshi','M',0),(772,231100,'黑河市',652,2,'heiheshi','H',0),(773,231102,'爱辉区',772,3,'aihuiqu','A',0),(774,231121,'嫩江县',772,3,'nenjiangxian','N',0),(775,231123,'逊克县',772,3,'xunkexian','X',0),(776,231124,'孙吴县',772,3,'sunwuxian','S',0),(777,231181,'北安市',772,3,'beianshi','B',0),(778,231182,'五大连池市',772,3,'wudalianchishi','W',0),(779,231200,'绥化市',652,2,'suihuashi','S',0),(780,231202,'北林区',779,3,'beilinqu','B',0),(781,231221,'望奎县',779,3,'wangkuixian','W',0),(782,231222,'兰西县',779,3,'lanxixian','L',0),(783,231223,'青冈县',779,3,'qinggangxian','Q',0),(784,231224,'庆安县',779,3,'qinganxian','Q',0),(785,231225,'明水县',779,3,'mingshuixian','M',0),(786,231226,'绥棱县',779,3,'suilengxian','S',0),(787,231281,'安达市',779,3,'andashi','A',0),(788,231282,'肇东市',779,3,'zhaodongshi','Z',0),(789,231283,'海伦市',779,3,'hailunshi','H',0),(790,232700,'大兴安岭地区',652,2,'daxinganlingdiqu','D',0),(791,232721,'呼玛县',790,3,'humaxian','H',0),(792,232722,'塔河县',790,3,'tahexian','T',0),(793,232723,'漠河县',790,3,'mohexian','M',0),(794,310000,'上海',0,1,'shanghai','S',0),(795,310100,'上海市',794,2,'shanghaishi','S',0),(796,310101,'黄浦区',795,3,'huangpuqu','H',0),(797,310104,'徐汇区',795,3,'xuhuiqu','X',0),(798,310105,'长宁区',795,3,'changningqu','C',0),(799,310106,'静安区',795,3,'jinganqu','J',0),(800,310107,'普陀区',795,3,'putuoqu','P',0),(801,310108,'闸北区',795,3,'zhabeiqu','Z',0),(802,310109,'虹口区',795,3,'hongkouqu','H',0),(803,310110,'杨浦区',795,3,'yangpuqu','Y',0),(804,310112,'闵行区',795,3,'minhangqu','M',0),(805,310113,'宝山区',795,3,'baoshanqu','B',0),(806,310114,'嘉定区',795,3,'jiadingqu','J',0),(807,310115,'浦东新区',795,3,'pudongxinqu','P',0),(808,310116,'金山区',795,3,'jinshanqu','J',0),(809,310117,'松江区',795,3,'songjiangqu','S',0),(810,310118,'青浦区',795,3,'qingpuqu','Q',0),(811,310120,'奉贤区',795,3,'fengxianqu','F',0),(812,310230,'崇明县',795,3,'chongmingxian','C',0),(813,320000,'江苏',0,1,'jiangsu','J',0),(814,320100,'南京市',813,2,'nanjingshi','N',0),(815,320102,'玄武区',814,3,'xuanwuqu','X',0),(816,320104,'秦淮区',814,3,'qinhuaiqu','Q',0),(817,320105,'建邺区',814,3,'jianyequ','J',0),(818,320106,'鼓楼区',814,3,'gulouqu','G',0),(819,320111,'浦口区',814,3,'pukouqu','P',0),(820,320113,'栖霞区',814,3,'qixiaqu','Q',0),(821,320114,'雨花台区',814,3,'yuhuataiqu','Y',0),(822,320115,'江宁区',814,3,'jiangningqu','J',0),(823,320116,'六合区',814,3,'liuhequ','L',0),(824,320117,'溧水区',814,3,'lishuiqu','L',0),(825,320118,'高淳区',814,3,'gaochunqu','G',0),(826,320200,'无锡市',813,2,'wuxishi','W',0),(827,320202,'崇安区',826,3,'chonganqu','C',0),(828,320203,'南长区',826,3,'nanchangqu','N',0),(829,320204,'北塘区',826,3,'beitangqu','B',0),(830,320205,'锡山区',826,3,'xishanqu','X',0),(831,320206,'惠山区',826,3,'huishanqu','H',0),(832,320211,'滨湖区',826,3,'binhuqu','B',0),(833,320281,'江阴市',826,3,'jiangyinshi','J',0),(834,320282,'宜兴市',826,3,'yixingshi','Y',0),(835,320300,'徐州市',813,2,'xuzhoushi','X',0),(836,320302,'鼓楼区',835,3,'gulouqu','G',0),(837,320303,'云龙区',835,3,'yunlongqu','Y',0),(838,320305,'贾汪区',835,3,'guwangqu','G',0),(839,320311,'泉山区',835,3,'quanshanqu','Q',0),(840,320312,'铜山区',835,3,'tongshanqu','T',0),(841,320321,'丰县',835,3,'fengxian','F',0),(842,320322,'沛县',835,3,'peixian','P',0),(843,320324,'睢宁县',835,3,'huiningxian','H',0),(844,320381,'新沂市',835,3,'xinyishi','X',0),(845,320382,'邳州市',835,3,'pizhoushi','P',0),(846,320400,'常州市',813,2,'changzhoushi','C',0),(847,320402,'天宁区',846,3,'tianningqu','T',0),(848,320404,'钟楼区',846,3,'zhonglouqu','Z',0),(849,320405,'戚墅堰区',846,3,'qishuyanqu','Q',0),(850,320411,'新北区',846,3,'xinbeiqu','X',0),(851,320412,'武进区',846,3,'wujinqu','W',0),(852,320481,'溧阳市',846,3,'liyangshi','L',0),(853,320482,'金坛市',846,3,'jintanshi','J',0),(854,320500,'苏州市',813,2,'suzhoushi','S',0),(855,320505,'虎丘区',854,3,'huqiuqu','H',0),(856,320506,'吴中区',854,3,'wuzhongqu','W',0),(857,320507,'相城区',854,3,'xiangchengqu','X',0),(858,320508,'姑苏区',854,3,'gusuqu','G',0),(859,320509,'吴江区',854,3,'wujiangqu','W',0),(860,320581,'常熟市',854,3,'changshushi','C',0),(861,320582,'张家港市',854,3,'zhangjiagangshi','Z',0),(862,320583,'昆山市',854,3,'kunshanshi','K',0),(863,320585,'太仓市',854,3,'taicangshi','T',0),(864,320600,'南通市',813,2,'nantongshi','N',0),(865,320602,'崇川区',864,3,'chongchuanqu','C',0),(866,320611,'港闸区',864,3,'gangzhaqu','G',0),(867,320612,'通州区',864,3,'tongzhouqu','T',0),(868,320621,'海安县',864,3,'haianxian','H',0),(869,320623,'如东县',864,3,'rudongxian','R',0),(870,320681,'启东市',864,3,'qidongshi','Q',0),(871,320682,'如皋市',864,3,'rugaoshi','R',0),(872,320684,'海门市',864,3,'haimenshi','H',0),(873,320700,'连云港市',813,2,'lianyungangshi','L',0),(874,320703,'连云区',873,3,'lianyunqu','L',0),(875,320705,'新浦区',873,3,'xinpuqu','X',0),(876,320706,'海州区',873,3,'haizhouqu','H',0),(877,320721,'赣榆县',873,3,'ganyuxian','G',0),(878,320722,'东海县',873,3,'donghaixian','D',0),(879,320723,'灌云县',873,3,'guanyunxian','G',0),(880,320724,'灌南县',873,3,'guannanxian','G',0),(881,320800,'淮安市',813,2,'huaianshi','H',0),(882,320802,'清河区',881,3,'qinghequ','Q',0),(883,320803,'淮安区',881,3,'huaianqu','H',0),(884,320804,'淮阴区',881,3,'huaiyinqu','H',0),(885,320811,'清浦区',881,3,'qingpuqu','Q',0),(886,320826,'涟水县',881,3,'lianshuixian','L',0),(887,320829,'洪泽县',881,3,'hongzexian','H',0),(888,320830,'盱眙县',881,3,'xuyixian','X',0),(889,320831,'金湖县',881,3,'jinhuxian','J',0),(890,320900,'盐城市',813,2,'yanchengshi','Y',0),(891,320902,'亭湖区',890,3,'tinghuqu','T',0),(892,320903,'盐都区',890,3,'yanduqu','Y',0),(893,320921,'响水县',890,3,'xiangshuixian','X',0),(894,320922,'滨海县',890,3,'binhaixian','B',0),(895,320923,'阜宁县',890,3,'funingxian','F',0),(896,320924,'射阳县',890,3,'sheyangxian','S',0),(897,320925,'建湖县',890,3,'jianhuxian','J',0),(898,320981,'东台市',890,3,'dongtaishi','D',0),(899,320982,'大丰市',890,3,'dafengshi','D',0),(900,321000,'扬州市',813,2,'yangzhoushi','Y',0),(901,321002,'广陵区',900,3,'guanglingqu','G',0),(902,321003,'邗江区',900,3,'hanjiangqu','H',0),(903,321012,'江都区',900,3,'jiangduqu','J',0),(904,321023,'宝应县',900,3,'baoyingxian','B',0),(905,321081,'仪征市',900,3,'yizhengshi','Y',0),(906,321084,'高邮市',900,3,'gaoyoushi','G',0),(907,321100,'镇江市',813,2,'zhenjiangshi','Z',0),(908,321102,'京口区',907,3,'jingkouqu','J',0),(909,321111,'润州区',907,3,'runzhouqu','R',0),(910,321112,'丹徒区',907,3,'dantuqu','D',0),(911,321181,'丹阳市',907,3,'danyangshi','D',0),(912,321182,'扬中市',907,3,'yangzhongshi','Y',0),(913,321183,'句容市',907,3,'jurongshi','J',0),(914,321200,'泰州市',813,2,'taizhoushi','T',0),(915,321202,'海陵区',914,3,'hailingqu','H',0),(916,321203,'高港区',914,3,'gaogangqu','G',0),(917,321204,'姜堰区',914,3,'jiangyanqu','J',0),(918,321281,'兴化市',914,3,'xinghuashi','X',0),(919,321282,'靖江市',914,3,'jingjiangshi','J',0),(920,321283,'泰兴市',914,3,'taixingshi','T',0),(921,321300,'宿迁市',813,2,'suqianshi','S',0),(922,321302,'宿城区',921,3,'suchengqu','S',0),(923,321311,'宿豫区',921,3,'suyuqu','S',0),(924,321322,'沭阳县',921,3,'shuyangxian','S',0),(925,321323,'泗阳县',921,3,'siyangxian','S',0),(926,321324,'泗洪县',921,3,'sihongxian','S',0),(927,330000,'浙江',0,1,'zhejiang','Z',0),(928,330100,'杭州市',927,2,'hangzhoushi','H',0),(929,330102,'上城区',928,3,'shangchengqu','S',0),(930,330103,'下城区',928,3,'xiachengqu','X',0),(931,330104,'江干区',928,3,'jiangganqu','J',0),(932,330105,'拱墅区',928,3,'gongshuqu','G',0),(933,330106,'西湖区',928,3,'xihuqu','X',0),(934,330108,'滨江区',928,3,'binjiangqu','B',0),(935,330109,'萧山区',928,3,'xiaoshanqu','X',0),(936,330110,'余杭区',928,3,'yuhangqu','Y',0),(937,330122,'桐庐县',928,3,'tongluxian','T',0),(938,330127,'淳安县',928,3,'chunanxian','C',0),(939,330182,'建德市',928,3,'jiandeshi','J',0),(940,330183,'富阳市',928,3,'fuyangshi','F',0),(941,330185,'临安市',928,3,'linanshi','L',0),(942,330200,'宁波市',927,2,'ningboshi','N',0),(943,330203,'海曙区',942,3,'haishuqu','H',0),(944,330204,'江东区',942,3,'jiangdongqu','J',0),(945,330205,'江北区',942,3,'jiangbeiqu','J',0),(946,330206,'北仑区',942,3,'beilunqu','B',0),(947,330211,'镇海区',942,3,'zhenhaiqu','Z',0),(948,330212,'鄞州区',942,3,'yinzhouqu','Y',0),(949,330225,'象山县',942,3,'xiangshanxian','X',0),(950,330226,'宁海县',942,3,'ninghaixian','N',0),(951,330281,'余姚市',942,3,'yuyaoshi','Y',0),(952,330282,'慈溪市',942,3,'cixishi','C',0),(953,330283,'奉化市',942,3,'fenghuashi','F',0),(954,330300,'温州市',927,2,'wenzhoushi','W',0),(955,330302,'鹿城区',954,3,'luchengqu','L',0),(956,330303,'龙湾区',954,3,'longwanqu','L',0),(957,330304,'瓯海区',954,3,'ouhaiqu','O',0),(958,330322,'洞头县',954,3,'dongtouxian','D',0),(959,330324,'永嘉县',954,3,'yongjiaxian','Y',0),(960,330326,'平阳县',954,3,'pingyangxian','P',0),(961,330327,'苍南县',954,3,'cangnanxian','C',0),(962,330328,'文成县',954,3,'wenchengxian','W',0),(963,330329,'泰顺县',954,3,'taishunxian','T',0),(964,330381,'瑞安市',954,3,'ruianshi','R',0),(965,330382,'乐清市',954,3,'leqingshi','L',0),(966,330400,'嘉兴市',927,2,'jiaxingshi','J',0),(967,330402,'南湖区',966,3,'nanhuqu','N',0),(968,330411,'秀洲区',966,3,'xiuzhouqu','X',0),(969,330421,'嘉善县',966,3,'jiashanxian','J',0),(970,330424,'海盐县',966,3,'haiyanxian','H',0),(971,330481,'海宁市',966,3,'hainingshi','H',0),(972,330482,'平湖市',966,3,'pinghushi','P',0),(973,330483,'桐乡市',966,3,'tongxiangshi','T',0),(974,330500,'湖州市',927,2,'huzhoushi','H',0),(975,330502,'吴兴区',974,3,'wuxingqu','W',0),(976,330503,'南浔区',974,3,'nanxunqu','N',0),(977,330521,'德清县',974,3,'deqingxian','D',0),(978,330522,'长兴县',974,3,'changxingxian','C',0),(979,330523,'安吉县',974,3,'anjixian','A',0),(980,330600,'绍兴市',927,2,'shaoxingshi','S',0),(981,330602,'越城区',980,3,'yuechengqu','Y',0),(982,330621,'绍兴县',980,3,'shaoxingxian','S',0),(983,330624,'新昌县',980,3,'xinchangxian','X',0),(984,330681,'诸暨市',980,3,'zhujishi','Z',0),(985,330682,'上虞市',980,3,'shangyushi','S',0),(986,330683,'嵊州市',980,3,'shengzhoushi','S',0),(987,330700,'金华市',927,2,'jinhuashi','J',0),(988,330702,'婺城区',987,3,'wuchengqu','W',0),(989,330703,'金东区',987,3,'jindongqu','J',0),(990,330723,'武义县',987,3,'wuyixian','W',0),(991,330726,'浦江县',987,3,'pujiangxian','P',0),(992,330727,'磐安县',987,3,'pananxian','P',0),(993,330781,'兰溪市',987,3,'lanxishi','L',0),(994,330782,'义乌市',987,3,'yiwushi','Y',0),(995,330783,'东阳市',987,3,'dongyangshi','D',0),(996,330784,'永康市',987,3,'yongkangshi','Y',0),(997,330800,'衢州市',927,2,'quzhoushi','Q',0),(998,330802,'柯城区',997,3,'kechengqu','K',0),(999,330803,'衢江区',997,3,'qujiangqu','Q',0),(1000,330822,'常山县',997,3,'changshanxian','C',0),(1001,330824,'开化县',997,3,'kaihuaxian','K',0),(1002,330825,'龙游县',997,3,'longyouxian','L',0),(1003,330881,'江山市',997,3,'jiangshanshi','J',0),(1004,330900,'舟山市',927,2,'zhoushanshi','Z',0),(1005,330902,'定海区',1004,3,'dinghaiqu','D',0),(1006,330903,'普陀区',1004,3,'putuoqu','P',0),(1007,330921,'岱山县',1004,3,'daishanxian','D',0),(1008,330922,'嵊泗县',1004,3,'shengsixian','S',0),(1009,331000,'台州市',927,2,'taizhoushi','T',0),(1010,331002,'椒江区',1009,3,'jiaojiangqu','J',0),(1011,331003,'黄岩区',1009,3,'huangyanqu','H',0),(1012,331004,'路桥区',1009,3,'luqiaoqu','L',0),(1013,331021,'玉环县',1009,3,'yuhuanxian','Y',0),(1014,331022,'三门县',1009,3,'sanmenxian','S',0),(1015,331023,'天台县',1009,3,'tiantaixian','T',0),(1016,331024,'仙居县',1009,3,'xianjuxian','X',0),(1017,331081,'温岭市',1009,3,'wenlingshi','W',0),(1018,331082,'临海市',1009,3,'linhaishi','L',0),(1019,331100,'丽水市',927,2,'lishuishi','L',0),(1020,331102,'莲都区',1019,3,'lianduqu','L',0),(1021,331121,'青田县',1019,3,'qingtianxian','Q',0),(1022,331122,'缙云县',1019,3,'jinyunxian','J',0),(1023,331123,'遂昌县',1019,3,'suichangxian','S',0),(1024,331124,'松阳县',1019,3,'songyangxian','S',0),(1025,331125,'云和县',1019,3,'yunhexian','Y',0),(1026,331126,'庆元县',1019,3,'qingyuanxian','Q',0),(1027,331127,'景宁县',1019,3,'jingningxian','J',0),(1028,331181,'龙泉市',1019,3,'longquanshi','L',0),(1029,340000,'安徽',0,1,'anhui','A',0),(1030,340100,'合肥市',1029,2,'hefeishi','H',0),(1031,340102,'瑶海区',1030,3,'yaohaiqu','Y',0),(1032,340103,'庐阳区',1030,3,'luyangqu','L',0),(1033,340104,'蜀山区',1030,3,'shushanqu','S',0),(1034,340111,'包河区',1030,3,'baohequ','B',0),(1035,340121,'长丰县',1030,3,'changfengxian','C',0),(1036,340122,'肥东县',1030,3,'feidongxian','F',0),(1037,340123,'肥西县',1030,3,'feixixian','F',0),(1038,340124,'庐江县',1030,3,'lujiangxian','L',0),(1039,340181,'巢湖市',1030,3,'chaohushi','C',0),(1040,340200,'芜湖市',1029,2,'wuhushi','W',0),(1041,340202,'镜湖区',1040,3,'jinghuqu','J',0),(1042,340203,'弋江区',1040,3,'yijiangqu','Y',0),(1043,340207,'鸠江区',1040,3,'jiujiangqu','J',0),(1044,340208,'三山区',1040,3,'sanshanqu','S',0),(1045,340221,'芜湖县',1040,3,'wuhuxian','W',0),(1046,340222,'繁昌县',1040,3,'fanchangxian','F',0),(1047,340223,'南陵县',1040,3,'nanlingxian','N',0),(1048,340225,'无为县',1040,3,'wuweixian','W',0),(1049,340300,'蚌埠市',1029,2,'bengbushi','B',0),(1050,340302,'龙子湖区',1049,3,'longzihuqu','L',0),(1051,340303,'蚌山区',1049,3,'bangshanqu','B',0),(1052,340304,'禹会区',1049,3,'yuhuiqu','Y',0),(1053,340311,'淮上区',1049,3,'huaishangqu','H',0),(1054,340321,'怀远县',1049,3,'huaiyuanxian','H',0),(1055,340322,'五河县',1049,3,'wuhexian','W',0),(1056,340323,'固镇县',1049,3,'guzhenxian','G',0),(1057,340400,'淮南市',1029,2,'huainanshi','H',0),(1058,340402,'大通区',1057,3,'datongqu','D',0),(1059,340403,'田家庵区',1057,3,'tianjiaanqu','T',0),(1060,340404,'谢家集区',1057,3,'xiejiajiqu','X',0),(1061,340405,'八公山区',1057,3,'bagongshanqu','B',0),(1062,340406,'潘集区',1057,3,'panjiqu','P',0),(1063,340421,'凤台县',1057,3,'fengtaixian','F',0),(1064,340500,'马鞍山市',1029,2,'maanshanshi','M',0),(1065,340503,'花山区',1064,3,'huashanqu','H',0),(1066,340504,'雨山区',1064,3,'yushanqu','Y',0),(1067,340506,'博望区',1064,3,'bowangqu','B',0),(1068,340521,'当涂县',1064,3,'dangtuxian','D',0),(1069,340522,'含山县',1064,3,'hanshanxian','H',0),(1070,340523,'和县',1064,3,'hexian','H',0),(1071,340600,'淮北市',1029,2,'huaibeishi','H',0),(1072,340602,'杜集区',1071,3,'dujiqu','D',0),(1073,340603,'相山区',1071,3,'xiangshanqu','X',0),(1074,340604,'烈山区',1071,3,'lieshanqu','L',0),(1075,340621,'濉溪县',1071,3,'suixixian','S',0),(1076,340700,'铜陵市',1029,2,'tonglingshi','T',0),(1077,340702,'铜官山区',1076,3,'tongguanshanqu','T',0),(1078,340703,'狮子山区',1076,3,'shizishanqu','S',0),(1079,340711,'郊区',1076,3,'jiaoqu','J',0),(1080,340721,'铜陵县',1076,3,'tonglingxian','T',0),(1081,340800,'安庆市',1029,2,'anqingshi','A',0),(1082,340802,'迎江区',1081,3,'yingjiangqu','Y',0),(1083,340803,'大观区',1081,3,'daguanqu','D',0),(1084,340811,'宜秀区',1081,3,'yixiuqu','Y',0),(1085,340822,'怀宁县',1081,3,'huainingxian','H',0),(1086,340823,'枞阳县',1081,3,'congyangxian','C',0),(1087,340824,'潜山县',1081,3,'qianshanxian','Q',0),(1088,340825,'太湖县',1081,3,'taihuxian','T',0),(1089,340826,'宿松县',1081,3,'susongxian','S',0),(1090,340827,'望江县',1081,3,'wangjiangxian','W',0),(1091,340828,'岳西县',1081,3,'yuexixian','Y',0),(1092,340881,'桐城市',1081,3,'tongchengshi','T',0),(1093,341000,'黄山市',1029,2,'huangshanshi','H',0),(1094,341002,'屯溪区',1093,3,'tunxiqu','T',0),(1095,341003,'黄山区',1093,3,'huangshanqu','H',0),(1096,341004,'徽州区',1093,3,'huizhouqu','H',0),(1097,341021,'歙县',1093,3,'xixian','X',0),(1098,341022,'休宁县',1093,3,'xiuningxian','X',0),(1099,341023,'黟县',1093,3,'yixian','Y',0),(1100,341024,'祁门县',1093,3,'qimenxian','Q',0),(1101,341100,'滁州市',1029,2,'chuzhoushi','C',0),(1102,341102,'琅琊区',1101,3,'langyaqu','L',0),(1103,341103,'南谯区',1101,3,'nanqiaoqu','N',0),(1104,341122,'来安县',1101,3,'laianxian','L',0),(1105,341124,'全椒县',1101,3,'quanjiaoxian','Q',0),(1106,341125,'定远县',1101,3,'dingyuanxian','D',0),(1107,341126,'凤阳县',1101,3,'fengyangxian','F',0),(1108,341181,'天长市',1101,3,'tianchangshi','T',0),(1109,341182,'明光市',1101,3,'mingguangshi','M',0),(1110,341200,'阜阳市',1029,2,'fuyangshi','F',0),(1111,341202,'颍州区',1110,3,'yingzhouqu','Y',0),(1112,341203,'颍东区',1110,3,'yingdongqu','Y',0),(1113,341204,'颍泉区',1110,3,'yingquanqu','Y',0),(1114,341221,'临泉县',1110,3,'linquanxian','L',0),(1115,341222,'太和县',1110,3,'taihexian','T',0),(1116,341225,'阜南县',1110,3,'funanxian','F',0),(1117,341226,'颍上县',1110,3,'yingshangxian','Y',0),(1118,341282,'界首市',1110,3,'jieshoushi','J',0),(1119,341300,'宿州市',1029,2,'suzhoushi','S',0),(1120,341302,'埇桥区',1119,3,'yongqiaoqu','Y',0),(1121,341321,'砀山县',1119,3,'dangshanxian','D',0),(1122,341322,'萧县',1119,3,'xiaoxian','X',0),(1123,341323,'灵璧县',1119,3,'lingbixian','L',0),(1124,341324,'泗县',1119,3,'sixian','S',0),(1125,341500,'六安市',1029,2,'liuanshi','L',0),(1126,341502,'金安区',1125,3,'jinanqu','J',0),(1127,341503,'裕安区',1125,3,'yuanqu','Y',0),(1128,341521,'寿县',1125,3,'shouxian','S',0),(1129,341522,'霍邱县',1125,3,'huoqiuxian','H',0),(1130,341523,'舒城县',1125,3,'shuchengxian','S',0),(1131,341524,'金寨县',1125,3,'jinzhaixian','J',0),(1132,341525,'霍山县',1125,3,'huoshanxian','H',0),(1133,341600,'亳州市',1029,2,'bozhoushi','B',0),(1134,341602,'谯城区',1133,3,'qiaochengqu','Q',0),(1135,341621,'涡阳县',1133,3,'woyangxian','W',0),(1136,341622,'蒙城县',1133,3,'mengchengxian','M',0),(1137,341623,'利辛县',1133,3,'lixinxian','L',0),(1138,341700,'池州市',1029,2,'chizhoushi','C',0),(1139,341702,'贵池区',1138,3,'guichiqu','G',0),(1140,341721,'东至县',1138,3,'dongzhixian','D',0),(1141,341722,'石台县',1138,3,'shitaixian','S',0),(1142,341723,'青阳县',1138,3,'qingyangxian','Q',0),(1143,341800,'宣城市',1029,2,'xuanchengshi','X',0),(1144,341802,'宣州区',1143,3,'xuanzhouqu','X',0),(1145,341821,'郎溪县',1143,3,'langxixian','L',0),(1146,341822,'广德县',1143,3,'guangdexian','G',0),(1147,341823,'泾县',1143,3,'jingxian','J',0),(1148,341824,'绩溪县',1143,3,'jixixian','J',0),(1149,341825,'旌德县',1143,3,'jingdexian','J',0),(1150,341881,'宁国市',1143,3,'ningguoshi','N',0),(1151,350000,'福建',0,1,'fujian','F',0),(1152,350100,'福州市',1151,2,'fuzhoushi','F',0),(1153,350102,'鼓楼区',1152,3,'gulouqu','G',0),(1154,350103,'台江区',1152,3,'taijiangqu','T',0),(1155,350104,'仓山区',1152,3,'cangshanqu','C',0),(1156,350105,'马尾区',1152,3,'maweiqu','M',0),(1157,350111,'晋安区',1152,3,'jinanqu','J',0),(1158,350121,'闽侯县',1152,3,'minhouxian','M',0),(1159,350122,'连江县',1152,3,'lianjiangxian','L',0),(1160,350123,'罗源县',1152,3,'luoyuanxian','L',0),(1161,350124,'闽清县',1152,3,'minqingxian','M',0),(1162,350125,'永泰县',1152,3,'yongtaixian','Y',0),(1163,350128,'平潭县',1152,3,'pingtanxian','P',0),(1164,350181,'福清市',1152,3,'fuqingshi','F',0),(1165,350182,'长乐市',1152,3,'changleshi','C',0),(1166,350200,'厦门市',1151,2,'shamenshi','S',0),(1167,350203,'思明区',1166,3,'simingqu','S',0),(1168,350205,'海沧区',1166,3,'haicangqu','H',0),(1169,350206,'湖里区',1166,3,'huliqu','H',0),(1170,350211,'集美区',1166,3,'jimeiqu','J',0),(1171,350212,'同安区',1166,3,'tonganqu','T',0),(1172,350213,'翔安区',1166,3,'xianganqu','X',0),(1173,350300,'莆田市',1151,2,'putianshi','P',0),(1174,350302,'城厢区',1173,3,'chengxiangqu','C',0),(1175,350303,'涵江区',1173,3,'hanjiangqu','H',0),(1176,350304,'荔城区',1173,3,'lichengqu','L',0),(1177,350305,'秀屿区',1173,3,'xiuyuqu','X',0),(1178,350322,'仙游县',1173,3,'xianyouxian','X',0),(1179,350400,'三明市',1151,2,'sanmingshi','S',0),(1180,350402,'梅列区',1179,3,'meiliequ','M',0),(1181,350403,'三元区',1179,3,'sanyuanqu','S',0),(1182,350421,'明溪县',1179,3,'mingxixian','M',0),(1183,350423,'清流县',1179,3,'qingliuxian','Q',0),(1184,350424,'宁化县',1179,3,'ninghuaxian','N',0),(1185,350425,'大田县',1179,3,'datianxian','D',0),(1186,350426,'尤溪县',1179,3,'youxixian','Y',0),(1187,350427,'沙县',1179,3,'shaxian','S',0),(1188,350428,'将乐县',1179,3,'jianglexian','J',0),(1189,350429,'泰宁县',1179,3,'tainingxian','T',0),(1190,350430,'建宁县',1179,3,'jianningxian','J',0),(1191,350481,'永安市',1179,3,'yonganshi','Y',0),(1192,350500,'泉州市',1151,2,'quanzhoushi','Q',0),(1193,350502,'鲤城区',1192,3,'lichengqu','L',0),(1194,350503,'丰泽区',1192,3,'fengzequ','F',0),(1195,350504,'洛江区',1192,3,'luojiangqu','L',0),(1196,350505,'泉港区',1192,3,'quangangqu','Q',0),(1197,350521,'惠安县',1192,3,'huianxian','H',0),(1198,350524,'安溪县',1192,3,'anxixian','A',0),(1199,350525,'永春县',1192,3,'yongchunxian','Y',0),(1200,350526,'德化县',1192,3,'dehuaxian','D',0),(1201,350527,'金门县',1192,3,'jinmenxian','J',0),(1202,350581,'石狮市',1192,3,'shishishi','S',0),(1203,350582,'晋江市',1192,3,'jinjiangshi','J',0),(1204,350583,'南安市',1192,3,'nananshi','N',0),(1205,350600,'漳州市',1151,2,'zhangzhoushi','Z',0),(1206,350602,'芗城区',1205,3,'xiangchengqu','X',0),(1207,350603,'龙文区',1205,3,'longwenqu','L',0),(1208,350622,'云霄县',1205,3,'yunxiaoxian','Y',0),(1209,350623,'漳浦县',1205,3,'zhangpuxian','Z',0),(1210,350624,'诏安县',1205,3,'zhaoanxian','Z',0),(1211,350625,'长泰县',1205,3,'changtaixian','C',0),(1212,350626,'东山县',1205,3,'dongshanxian','D',0),(1213,350627,'南靖县',1205,3,'nanjingxian','N',0),(1214,350628,'平和县',1205,3,'pinghexian','P',0),(1215,350629,'华安县',1205,3,'huaanxian','H',0),(1216,350681,'龙海市',1205,3,'longhaishi','L',0),(1217,350700,'南平市',1151,2,'nanpingshi','N',0),(1218,350702,'延平区',1217,3,'yanpingqu','Y',0),(1219,350721,'顺昌县',1217,3,'shunchangxian','S',0),(1220,350722,'浦城县',1217,3,'puchengxian','P',0),(1221,350723,'光泽县',1217,3,'guangzexian','G',0),(1222,350724,'松溪县',1217,3,'songxixian','S',0),(1223,350725,'政和县',1217,3,'zhenghexian','Z',0),(1224,350781,'邵武市',1217,3,'shaowushi','S',0),(1225,350782,'武夷山市',1217,3,'wuyishanshi','W',0),(1226,350783,'建瓯市',1217,3,'jianoushi','J',0),(1227,350784,'建阳市',1217,3,'jianyangshi','J',0),(1228,350800,'龙岩市',1151,2,'longyanshi','L',0),(1229,350802,'新罗区',1228,3,'xinluoqu','X',0),(1230,350821,'长汀县',1228,3,'changtingxian','C',0),(1231,350822,'永定县',1228,3,'yongdingxian','Y',0),(1232,350823,'上杭县',1228,3,'shanghangxian','S',0),(1233,350824,'武平县',1228,3,'wupingxian','W',0),(1234,350825,'连城县',1228,3,'lianchengxian','L',0),(1235,350881,'漳平市',1228,3,'zhangpingshi','Z',0),(1236,350900,'宁德市',1151,2,'ningdeshi','N',0),(1237,350902,'蕉城区',1236,3,'jiaochengqu','J',0),(1238,350921,'霞浦县',1236,3,'xiapuxian','X',0),(1239,350922,'古田县',1236,3,'gutianxian','G',0),(1240,350923,'屏南县',1236,3,'pingnanxian','P',0),(1241,350924,'寿宁县',1236,3,'shouningxian','S',0),(1242,350925,'周宁县',1236,3,'zhouningxian','Z',0),(1243,350926,'柘荣县',1236,3,'zherongxian','Z',0),(1244,350981,'福安市',1236,3,'fuanshi','F',0),(1245,350982,'福鼎市',1236,3,'fudingshi','F',0),(1246,360000,'江西',0,1,'jiangxi','J',0),(1247,360100,'南昌市',1246,2,'nanchangshi','N',0),(1248,360102,'东湖区',1247,3,'donghuqu','D',0),(1249,360103,'西湖区',1247,3,'xihuqu','X',0),(1250,360104,'青云谱区',1247,3,'qingyunpuqu','Q',0),(1251,360105,'湾里区',1247,3,'wanliqu','W',0),(1252,360111,'青山湖区',1247,3,'qingshanhuqu','Q',0),(1253,360121,'南昌县',1247,3,'nanchangxian','N',0),(1254,360122,'新建县',1247,3,'xinjianxian','X',0),(1255,360123,'安义县',1247,3,'anyixian','A',0),(1256,360124,'进贤县',1247,3,'jinxianxian','J',0),(1257,360200,'景德镇市',1246,2,'jingdezhenshi','J',0),(1258,360202,'昌江区',1257,3,'changjiangqu','C',0),(1259,360203,'珠山区',1257,3,'zhushanqu','Z',0),(1260,360222,'浮梁县',1257,3,'fuliangxian','F',0),(1261,360281,'乐平市',1257,3,'lepingshi','L',0),(1262,360300,'萍乡市',1246,2,'pingxiangshi','P',0),(1263,360302,'安源区',1262,3,'anyuanqu','A',0),(1264,360313,'湘东区',1262,3,'xiangdongqu','X',0),(1265,360321,'莲花县',1262,3,'lianhuaxian','L',0),(1266,360322,'上栗县',1262,3,'shanglixian','S',0),(1267,360323,'芦溪县',1262,3,'luxixian','L',0),(1268,360400,'九江市',1246,2,'jiujiangshi','J',0),(1269,360402,'庐山区',1268,3,'lushanqu','L',0),(1270,360403,'浔阳区',1268,3,'xunyangqu','X',0),(1271,360421,'九江县',1268,3,'jiujiangxian','J',0),(1272,360423,'武宁县',1268,3,'wuningxian','W',0),(1273,360424,'修水县',1268,3,'xiushuixian','X',0),(1274,360425,'永修县',1268,3,'yongxiuxian','Y',0),(1275,360426,'德安县',1268,3,'deanxian','D',0),(1276,360427,'星子县',1268,3,'xingzixian','X',0),(1277,360428,'都昌县',1268,3,'duchangxian','D',0),(1278,360429,'湖口县',1268,3,'hukouxian','H',0),(1279,360430,'彭泽县',1268,3,'pengzexian','P',0),(1280,360481,'瑞昌市',1268,3,'ruichangshi','R',0),(1281,360482,'共青城市',1268,3,'gongqingchengshi','G',0),(1282,360500,'新余市',1246,2,'xinyushi','X',0),(1283,360502,'渝水区',1282,3,'yushuiqu','Y',0),(1284,360521,'分宜县',1282,3,'fenyixian','F',0),(1285,360600,'鹰潭市',1246,2,'yingtanshi','Y',0),(1286,360602,'月湖区',1285,3,'yuehuqu','Y',0),(1287,360622,'余江县',1285,3,'yujiangxian','Y',0),(1288,360681,'贵溪市',1285,3,'guixishi','G',0),(1289,360700,'赣州市',1246,2,'ganzhoushi','G',0),(1290,360702,'章贡区',1289,3,'zhanggongqu','Z',0),(1291,360721,'赣县',1289,3,'ganxian','G',0),(1292,360722,'信丰县',1289,3,'xinfengxian','X',0),(1293,360723,'大余县',1289,3,'dayuxian','D',0),(1294,360724,'上犹县',1289,3,'shangyouxian','S',0),(1295,360725,'崇义县',1289,3,'chongyixian','C',0),(1296,360726,'安远县',1289,3,'anyuanxian','A',0),(1297,360727,'龙南县',1289,3,'longnanxian','L',0),(1298,360728,'定南县',1289,3,'dingnanxian','D',0),(1299,360729,'全南县',1289,3,'quannanxian','Q',0),(1300,360730,'宁都县',1289,3,'ningduxian','N',0),(1301,360731,'于都县',1289,3,'yuduxian','Y',0),(1302,360732,'兴国县',1289,3,'xingguoxian','X',0),(1303,360733,'会昌县',1289,3,'huichangxian','H',0),(1304,360734,'寻乌县',1289,3,'xunwuxian','X',0),(1305,360735,'石城县',1289,3,'shichengxian','S',0),(1306,360781,'瑞金市',1289,3,'ruijinshi','R',0),(1307,360782,'南康市',1289,3,'nankangshi','N',0),(1308,360800,'吉安市',1246,2,'jianshi','J',0),(1309,360802,'吉州区',1308,3,'jizhouqu','J',0),(1310,360803,'青原区',1308,3,'qingyuanqu','Q',0),(1311,360821,'吉安县',1308,3,'jianxian','J',0),(1312,360822,'吉水县',1308,3,'jishuixian','J',0),(1313,360823,'峡江县',1308,3,'xiajiangxian','X',0),(1314,360824,'新干县',1308,3,'xinganxian','X',0),(1315,360825,'永丰县',1308,3,'yongfengxian','Y',0),(1316,360826,'泰和县',1308,3,'taihexian','T',0),(1317,360827,'遂川县',1308,3,'suichuanxian','S',0),(1318,360828,'万安县',1308,3,'wananxian','W',0),(1319,360829,'安福县',1308,3,'anfuxian','A',0),(1320,360830,'永新县',1308,3,'yongxinxian','Y',0),(1321,360881,'井冈山市',1308,3,'jinggangshanshi','J',0),(1322,360900,'宜春市',1246,2,'yichunshi','Y',0),(1323,360902,'袁州区',1322,3,'yuanzhouqu','Y',0),(1324,360921,'奉新县',1322,3,'fengxinxian','F',0),(1325,360922,'万载县',1322,3,'wanzaixian','W',0),(1326,360923,'上高县',1322,3,'shanggaoxian','S',0),(1327,360924,'宜丰县',1322,3,'yifengxian','Y',0),(1328,360925,'靖安县',1322,3,'jinganxian','J',0),(1329,360926,'铜鼓县',1322,3,'tongguxian','T',0),(1330,360981,'丰城市',1322,3,'fengchengshi','F',0),(1331,360982,'樟树市',1322,3,'zhangshushi','Z',0),(1332,360983,'高安市',1322,3,'gaoanshi','G',0),(1333,361000,'抚州市',1246,2,'fuzhoushi','F',0),(1334,361002,'临川区',1333,3,'linchuanqu','L',0),(1335,361021,'南城县',1333,3,'nanchengxian','N',0),(1336,361022,'黎川县',1333,3,'lichuanxian','L',0),(1337,361023,'南丰县',1333,3,'nanfengxian','N',0),(1338,361024,'崇仁县',1333,3,'chongrenxian','C',0),(1339,361025,'乐安县',1333,3,'leanxian','L',0),(1340,361026,'宜黄县',1333,3,'yihuangxian','Y',0),(1341,361027,'金溪县',1333,3,'jinxixian','J',0),(1342,361028,'资溪县',1333,3,'zixixian','Z',0),(1343,361029,'东乡县',1333,3,'dongxiangxian','D',0),(1344,361030,'广昌县',1333,3,'guangchangxian','G',0),(1345,361100,'上饶市',1246,2,'shangraoshi','S',0),(1346,361102,'信州区',1345,3,'xinzhouqu','X',0),(1347,361121,'上饶县',1345,3,'shangraoxian','S',0),(1348,361122,'广丰县',1345,3,'guangfengxian','G',0),(1349,361123,'玉山县',1345,3,'yushanxian','Y',0),(1350,361124,'铅山县',1345,3,'qianshanxian','Q',0),(1351,361125,'横峰县',1345,3,'hengfengxian','H',0),(1352,361126,'弋阳县',1345,3,'yiyangxian','Y',0),(1353,361127,'余干县',1345,3,'yuganxian','Y',0),(1354,361128,'鄱阳县',1345,3,'poyangxian','P',0),(1355,361129,'万年县',1345,3,'wannianxian','W',0),(1356,361130,'婺源县',1345,3,'wuyuanxian','W',0),(1357,361181,'德兴市',1345,3,'dexingshi','D',0),(1358,370000,'山东',0,1,'shandong','S',0),(1359,370100,'济南市',1358,2,'jinanshi','J',0),(1360,370102,'历下区',1359,3,'lixiaqu','L',0),(1361,370103,'市中区',1359,3,'shizhongqu','S',0),(1362,370104,'槐荫区',1359,3,'huaiyinqu','H',0),(1363,370105,'天桥区',1359,3,'tianqiaoqu','T',0),(1364,370112,'历城区',1359,3,'lichengqu','L',0),(1365,370113,'长清区',1359,3,'changqingqu','C',0),(1366,370124,'平阴县',1359,3,'pingyinxian','P',0),(1367,370125,'济阳县',1359,3,'jiyangxian','J',0),(1368,370126,'商河县',1359,3,'shanghexian','S',0),(1369,370181,'章丘市',1359,3,'zhangqiushi','Z',0),(1370,370200,'青岛市',1358,2,'qingdaoshi','Q',0),(1371,370202,'市南区',1370,3,'shinanqu','S',0),(1372,370203,'市北区',1370,3,'shibeiqu','S',0),(1373,370211,'黄岛区',1370,3,'huangdaoqu','H',0),(1374,370212,'崂山区',1370,3,'laoshanqu','L',0),(1375,370213,'李沧区',1370,3,'licangqu','L',0),(1376,370214,'城阳区',1370,3,'chengyangqu','C',0),(1377,370281,'胶州市',1370,3,'jiaozhoushi','J',0),(1378,370282,'即墨市',1370,3,'jimoshi','J',0),(1379,370283,'平度市',1370,3,'pingdushi','P',0),(1380,370285,'莱西市',1370,3,'laixishi','L',0),(1381,370300,'淄博市',1358,2,'ziboshi','Z',0),(1382,370302,'淄川区',1381,3,'zichuanqu','Z',0),(1383,370303,'张店区',1381,3,'zhangdianqu','Z',0),(1384,370304,'博山区',1381,3,'boshanqu','B',0),(1385,370305,'临淄区',1381,3,'linziqu','L',0),(1386,370306,'周村区',1381,3,'zhoucunqu','Z',0),(1387,370321,'桓台县',1381,3,'huantaixian','H',0),(1388,370322,'高青县',1381,3,'gaoqingxian','G',0),(1389,370323,'沂源县',1381,3,'yiyuanxian','Y',0),(1390,370400,'枣庄市',1358,2,'zaozhuangshi','Z',0),(1391,370402,'市中区',1390,3,'shizhongqu','S',0),(1392,370403,'薛城区',1390,3,'xuechengqu','X',0),(1393,370404,'峄城区',1390,3,'yichengqu','Y',0),(1394,370405,'台儿庄区',1390,3,'taierzhuangqu','T',0),(1395,370406,'山亭区',1390,3,'shantingqu','S',0),(1396,370481,'滕州市',1390,3,'tengzhoushi','T',0),(1397,370500,'东营市',1358,2,'dongyingshi','D',0),(1398,370502,'东营区',1397,3,'dongyingqu','D',0),(1399,370503,'河口区',1397,3,'hekouqu','H',0),(1400,370521,'垦利县',1397,3,'kenlixian','K',0),(1401,370522,'利津县',1397,3,'lijinxian','L',0),(1402,370523,'广饶县',1397,3,'guangraoxian','G',0),(1403,370600,'烟台市',1358,2,'yantaishi','Y',0),(1404,370602,'芝罘区',1403,3,'zhifuqu','Z',0),(1405,370611,'福山区',1403,3,'fushanqu','F',0),(1406,370612,'牟平区',1403,3,'moupingqu','M',0),(1407,370613,'莱山区',1403,3,'laishanqu','L',0),(1408,370634,'长岛县',1403,3,'changdaoxian','C',0),(1409,370681,'龙口市',1403,3,'longkoushi','L',0),(1410,370682,'莱阳市',1403,3,'laiyangshi','L',0),(1411,370683,'莱州市',1403,3,'laizhoushi','L',0),(1412,370684,'蓬莱市',1403,3,'penglaishi','P',0),(1413,370685,'招远市',1403,3,'zhaoyuanshi','Z',0),(1414,370686,'栖霞市',1403,3,'qixiashi','Q',0),(1415,370687,'海阳市',1403,3,'haiyangshi','H',0),(1416,370700,'潍坊市',1358,2,'weifangshi','W',0),(1417,370702,'潍城区',1416,3,'weichengqu','W',0),(1418,370703,'寒亭区',1416,3,'hantingqu','H',0),(1419,370704,'坊子区',1416,3,'fangziqu','F',0),(1420,370705,'奎文区',1416,3,'kuiwenqu','K',0),(1421,370724,'临朐县',1416,3,'linquxian','L',0),(1422,370725,'昌乐县',1416,3,'changlexian','C',0),(1423,370781,'青州市',1416,3,'qingzhoushi','Q',0),(1424,370782,'诸城市',1416,3,'zhuchengshi','Z',0),(1425,370783,'寿光市',1416,3,'shouguangshi','S',0),(1426,370784,'安丘市',1416,3,'anqiushi','A',0),(1427,370785,'高密市',1416,3,'gaomishi','G',0),(1428,370786,'昌邑市',1416,3,'changyishi','C',0),(1429,370800,'济宁市',1358,2,'jiningshi','J',0),(1430,370802,'市中区',1429,3,'shizhongqu','S',0),(1431,370811,'任城区',1429,3,'renchengqu','R',0),(1432,370826,'微山县',1429,3,'weishanxian','W',0),(1433,370827,'鱼台县',1429,3,'yutaixian','Y',0),(1434,370828,'金乡县',1429,3,'jinxiangxian','J',0),(1435,370829,'嘉祥县',1429,3,'jiaxiangxian','J',0),(1436,370830,'汶上县',1429,3,'wenshangxian','W',0),(1437,370831,'泗水县',1429,3,'sishuixian','S',0),(1438,370832,'梁山县',1429,3,'liangshanxian','L',0),(1439,370881,'曲阜市',1429,3,'qufushi','Q',0),(1440,370882,'兖州市',1429,3,'yanzhoushi','Y',0),(1441,370883,'邹城市',1429,3,'zouchengshi','Z',0),(1442,370900,'泰安市',1358,2,'taianshi','T',0),(1443,370902,'泰山区',1442,3,'taishanqu','T',0),(1444,370911,'岱岳区',1442,3,'daiyuequ','D',0),(1445,370921,'宁阳县',1442,3,'ningyangxian','N',0),(1446,370923,'东平县',1442,3,'dongpingxian','D',0),(1447,370982,'新泰市',1442,3,'xintaishi','X',0),(1448,370983,'肥城市',1442,3,'feichengshi','F',0),(1449,371000,'威海市',1358,2,'weihaishi','W',0),(1450,371002,'环翠区',1449,3,'huancuiqu','H',0),(1451,371081,'文登市',1449,3,'wendengshi','W',0),(1452,371082,'荣成市',1449,3,'rongchengshi','R',0),(1453,371083,'乳山市',1449,3,'rushanshi','R',0),(1454,371100,'日照市',1358,2,'rizhaoshi','R',0),(1455,371102,'东港区',1454,3,'donggangqu','D',0),(1456,371103,'岚山区',1454,3,'lanshanqu','L',0),(1457,371121,'五莲县',1454,3,'wulianxian','W',0),(1458,371122,'莒县',1454,3,'juxian','J',0),(1459,371200,'莱芜市',1358,2,'laiwushi','L',0),(1460,371202,'莱城区',1459,3,'laichengqu','L',0),(1461,371203,'钢城区',1459,3,'gangchengqu','G',0),(1462,371300,'临沂市',1358,2,'linyishi','L',0),(1463,371302,'兰山区',1462,3,'lanshanqu','L',0),(1464,371311,'罗庄区',1462,3,'luozhuangqu','L',0),(1465,371312,'河东区',1462,3,'hedongqu','H',0),(1466,371321,'沂南县',1462,3,'yinanxian','Y',0),(1467,371322,'郯城县',1462,3,'tanchengxian','T',0),(1468,371323,'沂水县',1462,3,'yishuixian','Y',0),(1469,371324,'苍山县',1462,3,'cangshanxian','C',0),(1470,371325,'费县',1462,3,'feixian','F',0),(1471,371326,'平邑县',1462,3,'pingyixian','P',0),(1472,371327,'莒南县',1462,3,'junanxian','J',0),(1473,371328,'蒙阴县',1462,3,'mengyinxian','M',0),(1474,371329,'临沭县',1462,3,'linshuxian','L',0),(1475,371400,'德州市',1358,2,'dezhoushi','D',0),(1476,371402,'德城区',1475,3,'dechengqu','D',0),(1477,371421,'陵县',1475,3,'lingxian','L',0),(1478,371422,'宁津县',1475,3,'ningjinxian','N',0),(1479,371423,'庆云县',1475,3,'qingyunxian','Q',0),(1480,371424,'临邑县',1475,3,'linyixian','L',0),(1481,371425,'齐河县',1475,3,'qihexian','Q',0),(1482,371426,'平原县',1475,3,'pingyuanxian','P',0),(1483,371427,'夏津县',1475,3,'xiajinxian','X',0),(1484,371428,'武城县',1475,3,'wuchengxian','W',0),(1485,371481,'乐陵市',1475,3,'lelingshi','L',0),(1486,371482,'禹城市',1475,3,'yuchengshi','Y',0),(1487,371500,'聊城市',1358,2,'liaochengshi','L',0),(1488,371502,'东昌府区',1487,3,'dongchangfuqu','D',0),(1489,371521,'阳谷县',1487,3,'yangguxian','Y',0),(1490,371522,'莘县',1487,3,'shenxian','S',0),(1491,371523,'茌平县',1487,3,'chipingxian','C',0),(1492,371524,'东阿县',1487,3,'dongaxian','D',0),(1493,371525,'冠县',1487,3,'guanxian','G',0),(1494,371526,'高唐县',1487,3,'gaotangxian','G',0),(1495,371581,'临清市',1487,3,'linqingshi','L',0),(1496,371600,'滨州市',1358,2,'binzhoushi','B',0),(1497,371602,'滨城区',1496,3,'binchengqu','B',0),(1498,371621,'惠民县',1496,3,'huiminxian','H',0),(1499,371622,'阳信县',1496,3,'yangxinxian','Y',0),(1500,371623,'无棣县',1496,3,'wudixian','W',0),(1501,371624,'沾化县',1496,3,'zhanhuaxian','Z',0),(1502,371625,'博兴县',1496,3,'boxingxian','B',0),(1503,371626,'邹平县',1496,3,'zoupingxian','Z',0),(1504,371700,'菏泽市',1358,2,'hezeshi','H',0),(1505,371702,'牡丹区',1504,3,'mudanqu','M',0),(1506,371721,'曹县',1504,3,'caoxian','C',0),(1507,371722,'单县',1504,3,'danxian','D',0),(1508,371723,'成武县',1504,3,'chengwuxian','C',0),(1509,371724,'巨野县',1504,3,'juyexian','J',0),(1510,371725,'郓城县',1504,3,'yunchengxian','Y',0),(1511,371726,'鄄城县',1504,3,'juanchengxian','J',0),(1512,371727,'定陶县',1504,3,'dingtaoxian','D',0),(1513,371728,'东明县',1504,3,'dongmingxian','D',0),(1514,410000,'河南',0,1,'henan','H',0),(1515,410100,'郑州市',1514,2,'zhengzhoushi','Z',0),(1516,410102,'中原区',1515,3,'zhongyuanqu','Z',0),(1517,410103,'二七区',1515,3,'erqiqu','E',0),(1518,410104,'管城区',1515,3,'guanchengqu','G',0),(1519,410105,'金水区',1515,3,'jinshuiqu','J',0),(1520,410106,'上街区',1515,3,'shangjiequ','S',0),(1521,410108,'惠济区',1515,3,'huijiqu','H',0),(1522,410122,'中牟县',1515,3,'zhongmouxian','Z',0),(1523,410181,'巩义市',1515,3,'gongyishi','G',0),(1524,410182,'荥阳市',1515,3,'xingyangshi','X',0),(1525,410183,'新密市',1515,3,'xinmishi','X',0),(1526,410184,'新郑市',1515,3,'xinzhengshi','X',0),(1527,410185,'登封市',1515,3,'dengfengshi','D',0),(1528,410200,'开封市',1514,2,'kaifengshi','K',0),(1529,410202,'龙亭区',1528,3,'longtingqu','L',0),(1530,410203,'顺河区',1528,3,'shunhequ','S',0),(1531,410204,'鼓楼区',1528,3,'gulouqu','G',0),(1532,410205,'禹王台区',1528,3,'yuwangtaiqu','Y',0),(1533,410211,'金明区',1528,3,'jinmingqu','J',0),(1534,410221,'杞县',1528,3,'qixian','Q',0),(1535,410222,'通许县',1528,3,'tongxuxian','T',0),(1536,410223,'尉氏县',1528,3,'weishixian','W',0),(1537,410224,'开封县',1528,3,'kaifengxian','K',0),(1538,410225,'兰考县',1528,3,'lankaoxian','L',0),(1539,410300,'洛阳市',1514,2,'luoyangshi','L',0),(1540,410302,'老城区',1539,3,'laochengqu','L',0),(1541,410303,'西工区',1539,3,'xigongqu','X',0),(1542,410304,'瀍河区',1539,3,'chanhequ','C',0),(1543,410305,'涧西区',1539,3,'jianxiqu','J',0),(1544,410306,'吉利区',1539,3,'jiliqu','J',0),(1545,410311,'洛龙区',1539,3,'luolongqu','L',0),(1546,410322,'孟津县',1539,3,'mengjinxian','M',0),(1547,410323,'新安县',1539,3,'xinanxian','X',0),(1548,410324,'栾川县',1539,3,'luanchuanxian','L',0),(1549,410325,'嵩县',1539,3,'songxian','S',0),(1550,410326,'汝阳县',1539,3,'ruyangxian','R',0),(1551,410327,'宜阳县',1539,3,'yiyangxian','Y',0),(1552,410328,'洛宁县',1539,3,'luoningxian','L',0),(1553,410329,'伊川县',1539,3,'yichuanxian','Y',0),(1554,410381,'偃师市',1539,3,'yanshishi','Y',0),(1555,410400,'平顶山市',1514,2,'pingdingshanshi','P',0),(1556,410402,'新华区',1555,3,'xinhuaqu','X',0),(1557,410403,'卫东区',1555,3,'weidongqu','W',0),(1558,410404,'石龙区',1555,3,'shilongqu','S',0),(1559,410411,'湛河区',1555,3,'zhanhequ','Z',0),(1560,410421,'宝丰县',1555,3,'baofengxian','B',0),(1561,410422,'叶县',1555,3,'yexian','Y',0),(1562,410423,'鲁山县',1555,3,'lushanxian','L',0),(1563,410425,'郏县',1555,3,'jiaxian','J',0),(1564,410481,'舞钢市',1555,3,'wugangshi','W',0),(1565,410482,'汝州市',1555,3,'ruzhoushi','R',0),(1566,410500,'安阳市',1514,2,'anyangshi','A',0),(1567,410502,'文峰区',1566,3,'wenfengqu','W',0),(1568,410503,'北关区',1566,3,'beiguanqu','B',0),(1569,410505,'殷都区',1566,3,'yinduqu','Y',0),(1570,410506,'龙安区',1566,3,'longanqu','L',0),(1571,410522,'安阳县',1566,3,'anyangxian','A',0),(1572,410523,'汤阴县',1566,3,'tangyinxian','T',0),(1573,410526,'滑县',1566,3,'huaxian','H',0),(1574,410527,'内黄县',1566,3,'neihuangxian','N',0),(1575,410581,'林州市',1566,3,'linzhoushi','L',0),(1576,410600,'鹤壁市',1514,2,'hebishi','H',0),(1577,410602,'鹤山区',1576,3,'heshanqu','H',0),(1578,410603,'山城区',1576,3,'shanchengqu','S',0),(1579,410611,'淇滨区',1576,3,'qibinqu','Q',0),(1580,410621,'浚县',1576,3,'junxian','J',0),(1581,410622,'淇县',1576,3,'qixian','Q',0),(1582,410700,'新乡市',1514,2,'xinxiangshi','X',0),(1583,410702,'红旗区',1582,3,'hongqiqu','H',0),(1584,410703,'卫滨区',1582,3,'weibinqu','W',0),(1585,410704,'凤泉区',1582,3,'fengquanqu','F',0),(1586,410711,'牧野区',1582,3,'muyequ','M',0),(1587,410721,'新乡县',1582,3,'xinxiangxian','X',0),(1588,410724,'获嘉县',1582,3,'huojiaxian','H',0),(1589,410725,'原阳县',1582,3,'yuanyangxian','Y',0),(1590,410726,'延津县',1582,3,'yanjinxian','Y',0),(1591,410727,'封丘县',1582,3,'fengqiuxian','F',0),(1592,410728,'长垣县',1582,3,'changyuanxian','C',0),(1593,410781,'卫辉市',1582,3,'weihuishi','W',0),(1594,410782,'辉县市',1582,3,'huixianshi','H',0),(1595,410800,'焦作市',1514,2,'jiaozuoshi','J',0),(1596,410802,'解放区',1595,3,'jiefangqu','J',0),(1597,410803,'中站区',1595,3,'zhongzhanqu','Z',0),(1598,410804,'马村区',1595,3,'macunqu','M',0),(1599,410811,'山阳区',1595,3,'shanyangqu','S',0),(1600,410821,'修武县',1595,3,'xiuwuxian','X',0),(1601,410822,'博爱县',1595,3,'boaixian','B',0),(1602,410823,'武陟县',1595,3,'wuzhixian','W',0),(1603,410825,'温县',1595,3,'wenxian','W',0),(1604,410882,'沁阳市',1595,3,'qinyangshi','Q',0),(1605,410883,'孟州市',1595,3,'mengzhoushi','M',0),(1606,410900,'濮阳市',1514,2,'puyangshi','P',0),(1607,410902,'华龙区',1606,3,'hualongqu','H',0),(1608,410922,'清丰县',1606,3,'qingfengxian','Q',0),(1609,410923,'南乐县',1606,3,'nanlexian','N',0),(1610,410926,'范县',1606,3,'fanxian','F',0),(1611,410927,'台前县',1606,3,'taiqianxian','T',0),(1612,410928,'濮阳县',1606,3,'puyangxian','P',0),(1613,411000,'许昌市',1514,2,'xuchangshi','X',0),(1614,411002,'魏都区',1613,3,'weiduqu','W',0),(1615,411023,'许昌县',1613,3,'xuchangxian','X',0),(1616,411024,'鄢陵县',1613,3,'yanlingxian','Y',0),(1617,411025,'襄城县',1613,3,'xiangchengxian','X',0),(1618,411081,'禹州市',1613,3,'yuzhoushi','Y',0),(1619,411082,'长葛市',1613,3,'changgeshi','C',0),(1620,411100,'漯河市',1514,2,'luoheshi','L',0),(1621,411102,'源汇区',1620,3,'yuanhuiqu','Y',0),(1622,411103,'郾城区',1620,3,'yanchengqu','Y',0),(1623,411104,'召陵区',1620,3,'zhaolingqu','Z',0),(1624,411121,'舞阳县',1620,3,'wuyangxian','W',0),(1625,411122,'临颍县',1620,3,'linyingxian','L',0),(1626,411200,'三门峡市',1514,2,'sanmenxiashi','S',0),(1627,411202,'湖滨区',1626,3,'hubinqu','H',0),(1628,411221,'渑池县',1626,3,'mianchixian','M',0),(1629,411222,'陕县',1626,3,'shanxian','S',0),(1630,411224,'卢氏县',1626,3,'lushixian','L',0),(1631,411281,'义马市',1626,3,'yimashi','Y',0),(1632,411282,'灵宝市',1626,3,'lingbaoshi','L',0),(1633,411300,'南阳市',1514,2,'nanyangshi','N',0),(1634,411302,'宛城区',1633,3,'wanchengqu','W',0),(1635,411303,'卧龙区',1633,3,'wolongqu','W',0),(1636,411321,'南召县',1633,3,'nanzhaoxian','N',0),(1637,411322,'方城县',1633,3,'fangchengxian','F',0),(1638,411323,'西峡县',1633,3,'xixiaxian','X',0),(1639,411324,'镇平县',1633,3,'zhenpingxian','Z',0),(1640,411325,'内乡县',1633,3,'neixiangxian','N',0),(1641,411326,'淅川县',1633,3,'xichuanxian','X',0),(1642,411327,'社旗县',1633,3,'sheqixian','S',0),(1643,411328,'唐河县',1633,3,'tanghexian','T',0),(1644,411329,'新野县',1633,3,'xinyexian','X',0),(1645,411330,'桐柏县',1633,3,'tongbaixian','T',0),(1646,411381,'邓州市',1633,3,'dengzhoushi','D',0),(1647,411400,'商丘市',1514,2,'shangqiushi','S',0),(1648,411402,'梁园区',1647,3,'liangyuanqu','L',0),(1649,411403,'睢阳区',1647,3,'huiyangqu','H',0),(1650,411421,'民权县',1647,3,'minquanxian','M',0),(1651,411422,'睢县',1647,3,'huixian','H',0),(1652,411423,'宁陵县',1647,3,'ninglingxian','N',0),(1653,411424,'柘城县',1647,3,'zhechengxian','Z',0),(1654,411425,'虞城县',1647,3,'yuchengxian','Y',0),(1655,411426,'夏邑县',1647,3,'xiayixian','X',0),(1656,411481,'永城市',1647,3,'yongchengshi','Y',0),(1657,411500,'信阳市',1514,2,'xinyangshi','X',0),(1658,411502,'浉河区',1657,3,'shihequ','S',0),(1659,411503,'平桥区',1657,3,'pingqiaoqu','P',0),(1660,411521,'罗山县',1657,3,'luoshanxian','L',0),(1661,411522,'光山县',1657,3,'guangshanxian','G',0),(1662,411523,'新县',1657,3,'xinxian','X',0),(1663,411524,'商城县',1657,3,'shangchengxian','S',0),(1664,411525,'固始县',1657,3,'gushixian','G',0),(1665,411526,'潢川县',1657,3,'huangchuanxian','H',0),(1666,411527,'淮滨县',1657,3,'huaibinxian','H',0),(1667,411528,'息县',1657,3,'xixian','X',0),(1668,411600,'周口市',1514,2,'zhoukoushi','Z',0),(1669,411602,'川汇区',1668,3,'chuanhuiqu','C',0),(1670,411621,'扶沟县',1668,3,'fugouxian','F',0),(1671,411622,'西华县',1668,3,'xihuaxian','X',0),(1672,411623,'商水县',1668,3,'shangshuixian','S',0),(1673,411624,'沈丘县',1668,3,'shenqiuxian','S',0),(1674,411625,'郸城县',1668,3,'danchengxian','D',0),(1675,411626,'淮阳县',1668,3,'huaiyangxian','H',0),(1676,411627,'太康县',1668,3,'taikangxian','T',0),(1677,411628,'鹿邑县',1668,3,'luyixian','L',0),(1678,411681,'项城市',1668,3,'xiangchengshi','X',0),(1679,411700,'驻马店市',1514,2,'zhumadianshi','Z',0),(1680,411702,'驿城区',1679,3,'yichengqu','Y',0),(1681,411721,'西平县',1679,3,'xipingxian','X',0),(1682,411722,'上蔡县',1679,3,'shangcaixian','S',0),(1683,411723,'平舆县',1679,3,'pingyuxian','P',0),(1684,411724,'正阳县',1679,3,'zhengyangxian','Z',0),(1685,411725,'确山县',1679,3,'queshanxian','Q',0),(1686,411726,'泌阳县',1679,3,'miyangxian','M',0),(1687,411727,'汝南县',1679,3,'runanxian','R',0),(1688,411728,'遂平县',1679,3,'suipingxian','S',0),(1689,411729,'新蔡县',1679,3,'xincaixian','X',0),(1690,419001,'济源市',1514,2,'jiyuanshi','J',0),(1691,420000,'湖北',0,1,'hubei','H',0),(1692,420100,'武汉市',1691,2,'wuhanshi','W',0),(1693,420102,'江岸区',1692,3,'jianganqu','J',0),(1694,420103,'江汉区',1692,3,'jianghanqu','J',0),(1695,420104,'硚口区',1692,3,'qiaokouqu','Q',0),(1696,420105,'汉阳区',1692,3,'hanyangqu','H',0),(1697,420106,'武昌区',1692,3,'wuchangqu','W',0),(1698,420107,'青山区',1692,3,'qingshanqu','Q',0),(1699,420111,'洪山区',1692,3,'hongshanqu','H',0),(1700,420112,'东西湖区',1692,3,'dongxihuqu','D',0),(1701,420113,'汉南区',1692,3,'hannanqu','H',0),(1702,420114,'蔡甸区',1692,3,'caidianqu','C',0),(1703,420115,'江夏区',1692,3,'jiangxiaqu','J',0),(1704,420116,'黄陂区',1692,3,'huangbeiqu','H',0),(1705,420117,'新洲区',1692,3,'xinzhouqu','X',0),(1706,420200,'黄石市',1691,2,'huangshishi','H',0),(1707,420202,'黄石港区',1706,3,'huangshigangqu','H',0),(1708,420203,'西塞山区',1706,3,'xisaishanqu','X',0),(1709,420204,'下陆区',1706,3,'xialuqu','X',0),(1710,420205,'铁山区',1706,3,'tieshanqu','T',0),(1711,420222,'阳新县',1706,3,'yangxinxian','Y',0),(1712,420281,'大冶市',1706,3,'dayeshi','D',0),(1713,420300,'十堰市',1691,2,'shiyanshi','S',0),(1714,420302,'茅箭区',1713,3,'maojianqu','M',0),(1715,420303,'张湾区',1713,3,'zhangwanqu','Z',0),(1716,420321,'郧县',1713,3,'yunxian','Y',0),(1717,420322,'郧西县',1713,3,'yunxixian','Y',0),(1718,420323,'竹山县',1713,3,'zhushanxian','Z',0),(1719,420324,'竹溪县',1713,3,'zhuxixian','Z',0),(1720,420325,'房县',1713,3,'fangxian','F',0),(1721,420381,'丹江口市',1713,3,'danjiangkoushi','D',0),(1722,420500,'宜昌市',1691,2,'yichangshi','Y',0),(1723,420502,'西陵区',1722,3,'xilingqu','X',0),(1724,420503,'伍家岗区',1722,3,'wujiagangqu','W',0),(1725,420504,'点军区',1722,3,'dianjunqu','D',0),(1726,420505,'猇亭区',1722,3,'xiaotingqu','X',0),(1727,420506,'夷陵区',1722,3,'yilingqu','Y',0),(1728,420525,'远安县',1722,3,'yuananxian','Y',0),(1729,420526,'兴山县',1722,3,'xingshanxian','X',0),(1730,420527,'秭归县',1722,3,'ziguixian','Z',0),(1731,420528,'长阳县',1722,3,'changyangxian','C',0),(1732,420529,'五峰县',1722,3,'wufengxian','W',0),(1733,420581,'宜都市',1722,3,'yidushi','Y',0),(1734,420582,'当阳市',1722,3,'dangyangshi','D',0),(1735,420583,'枝江市',1722,3,'zhijiangshi','Z',0),(1736,420600,'襄阳市',1691,2,'xiangyangshi','X',0),(1737,420602,'襄城区',1736,3,'xiangchengqu','X',0),(1738,420606,'樊城区',1736,3,'fanchengqu','F',0),(1739,420607,'襄州区',1736,3,'xiangzhouqu','X',0),(1740,420624,'南漳县',1736,3,'nanzhangxian','N',0),(1741,420625,'谷城县',1736,3,'guchengxian','G',0),(1742,420626,'保康县',1736,3,'baokangxian','B',0),(1743,420682,'老河口市',1736,3,'laohekoushi','L',0),(1744,420683,'枣阳市',1736,3,'zaoyangshi','Z',0),(1745,420684,'宜城市',1736,3,'yichengshi','Y',0),(1746,420700,'鄂州市',1691,2,'ezhoushi','E',0),(1747,420702,'梁子湖区',1746,3,'liangzihuqu','L',0),(1748,420703,'华容区',1746,3,'huarongqu','H',0),(1749,420704,'鄂城区',1746,3,'echengqu','E',0),(1750,420800,'荆门市',1691,2,'jingmenshi','J',0),(1751,420802,'东宝区',1750,3,'dongbaoqu','D',0),(1752,420804,'掇刀区',1750,3,'duodaoqu','D',0),(1753,420821,'京山县',1750,3,'jingshanxian','J',0),(1754,420822,'沙洋县',1750,3,'shayangxian','S',0),(1755,420881,'钟祥市',1750,3,'zhongxiangshi','Z',0),(1756,420900,'孝感市',1691,2,'xiaoganshi','X',0),(1757,420902,'孝南区',1756,3,'xiaonanqu','X',0),(1758,420921,'孝昌县',1756,3,'xiaochangxian','X',0),(1759,420922,'大悟县',1756,3,'dawuxian','D',0),(1760,420923,'云梦县',1756,3,'yunmengxian','Y',0),(1761,420981,'应城市',1756,3,'yingchengshi','Y',0),(1762,420982,'安陆市',1756,3,'anlushi','A',0),(1763,420984,'汉川市',1756,3,'hanchuanshi','H',0),(1764,421000,'荆州市',1691,2,'jingzhoushi','J',0),(1765,421002,'沙市区',1764,3,'shashiqu','S',0),(1766,421003,'荆州区',1764,3,'jingzhouqu','J',0),(1767,421022,'公安县',1764,3,'gonganxian','G',0),(1768,421023,'监利县',1764,3,'jianlixian','J',0),(1769,421024,'江陵县',1764,3,'jianglingxian','J',0),(1770,421081,'石首市',1764,3,'shishoushi','S',0),(1771,421083,'洪湖市',1764,3,'honghushi','H',0),(1772,421087,'松滋市',1764,3,'songzishi','S',0),(1773,421100,'黄冈市',1691,2,'huanggangshi','H',0),(1774,421102,'黄州区',1773,3,'huangzhouqu','H',0),(1775,421121,'团风县',1773,3,'tuanfengxian','T',0),(1776,421122,'红安县',1773,3,'honganxian','H',0),(1777,421123,'罗田县',1773,3,'luotianxian','L',0),(1778,421124,'英山县',1773,3,'yingshanxian','Y',0),(1779,421125,'浠水县',1773,3,'xishuixian','X',0),(1780,421126,'蕲春县',1773,3,'qichunxian','Q',0),(1781,421127,'黄梅县',1773,3,'huangmeixian','H',0),(1782,421181,'麻城市',1773,3,'machengshi','M',0),(1783,421182,'武穴市',1773,3,'wuxueshi','W',0),(1784,421200,'咸宁市',1691,2,'xianningshi','X',0),(1785,421202,'咸安区',1784,3,'xiananqu','X',0),(1786,421221,'嘉鱼县',1784,3,'jiayuxian','J',0),(1787,421222,'通城县',1784,3,'tongchengxian','T',0),(1788,421223,'崇阳县',1784,3,'chongyangxian','C',0),(1789,421224,'通山县',1784,3,'tongshanxian','T',0),(1790,421281,'赤壁市',1784,3,'chibishi','C',0),(1791,421300,'随州市',1691,2,'suizhoushi','S',0),(1792,421303,'曾都区',1791,3,'zengduqu','Z',0),(1793,421321,'随县',1791,3,'suixian','S',0),(1794,421381,'广水市',1791,3,'guangshuishi','G',0),(1795,422800,'恩施州',1691,2,'enshizhou','E',0),(1796,422801,'恩施市',1795,3,'enshishi','E',0),(1797,422802,'利川市',1795,3,'lichuanshi','L',0),(1798,422822,'建始县',1795,3,'jianshixian','J',0),(1799,422823,'巴东县',1795,3,'badongxian','B',0),(1800,422825,'宣恩县',1795,3,'xuanenxian','X',0),(1801,422826,'咸丰县',1795,3,'xianfengxian','X',0),(1802,422827,'来凤县',1795,3,'laifengxian','L',0),(1803,422828,'鹤峰县',1795,3,'hefengxian','H',0),(1804,429004,'仙桃市',1691,2,'xiantaoshi','X',0),(1805,429005,'潜江市',1691,2,'qianjiangshi','Q',0),(1806,429006,'天门市',1691,2,'tianmenshi','T',0),(1807,429021,'神农架林区',1691,2,'shennongjialinqu','S',0),(1808,430000,'湖南',0,1,'hunan','H',0),(1809,430100,'长沙市',1808,2,'changshashi','C',0),(1810,430102,'芙蓉区',1809,3,'furongqu','F',0),(1811,430103,'天心区',1809,3,'tianxinqu','T',0),(1812,430104,'岳麓区',1809,3,'yueluqu','Y',0),(1813,430105,'开福区',1809,3,'kaifuqu','K',0),(1814,430111,'雨花区',1809,3,'yuhuaqu','Y',0),(1815,430112,'望城区',1809,3,'wangchengqu','W',0),(1816,430121,'长沙县',1809,3,'changshaxian','C',0),(1817,430124,'宁乡县',1809,3,'ningxiangxian','N',0),(1818,430181,'浏阳市',1809,3,'liuyangshi','L',0),(1819,430200,'株洲市',1808,2,'zhuzhoushi','Z',0),(1820,430202,'荷塘区',1819,3,'hetangqu','H',0),(1821,430203,'芦淞区',1819,3,'lusongqu','L',0),(1822,430204,'石峰区',1819,3,'shifengqu','S',0),(1823,430211,'天元区',1819,3,'tianyuanqu','T',0),(1824,430221,'株洲县',1819,3,'zhuzhouxian','Z',0),(1825,430223,'攸县',1819,3,'youxian','Y',0),(1826,430224,'茶陵县',1819,3,'chalingxian','C',0),(1827,430225,'炎陵县',1819,3,'yanlingxian','Y',0),(1828,430281,'醴陵市',1819,3,'lilingshi','L',0),(1829,430300,'湘潭市',1808,2,'xiangtanshi','X',0),(1830,430302,'雨湖区',1829,3,'yuhuqu','Y',0),(1831,430304,'岳塘区',1829,3,'yuetangqu','Y',0),(1832,430321,'湘潭县',1829,3,'xiangtanxian','X',0),(1833,430381,'湘乡市',1829,3,'xiangxiangshi','X',0),(1834,430382,'韶山市',1829,3,'shaoshanshi','S',0),(1835,430400,'衡阳市',1808,2,'hengyangshi','H',0),(1836,430405,'珠晖区',1835,3,'zhuhuiqu','Z',0),(1837,430406,'雁峰区',1835,3,'yanfengqu','Y',0),(1838,430407,'石鼓区',1835,3,'shiguqu','S',0),(1839,430408,'蒸湘区',1835,3,'zhengxiangqu','Z',0),(1840,430412,'南岳区',1835,3,'nanyuequ','N',0),(1841,430421,'衡阳县',1835,3,'hengyangxian','H',0),(1842,430422,'衡南县',1835,3,'hengnanxian','H',0),(1843,430423,'衡山县',1835,3,'hengshanxian','H',0),(1844,430424,'衡东县',1835,3,'hengdongxian','H',0),(1845,430426,'祁东县',1835,3,'qidongxian','Q',0),(1846,430481,'耒阳市',1835,3,'leiyangshi','L',0),(1847,430482,'常宁市',1835,3,'changningshi','C',0),(1848,430500,'邵阳市',1808,2,'shaoyangshi','S',0),(1849,430502,'双清区',1848,3,'shuangqingqu','S',0),(1850,430503,'大祥区',1848,3,'daxiangqu','D',0),(1851,430511,'北塔区',1848,3,'beitaqu','B',0),(1852,430521,'邵东县',1848,3,'shaodongxian','S',0),(1853,430522,'新邵县',1848,3,'xinshaoxian','X',0),(1854,430523,'邵阳县',1848,3,'shaoyangxian','S',0),(1855,430524,'隆回县',1848,3,'longhuixian','L',0),(1856,430525,'洞口县',1848,3,'dongkouxian','D',0),(1857,430527,'绥宁县',1848,3,'suiningxian','S',0),(1858,430528,'新宁县',1848,3,'xinningxian','X',0),(1859,430529,'城步县',1848,3,'chengbuxian','C',0),(1860,430581,'武冈市',1848,3,'wugangshi','W',0),(1861,430600,'岳阳市',1808,2,'yueyangshi','Y',0),(1862,430602,'岳阳楼区',1861,3,'yueyanglouqu','Y',0),(1863,430603,'云溪区',1861,3,'yunxiqu','Y',0),(1864,430611,'君山区',1861,3,'junshanqu','J',0),(1865,430621,'岳阳县',1861,3,'yueyangxian','Y',0),(1866,430623,'华容县',1861,3,'huarongxian','H',0),(1867,430624,'湘阴县',1861,3,'xiangyinxian','X',0),(1868,430626,'平江县',1861,3,'pingjiangxian','P',0),(1869,430681,'汨罗市',1861,3,'miluoshi','M',0),(1870,430682,'临湘市',1861,3,'linxiangshi','L',0),(1871,430700,'常德市',1808,2,'changdeshi','C',0),(1872,430702,'武陵区',1871,3,'wulingqu','W',0),(1873,430703,'鼎城区',1871,3,'dingchengqu','D',0),(1874,430721,'安乡县',1871,3,'anxiangxian','A',0),(1875,430722,'汉寿县',1871,3,'hanshouxian','H',0),(1876,430723,'澧县',1871,3,'lixian','L',0),(1877,430724,'临澧县',1871,3,'linlixian','L',0),(1878,430725,'桃源县',1871,3,'taoyuanxian','T',0),(1879,430726,'石门县',1871,3,'shimenxian','S',0),(1880,430781,'津市市',1871,3,'jinshishi','J',0),(1881,430800,'张家界市',1808,2,'zhangjiajieshi','Z',0),(1882,430802,'永定区',1881,3,'yongdingqu','Y',0),(1883,430811,'武陵源区',1881,3,'wulingyuanqu','W',0),(1884,430821,'慈利县',1881,3,'cilixian','C',0),(1885,430822,'桑植县',1881,3,'sangzhixian','S',0),(1886,430900,'益阳市',1808,2,'yiyangshi','Y',0),(1887,430902,'资阳区',1886,3,'ziyangqu','Z',0),(1888,430903,'赫山区',1886,3,'heshanqu','H',0),(1889,430921,'南县',1886,3,'nanxian','N',0),(1890,430922,'桃江县',1886,3,'taojiangxian','T',0),(1891,430923,'安化县',1886,3,'anhuaxian','A',0),(1892,430981,'沅江市',1886,3,'yuanjiangshi','Y',0),(1893,431000,'郴州市',1808,2,'chenzhoushi','C',0),(1894,431002,'北湖区',1893,3,'beihuqu','B',0),(1895,431003,'苏仙区',1893,3,'suxianqu','S',0),(1896,431021,'桂阳县',1893,3,'guiyangxian','G',0),(1897,431022,'宜章县',1893,3,'yizhangxian','Y',0),(1898,431023,'永兴县',1893,3,'yongxingxian','Y',0),(1899,431024,'嘉禾县',1893,3,'jiahexian','J',0),(1900,431025,'临武县',1893,3,'linwuxian','L',0),(1901,431026,'汝城县',1893,3,'ruchengxian','R',0),(1902,431027,'桂东县',1893,3,'guidongxian','G',0),(1903,431028,'安仁县',1893,3,'anrenxian','A',0),(1904,431081,'资兴市',1893,3,'zixingshi','Z',0),(1905,431100,'永州市',1808,2,'yongzhoushi','Y',0),(1906,431102,'零陵区',1905,3,'linglingqu','L',0),(1907,431103,'冷水滩区',1905,3,'lengshuitanqu','L',0),(1908,431121,'祁阳县',1905,3,'qiyangxian','Q',0),(1909,431122,'东安县',1905,3,'donganxian','D',0),(1910,431123,'双牌县',1905,3,'shuangpaixian','S',0),(1911,431124,'道县',1905,3,'daoxian','D',0),(1912,431125,'江永县',1905,3,'jiangyongxian','J',0),(1913,431126,'宁远县',1905,3,'ningyuanxian','N',0),(1914,431127,'蓝山县',1905,3,'lanshanxian','L',0),(1915,431128,'新田县',1905,3,'xintianxian','X',0),(1916,431129,'江华县',1905,3,'jianghuaxian','J',0),(1917,431200,'怀化市',1808,2,'huaihuashi','H',0),(1918,431202,'鹤城区',1917,3,'hechengqu','H',0),(1919,431221,'中方县',1917,3,'zhongfangxian','Z',0),(1920,431222,'沅陵县',1917,3,'yuanlingxian','Y',0),(1921,431223,'辰溪县',1917,3,'chenxixian','C',0),(1922,431224,'溆浦县',1917,3,'xupuxian','X',0),(1923,431225,'会同县',1917,3,'huitongxian','H',0),(1924,431226,'麻阳县',1917,3,'mayangxian','M',0),(1925,431227,'新晃县',1917,3,'xinhuangxian','X',0),(1926,431228,'芷江县',1917,3,'zhijiangxian','Z',0),(1927,431229,'靖州县',1917,3,'jingzhouxian','J',0),(1928,431230,'通道县',1917,3,'tongdaoxian','T',0),(1929,431281,'洪江市',1917,3,'hongjiangshi','H',0),(1930,431300,'娄底市',1808,2,'loudishi','L',0),(1931,431302,'娄星区',1930,3,'louxingqu','L',0),(1932,431321,'双峰县',1930,3,'shuangfengxian','S',0),(1933,431322,'新化县',1930,3,'xinhuaxian','X',0),(1934,431381,'冷水江市',1930,3,'lengshuijiangshi','L',0),(1935,431382,'涟源市',1930,3,'lianyuanshi','L',0),(1936,433100,'湘西州',1808,2,'xiangxizhou','X',0),(1937,433101,'吉首市',1936,3,'jishoushi','J',0),(1938,433122,'泸溪县',1936,3,'luxixian','L',0),(1939,433123,'凤凰县',1936,3,'fenghuangxian','F',0),(1940,433124,'花垣县',1936,3,'huayuanxian','H',0),(1941,433125,'保靖县',1936,3,'baojingxian','B',0),(1942,433126,'古丈县',1936,3,'guzhangxian','G',0),(1943,433127,'永顺县',1936,3,'yongshunxian','Y',0),(1944,433130,'龙山县',1936,3,'longshanxian','L',0),(1945,440000,'广东',0,1,'guangdong','G',0),(1946,440100,'广州市',1945,2,'guangzhoushi','G',0),(1947,440103,'荔湾区',1946,3,'liwanqu','L',0),(1948,440104,'越秀区',1946,3,'yuexiuqu','Y',0),(1949,440105,'海珠区',1946,3,'haizhuqu','H',0),(1950,440106,'天河区',1946,3,'tianhequ','T',0),(1951,440111,'白云区',1946,3,'baiyunqu','B',0),(1952,440112,'黄埔区',1946,3,'huangpuqu','H',0),(1953,440113,'番禺区',1946,3,'fanyuqu','F',0),(1954,440114,'花都区',1946,3,'huaduqu','H',0),(1955,440115,'南沙区',1946,3,'nanshaqu','N',0),(1956,440116,'萝岗区',1946,3,'luogangqu','L',0),(1957,440183,'增城市',1946,3,'zengchengshi','Z',0),(1958,440184,'从化市',1946,3,'conghuashi','C',0),(1959,440200,'韶关市',1945,2,'shaoguanshi','S',0),(1960,440203,'武江区',1959,3,'wujiangqu','W',0),(1961,440204,'浈江区',1959,3,'zhenjiangqu','Z',0),(1962,440205,'曲江区',1959,3,'qujiangqu','Q',0),(1963,440222,'始兴县',1959,3,'shixingxian','S',0),(1964,440224,'仁化县',1959,3,'renhuaxian','R',0),(1965,440229,'翁源县',1959,3,'wengyuanxian','W',0),(1966,440232,'乳源县',1959,3,'ruyuanxian','R',0),(1967,440233,'新丰县',1959,3,'xinfengxian','X',0),(1968,440281,'乐昌市',1959,3,'lechangshi','L',0),(1969,440282,'南雄市',1959,3,'nanxiongshi','N',0),(1970,440300,'深圳市',1945,2,'shenzhenshi','S',0),(1971,440303,'罗湖区',1970,3,'luohuqu','L',0),(1972,440304,'福田区',1970,3,'futianqu','F',0),(1973,440305,'南山区',1970,3,'nanshanqu','N',0),(1974,440306,'宝安区',1970,3,'baoanqu','B',0),(1975,440307,'龙岗区',1970,3,'longgangqu','L',0),(1976,440308,'盐田区',1970,3,'yantianqu','Y',0),(1977,440400,'珠海市',1945,2,'zhuhaishi','Z',0),(1978,440402,'香洲区',1977,3,'xiangzhouqu','X',0),(1979,440403,'斗门区',1977,3,'doumenqu','D',0),(1980,440404,'金湾区',1977,3,'jinwanqu','J',0),(1981,440500,'汕头市',1945,2,'shantoushi','S',0),(1982,440507,'龙湖区',1981,3,'longhuqu','L',0),(1983,440511,'金平区',1981,3,'jinpingqu','J',0),(1984,440512,'濠江区',1981,3,'haojiangqu','H',0),(1985,440513,'潮阳区',1981,3,'chaoyangqu','C',0),(1986,440514,'潮南区',1981,3,'chaonanqu','C',0),(1987,440515,'澄海区',1981,3,'chenghaiqu','C',0),(1988,440523,'南澳县',1981,3,'nanaoxian','N',0),(1989,440600,'佛山市',1945,2,'foshanshi','F',0),(1990,440604,'禅城区',1989,3,'chanchengqu','C',0),(1991,440605,'南海区',1989,3,'nanhaiqu','N',0),(1992,440606,'顺德区',1989,3,'shundequ','S',0),(1993,440607,'三水区',1989,3,'sanshuiqu','S',0),(1994,440608,'高明区',1989,3,'gaomingqu','G',0),(1995,440700,'江门市',1945,2,'jiangmenshi','J',0),(1996,440703,'蓬江区',1995,3,'pengjiangqu','P',0),(1997,440704,'江海区',1995,3,'jianghaiqu','J',0),(1998,440705,'新会区',1995,3,'xinhuiqu','X',0),(1999,440781,'台山市',1995,3,'taishanshi','T',0),(2000,440783,'开平市',1995,3,'kaipingshi','K',0),(2001,440784,'鹤山市',1995,3,'heshanshi','H',0),(2002,440785,'恩平市',1995,3,'enpingshi','E',0),(2003,440800,'湛江市',1945,2,'zhanjiangshi','Z',0),(2004,440802,'赤坎区',2003,3,'chikanqu','C',0),(2005,440803,'霞山区',2003,3,'xiashanqu','X',0),(2006,440804,'坡头区',2003,3,'potouqu','P',0),(2007,440811,'麻章区',2003,3,'mazhangqu','M',0),(2008,440823,'遂溪县',2003,3,'suixixian','S',0),(2009,440825,'徐闻县',2003,3,'xuwenxian','X',0),(2010,440881,'廉江市',2003,3,'lianjiangshi','L',0),(2011,440882,'雷州市',2003,3,'leizhoushi','L',0),(2012,440883,'吴川市',2003,3,'wuchuanshi','W',0),(2013,440900,'茂名市',1945,2,'maomingshi','M',0),(2014,440902,'茂南区',2013,3,'maonanqu','M',0),(2015,440903,'茂港区',2013,3,'maogangqu','M',0),(2016,440923,'电白县',2013,3,'dianbaixian','D',0),(2017,440981,'高州市',2013,3,'gaozhoushi','G',0),(2018,440982,'化州市',2013,3,'huazhoushi','H',0),(2019,440983,'信宜市',2013,3,'xinyishi','X',0),(2020,441200,'肇庆市',1945,2,'zhaoqingshi','Z',0),(2021,441202,'端州区',2020,3,'duanzhouqu','D',0),(2022,441203,'鼎湖区',2020,3,'dinghuqu','D',0),(2023,441223,'广宁县',2020,3,'guangningxian','G',0),(2024,441224,'怀集县',2020,3,'huaijixian','H',0),(2025,441225,'封开县',2020,3,'fengkaixian','F',0),(2026,441226,'德庆县',2020,3,'deqingxian','D',0),(2027,441283,'高要市',2020,3,'gaoyaoshi','G',0),(2028,441284,'四会市',2020,3,'sihuishi','S',0),(2029,441300,'惠州市',1945,2,'huizhoushi','H',0),(2030,441302,'惠城区',2029,3,'huichengqu','H',0),(2031,441303,'惠阳区',2029,3,'huiyangqu','H',0),(2032,441322,'博罗县',2029,3,'boluoxian','B',0),(2033,441323,'惠东县',2029,3,'huidongxian','H',0),(2034,441324,'龙门县',2029,3,'longmenxian','L',0),(2035,441400,'梅州市',1945,2,'meizhoushi','M',0),(2036,441402,'梅江区',2035,3,'meijiangqu','M',0),(2037,441421,'梅县',2035,3,'meixian','M',0),(2038,441422,'大埔县',2035,3,'dapuxian','D',0),(2039,441423,'丰顺县',2035,3,'fengshunxian','F',0),(2040,441424,'五华县',2035,3,'wuhuaxian','W',0),(2041,441426,'平远县',2035,3,'pingyuanxian','P',0),(2042,441427,'蕉岭县',2035,3,'jiaolingxian','J',0),(2043,441481,'兴宁市',2035,3,'xingningshi','X',0),(2044,441500,'汕尾市',1945,2,'shanweishi','S',0),(2045,441502,'城区',2044,3,'chengqu','C',0),(2046,441521,'海丰县',2044,3,'haifengxian','H',0),(2047,441523,'陆河县',2044,3,'luhexian','L',0),(2048,441581,'陆丰市',2044,3,'lufengshi','L',0),(2049,441600,'河源市',1945,2,'heyuanshi','H',0),(2050,441602,'源城区',2049,3,'yuanchengqu','Y',0),(2051,441621,'紫金县',2049,3,'zijinxian','Z',0),(2052,441622,'龙川县',2049,3,'longchuanxian','L',0),(2053,441623,'连平县',2049,3,'lianpingxian','L',0),(2054,441624,'和平县',2049,3,'hepingxian','H',0),(2055,441625,'东源县',2049,3,'dongyuanxian','D',0),(2056,441700,'阳江市',1945,2,'yangjiangshi','Y',0),(2057,441702,'江城区',2056,3,'jiangchengqu','J',0),(2058,441721,'阳西县',2056,3,'yangxixian','Y',0),(2059,441723,'阳东县',2056,3,'yangdongxian','Y',0),(2060,441781,'阳春市',2056,3,'yangchunshi','Y',0),(2061,441800,'清远市',1945,2,'qingyuanshi','Q',0),(2062,441802,'清城区',2061,3,'qingchengqu','Q',0),(2063,441803,'清新区',2061,3,'qingxinqu','Q',0),(2064,441821,'佛冈县',2061,3,'fogangxian','F',0),(2065,441823,'阳山县',2061,3,'yangshanxian','Y',0),(2066,441825,'连山县',2061,3,'lianshanxian','L',0),(2067,441826,'连南县',2061,3,'liannanxian','L',0),(2068,441881,'英德市',2061,3,'yingdeshi','Y',0),(2069,441882,'连州市',2061,3,'lianzhoushi','L',0),(2070,441900,'东莞市',1945,2,'dongguanshi','D',0),(2071,442000,'中山市',1945,2,'zhongshanshi','Z',0),(2072,445100,'潮州市',1945,2,'chaozhoushi','C',0),(2073,445102,'湘桥区',2072,3,'xiangqiaoqu','X',0),(2074,445103,'潮安区',2072,3,'chaoanqu','C',0),(2075,445122,'饶平县',2072,3,'raopingxian','R',0),(2076,445200,'揭阳市',1945,2,'jieyangshi','J',0),(2077,445202,'榕城区',2076,3,'rongchengqu','R',0),(2078,445203,'揭东区',2076,3,'jiedongqu','J',0),(2079,445222,'揭西县',2076,3,'jiexixian','J',0),(2080,445224,'惠来县',2076,3,'huilaixian','H',0),(2081,445281,'普宁市',2076,3,'puningshi','P',0),(2082,445300,'云浮市',1945,2,'yunfushi','Y',0),(2083,445302,'云城区',2082,3,'yunchengqu','Y',0),(2084,445321,'新兴县',2082,3,'xinxingxian','X',0),(2085,445322,'郁南县',2082,3,'yunanxian','Y',0),(2086,445323,'云安县',2082,3,'yunanxian','Y',0),(2087,445381,'罗定市',2082,3,'luodingshi','L',0),(2088,450000,'广西',0,1,'guangxi','G',0),(2089,450100,'南宁市',2088,2,'nanningshi','N',0),(2090,450102,'兴宁区',2089,3,'xingningqu','X',0),(2091,450103,'青秀区',2089,3,'qingxiuqu','Q',0),(2092,450105,'江南区',2089,3,'jiangnanqu','J',0),(2093,450107,'西乡塘区',2089,3,'xixiangtangqu','X',0),(2094,450108,'良庆区',2089,3,'liangqingqu','L',0),(2095,450109,'邕宁区',2089,3,'yongningqu','Y',0),(2096,450122,'武鸣县',2089,3,'wumingxian','W',0),(2097,450123,'隆安县',2089,3,'longanxian','L',0),(2098,450124,'马山县',2089,3,'mashanxian','M',0),(2099,450125,'上林县',2089,3,'shanglinxian','S',0),(2100,450126,'宾阳县',2089,3,'binyangxian','B',0),(2101,450127,'横县',2089,3,'hengxian','H',0),(2102,450200,'柳州市',2088,2,'liuzhoushi','L',0),(2103,450202,'城中区',2102,3,'chengzhongqu','C',0),(2104,450203,'鱼峰区',2102,3,'yufengqu','Y',0),(2105,450204,'柳南区',2102,3,'liunanqu','L',0),(2106,450205,'柳北区',2102,3,'liubeiqu','L',0),(2107,450221,'柳江县',2102,3,'liujiangxian','L',0),(2108,450222,'柳城县',2102,3,'liuchengxian','L',0),(2109,450223,'鹿寨县',2102,3,'luzhaixian','L',0),(2110,450224,'融安县',2102,3,'ronganxian','R',0),(2111,450225,'融水县',2102,3,'rongshuixian','R',0),(2112,450226,'三江县',2102,3,'sanjiangxian','S',0),(2113,450300,'桂林市',2088,2,'guilinshi','G',0),(2114,450302,'秀峰区',2113,3,'xiufengqu','X',0),(2115,450303,'叠彩区',2113,3,'diecaiqu','D',0),(2116,450304,'象山区',2113,3,'xiangshanqu','X',0),(2117,450305,'七星区',2113,3,'qixingqu','Q',0),(2118,450311,'雁山区',2113,3,'yanshanqu','Y',0),(2119,450312,'临桂区',2113,3,'linguiqu','L',0),(2120,450321,'阳朔县',2113,3,'yangshuoxian','Y',0),(2121,450323,'灵川县',2113,3,'lingchuanxian','L',0),(2122,450324,'全州县',2113,3,'quanzhouxian','Q',0),(2123,450325,'兴安县',2113,3,'xinganxian','X',0),(2124,450326,'永福县',2113,3,'yongfuxian','Y',0),(2125,450327,'灌阳县',2113,3,'guanyangxian','G',0),(2126,450328,'龙胜县',2113,3,'longshengxian','L',0),(2127,450329,'资源县',2113,3,'ziyuanxian','Z',0),(2128,450330,'平乐县',2113,3,'pinglexian','P',0),(2129,450331,'荔浦县',2113,3,'lipuxian','L',0),(2130,450332,'恭城县',2113,3,'gongchengxian','G',0),(2131,450400,'梧州市',2088,2,'wuzhoushi','W',0),(2132,450403,'万秀区',2131,3,'wanxiuqu','W',0),(2133,450405,'长洲区',2131,3,'changzhouqu','C',0),(2134,450406,'龙圩区',2131,3,'longweiqu','L',0),(2135,450421,'苍梧县',2131,3,'cangwuxian','C',0),(2136,450422,'藤县',2131,3,'tengxian','T',0),(2137,450423,'蒙山县',2131,3,'mengshanxian','M',0),(2138,450481,'岑溪市',2131,3,'cenxishi','C',0),(2139,450500,'北海市',2088,2,'beihaishi','B',0),(2140,450502,'海城区',2139,3,'haichengqu','H',0),(2141,450503,'银海区',2139,3,'yinhaiqu','Y',0),(2142,450512,'铁山港区',2139,3,'tieshangangqu','T',0),(2143,450521,'合浦县',2139,3,'hepuxian','H',0),(2144,450600,'防城港市',2088,2,'fangchenggangshi','F',0),(2145,450602,'港口区',2144,3,'gangkouqu','G',0),(2146,450603,'防城区',2144,3,'fangchengqu','F',0),(2147,450621,'上思县',2144,3,'shangsixian','S',0),(2148,450681,'东兴市',2144,3,'dongxingshi','D',0),(2149,450700,'钦州市',2088,2,'qinzhoushi','Q',0),(2150,450702,'钦南区',2149,3,'qinnanqu','Q',0),(2151,450703,'钦北区',2149,3,'qinbeiqu','Q',0),(2152,450721,'灵山县',2149,3,'lingshanxian','L',0),(2153,450722,'浦北县',2149,3,'pubeixian','P',0),(2154,450800,'贵港市',2088,2,'guigangshi','G',0),(2155,450802,'港北区',2154,3,'gangbeiqu','G',0),(2156,450803,'港南区',2154,3,'gangnanqu','G',0),(2157,450804,'覃塘区',2154,3,'tantangqu','T',0),(2158,450821,'平南县',2154,3,'pingnanxian','P',0),(2159,450881,'桂平市',2154,3,'guipingshi','G',0),(2160,450900,'玉林市',2088,2,'yulinshi','Y',0),(2161,450902,'玉州区',2160,3,'yuzhouqu','Y',0),(2162,450903,'福绵区',2160,3,'fumianqu','F',0),(2163,450921,'容县',2160,3,'rongxian','R',0),(2164,450922,'陆川县',2160,3,'luchuanxian','L',0),(2165,450923,'博白县',2160,3,'bobaixian','B',0),(2166,450924,'兴业县',2160,3,'xingyexian','X',0),(2167,450981,'北流市',2160,3,'beiliushi','B',0),(2168,451000,'百色市',2088,2,'baiseshi','B',0),(2169,451002,'右江区',2168,3,'youjiangqu','Y',0),(2170,451021,'田阳县',2168,3,'tianyangxian','T',0),(2171,451022,'田东县',2168,3,'tiandongxian','T',0),(2172,451023,'平果县',2168,3,'pingguoxian','P',0),(2173,451024,'德保县',2168,3,'debaoxian','D',0),(2174,451025,'靖西县',2168,3,'jingxixian','J',0),(2175,451026,'那坡县',2168,3,'napoxian','N',0),(2176,451027,'凌云县',2168,3,'lingyunxian','L',0),(2177,451028,'乐业县',2168,3,'leyexian','L',0),(2178,451029,'田林县',2168,3,'tianlinxian','T',0),(2179,451030,'西林县',2168,3,'xilinxian','X',0),(2180,451031,'隆林县',2168,3,'longlinxian','L',0),(2181,451100,'贺州市',2088,2,'hezhoushi','H',0),(2182,451102,'八步区',2181,3,'babuqu','B',0),(2183,451121,'昭平县',2181,3,'zhaopingxian','Z',0),(2184,451122,'钟山县',2181,3,'zhongshanxian','Z',0),(2185,451123,'富川县',2181,3,'fuchuanxian','F',0),(2186,451200,'河池市',2088,2,'hechishi','H',0),(2187,451202,'金城江区',2186,3,'jinchengjiangqu','J',0),(2188,451221,'南丹县',2186,3,'nandanxian','N',0),(2189,451222,'天峨县',2186,3,'tianexian','T',0),(2190,451223,'凤山县',2186,3,'fengshanxian','F',0),(2191,451224,'东兰县',2186,3,'donglanxian','D',0),(2192,451225,'罗城县',2186,3,'luochengxian','L',0),(2193,451226,'环江县',2186,3,'huanjiangxian','H',0),(2194,451227,'巴马县',2186,3,'bamaxian','B',0),(2195,451228,'都安县',2186,3,'duanxian','D',0),(2196,451229,'大化县',2186,3,'dahuaxian','D',0),(2197,451281,'宜州市',2186,3,'yizhoushi','Y',0),(2198,451300,'来宾市',2088,2,'laibinshi','L',0),(2199,451302,'兴宾区',2198,3,'xingbinqu','X',0),(2200,451321,'忻城县',2198,3,'xinchengxian','X',0),(2201,451322,'象州县',2198,3,'xiangzhouxian','X',0),(2202,451323,'武宣县',2198,3,'wuxuanxian','W',0),(2203,451324,'金秀县',2198,3,'jinxiuxian','J',0),(2204,451381,'合山市',2198,3,'heshanshi','H',0),(2205,451400,'崇左市',2088,2,'chongzuoshi','C',0),(2206,451402,'江州区',2205,3,'jiangzhouqu','J',0),(2207,451421,'扶绥县',2205,3,'fusuixian','F',0),(2208,451422,'宁明县',2205,3,'ningmingxian','N',0),(2209,451423,'龙州县',2205,3,'longzhouxian','L',0),(2210,451424,'大新县',2205,3,'daxinxian','D',0),(2211,451425,'天等县',2205,3,'tiandengxian','T',0),(2212,451481,'凭祥市',2205,3,'pingxiangshi','P',0),(2213,460000,'海南',0,1,'hainan','H',0),(2214,460100,'海口市',2213,2,'haikoushi','H',0),(2215,460105,'秀英区',2214,3,'xiuyingqu','X',0),(2216,460106,'龙华区',2214,3,'longhuaqu','L',0),(2217,460107,'琼山区',2214,3,'qiongshanqu','Q',0),(2218,460108,'美兰区',2214,3,'meilanqu','M',0),(2219,460200,'三亚市',2213,2,'sanyashi','S',0),(2220,460300,'三沙市',2213,2,'sanshashi','S',0),(2221,460321,'西沙群岛',2220,3,'xishaqundao','X',0),(2222,460322,'南沙群岛',2220,3,'nanshaqundao','N',0),(2223,460323,'中沙群岛',2220,3,'zhongshaqundao','Z',0),(2224,469001,'五指山市',2213,2,'wuzhishanshi','W',0),(2225,469002,'琼海市',2213,2,'qionghaishi','Q',0),(2226,469003,'儋州市',2213,2,'danzhoushi','D',0),(2227,469005,'文昌市',2213,2,'wenchangshi','W',0),(2228,469006,'万宁市',2213,2,'wanningshi','W',0),(2229,469007,'东方市',2213,2,'dongfangshi','D',0),(2230,469021,'定安县',2213,2,'dinganxian','D',0),(2231,469022,'屯昌县',2213,2,'tunchangxian','T',0),(2232,469023,'澄迈县',2213,2,'chengmaixian','C',0),(2233,469024,'临高县',2213,2,'lingaoxian','L',0),(2234,469025,'白沙县',2213,2,'baishaxian','B',0),(2235,469026,'昌江县',2213,2,'changjiangxian','C',0),(2236,469027,'乐东县',2213,2,'ledongxian','L',0),(2237,469028,'陵水县',2213,2,'lingshuixian','L',0),(2238,469029,'保亭县',2213,2,'baotingxian','B',0),(2239,469030,'琼中县',2213,2,'qiongzhongxian','Q',0),(2240,500000,'重庆',0,1,'chongqing','C',0),(2241,500100,'重庆市',2240,2,'zhongqingshi','Z',0),(2242,500101,'万州区',2241,3,'wanzhouqu','W',0),(2243,500102,'涪陵区',2241,3,'fulingqu','F',0),(2244,500103,'渝中区',2241,3,'yuzhongqu','Y',0),(2245,500104,'大渡口区',2241,3,'dadukouqu','D',0),(2246,500105,'江北区',2241,3,'jiangbeiqu','J',0),(2247,500106,'沙坪坝区',2241,3,'shapingbaqu','S',0),(2248,500107,'九龙坡区',2241,3,'jiulongpoqu','J',0),(2249,500108,'南岸区',2241,3,'nananqu','N',0),(2250,500109,'北碚区',2241,3,'beibeiqu','B',0),(2251,500110,'綦江区',2241,3,'qijiangqu','Q',0),(2252,500111,'大足区',2241,3,'dazuqu','D',0),(2253,500112,'渝北区',2241,3,'yubeiqu','Y',0),(2254,500113,'巴南区',2241,3,'bananqu','B',0),(2255,500114,'黔江区',2241,3,'qianjiangqu','Q',0),(2256,500115,'长寿区',2241,3,'changshouqu','C',0),(2257,500116,'江津区',2241,3,'jiangjinqu','J',0),(2258,500117,'合川区',2241,3,'hechuanqu','H',0),(2259,500118,'永川区',2241,3,'yongchuanqu','Y',0),(2260,500119,'南川区',2241,3,'nanchuanqu','N',0),(2261,500223,'潼南县',2241,3,'tongnanxian','T',0),(2262,500224,'铜梁县',2241,3,'tongliangxian','T',0),(2263,500226,'荣昌县',2241,3,'rongchangxian','R',0),(2264,500227,'璧山县',2241,3,'bishanxian','B',0),(2265,500228,'梁平县',2241,3,'liangpingxian','L',0),(2266,500229,'城口县',2241,3,'chengkouxian','C',0),(2267,500230,'丰都县',2241,3,'fengduxian','F',0),(2268,500231,'垫江县',2241,3,'dianjiangxian','D',0),(2269,500232,'武隆县',2241,3,'wulongxian','W',0),(2270,500233,'忠县',2241,3,'zhongxian','Z',0),(2271,500234,'开县',2241,3,'kaixian','K',0),(2272,500235,'云阳县',2241,3,'yunyangxian','Y',0),(2273,500236,'奉节县',2241,3,'fengjiexian','F',0),(2274,500237,'巫山县',2241,3,'wushanxian','W',0),(2275,500238,'巫溪县',2241,3,'wuxixian','W',0),(2276,500240,'石柱县',2241,3,'shizhuxian','S',0),(2277,500241,'秀山县',2241,3,'xiushanxian','X',0),(2278,500242,'酉阳县',2241,3,'youyangxian','Y',0),(2279,500243,'彭水县',2241,3,'pengshuixian','P',0),(2280,510000,'四川',0,1,'sichuan','S',0),(2281,510100,'成都市',2280,2,'chengdushi','C',0),(2282,510104,'锦江区',2281,3,'jinjiangqu','J',0),(2283,510105,'青羊区',2281,3,'qingyangqu','Q',0),(2284,510106,'金牛区',2281,3,'jinniuqu','J',0),(2285,510107,'武侯区',2281,3,'wuhouqu','W',0),(2286,510108,'成华区',2281,3,'chenghuaqu','C',0),(2287,510112,'龙泉驿区',2281,3,'longquanyiqu','L',0),(2288,510113,'青白江区',2281,3,'qingbaijiangqu','Q',0),(2289,510114,'新都区',2281,3,'xinduqu','X',0),(2290,510115,'温江区',2281,3,'wenjiangqu','W',0),(2291,510121,'金堂县',2281,3,'jintangxian','J',0),(2292,510122,'双流县',2281,3,'shuangliuxian','S',0),(2293,510124,'郫县',2281,3,'pixian','P',0),(2294,510129,'大邑县',2281,3,'dayixian','D',0),(2295,510131,'蒲江县',2281,3,'pujiangxian','P',0),(2296,510132,'新津县',2281,3,'xinjinxian','X',0),(2297,510181,'都江堰市',2281,3,'dujiangyanshi','D',0),(2298,510182,'彭州市',2281,3,'pengzhoushi','P',0),(2299,510183,'邛崃市',2281,3,'qionglaishi','Q',0),(2300,510184,'崇州市',2281,3,'chongzhoushi','C',0),(2301,510300,'自贡市',2280,2,'zigongshi','Z',0),(2302,510302,'自流井区',2301,3,'ziliujingqu','Z',0),(2303,510303,'贡井区',2301,3,'gongjingqu','G',0),(2304,510304,'大安区',2301,3,'daanqu','D',0),(2305,510311,'沿滩区',2301,3,'yantanqu','Y',0),(2306,510321,'荣县',2301,3,'rongxian','R',0),(2307,510322,'富顺县',2301,3,'fushunxian','F',0),(2308,510400,'攀枝花市',2280,2,'panzhihuashi','P',0),(2309,510402,'东区',2308,3,'dongqu','D',0),(2310,510403,'西区',2308,3,'xiqu','X',0),(2311,510411,'仁和区',2308,3,'renhequ','R',0),(2312,510421,'米易县',2308,3,'miyixian','M',0),(2313,510422,'盐边县',2308,3,'yanbianxian','Y',0),(2314,510500,'泸州市',2280,2,'luzhoushi','L',0),(2315,510502,'江阳区',2314,3,'jiangyangqu','J',0),(2316,510503,'纳溪区',2314,3,'naxiqu','N',0),(2317,510504,'龙马潭区',2314,3,'longmatanqu','L',0),(2318,510521,'泸县',2314,3,'luxian','L',0),(2319,510522,'合江县',2314,3,'hejiangxian','H',0),(2320,510524,'叙永县',2314,3,'xuyongxian','X',0),(2321,510525,'古蔺县',2314,3,'gulinxian','G',0),(2322,510600,'德阳市',2280,2,'deyangshi','D',0),(2323,510603,'旌阳区',2322,3,'jingyangqu','J',0),(2324,510623,'中江县',2322,3,'zhongjiangxian','Z',0),(2325,510626,'罗江县',2322,3,'luojiangxian','L',0),(2326,510681,'广汉市',2322,3,'guanghanshi','G',0),(2327,510682,'什邡市',2322,3,'shifangshi','S',0),(2328,510683,'绵竹市',2322,3,'mianzhushi','M',0),(2329,510700,'绵阳市',2280,2,'mianyangshi','M',0),(2330,510703,'涪城区',2329,3,'fuchengqu','F',0),(2331,510704,'游仙区',2329,3,'youxianqu','Y',0),(2332,510722,'三台县',2329,3,'santaixian','S',0),(2333,510723,'盐亭县',2329,3,'yantingxian','Y',0),(2334,510724,'安县',2329,3,'anxian','A',0),(2335,510725,'梓潼县',2329,3,'zitongxian','Z',0),(2336,510726,'北川县',2329,3,'beichuanxian','B',0),(2337,510727,'平武县',2329,3,'pingwuxian','P',0),(2338,510781,'江油市',2329,3,'jiangyoushi','J',0),(2339,510800,'广元市',2280,2,'guangyuanshi','G',0),(2340,510802,'利州区',2339,3,'lizhouqu','L',0),(2341,510811,'元坝区',2339,3,'yuanbaqu','Y',0),(2342,510812,'朝天区',2339,3,'zhaotianqu','Z',0),(2343,510821,'旺苍县',2339,3,'wangcangxian','W',0),(2344,510822,'青川县',2339,3,'qingchuanxian','Q',0),(2345,510823,'剑阁县',2339,3,'jiangexian','J',0),(2346,510824,'苍溪县',2339,3,'cangxixian','C',0),(2347,510900,'遂宁市',2280,2,'suiningshi','S',0),(2348,510903,'船山区',2347,3,'chuanshanqu','C',0),(2349,510904,'安居区',2347,3,'anjuqu','A',0),(2350,510921,'蓬溪县',2347,3,'pengxixian','P',0),(2351,510922,'射洪县',2347,3,'shehongxian','S',0),(2352,510923,'大英县',2347,3,'dayingxian','D',0),(2353,511000,'内江市',2280,2,'neijiangshi','N',0),(2354,511002,'市中区',2353,3,'shizhongqu','S',0),(2355,511011,'东兴区',2353,3,'dongxingqu','D',0),(2356,511024,'威远县',2353,3,'weiyuanxian','W',0),(2357,511025,'资中县',2353,3,'zizhongxian','Z',0),(2358,511028,'隆昌县',2353,3,'longchangxian','L',0),(2359,511100,'乐山市',2280,2,'leshanshi','L',0),(2360,511102,'市中区',2359,3,'shizhongqu','S',0),(2361,511111,'沙湾区',2359,3,'shawanqu','S',0),(2362,511112,'五通桥区',2359,3,'wutongqiaoqu','W',0),(2363,511113,'金口河区',2359,3,'jinkouhequ','J',0),(2364,511123,'犍为县',2359,3,'jianweixian','J',0),(2365,511124,'井研县',2359,3,'jingyanxian','J',0),(2366,511126,'夹江县',2359,3,'jiajiangxian','J',0),(2367,511129,'沐川县',2359,3,'muchuanxian','M',0),(2368,511132,'峨边县',2359,3,'ebianxian','E',0),(2369,511133,'马边县',2359,3,'mabianxian','M',0),(2370,511181,'峨眉山市',2359,3,'emeishanshi','E',0),(2371,511300,'南充市',2280,2,'nanchongshi','N',0),(2372,511302,'顺庆区',2371,3,'shunqingqu','S',0),(2373,511303,'高坪区',2371,3,'gaopingqu','G',0),(2374,511304,'嘉陵区',2371,3,'jialingqu','J',0),(2375,511321,'南部县',2371,3,'nanbuxian','N',0),(2376,511322,'营山县',2371,3,'yingshanxian','Y',0),(2377,511323,'蓬安县',2371,3,'penganxian','P',0),(2378,511324,'仪陇县',2371,3,'yilongxian','Y',0),(2379,511325,'西充县',2371,3,'xichongxian','X',0),(2380,511381,'阆中市',2371,3,'langzhongshi','L',0),(2381,511400,'眉山市',2280,2,'meishanshi','M',0),(2382,511402,'东坡区',2381,3,'dongpoqu','D',0),(2383,511421,'仁寿县',2381,3,'renshouxian','R',0),(2384,511422,'彭山县',2381,3,'pengshanxian','P',0),(2385,511423,'洪雅县',2381,3,'hongyaxian','H',0),(2386,511424,'丹棱县',2381,3,'danlengxian','D',0),(2387,511425,'青神县',2381,3,'qingshenxian','Q',0),(2388,511500,'宜宾市',2280,2,'yibinshi','Y',0),(2389,511502,'翠屏区',2388,3,'cuipingqu','C',0),(2390,511503,'南溪区',2388,3,'nanxiqu','N',0),(2391,511521,'宜宾县',2388,3,'yibinxian','Y',0),(2392,511523,'江安县',2388,3,'jianganxian','J',0),(2393,511524,'长宁县',2388,3,'changningxian','C',0),(2394,511525,'高县',2388,3,'gaoxian','G',0),(2395,511526,'珙县',2388,3,'gongxian','G',0),(2396,511527,'筠连县',2388,3,'yunlianxian','Y',0),(2397,511528,'兴文县',2388,3,'xingwenxian','X',0),(2398,511529,'屏山县',2388,3,'pingshanxian','P',0),(2399,511600,'广安市',2280,2,'guanganshi','G',0),(2400,511602,'广安区',2399,3,'guanganqu','G',0),(2401,511603,'前锋区',2399,3,'qianfengqu','Q',0),(2402,511621,'岳池县',2399,3,'yuechixian','Y',0),(2403,511622,'武胜县',2399,3,'wushengxian','W',0),(2404,511623,'邻水县',2399,3,'linshuixian','L',0),(2405,511681,'华蓥市',2399,3,'huayingshi','H',0),(2406,511700,'达州市',2280,2,'dazhoushi','D',0),(2407,511702,'通川区',2406,3,'tongchuanqu','T',0),(2408,511703,'达川区',2406,3,'dachuanqu','D',0),(2409,511722,'宣汉县',2406,3,'xuanhanxian','X',0),(2410,511723,'开江县',2406,3,'kaijiangxian','K',0),(2411,511724,'大竹县',2406,3,'dazhuxian','D',0),(2412,511725,'渠县',2406,3,'quxian','Q',0),(2413,511781,'万源市',2406,3,'wanyuanshi','W',0),(2414,511800,'雅安市',2280,2,'yaanshi','Y',0),(2415,511802,'雨城区',2414,3,'yuchengqu','Y',0),(2416,511803,'名山区',2414,3,'mingshanqu','M',0),(2417,511822,'荥经县',2414,3,'xingjingxian','X',0),(2418,511823,'汉源县',2414,3,'hanyuanxian','H',0),(2419,511824,'石棉县',2414,3,'shimianxian','S',0),(2420,511825,'天全县',2414,3,'tianquanxian','T',0),(2421,511826,'芦山县',2414,3,'lushanxian','L',0),(2422,511827,'宝兴县',2414,3,'baoxingxian','B',0),(2423,511900,'巴中市',2280,2,'bazhongshi','B',0),(2424,511902,'巴州区',2423,3,'bazhouqu','B',0),(2425,511903,'恩阳区',2423,3,'enyangqu','E',0),(2426,511921,'通江县',2423,3,'tongjiangxian','T',0),(2427,511922,'南江县',2423,3,'nanjiangxian','N',0),(2428,511923,'平昌县',2423,3,'pingchangxian','P',0),(2429,512000,'资阳市',2280,2,'ziyangshi','Z',0),(2430,512002,'雁江区',2429,3,'yanjiangqu','Y',0),(2431,512021,'安岳县',2429,3,'anyuexian','A',0),(2432,512022,'乐至县',2429,3,'lezhixian','L',0),(2433,512081,'简阳市',2429,3,'jianyangshi','J',0),(2434,513200,'阿坝州',2280,2,'abazhou','A',0),(2435,513221,'汶川县',2434,3,'wenchuanxian','W',0),(2436,513222,'理县',2434,3,'lixian','L',0),(2437,513223,'茂县',2434,3,'maoxian','M',0),(2438,513224,'松潘县',2434,3,'songpanxian','S',0),(2439,513225,'九寨沟县',2434,3,'jiuzhaigouxian','J',0),(2440,513226,'金川县',2434,3,'jinchuanxian','J',0),(2441,513227,'小金县',2434,3,'xiaojinxian','X',0),(2442,513228,'黑水县',2434,3,'heishuixian','H',0),(2443,513229,'马尔康县',2434,3,'maerkangxian','M',0),(2444,513230,'壤塘县',2434,3,'rangtangxian','R',0),(2445,513231,'阿坝县',2434,3,'abaxian','A',0),(2446,513232,'若尔盖县',2434,3,'ruoergaixian','R',0),(2447,513233,'红原县',2434,3,'hongyuanxian','H',0),(2448,513300,'甘孜州',2280,2,'ganzizhou','G',0),(2449,513321,'康定县',2448,3,'kangdingxian','K',0),(2450,513322,'泸定县',2448,3,'ludingxian','L',0),(2451,513323,'丹巴县',2448,3,'danbaxian','D',0),(2452,513324,'九龙县',2448,3,'jiulongxian','J',0),(2453,513325,'雅江县',2448,3,'yajiangxian','Y',0),(2454,513326,'道孚县',2448,3,'daofuxian','D',0),(2455,513327,'炉霍县',2448,3,'luhuoxian','L',0),(2456,513328,'甘孜县',2448,3,'ganzixian','G',0),(2457,513329,'新龙县',2448,3,'xinlongxian','X',0),(2458,513330,'德格县',2448,3,'degexian','D',0),(2459,513331,'白玉县',2448,3,'baiyuxian','B',0),(2460,513332,'石渠县',2448,3,'shiquxian','S',0),(2461,513333,'色达县',2448,3,'sedaxian','S',0),(2462,513334,'理塘县',2448,3,'litangxian','L',0),(2463,513335,'巴塘县',2448,3,'batangxian','B',0),(2464,513336,'乡城县',2448,3,'xiangchengxian','X',0),(2465,513337,'稻城县',2448,3,'daochengxian','D',0),(2466,513338,'得荣县',2448,3,'derongxian','D',0),(2467,513400,'凉山州',2280,2,'liangshanzhou','L',0),(2468,513401,'西昌市',2467,3,'xichangshi','X',0),(2469,513422,'木里县',2467,3,'mulixian','M',0),(2470,513423,'盐源县',2467,3,'yanyuanxian','Y',0),(2471,513424,'德昌县',2467,3,'dechangxian','D',0),(2472,513425,'会理县',2467,3,'huilixian','H',0),(2473,513426,'会东县',2467,3,'huidongxian','H',0),(2474,513427,'宁南县',2467,3,'ningnanxian','N',0),(2475,513428,'普格县',2467,3,'pugexian','P',0),(2476,513429,'布拖县',2467,3,'butuoxian','B',0),(2477,513430,'金阳县',2467,3,'jinyangxian','J',0),(2478,513431,'昭觉县',2467,3,'zhaojuexian','Z',0),(2479,513432,'喜德县',2467,3,'xidexian','X',0),(2480,513433,'冕宁县',2467,3,'mianningxian','M',0),(2481,513434,'越西县',2467,3,'yuexixian','Y',0),(2482,513435,'甘洛县',2467,3,'ganluoxian','G',0),(2483,513436,'美姑县',2467,3,'meiguxian','M',0),(2484,513437,'雷波县',2467,3,'leiboxian','L',0),(2485,520000,'贵州',0,1,'guizhou','G',0),(2486,520100,'贵阳市',2485,2,'guiyangshi','G',0),(2487,520102,'南明区',2486,3,'nanmingqu','N',0),(2488,520103,'云岩区',2486,3,'yunyanqu','Y',0),(2489,520111,'花溪区',2486,3,'huaxiqu','H',0),(2490,520112,'乌当区',2486,3,'wudangqu','W',0),(2491,520113,'白云区',2486,3,'baiyunqu','B',0),(2492,520115,'观山湖区',2486,3,'guanshanhuqu','G',0),(2493,520121,'开阳县',2486,3,'kaiyangxian','K',0),(2494,520122,'息烽县',2486,3,'xifengxian','X',0),(2495,520123,'修文县',2486,3,'xiuwenxian','X',0),(2496,520181,'清镇市',2486,3,'qingzhenshi','Q',0),(2497,520200,'六盘水市',2485,2,'liupanshuishi','L',0),(2498,520201,'钟山区',2497,3,'zhongshanqu','Z',0),(2499,520203,'六枝特区',2497,3,'liuzhitequ','L',0),(2500,520221,'水城县',2497,3,'shuichengxian','S',0),(2501,520222,'盘县',2497,3,'panxian','P',0),(2502,520300,'遵义市',2485,2,'zunyishi','Z',0),(2503,520302,'红花岗区',2502,3,'honghuagangqu','H',0),(2504,520303,'汇川区',2502,3,'huichuanqu','H',0),(2505,520321,'遵义县',2502,3,'zunyixian','Z',0),(2506,520322,'桐梓县',2502,3,'tongzixian','T',0),(2507,520323,'绥阳县',2502,3,'suiyangxian','S',0),(2508,520324,'正安县',2502,3,'zhenganxian','Z',0),(2509,520325,'道真县',2502,3,'daozhenxian','D',0),(2510,520326,'务川县',2502,3,'wuchuanxian','W',0),(2511,520327,'凤冈县',2502,3,'fenggangxian','F',0),(2512,520328,'湄潭县',2502,3,'meitanxian','M',0),(2513,520329,'余庆县',2502,3,'yuqingxian','Y',0),(2514,520330,'习水县',2502,3,'xishuixian','X',0),(2515,520381,'赤水市',2502,3,'chishuishi','C',0),(2516,520382,'仁怀市',2502,3,'renhuaishi','R',0),(2517,520400,'安顺市',2485,2,'anshunshi','A',0),(2518,520402,'西秀区',2517,3,'xixiuqu','X',0),(2519,520421,'平坝县',2517,3,'pingbaxian','P',0),(2520,520422,'普定县',2517,3,'pudingxian','P',0),(2521,520423,'镇宁县',2517,3,'zhenningxian','Z',0),(2522,520424,'关岭县',2517,3,'guanlingxian','G',0),(2523,520425,'紫云县',2517,3,'ziyunxian','Z',0),(2524,520500,'毕节市',2485,2,'bijieshi','B',0),(2525,520502,'七星关区',2524,3,'qixingguanqu','Q',0),(2526,520521,'大方县',2524,3,'dafangxian','D',0),(2527,520522,'黔西县',2524,3,'qianxixian','Q',0),(2528,520523,'金沙县',2524,3,'jinshaxian','J',0),(2529,520524,'织金县',2524,3,'zhijinxian','Z',0),(2530,520525,'纳雍县',2524,3,'nayongxian','N',0),(2531,520526,'威宁县',2524,3,'weiningxian','W',0),(2532,520527,'赫章县',2524,3,'hezhangxian','H',0),(2533,520600,'铜仁市',2485,2,'tongrenshi','T',0),(2534,520602,'碧江区',2533,3,'bijiangqu','B',0),(2535,520603,'万山区',2533,3,'wanshanqu','W',0),(2536,520621,'江口县',2533,3,'jiangkouxian','J',0),(2537,520622,'玉屏县',2533,3,'yupingxian','Y',0),(2538,520623,'石阡县',2533,3,'shiqianxian','S',0),(2539,520624,'思南县',2533,3,'sinanxian','S',0),(2540,520625,'印江县',2533,3,'yinjiangxian','Y',0),(2541,520626,'德江县',2533,3,'dejiangxian','D',0),(2542,520627,'沿河县',2533,3,'yanhexian','Y',0),(2543,520628,'松桃县',2533,3,'songtaoxian','S',0),(2544,522300,'黔西南州',2485,2,'qianxinanzhou','Q',0),(2545,522301,'兴义市',2544,3,'xingyishi','X',0),(2546,522322,'兴仁县',2544,3,'xingrenxian','X',0),(2547,522323,'普安县',2544,3,'puanxian','P',0),(2548,522324,'晴隆县',2544,3,'qinglongxian','Q',0),(2549,522325,'贞丰县',2544,3,'zhenfengxian','Z',0),(2550,522326,'望谟县',2544,3,'wangmoxian','W',0),(2551,522327,'册亨县',2544,3,'cehengxian','C',0),(2552,522328,'安龙县',2544,3,'anlongxian','A',0),(2553,522600,'黔东南州',2485,2,'qiandongnanzhou','Q',0),(2554,522601,'凯里市',2553,3,'kailishi','K',0),(2555,522622,'黄平县',2553,3,'huangpingxian','H',0),(2556,522623,'施秉县',2553,3,'shibingxian','S',0),(2557,522624,'三穗县',2553,3,'sansuixian','S',0),(2558,522625,'镇远县',2553,3,'zhenyuanxian','Z',0),(2559,522626,'岑巩县',2553,3,'cengongxian','C',0),(2560,522627,'天柱县',2553,3,'tianzhuxian','T',0),(2561,522628,'锦屏县',2553,3,'jinpingxian','J',0),(2562,522629,'剑河县',2553,3,'jianhexian','J',0),(2563,522630,'台江县',2553,3,'taijiangxian','T',0),(2564,522631,'黎平县',2553,3,'lipingxian','L',0),(2565,522632,'榕江县',2553,3,'rongjiangxian','R',0),(2566,522633,'从江县',2553,3,'congjiangxian','C',0),(2567,522634,'雷山县',2553,3,'leishanxian','L',0),(2568,522635,'麻江县',2553,3,'majiangxian','M',0),(2569,522636,'丹寨县',2553,3,'danzhaixian','D',0),(2570,522700,'黔南州',2485,2,'qiannanzhou','Q',0),(2571,522701,'都匀市',2570,3,'duyunshi','D',0),(2572,522702,'福泉市',2570,3,'fuquanshi','F',0),(2573,522722,'荔波县',2570,3,'liboxian','L',0),(2574,522723,'贵定县',2570,3,'guidingxian','G',0),(2575,522725,'瓮安县',2570,3,'wenganxian','W',0),(2576,522726,'独山县',2570,3,'dushanxian','D',0),(2577,522727,'平塘县',2570,3,'pingtangxian','P',0),(2578,522728,'罗甸县',2570,3,'luodianxian','L',0),(2579,522729,'长顺县',2570,3,'changshunxian','C',0),(2580,522730,'龙里县',2570,3,'longlixian','L',0),(2581,522731,'惠水县',2570,3,'huishuixian','H',0),(2582,522732,'三都县',2570,3,'sanduxian','S',0),(2583,530000,'云南',0,1,'yunnan','Y',0),(2584,530100,'昆明市',2583,2,'kunmingshi','K',0),(2585,530102,'五华区',2584,3,'wuhuaqu','W',0),(2586,530103,'盘龙区',2584,3,'panlongqu','P',0),(2587,530111,'官渡区',2584,3,'guanduqu','G',0),(2588,530112,'西山区',2584,3,'xishanqu','X',0),(2589,530113,'东川区',2584,3,'dongchuanqu','D',0),(2590,530114,'呈贡区',2584,3,'chenggongqu','C',0),(2591,530122,'晋宁县',2584,3,'jinningxian','J',0),(2592,530124,'富民县',2584,3,'fuminxian','F',0),(2593,530125,'宜良县',2584,3,'yiliangxian','Y',0),(2594,530126,'石林县',2584,3,'shilinxian','S',0),(2595,530127,'嵩明县',2584,3,'songmingxian','S',0),(2596,530128,'禄劝县',2584,3,'luquanxian','L',0),(2597,530129,'寻甸县',2584,3,'xundianxian','X',0),(2598,530181,'安宁市',2584,3,'anningshi','A',0),(2599,530300,'曲靖市',2583,2,'qujingshi','Q',0),(2600,530302,'麒麟区',2599,3,'qilinqu','Q',0),(2601,530321,'马龙县',2599,3,'malongxian','M',0),(2602,530322,'陆良县',2599,3,'luliangxian','L',0),(2603,530323,'师宗县',2599,3,'shizongxian','S',0),(2604,530324,'罗平县',2599,3,'luopingxian','L',0),(2605,530325,'富源县',2599,3,'fuyuanxian','F',0),(2606,530326,'会泽县',2599,3,'huizexian','H',0),(2607,530328,'沾益县',2599,3,'zhanyixian','Z',0),(2608,530381,'宣威市',2599,3,'xuanweishi','X',0),(2609,530400,'玉溪市',2583,2,'yuxishi','Y',0),(2610,530402,'红塔区',2609,3,'hongtaqu','H',0),(2611,530421,'江川县',2609,3,'jiangchuanxian','J',0),(2612,530422,'澄江县',2609,3,'chengjiangxian','C',0),(2613,530423,'通海县',2609,3,'tonghaixian','T',0),(2614,530424,'华宁县',2609,3,'huaningxian','H',0),(2615,530425,'易门县',2609,3,'yimenxian','Y',0),(2616,530426,'峨山县',2609,3,'eshanxian','E',0),(2617,530427,'新平县',2609,3,'xinpingxian','X',0),(2618,530428,'元江县',2609,3,'yuanjiangxian','Y',0),(2619,530500,'保山市',2583,2,'baoshanshi','B',0),(2620,530502,'隆阳区',2619,3,'longyangqu','L',0),(2621,530521,'施甸县',2619,3,'shidianxian','S',0),(2622,530522,'腾冲县',2619,3,'tengchongxian','T',0),(2623,530523,'龙陵县',2619,3,'longlingxian','L',0),(2624,530524,'昌宁县',2619,3,'changningxian','C',0),(2625,530600,'昭通市',2583,2,'zhaotongshi','Z',0),(2626,530602,'昭阳区',2625,3,'zhaoyangqu','Z',0),(2627,530621,'鲁甸县',2625,3,'ludianxian','L',0),(2628,530622,'巧家县',2625,3,'qiaojiaxian','Q',0),(2629,530623,'盐津县',2625,3,'yanjinxian','Y',0),(2630,530624,'大关县',2625,3,'daguanxian','D',0),(2631,530625,'永善县',2625,3,'yongshanxian','Y',0),(2632,530626,'绥江县',2625,3,'suijiangxian','S',0),(2633,530627,'镇雄县',2625,3,'zhenxiongxian','Z',0),(2634,530628,'彝良县',2625,3,'yiliangxian','Y',0),(2635,530629,'威信县',2625,3,'weixinxian','W',0),(2636,530630,'水富县',2625,3,'shuifuxian','S',0),(2637,530700,'丽江市',2583,2,'lijiangshi','L',0),(2638,530702,'古城区',2637,3,'guchengqu','G',0),(2639,530721,'玉龙县',2637,3,'yulongxian','Y',0),(2640,530722,'永胜县',2637,3,'yongshengxian','Y',0),(2641,530723,'华坪县',2637,3,'huapingxian','H',0),(2642,530724,'宁蒗县',2637,3,'ninglangxian','N',0),(2643,530800,'普洱市',2583,2,'puershi','P',0),(2644,530802,'思茅区',2643,3,'simaoqu','S',0),(2645,530821,'宁洱县',2643,3,'ningerxian','N',0),(2646,530822,'墨江县',2643,3,'mojiangxian','M',0),(2647,530823,'景东县',2643,3,'jingdongxian','J',0),(2648,530824,'景谷县',2643,3,'jingguxian','J',0),(2649,530825,'镇沅县',2643,3,'zhenyuanxian','Z',0),(2650,530826,'江城县',2643,3,'jiangchengxian','J',0),(2651,530827,'孟连县',2643,3,'menglianxian','M',0),(2652,530828,'澜沧县',2643,3,'lancangxian','L',0),(2653,530829,'西盟县',2643,3,'ximengxian','X',0),(2654,530900,'临沧市',2583,2,'lincangshi','L',0),(2655,530902,'临翔区',2654,3,'linxiangqu','L',0),(2656,530921,'凤庆县',2654,3,'fengqingxian','F',0),(2657,530922,'云县',2654,3,'yunxian','Y',0),(2658,530923,'永德县',2654,3,'yongdexian','Y',0),(2659,530924,'镇康县',2654,3,'zhenkangxian','Z',0),(2660,530925,'双江县',2654,3,'shuangjiangxian','S',0),(2661,530926,'耿马县',2654,3,'gengmaxian','G',0),(2662,530927,'沧源县',2654,3,'cangyuanxian','C',0),(2663,532300,'楚雄州',2583,2,'chuxiongzhou','C',0),(2664,532301,'楚雄市',2663,3,'chuxiongshi','C',0),(2665,532322,'双柏县',2663,3,'shuangbaixian','S',0),(2666,532323,'牟定县',2663,3,'moudingxian','M',0),(2667,532324,'南华县',2663,3,'nanhuaxian','N',0),(2668,532325,'姚安县',2663,3,'yaoanxian','Y',0),(2669,532326,'大姚县',2663,3,'dayaoxian','D',0),(2670,532327,'永仁县',2663,3,'yongrenxian','Y',0),(2671,532328,'元谋县',2663,3,'yuanmouxian','Y',0),(2672,532329,'武定县',2663,3,'wudingxian','W',0),(2673,532331,'禄丰县',2663,3,'lufengxian','L',0),(2674,532500,'红河州',2583,2,'honghezhou','H',0),(2675,532501,'个旧市',2674,3,'gejiushi','G',0),(2676,532502,'开远市',2674,3,'kaiyuanshi','K',0),(2677,532503,'蒙自市',2674,3,'mengzishi','M',0),(2678,532504,'弥勒市',2674,3,'mileshi','M',0),(2679,532523,'屏边县',2674,3,'pingbianxian','P',0),(2680,532524,'建水县',2674,3,'jianshuixian','J',0),(2681,532525,'石屏县',2674,3,'shipingxian','S',0),(2682,532527,'泸西县',2674,3,'luxixian','L',0),(2683,532528,'元阳县',2674,3,'yuanyangxian','Y',0),(2684,532529,'红河县',2674,3,'honghexian','H',0),(2685,532530,'金平县',2674,3,'jinpingxian','J',0),(2686,532531,'绿春县',2674,3,'lvchunxian','L',0),(2687,532532,'河口县',2674,3,'hekouxian','H',0),(2688,532600,'文山州',2583,2,'wenshanzhou','W',0),(2689,532601,'文山市',2688,3,'wenshanshi','W',0),(2690,532622,'砚山县',2688,3,'yanshanxian','Y',0),(2691,532623,'西畴县',2688,3,'xichouxian','X',0),(2692,532624,'麻栗坡县',2688,3,'malipoxian','M',0),(2693,532625,'马关县',2688,3,'maguanxian','M',0),(2694,532626,'丘北县',2688,3,'qiubeixian','Q',0),(2695,532627,'广南县',2688,3,'guangnanxian','G',0),(2696,532628,'富宁县',2688,3,'funingxian','F',0),(2697,532800,'西双版纳州',2583,2,'xishuangbannazhou','X',0),(2698,532801,'景洪市',2697,3,'jinghongshi','J',0),(2699,532822,'勐海县',2697,3,'menghaixian','M',0),(2700,532823,'勐腊县',2697,3,'menglaxian','M',0),(2701,532900,'大理州',2583,2,'dalizhou','D',0),(2702,532901,'大理市',2701,3,'dalishi','D',0),(2703,532922,'漾濞县',2701,3,'yangbixian','Y',0),(2704,532923,'祥云县',2701,3,'xiangyunxian','X',0),(2705,532924,'宾川县',2701,3,'binchuanxian','B',0),(2706,532925,'弥渡县',2701,3,'miduxian','M',0),(2707,532926,'南涧县',2701,3,'nanjianxian','N',0),(2708,532927,'巍山县',2701,3,'weishanxian','W',0),(2709,532928,'永平县',2701,3,'yongpingxian','Y',0),(2710,532929,'云龙县',2701,3,'yunlongxian','Y',0),(2711,532930,'洱源县',2701,3,'eryuanxian','E',0),(2712,532931,'剑川县',2701,3,'jianchuanxian','J',0),(2713,532932,'鹤庆县',2701,3,'heqingxian','H',0),(2714,533100,'德宏州',2583,2,'dehongzhou','D',0),(2715,533102,'瑞丽市',2714,3,'ruilishi','R',0),(2716,533103,'芒市',2714,3,'mangshi','M',0),(2717,533122,'梁河县',2714,3,'lianghexian','L',0),(2718,533123,'盈江县',2714,3,'yingjiangxian','Y',0),(2719,533124,'陇川县',2714,3,'longchuanxian','L',0),(2720,533300,'怒江州',2583,2,'nujiangzhou','N',0),(2721,533321,'泸水县',2720,3,'lushuixian','L',0),(2722,533323,'福贡县',2720,3,'fugongxian','F',0),(2723,533324,'贡山县',2720,3,'gongshanxian','G',0),(2724,533325,'兰坪县',2720,3,'lanpingxian','L',0),(2725,533400,'迪庆州',2583,2,'diqingzhou','D',0),(2726,533421,'香格里拉县',2725,3,'xianggelilaxian','X',0),(2727,533422,'德钦县',2725,3,'deqinxian','D',0),(2728,533423,'维西县',2725,3,'weixixian','W',0),(2729,540000,'西藏',0,1,'xizang','X',0),(2730,540100,'拉萨市',2729,2,'lasashi','L',0),(2731,540102,'城关区',2730,3,'chengguanqu','C',0),(2732,540121,'林周县',2730,3,'linzhouxian','L',0),(2733,540122,'当雄县',2730,3,'dangxiongxian','D',0),(2734,540123,'尼木县',2730,3,'nimuxian','N',0),(2735,540124,'曲水县',2730,3,'qushuixian','Q',0),(2736,540125,'堆龙德庆县',2730,3,'duilongdeqingxian','D',0),(2737,540126,'达孜县',2730,3,'dazixian','D',0),(2738,540127,'墨竹工卡县',2730,3,'mozhugongqiaxian','M',0),(2739,542100,'昌都地区',2729,2,'changdudiqu','C',0),(2740,542121,'昌都县',2739,3,'changdouxian','C',0),(2741,542122,'江达县',2739,3,'jiangdaxian','J',0),(2742,542123,'贡觉县',2739,3,'gongjuexian','G',0),(2743,542124,'类乌齐县',2739,3,'leiwuqixian','L',0),(2744,542125,'丁青县',2739,3,'dingqingxian','D',0),(2745,542126,'察雅县',2739,3,'chayaxian','C',0),(2746,542127,'八宿县',2739,3,'basuxian','B',0),(2747,542128,'左贡县',2739,3,'zuogongxian','Z',0),(2748,542129,'芒康县',2739,3,'mangkangxian','M',0),(2749,542132,'洛隆县',2739,3,'luolongxian','L',0),(2750,542133,'边坝县',2739,3,'bianbaxian','B',0),(2751,542200,'山南地区',2729,2,'shannandiqu','S',0),(2752,542221,'乃东县',2751,3,'naidongxian','N',0),(2753,542222,'扎囊县',2751,3,'zanangxian','Z',0),(2754,542223,'贡嘎县',2751,3,'gonggaxian','G',0),(2755,542224,'桑日县',2751,3,'sangrixian','S',0),(2756,542225,'琼结县',2751,3,'qiongjiexian','Q',0),(2757,542226,'曲松县',2751,3,'qusongxian','Q',0),(2758,542227,'措美县',2751,3,'cuomeixian','C',0),(2759,542228,'洛扎县',2751,3,'luozaxian','L',0),(2760,542229,'加查县',2751,3,'jiachaxian','J',0),(2761,542231,'隆子县',2751,3,'longzixian','L',0),(2762,542232,'错那县',2751,3,'cuonaxian','C',0),(2763,542233,'浪卡子县',2751,3,'langqiazixian','L',0),(2764,542300,'日喀则地区',2729,2,'rikazediqu','R',0),(2765,542301,'日喀则市',2764,3,'rikazeshi','R',0),(2766,542322,'南木林县',2764,3,'nanmulinxian','N',0),(2767,542323,'江孜县',2764,3,'jiangzixian','J',0),(2768,542324,'定日县',2764,3,'dingrixian','D',0),(2769,542325,'萨迦县',2764,3,'sajiaxian','S',0),(2770,542326,'拉孜县',2764,3,'lazixian','L',0),(2771,542327,'昂仁县',2764,3,'angrenxian','A',0),(2772,542328,'谢通门县',2764,3,'xietongmenxian','X',0),(2773,542329,'白朗县',2764,3,'bailangxian','B',0),(2774,542330,'仁布县',2764,3,'renbuxian','R',0),(2775,542331,'康马县',2764,3,'kangmaxian','K',0),(2776,542332,'定结县',2764,3,'dingjiexian','D',0),(2777,542333,'仲巴县',2764,3,'zhongbaxian','Z',0),(2778,542334,'亚东县',2764,3,'yadongxian','Y',0),(2779,542335,'吉隆县',2764,3,'jilongxian','J',0),(2780,542336,'聂拉木县',2764,3,'nielamuxian','N',0),(2781,542337,'萨嘎县',2764,3,'sagaxian','S',0),(2782,542338,'岗巴县',2764,3,'gangbaxian','G',0),(2783,542400,'那曲地区',2729,2,'naqudiqu','N',0),(2784,542421,'那曲县',2783,3,'naquxian','N',0),(2785,542422,'嘉黎县',2783,3,'jialixian','J',0),(2786,542423,'比如县',2783,3,'biruxian','B',0),(2787,542424,'聂荣县',2783,3,'nierongxian','N',0),(2788,542425,'安多县',2783,3,'anduoxian','A',0),(2789,542426,'申扎县',2783,3,'shenzaxian','S',0),(2790,542427,'索县',2783,3,'suoxian','S',0),(2791,542428,'班戈县',2783,3,'bangexian','B',0),(2792,542429,'巴青县',2783,3,'baqingxian','B',0),(2793,542430,'尼玛县',2783,3,'nimaxian','N',0),(2794,542431,'双湖县',2783,3,'shuanghuxian','S',0),(2795,542500,'阿里地区',2729,2,'alidiqu','A',0),(2796,542521,'普兰县',2795,3,'pulanxian','P',0),(2797,542522,'札达县',2795,3,'zhadaxian','Z',0),(2798,542523,'噶尔县',2795,3,'gaerxian','G',0),(2799,542524,'日土县',2795,3,'rituxian','R',0),(2800,542525,'革吉县',2795,3,'gejixian','G',0),(2801,542526,'改则县',2795,3,'gaizexian','G',0),(2802,542527,'措勤县',2795,3,'cuoqinxian','C',0),(2803,542600,'林芝地区',2729,2,'linzhidiqu','L',0),(2804,542621,'林芝县',2803,3,'linzhixian','L',0),(2805,542622,'工布江达县',2803,3,'gongbujiangdaxian','G',0),(2806,542623,'米林县',2803,3,'milinxian','M',0),(2807,542624,'墨脱县',2803,3,'motuoxian','M',0),(2808,542625,'波密县',2803,3,'bomixian','B',0),(2809,542626,'察隅县',2803,3,'chayuxian','C',0),(2810,542627,'朗县',2803,3,'langxian','L',0),(2811,610000,'陕西',0,1,'shanxi','S',0),(2812,610100,'西安市',2811,2,'xianshi','X',0),(2813,610102,'新城区',2812,3,'xinchengqu','X',0),(2814,610103,'碑林区',2812,3,'beilinqu','B',0),(2815,610104,'莲湖区',2812,3,'lianhuqu','L',0),(2816,610111,'灞桥区',2812,3,'baqiaoqu','B',0),(2817,610112,'未央区',2812,3,'weiyangqu','W',0),(2818,610113,'雁塔区',2812,3,'yantaqu','Y',0),(2819,610114,'阎良区',2812,3,'yanliangqu','Y',0),(2820,610115,'临潼区',2812,3,'lintongqu','L',0),(2821,610116,'长安区',2812,3,'changanqu','C',0),(2822,610122,'蓝田县',2812,3,'lantianxian','L',0),(2823,610124,'周至县',2812,3,'zhouzhixian','Z',0),(2824,610125,'户县',2812,3,'huxian','H',0),(2825,610126,'高陵县',2812,3,'gaolingxian','G',0),(2826,610200,'铜川市',2811,2,'tongchuanshi','T',0),(2827,610202,'王益区',2826,3,'wangyiqu','W',0),(2828,610203,'印台区',2826,3,'yintaiqu','Y',0),(2829,610204,'耀州区',2826,3,'yaozhouqu','Y',0),(2830,610222,'宜君县',2826,3,'yijunxian','Y',0),(2831,610300,'宝鸡市',2811,2,'baojishi','B',0),(2832,610302,'渭滨区',2831,3,'weibinqu','W',0),(2833,610303,'金台区',2831,3,'jintaiqu','J',0),(2834,610304,'陈仓区',2831,3,'chencangqu','C',0),(2835,610322,'凤翔县',2831,3,'fengxiangxian','F',0),(2836,610323,'岐山县',2831,3,'qishanxian','Q',0),(2837,610324,'扶风县',2831,3,'fufengxian','F',0),(2838,610326,'眉县',2831,3,'meixian','M',0),(2839,610327,'陇县',2831,3,'longxian','L',0),(2840,610328,'千阳县',2831,3,'qianyangxian','Q',0),(2841,610329,'麟游县',2831,3,'linyouxian','L',0),(2842,610330,'凤县',2831,3,'fengxian','F',0),(2843,610331,'太白县',2831,3,'taibaixian','T',0),(2844,610400,'咸阳市',2811,2,'xianyangshi','X',0),(2845,610402,'秦都区',2844,3,'qinduqu','Q',0),(2846,610403,'杨陵区',2844,3,'yanglingqu','Y',0),(2847,610404,'渭城区',2844,3,'weichengqu','W',0),(2848,610422,'三原县',2844,3,'sanyuanxian','S',0),(2849,610423,'泾阳县',2844,3,'jingyangxian','J',0),(2850,610424,'乾县',2844,3,'qianxian','Q',0),(2851,610425,'礼泉县',2844,3,'liquanxian','L',0),(2852,610426,'永寿县',2844,3,'yongshouxian','Y',0),(2853,610427,'彬县',2844,3,'binxian','B',0),(2854,610428,'长武县',2844,3,'changwuxian','C',0),(2855,610429,'旬邑县',2844,3,'xunyixian','X',0),(2856,610430,'淳化县',2844,3,'chunhuaxian','C',0),(2857,610431,'武功县',2844,3,'wugongxian','W',0),(2858,610481,'兴平市',2844,3,'xingpingshi','X',0),(2859,610500,'渭南市',2811,2,'weinanshi','W',0),(2860,610502,'临渭区',2859,3,'linweiqu','L',0),(2861,610521,'华县',2859,3,'huaxian','H',0),(2862,610522,'潼关县',2859,3,'tongguanxian','T',0),(2863,610523,'大荔县',2859,3,'dalixian','D',0),(2864,610524,'合阳县',2859,3,'heyangxian','H',0),(2865,610525,'澄城县',2859,3,'chengchengxian','C',0),(2866,610526,'蒲城县',2859,3,'puchengxian','P',0),(2867,610527,'白水县',2859,3,'baishuixian','B',0),(2868,610528,'富平县',2859,3,'fupingxian','F',0),(2869,610581,'韩城市',2859,3,'hanchengshi','H',0),(2870,610582,'华阴市',2859,3,'huayinshi','H',0),(2871,610600,'延安市',2811,2,'yananshi','Y',0),(2872,610602,'宝塔区',2871,3,'baotaqu','B',0),(2873,610621,'延长县',2871,3,'yanchangxian','Y',0),(2874,610622,'延川县',2871,3,'yanchuanxian','Y',0),(2875,610623,'子长县',2871,3,'zichangxian','Z',0),(2876,610624,'安塞县',2871,3,'ansaixian','A',0),(2877,610625,'志丹县',2871,3,'zhidanxian','Z',0),(2878,610626,'吴起县',2871,3,'wuqixian','W',0),(2879,610627,'甘泉县',2871,3,'ganquanxian','G',0),(2880,610628,'富县',2871,3,'fuxian','F',0),(2881,610629,'洛川县',2871,3,'luochuanxian','L',0),(2882,610630,'宜川县',2871,3,'yichuanxian','Y',0),(2883,610631,'黄龙县',2871,3,'huanglongxian','H',0),(2884,610632,'黄陵县',2871,3,'huanglingxian','H',0),(2885,610700,'汉中市',2811,2,'hanzhongshi','H',0),(2886,610702,'汉台区',2885,3,'hantaiqu','H',0),(2887,610721,'南郑县',2885,3,'nanzhengxian','N',0),(2888,610722,'城固县',2885,3,'chengguxian','C',0),(2889,610723,'洋县',2885,3,'yangxian','Y',0),(2890,610724,'西乡县',2885,3,'xixiangxian','X',0),(2891,610725,'勉县',2885,3,'mianxian','M',0),(2892,610726,'宁强县',2885,3,'ningqiangxian','N',0),(2893,610727,'略阳县',2885,3,'lveyangxian','L',0),(2894,610728,'镇巴县',2885,3,'zhenbaxian','Z',0),(2895,610729,'留坝县',2885,3,'liubaxian','L',0),(2896,610730,'佛坪县',2885,3,'fopingxian','F',0),(2897,610800,'榆林市',2811,2,'yulinshi','Y',0),(2898,610802,'榆阳区',2897,3,'yuyangqu','Y',0),(2899,610821,'神木县',2897,3,'shenmuxian','S',0),(2900,610822,'府谷县',2897,3,'fuguxian','F',0),(2901,610823,'横山县',2897,3,'hengshanxian','H',0),(2902,610824,'靖边县',2897,3,'jingbianxian','J',0),(2903,610825,'定边县',2897,3,'dingbianxian','D',0),(2904,610826,'绥德县',2897,3,'suidexian','S',0),(2905,610827,'米脂县',2897,3,'mizhixian','M',0),(2906,610828,'佳县',2897,3,'jiaxian','J',0),(2907,610829,'吴堡县',2897,3,'wubaoxian','W',0),(2908,610830,'清涧县',2897,3,'qingjianxian','Q',0),(2909,610831,'子洲县',2897,3,'zizhouxian','Z',0),(2910,610900,'安康市',2811,2,'ankangshi','A',0),(2911,610902,'汉滨区',2910,3,'hanbinqu','H',0),(2912,610921,'汉阴县',2910,3,'hanyinxian','H',0),(2913,610922,'石泉县',2910,3,'shiquanxian','S',0),(2914,610923,'宁陕县',2910,3,'ningshanxian','N',0),(2915,610924,'紫阳县',2910,3,'ziyangxian','Z',0),(2916,610925,'岚皋县',2910,3,'langaoxian','L',0),(2917,610926,'平利县',2910,3,'pinglixian','P',0),(2918,610927,'镇坪县',2910,3,'zhenpingxian','Z',0),(2919,610928,'旬阳县',2910,3,'xunyangxian','X',0),(2920,610929,'白河县',2910,3,'baihexian','B',0),(2921,611000,'商洛市',2811,2,'shangluoshi','S',0),(2922,611002,'商州区',2921,3,'shangzhouqu','S',0),(2923,611021,'洛南县',2921,3,'luonanxian','L',0),(2924,611022,'丹凤县',2921,3,'danfengxian','D',0),(2925,611023,'商南县',2921,3,'shangnanxian','S',0),(2926,611024,'山阳县',2921,3,'shanyangxian','S',0),(2927,611025,'镇安县',2921,3,'zhenanxian','Z',0),(2928,611026,'柞水县',2921,3,'zuoshuixian','Z',0),(2929,620000,'甘肃',0,1,'gansu','G',0),(2930,620100,'兰州市',2929,2,'lanzhoushi','L',0),(2931,620102,'城关区',2930,3,'chengguanqu','C',0),(2932,620103,'七里河区',2930,3,'qilihequ','Q',0),(2933,620104,'西固区',2930,3,'xiguqu','X',0),(2934,620105,'安宁区',2930,3,'anningqu','A',0),(2935,620111,'红古区',2930,3,'hongguqu','H',0),(2936,620121,'永登县',2930,3,'yongdengxian','Y',0),(2937,620122,'皋兰县',2930,3,'gaolanxian','G',0),(2938,620123,'榆中县',2930,3,'yuzhongxian','Y',0),(2939,620200,'嘉峪关市',2929,2,'jiayuguanshi','J',0),(2940,620300,'金昌市',2929,2,'jinchangshi','J',0),(2941,620302,'金川区',2940,3,'jinchuanqu','J',0),(2942,620321,'永昌县',2940,3,'yongchangxian','Y',0),(2943,620400,'白银市',2929,2,'baiyinshi','B',0),(2944,620402,'白银区',2943,3,'baiyinqu','B',0),(2945,620403,'平川区',2943,3,'pingchuanqu','P',0),(2946,620421,'靖远县',2943,3,'jingyuanxian','J',0),(2947,620422,'会宁县',2943,3,'huiningxian','H',0),(2948,620423,'景泰县',2943,3,'jingtaixian','J',0),(2949,620500,'天水市',2929,2,'tianshuishi','T',0),(2950,620502,'秦州区',2949,3,'qinzhouqu','Q',0),(2951,620503,'麦积区',2949,3,'maijiqu','M',0),(2952,620521,'清水县',2949,3,'qingshuixian','Q',0),(2953,620522,'秦安县',2949,3,'qinanxian','Q',0),(2954,620523,'甘谷县',2949,3,'ganguxian','G',0),(2955,620524,'武山县',2949,3,'wushanxian','W',0),(2956,620525,'张家川县',2949,3,'zhangjiachuanxian','Z',0),(2957,620600,'武威市',2929,2,'wuweishi','W',0),(2958,620602,'凉州区',2957,3,'liangzhouqu','L',0),(2959,620621,'民勤县',2957,3,'minqinxian','M',0),(2960,620622,'古浪县',2957,3,'gulangxian','G',0),(2961,620623,'天祝县',2957,3,'tianzhuxian','T',0),(2962,620700,'张掖市',2929,2,'zhangyeshi','Z',0),(2963,620702,'甘州区',2962,3,'ganzhouqu','G',0),(2964,620721,'肃南县',2962,3,'sunanxian','S',0),(2965,620722,'民乐县',2962,3,'minlexian','M',0),(2966,620723,'临泽县',2962,3,'linzexian','L',0),(2967,620724,'高台县',2962,3,'gaotaixian','G',0),(2968,620725,'山丹县',2962,3,'shandanxian','S',0),(2969,620800,'平凉市',2929,2,'pingliangshi','P',0),(2970,620802,'崆峒区',2969,3,'kongtongqu','K',0),(2971,620821,'泾川县',2969,3,'jingchuanxian','J',0),(2972,620822,'灵台县',2969,3,'lingtaixian','L',0),(2973,620823,'崇信县',2969,3,'chongxinxian','C',0),(2974,620824,'华亭县',2969,3,'huatingxian','H',0),(2975,620825,'庄浪县',2969,3,'zhuanglangxian','Z',0),(2976,620826,'静宁县',2969,3,'jingningxian','J',0),(2977,620900,'酒泉市',2929,2,'jiuquanshi','J',0),(2978,620902,'肃州区',2977,3,'suzhouqu','S',0),(2979,620921,'金塔县',2977,3,'jintaxian','J',0),(2980,620922,'瓜州县',2977,3,'guazhouxian','G',0),(2981,620923,'肃北县',2977,3,'subeixian','S',0),(2982,620924,'阿克塞县',2977,3,'akesaixian','A',0),(2983,620981,'玉门市',2977,3,'yumenshi','Y',0),(2984,620982,'敦煌市',2977,3,'dunhuangshi','D',0),(2985,621000,'庆阳市',2929,2,'qingyangshi','Q',0),(2986,621002,'西峰区',2985,3,'xifengqu','X',0),(2987,621021,'庆城县',2985,3,'qingchengxian','Q',0),(2988,621022,'环县',2985,3,'huanxian','H',0),(2989,621023,'华池县',2985,3,'huachixian','H',0),(2990,621024,'合水县',2985,3,'heshuixian','H',0),(2991,621025,'正宁县',2985,3,'zhengningxian','Z',0),(2992,621026,'宁县',2985,3,'ningxian','N',0),(2993,621027,'镇原县',2985,3,'zhenyuanxian','Z',0),(2994,621100,'定西市',2929,2,'dingxishi','D',0),(2995,621102,'安定区',2994,3,'andingqu','A',0),(2996,621121,'通渭县',2994,3,'tongweixian','T',0),(2997,621122,'陇西县',2994,3,'longxixian','L',0),(2998,621123,'渭源县',2994,3,'weiyuanxian','W',0),(2999,621124,'临洮县',2994,3,'lintaoxian','L',0),(3000,621125,'漳县',2994,3,'zhangxian','Z',0),(3001,621126,'岷县',2994,3,'minxian','M',0),(3002,621200,'陇南市',2929,2,'longnanshi','L',0),(3003,621202,'武都区',3002,3,'wuduqu','W',0),(3004,621221,'成县',3002,3,'chengxian','C',0),(3005,621222,'文县',3002,3,'wenxian','W',0),(3006,621223,'宕昌县',3002,3,'dangchangxian','D',0),(3007,621224,'康县',3002,3,'kangxian','K',0),(3008,621225,'西和县',3002,3,'xihexian','X',0),(3009,621226,'礼县',3002,3,'lixian','L',0),(3010,621227,'徽县',3002,3,'huixian','H',0),(3011,621228,'两当县',3002,3,'liangdangxian','L',0),(3012,622900,'临夏州',2929,2,'linxiazhou','L',0),(3013,622901,'临夏市',3012,3,'linxiashi','L',0),(3014,622921,'临夏县',3012,3,'linxiaxian','L',0),(3015,622922,'康乐县',3012,3,'kanglexian','K',0),(3016,622923,'永靖县',3012,3,'yongjingxian','Y',0),(3017,622924,'广河县',3012,3,'guanghexian','G',0),(3018,622925,'和政县',3012,3,'hezhengxian','H',0),(3019,622926,'县',3012,3,'xian','X',0),(3020,622927,'积石山县',3012,3,'jishishanxian','J',0),(3021,623000,'甘南州',2929,2,'gannanzhou','G',0),(3022,623001,'合作市',3021,3,'hezuoshi','H',0),(3023,623021,'临潭县',3021,3,'lintanxian','L',0),(3024,623022,'卓尼县',3021,3,'zhuonixian','Z',0),(3025,623023,'舟曲县',3021,3,'zhouquxian','Z',0),(3026,623024,'迭部县',3021,3,'diebuxian','D',0),(3027,623025,'玛曲县',3021,3,'maquxian','M',0),(3028,623026,'碌曲县',3021,3,'luquxian','L',0),(3029,623027,'夏河县',3021,3,'xiahexian','X',0),(3030,630000,'青海',0,1,'qinghai','Q',0),(3031,630100,'西宁市',3030,2,'xiningshi','X',0),(3032,630102,'城东区',3031,3,'chengdongqu','C',0),(3033,630103,'城中区',3031,3,'chengzhongqu','C',0),(3034,630104,'城西区',3031,3,'chengxiqu','C',0),(3035,630105,'城北区',3031,3,'chengbeiqu','C',0),(3036,630121,'大通县',3031,3,'datongxian','D',0),(3037,630122,'湟中县',3031,3,'huangzhongxian','H',0),(3038,630123,'湟源县',3031,3,'huangyuanxian','H',0),(3039,630200,'海东市',3030,2,'haidongshi','H',0),(3040,630202,'乐都区',3039,3,'leduqu','L',0),(3041,630221,'平安县',3039,3,'pinganxian','P',0),(3042,630222,'民和县',3039,3,'minhexian','M',0),(3043,630223,'互助县',3039,3,'huzhuxian','H',0),(3044,630224,'化隆县',3039,3,'hualongxian','H',0),(3045,630225,'循化县',3039,3,'xunhuaxian','X',0),(3046,632200,'海北州',3030,2,'haibeizhou','H',0),(3047,632221,'门源县',3046,3,'menyuanxian','M',0),(3048,632222,'祁连县',3046,3,'qilianxian','Q',0),(3049,632223,'海晏县',3046,3,'haiyanxian','H',0),(3050,632224,'刚察县',3046,3,'gangchaxian','G',0),(3051,632300,'黄南州',3030,2,'huangnanzhou','H',0),(3052,632321,'同仁县',3051,3,'tongrenxian','T',0),(3053,632322,'尖扎县',3051,3,'jianzaxian','J',0),(3054,632323,'泽库县',3051,3,'zekuxian','Z',0),(3055,632324,'河南县',3051,3,'henanxian','H',0),(3056,632500,'海南州',3030,2,'hainanzhou','H',0),(3057,632521,'共和县',3056,3,'gonghexian','G',0),(3058,632522,'同德县',3056,3,'tongdexian','T',0),(3059,632523,'贵德县',3056,3,'guidexian','G',0),(3060,632524,'兴海县',3056,3,'xinghaixian','X',0),(3061,632525,'贵南县',3056,3,'guinanxian','G',0),(3062,632600,'果洛州',3030,2,'guoluozhou','G',0),(3063,632621,'玛沁县',3062,3,'maqinxian','M',0),(3064,632622,'班玛县',3062,3,'banmaxian','B',0),(3065,632623,'甘德县',3062,3,'gandexian','G',0),(3066,632624,'达日县',3062,3,'darixian','D',0),(3067,632625,'久治县',3062,3,'jiuzhixian','J',0),(3068,632626,'玛多县',3062,3,'maduoxian','M',0),(3069,632700,'玉树州',3030,2,'yushuzhou','Y',0),(3070,632701,'玉树市',3069,3,'yushushi','Y',0),(3071,632722,'杂多县',3069,3,'zaduoxian','Z',0),(3072,632723,'称多县',3069,3,'chengduoxian','C',0),(3073,632724,'治多县',3069,3,'zhiduoxian','Z',0),(3074,632725,'囊谦县',3069,3,'nangqianxian','N',0),(3075,632726,'曲麻莱县',3069,3,'qumalaixian','Q',0),(3076,632800,'海西州',3030,2,'haixizhou','H',0),(3077,632801,'格尔木市',3076,3,'geermushi','G',0),(3078,632802,'德令哈市',3076,3,'delinghashi','D',0),(3079,632821,'乌兰县',3076,3,'wulanxian','W',0),(3080,632822,'都兰县',3076,3,'dulanxian','D',0),(3081,632823,'天峻县',3076,3,'tianjunxian','T',0),(3082,640000,'宁夏',0,1,'ningxia','N',0),(3083,640100,'银川市',3082,2,'yinchuanshi','Y',0),(3084,640104,'兴庆区',3083,3,'xingqingqu','X',0),(3085,640105,'西夏区',3083,3,'xixiaqu','X',0),(3086,640106,'金凤区',3083,3,'jinfengqu','J',0),(3087,640121,'永宁县',3083,3,'yongningxian','Y',0),(3088,640122,'贺兰县',3083,3,'helanxian','H',0),(3089,640181,'灵武市',3083,3,'lingwushi','L',0),(3090,640200,'石嘴山市',3082,2,'shizuishanshi','S',0),(3091,640202,'大武口区',3090,3,'dawukouqu','D',0),(3092,640205,'惠农区',3090,3,'huinongqu','H',0),(3093,640221,'平罗县',3090,3,'pingluoxian','P',0),(3094,640300,'吴忠市',3082,2,'wuzhongshi','W',0),(3095,640302,'利通区',3094,3,'litongqu','L',0),(3096,640303,'红寺堡区',3094,3,'hongsibaoqu','H',0),(3097,640323,'盐池县',3094,3,'yanchixian','Y',0),(3098,640324,'同心县',3094,3,'tongxinxian','T',0),(3099,640381,'青铜峡市',3094,3,'qingtongxiashi','Q',0),(3100,640400,'固原市',3082,2,'guyuanshi','G',0),(3101,640402,'原州区',3100,3,'yuanzhouqu','Y',0),(3102,640422,'西吉县',3100,3,'xijixian','X',0),(3103,640423,'隆德县',3100,3,'longdexian','L',0),(3104,640424,'泾源县',3100,3,'jingyuanxian','J',0),(3105,640425,'彭阳县',3100,3,'pengyangxian','P',0),(3106,640500,'中卫市',3082,2,'zhongweishi','Z',0),(3107,640502,'沙坡头区',3106,3,'shapotouqu','S',0),(3108,640521,'中宁县',3106,3,'zhongningxian','Z',0),(3109,640522,'海原县',3106,3,'haiyuanxian','H',0),(3110,650000,'新疆',0,1,'xinjiang','X',0),(3111,650100,'乌鲁木齐市',3110,2,'wulumuqishi','W',0),(3112,650102,'天山区',3111,3,'tianshanqu','T',0),(3113,650103,'沙依巴克区',3111,3,'shayibakequ','S',0),(3114,650104,'新市区',3111,3,'xinshiqu','X',0),(3115,650105,'水磨沟区',3111,3,'shuimogouqu','S',0),(3116,650106,'头屯河区',3111,3,'toutunhequ','T',0),(3117,650107,'达坂城区',3111,3,'dabanchengqu','D',0),(3118,650109,'米东区',3111,3,'midongqu','M',0),(3119,650121,'乌鲁木齐县',3111,3,'wulumuqixian','W',0),(3120,650200,'克拉玛依市',3110,2,'kelamayishi','K',0),(3121,650202,'独山子区',3120,3,'dushanziqu','D',0),(3122,650203,'克拉玛依区',3120,3,'kelamayiqu','K',0),(3123,650204,'白碱滩区',3120,3,'baijiantanqu','B',0),(3124,650205,'乌尔禾区',3120,3,'wuerhequ','W',0),(3125,652100,'吐鲁番地区',3110,2,'tulufandiqu','T',0),(3126,652101,'吐鲁番市',3125,3,'tulufanshi','T',0),(3127,652122,'鄯善县',3125,3,'shanshanxian','S',0),(3128,652123,'托克逊县',3125,3,'tuokexunxian','T',0),(3129,652200,'哈密地区',3110,2,'hamidiqu','H',0),(3130,652201,'哈密市',3129,3,'hamishi','H',0),(3131,652222,'巴里坤哈萨克县',3129,3,'balikunhasakexian','B',0),(3132,652223,'伊吾县',3129,3,'yiwuxian','Y',0),(3133,652300,'昌吉州',3110,2,'changjizhou','C',0),(3134,652301,'昌吉市',3133,3,'changjishi','C',0),(3135,652302,'阜康市',3133,3,'fukangshi','F',0),(3136,652323,'呼图壁县',3133,3,'hutubixian','H',0),(3137,652324,'玛纳斯县',3133,3,'manasixian','M',0),(3138,652325,'奇台县',3133,3,'qitaixian','Q',0),(3139,652327,'吉木萨尔县',3133,3,'jimusaerxian','J',0),(3140,652328,'木垒哈萨克县',3133,3,'muleihasakexian','M',0),(3141,652700,'博尔塔拉州',3110,2,'boertalazhou','B',0),(3142,652701,'博乐市',3141,3,'boleshi','B',0),(3143,652702,'阿拉山口市',3141,3,'alashankoushi','A',0),(3144,652722,'精河县',3141,3,'jinghexian','J',0),(3145,652723,'温泉县',3141,3,'wenquanxian','W',0),(3146,652800,'巴音郭楞州',3110,2,'bayinguolengzhou','B',0),(3147,652801,'库尔勒市',3146,3,'kuerleshi','K',0),(3148,652822,'轮台县',3146,3,'luntaixian','L',0),(3149,652823,'尉犁县',3146,3,'weilixian','W',0),(3150,652824,'若羌县',3146,3,'ruoqiangxian','R',0),(3151,652825,'且末县',3146,3,'qiemoxian','Q',0),(3152,652826,'焉耆县',3146,3,'yanqixian','Y',0),(3153,652827,'和静县',3146,3,'hejingxian','H',0),(3154,652828,'和硕县',3146,3,'heshuoxian','H',0),(3155,652829,'博湖县',3146,3,'bohuxian','B',0),(3156,652900,'阿克苏地区',3110,2,'akesudiqu','A',0),(3157,652901,'阿克苏市',3156,3,'akesushi','A',0),(3158,652922,'温宿县',3156,3,'wensuxian','W',0),(3159,652923,'库车县',3156,3,'kuchexian','K',0),(3160,652924,'沙雅县',3156,3,'shayaxian','S',0),(3161,652925,'新和县',3156,3,'xinhexian','X',0),(3162,652926,'拜城县',3156,3,'baichengxian','B',0),(3163,652927,'乌什县',3156,3,'wushixian','W',0),(3164,652928,'阿瓦提县',3156,3,'awatixian','A',0),(3165,652929,'柯坪县',3156,3,'kepingxian','K',0),(3166,653000,'克孜勒苏州',3110,2,'kezilesuzhou','K',0),(3167,653001,'阿图什市',3166,3,'atushishi','A',0),(3168,653022,'阿克陶县',3166,3,'aketaoxian','A',0),(3169,653023,'阿合奇县',3166,3,'aheqixian','A',0),(3170,653024,'乌恰县',3166,3,'wuqiaxian','W',0),(3171,653100,'喀什地区',3110,2,'kashidiqu','K',0),(3172,653101,'喀什市',3171,3,'kashishi','K',0),(3173,653121,'疏附县',3171,3,'shufuxian','S',0),(3174,653122,'疏勒县',3171,3,'shulexian','S',0),(3175,653123,'英吉沙县',3171,3,'yingjishaxian','Y',0),(3176,653124,'泽普县',3171,3,'zepuxian','Z',0),(3177,653125,'莎车县',3171,3,'suochexian','S',0),(3178,653126,'叶城县',3171,3,'yechengxian','Y',0),(3179,653127,'麦盖提县',3171,3,'maigaitixian','M',0),(3180,653128,'岳普湖县',3171,3,'yuepuhuxian','Y',0),(3181,653129,'伽师县',3171,3,'qieshixian','Q',0),(3182,653130,'巴楚县',3171,3,'bachuxian','B',0),(3183,653131,'塔什库尔干县',3171,3,'tashikuerganxian','T',0),(3184,653200,'和田地区',3110,2,'hetiandiqu','H',0),(3185,653201,'和田市',3184,3,'hetianshi','H',0),(3186,653221,'和田县',3184,3,'hetianxian','H',0),(3187,653222,'墨玉县',3184,3,'moyuxian','M',0),(3188,653223,'皮山县',3184,3,'pishanxian','P',0),(3189,653224,'洛浦县',3184,3,'luopuxian','L',0),(3190,653225,'策勒县',3184,3,'celexian','C',0),(3191,653226,'于田县',3184,3,'yutianxian','Y',0),(3192,653227,'民丰县',3184,3,'minfengxian','M',0),(3193,654000,'伊犁哈萨克州',3110,2,'yilihasakezhou','Y',0),(3194,654002,'伊宁市',3193,3,'yiningshi','Y',0),(3195,654003,'奎屯市',3193,3,'kuitunshi','K',0),(3196,654021,'伊宁县',3193,3,'yiningxian','Y',0),(3197,654022,'察布查尔锡伯县',3193,3,'chabuchaerxiboxian','C',0),(3198,654023,'霍城县',3193,3,'huochengxian','H',0),(3199,654024,'巩留县',3193,3,'gongliuxian','G',0),(3200,654025,'新源县',3193,3,'xinyuanxian','X',0),(3201,654026,'昭苏县',3193,3,'zhaosuxian','Z',0),(3202,654027,'特克斯县',3193,3,'tekesixian','T',0),(3203,654028,'尼勒克县',3193,3,'nilekexian','N',0),(3204,654200,'塔城地区',3110,2,'tachengdiqu','T',0),(3205,654201,'塔城市',3204,3,'tachengshi','T',0),(3206,654202,'乌苏市',3204,3,'wusushi','W',0),(3207,654221,'额敏县',3204,3,'eminxian','E',0),(3208,654223,'沙湾县',3204,3,'shawanxian','S',0),(3209,654224,'托里县',3204,3,'tuolixian','T',0),(3210,654225,'裕民县',3204,3,'yuminxian','Y',0),(3211,654226,'和布克赛尔县',3204,3,'hebukesaierxian','H',0),(3212,654300,'阿勒泰地区',3110,2,'aletaidiqu','A',0),(3213,654301,'阿勒泰市',3212,3,'aletaishi','A',0),(3214,654321,'布尔津县',3212,3,'buerjinxian','B',0),(3215,654322,'富蕴县',3212,3,'fuyunxian','F',0),(3216,654323,'福海县',3212,3,'fuhaixian','F',0),(3217,654324,'哈巴河县',3212,3,'habahexian','H',0),(3218,654325,'青河县',3212,3,'qinghexian','Q',0),(3219,654326,'吉木乃县',3212,3,'jimunaixian','J',0),(3220,659001,'石河子市',3110,2,'shihezishi','S',0),(3221,659002,'阿拉尔市',3110,2,'alaershi','A',0),(3222,659003,'图木舒克市',3110,2,'tumushukeshi','T',0),(3223,659004,'五家渠市',3110,2,'wujiaqushi','W',0),(3224,710000,'台湾',0,1,'taiwan','T',0),(3225,810000,'香港',0,1,'xianggang','X',0),(3226,820000,'澳门',0,1,'aomen','A',0)):
            area = Area(id=area[0], cn_id=area[1], area=area[2], father_id=area[3], level=area[4], pinyin=area[5], pinyin_index=area[6], distributor_amount=area[7])
            db.session.add(area)
        db.session.commit()

    def area_address(self):
        areas = []
        area = self
        while area is not None:
            if area.area not in ['北京市', '上海市', '天津市', '重庆市']:
                areas.append(area.area)
            area = Area.query.get(area.father_id)
        areas.reverse()
        return ''.join(areas)

    def grade(self):
        grades = []
        area = self
        while area is not None:
            grades.append(area)
            area = Area.query.get(area.father_id)
        grades.reverse()
        return grades

    @property
    def father(self):
        return self.get_or_flush('father')

    def children(self):
        if self.level < 3:
            return Area.query.filter_by(father_id=self.id).all()
        return []

    def city(self):
        if self.level == 2:
            return self
        return self.father

    def experience_dict(self, distributor_id):
        if self.level == 3:
            third_area = self
            second_area = self.father
            first_area = second_area.father
        else:
            third_area = second_area = self
            first_area = second_area.father
        return {first_area.cn_id: {'area': first_area.area, 'children': {
            second_area.cn_id: {'area': second_area.area, 'children': {
                third_area.cn_id: {'area': third_area.area, 'distributors': [distributor_id]}
            }}
        }}}


class Address(Property):
    id = db.Column(db.Integer, primary_key=True)
    cn_id = db.Column(db.Integer, nullable=False)
    address = db.Column(db.Unicode(30), nullable=False)
    created = db.Column(db.Integer, default=time.time, nullable=False)
    longitude = db.Column(db.Float(precision=32), default=0, nullable=False)
    latitude = db.Column(db.Float(precision=32), default=0, nullable=False)
    # 百度地图poi id
    poi_id = db.Column(db.Integer, default=0, nullable=False)

    _flush = {
        'area': lambda x: Area.query.filter_by(cn_id=x.cn_id).limit(1).first()
    }
    _area = None

    @property
    def area(self):
        return self.get_or_flush('area')

    def vague_address(self):
        return self.area.area_address() if self.area else ''

    def precise_address(self):
        return '%s%s' % (self.vague_address(), self.address)


class UserAddress(Address, db.Model):
    __tablename__ = 'user_addresses'
    user_id = db.Column(db.Integer, nullable=False)
    mobile = db.Column(db.CHAR(11), unique=True, nullable=False)


class VendorAddress(Address, db.Model):
    __tablename__ = 'vendor_addresses'
    vendor_id = db.Column(db.Integer, nullable=False)

    def __init__(self, vendor_id, cn_id, address):
        self.vendor_id = vendor_id
        self.cn_id = cn_id
        self.address = address


class DistributorAddress(Address, db.Model):
    __tablename__ = 'distributor_addresses'
    distributor_id = db.Column(db.Integer, nullable=False, index=True)

    def __init__(self, distributor_id, cn_id, address):
        self.distributor_id = distributor_id
        self.cn_id = cn_id
        self.address = address

    @property
    def distributor(self):
        return Distributor.query.get(self.distributor_id)

    def update_distributor_amount(self):
        city = self.area.city()
        districts = city.children()
        cn_ids = [district.cn_id for district in districts]
        cn_ids.append(city.cn_id)
        city.distributor_amount = DistributorAddress.query.filter(DistributorAddress.cn_id.in_(cn_ids),
                                                                  Distributor.id == DistributorAddress.distributor_id,
                                                                  Distributor.is_revoked == False).count()
        db.session.commit()


class Stove(db.Model):
    __tablename__ = 'stoves'
    id = db.Column(db.Integer, primary_key=True)
    stove = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for stove in (u'水煮', u'蒸汽', u'煮蜡'):
            db.session.add(Stove(stove=stove))
        db.session.commit()


class Carve(db.Model):
    __tablename__ = 'carves'
    id = db.Column(db.Integer, primary_key=True)
    carve = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for carve in (u'通雕', u'透雕', u'浮雕', u'浅浮雕', u'镂空雕', u'圆雕(立体雕)', u'微雕', u'阴阳额雕', u'阴雕(阴刻)', u'无'):
            db.session.add(Carve(carve=carve))
        db.session.commit()


class CarveType(db.Model):
    __tablename__ = 'carve_types'
    id = db.Column(db.Integer, primary_key=True)
    carve_type = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for carve_type in ('手工雕', '机雕+手工雕', '机器雕刻', '其他', '无'):
            db.session.add(CarveType(carve_type=carve_type))
        db.session.commit()


class Sand(db.Model):
    __tablename__ = 'sands'
    id = db.Column(db.Integer, primary_key=True)
    sand = db.Column(db.Integer, nullable=False)

    @staticmethod
    def generate_fake():
        for sand in (180, 280, 320, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000):
            db.session.add(Sand(sand=sand))
        db.session.commit()


class Paint(db.Model):
    __tablename__ = 'paints'
    id = db.Column(db.Integer, primary_key=True)
    paint = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for paint in (u"生漆", u"烫蜡", u"无"):
            db.session.add(Paint(paint=paint))
        db.session.commit()


class Decoration(db.Model):
    __tablename__ = 'decorations'
    id = db.Column(db.Integer, primary_key=True)
    decoration = db.Column(db.Unicode(10), nullable=False)

    @staticmethod
    def generate_fake():
        for decoration in (u"白铜镶嵌", u"黄铜镶嵌", u"石料镶嵌", u"玻璃镶嵌", u"金丝楠木镶嵌", u"其他", u"无"):
            db.session.add(Decoration(decoration=decoration))
        db.session.commit()


class Tenon(db.Model):
    __tablename__ = 'tenons'
    id = db.Column(db.Integer, primary_key=True)
    tenon = db.Column(db.Unicode(20), nullable=False)

    @staticmethod
    def generate_fake():
        for tenon in (u'楔钉榫', u'夹头榫', u'抄手榫', u'走马销', u'霸王枨', u'柜子底枨', u'挖烟袋锅榫', u'云型插肩榫', u'扇形插肩榫', u'传统粽角榫', u'双榫粽角榫', u'带板粽角榫', u'插肩榫变形', u'高束腰抱肩榫', u'圆方结合裹腿', u'挂肩四面平榫', u'攒边打槽装板', u'三根直材交叉', u'方材丁字结合', u'直材交叉结合', u'圆柱丁字结合榫', u'圆香几攒边打槽', u'厚板闷榫角结合', u'平板明榫角结合', u'一腿三牙方桌结构', u'弧形直材十字交叉', u'弧形面直材角结合', u'圆柱二维直角交叉榫', u'方材角结合床围子攒接万字', u'厚板出透榫及榫舌拍抹头', u'方形家具腿足与方托泥的结合', u'椅盘边抹与椅子腿足的结构', u'方材丁字形结合榫卯用大格肩', u'加云子无束腰裹腿杌凳腿足与凳面结合'):
            db.session.add(Tenon(tenon=tenon))
        db.session.commit()


class ItemCarve(db.Model):
    __tablename__ = 'item_carves'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    carve_id = db.Column(db.Integer, nullable=False)


class ItemTenon(db.Model):
    __tablename__ = 'item_tenons'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, nullable=False)
    tenon_id = db.Column(db.Integer, nullable=False)


class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, default=0, nullable=False)
    feedback = db.Column(db.Unicode(200), nullable=False)
    contact = db.Column(db.Unicode(30), default='', nullable=False)


@login_manager.user_loader
def load_user(user_id):
    id_ = int(user_id[1:])
    if user_id.startswith(privilege_id_prefix):
        return Privilege.query.get(id_)
    elif user_id.startswith(vendor_id_prefix):
        return Vendor.query.get(id_)
    elif user_id.startswith(distributor_id_prefix):
        return Distributor.query.get(id_)
    return User.query.get(id_)


def generate_fake_data(num=100):
    Category.generate_fake()
    FirstMaterial.generate_fake()
    SecondMaterial.generate_fake()
    Stove.generate_fake()
    Carve.generate_fake()
    Sand.generate_fake()
    Paint.generate_fake()
    Decoration.generate_fake()
    Tenon.generate_fake()
    Scene.generate_fake()
    Style.generate_fake()
    Area.generate_fake()
    # Vendor.generate_fake()
    # Privilege.generate_fake()

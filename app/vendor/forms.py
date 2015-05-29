# -*- coding: utf-8 -*-
from PIL import Image
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SelectField, SelectMultipleField
from wtforms.validators import ValidationError, DataRequired, Length, EqualTo, NumberRange

from app import db
from app.models import Vendor, District, VendorAddress, Material, SecondCategory, Stove, Carve, Sand, Paint, \
    Decoration, Tenon, Item, ItemTenon
from app.utils import save_image, PY3
from app.utils.validator import Email, Mobile, QueryID

if PY3:
    from io import StringIO
else:
    from cStringIO import StringIO


class LoginForm(Form):
    mobile = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])


class RegistrationDetailForm(Form):
    email = StringField(validators=[Email()])
    password = PasswordField(validators=[DataRequired(), Length(6, 32), EqualTo('confirm_password')])
    confirm_password = PasswordField(validators=[DataRequired(), Length(6, 32)])
    legal_person_name = StringField(validators=[DataRequired(u'必填')])
    legal_person_identity = StringField(validators=[DataRequired(u'必填'), Length(18, 18, u'身份证号码不符合规范!')])
    legal_person_identity_front = FileField(validators=[
        FileRequired(u'必填'), FileAllowed(['jpg', 'png'], u'只支持jpg, png!')])
    legal_person_identity_back = FileField(validators=[
        FileRequired(u'必填'), FileAllowed(['jpg', 'png'], u'只支持jpg, png!')])
    name = StringField(validators=[DataRequired(u'必填'), Length(2, 30, u'品牌厂商名称不符合规范')])
    license_address = StringField(validators=[DataRequired(u'必填')])
    license_limit = StringField(validators=[Length(8, 8)])
    license_long_time_limit = BooleanField()
    license_image = FileField(validators=[FileRequired(u'必填'), FileAllowed(['jpg', 'png'], u'只支持jpg, png!')])
    contact_mobile = StringField(validators=[DataRequired(u'必填'), Mobile(available=False)])
    contact_telephone = StringField(validators=[DataRequired(u'必填'), Length(7, 15)])
    address = StringField(validators=[DataRequired(u'必填'), Length(1, 30)])
    address_id = StringField(validators=[DataRequired(), Length(6, 6)])

    # TODO: add address select

    def validate_license_limit(self, field):
        if not field.data and not self.license_long_time_limit.data:
            raise ValidationError(u'请填写营业执照期限或选择长期营业执照')

    def validate_legal_person_identity_front(self, field):
        try:
            im = Image.open(StringIO(field.data))
            im.verify()
        except:
            raise ValidationError(u'图片格式错误')

    def validate_legal_person_identity_back(self, field):
        try:
            im = Image.open(StringIO(field.data))
            im.verify()
        except:
            raise ValidationError(u'图片格式错误')

    def validate_license_image(self, field):
        try:
            im = Image.open(StringIO(field.data))
            im.verify()
        except:
            raise ValidationError(u'图片格式错误')

    def add_vendor(self, mobile):
        district = District.query.filter_by(cn_id=self.address_id)
        address = VendorAddress(vendor_id='', district_id=district.id, address=self.address.data)
        db.session.add(address)
        db.session.commit()
        vendor = Vendor(
            password=self.password.data,
            email=self.password.data,
            mobile=mobile,
            legal_person_name=self.legal_person_name.data,
            legal_person_identity=self.legal_person_identity.data,
            license_address=self.license_address.data,
            license_limit=self.license_limit.data,
            license_long_time_limit=self.license_long_time_limit.data,
            name=self.name.data,
            contact_mobile=self.contact_mobile.data,
            contact_telephone=self.contact_telephone.data,
            address_id=address.id
        )
        db.session.add(vendor)
        db.session.commit()
        identity_front = save_image(vendor.id, self.legal_person_identity_front)
        identity_back = save_image(vendor.id, self.legal_person_identity_back)
        license_image = save_image(vendor.id, self.license_image)
        vendor.legal_person_identity_front = identity_front
        vendor.legal_person_identity_back = identity_back
        vendor.license_image = license_image


class ItemForm(Form):
    item = StringField(validators=[DataRequired()])
    length = IntegerField(validators=[DataRequired(), NumberRange(1)])
    width = IntegerField(validators=[DataRequired(), NumberRange(1)])
    height = IntegerField(validators=[DataRequired(), NumberRange(1)])
    price = IntegerField(validators=[DataRequired(), NumberRange(1)])
    material_id = IntegerField(validators=[DataRequired(), QueryID(Material)])
    second_category_id = IntegerField(validators=[DataRequired(), QueryID(SecondCategory)])
    stove_id = SelectField(coerce=int, validators=[DataRequired(), QueryID(Stove)])
    carve_id = SelectField(coerce=int, validators=[DataRequired(), QueryID(Carve)])
    sand_id = SelectField(coerce=int, validators=[DataRequired(), QueryID(Sand)])
    paint_id = SelectField(coerce=int, validators=[DataRequired(), QueryID(Paint)])
    decoration_id = SelectField(coerce=int, validators=[DataRequired(), QueryID(Decoration)])
    tenon_id = SelectMultipleField(coerce=int, validators=[DataRequired(), QueryID(Tenon)])

    attributes = ('item', 'length', 'width', 'height', 'price', 'material_id', 'second_category_id', 'stove_id',
                  'carve_id', 'sand_id', 'decoration_id')

    def generate_choices(self):
        self.stove_id.choices = [(choice.id, choice.stove) for choice in Stove.query.all()]
        self.carve_id.choices = [(choice.id, choice.carve) for choice in Carve.query.all()]
        self.sand_id.choices = [(choice.id, choice.sand) for choice in Sand.query.all()]
        self.paint_id.choices = [(choice.id, choice.paint) for choice in Paint.query.all()]
        self.decoration_id.choices = [(choice.id, choice.decoration_id) for choice in Decoration.query.all()]
        self.tenon_id.choices = [(choice.id, choice.tenon) for choice in Tenon.query.all()]

    def add_item(self, vendor_id):
        # TODO: upload images
        item = Item(
            vendor_id=vendor_id,
            item=self.item.data,
            price=self.price.data,
            material_id=self.material_id.data,
            second_category_id=self.second_category_id.data,
            length=self.length.data,
            width=self.width.data,
            height=self.height.data,
            stove_id=self.stove_id.data,
            carve_id=self.carve_id.data,
            sand_id=self.sand_id.data,
            paint_id=self.paint_id.data,
            decoration_id=self.decoration_id.data
        )
        db.session.add(item)
        db.sessoin.commit()
        for tenon_id in self.tenon_id.data:
            db.session.add(ItemTenon(item_id=item.id, tenon_id=tenon_id))
        db.session.commit()
        return item

    def show_item(self, item):
        for attr in self.attributes:
            getattr(self, attr).data = getattr(item, attr)
        self.tenon_id.data = item.get_tenon_id()

    def update_item(self, item):
        for attr in self.attributes:
            if not getattr(self, attr).data == getattr(item, attr):
                setattr(item, attr, getattr(self, attr).data)

        item_tenons = item.get_tenon_id()
        add_tenons = set(self.tenon_id.data) - set(item_tenons)
        del_tenons = set(item_tenons) - set(self.tenon_id.data)
        for tenon_id in add_tenons:
            db.session.add(ItemTenon(item_id=item.id, tenon_id=tenon_id))
        for tenon_id in del_tenons:
            db.session.delete(ItemTenon.query.filter_by(item_id=item.id, tenon_id=tenon_id).limit(1).first())
        db.session.add(item)
        db.session.commit()
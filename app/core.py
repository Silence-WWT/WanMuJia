# -*- coding: utf-8 -*-
from flask import current_app, request, render_template, redirect, flash, session
from flask.ext.login import login_user, logout_user, login_required
from flask.ext.principal import identity_changed, Identity

from app import db
from app.models import User, Vendor, Distributor
from app.constants import *
from app.forms import *


def _get_login_instance(model, username, *args):
    if 'username' in args:
        instance = model.query.filter_by(username=username).limit(1).first()
        if instance:
            return instance
    instance = model.query.filter_by(mobile=username).limit(1).first() or \
        model.query.filter_by(email=username).limit(1).first()
    return instance


def login(model, form):
    if model == User or model == Distributor:
        instance = _get_login_instance(model, form.username.data, 'username')
    else:
        instance = _get_login_instance(model, form.username.data)
    if instance and instance.verify_password(form.password.data):
        login_user(instance)
        identity_changed.send(current_app._get_current_object(), Identity(instance.get_id()))
        return instance
    return False


def reset_password(model, url_prefix):
    mobile_form = MobileResetPasswordForm()
    email_form = EmailResetPasswordForm()
    reset_form = ResetPasswordForm()
    form_type = request.args.get('form')
    if form_type == 'mobile' and mobile_form.validate_on_submit():
        # TODO: store data in redis
        session['reset'] = True
        session['mobile'] = mobile_form.mobile.data
        return 'mobile ok'
    elif form_type == 'email' and email_form.validate_on_submit():
        session['reset'] = True
        session['email'] = email_form.email.data
        return 'email ok'
    elif 'reset' in session and session['reset'] is True:
        instance = None
        session.pop('reset')
        if 'mobile' in session:
            instance = model.query.filter_by(mobile=session['mobile']).first()
            session.pop('mobile')
        elif 'email' in session:
            instance = model.query.filter_by(email=session['email']).first()
            session.pop('email')
        if instance:
            instance.password = reset_form.password.data
            return 'reset password success'
        else:
            return 'error', 401
    return render_template('%s/reset_password.html' % url_prefix, mobile_form=mobile_form, email_form=email_form)
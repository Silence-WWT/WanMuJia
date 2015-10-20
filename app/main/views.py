# -*- coding: utf-8 -*-
import json

from flask import render_template, abort
from sqlalchemy import func
from flask.ext.login import current_user

from app import statisitc
from app.models import Item, FirstScene, SecondScene
from app.utils.redis import redis_set, redis_get
from .import main


@main.route('/')
def index():
    item_ids = redis_get('INDEX_ITEMS', 'ITEMS')
    if item_ids:
        item_ids = json.loads(item_ids)
    else:
        items = statisitc.item_query.order_by(func.rand()).limit(18).all()
        item_ids = [item.id for item in items]
        redis_set('INDEX_ITEMS', 'ITEMS', json.dumps(item_ids), expire=86400)
    print(item_ids, type(item_ids))
    items = Item.query.filter(Item.id.in_(item_ids)).order_by(Item.id).all()
    while len(items) < 18:
        items.append(items[0])
    scenes = []
    for first_scene in FirstScene.query.order_by(FirstScene.id):
        l = [(first_scene.id, first_scene.first_scene), []]
        for second_scene in SecondScene.query.filter_by(first_scene_id=first_scene.id).order_by(SecondScene.id):
            l[1].append((second_scene.id, second_scene.second_scene))
        scenes.append(l)
    print(scenes)
    return render_template('user/index.html', user=current_user, scenes=scenes,
                           group1=items[:6], group2=items[6:12], group3=items[12:18])


@main.route('/legal/<string:role>')
def legal(role):
    if role == 'user':
        return render_template('site/user_legal.html', user=current_user)
    elif role == 'vendor':
        return render_template('site/vendor_legal.html', user=current_user)
    abort(404)


@main.route('/about')
def about():
    return render_template('site/about.html', user=current_user)


@main.route('/join')
def join():
    return render_template('site/join.html', user=current_user)


@main.route('/center')
def center():
    return render_template('site/center.html', user=current_user)

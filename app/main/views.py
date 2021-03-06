# -*- coding: utf-8 -*-
import random
import json

from flask import render_template, current_app, Response, request, abort, jsonify

from app import statisitc
from app.models import Item, Scene
from app.utils import items_json
from app.utils.redis import redis_set, redis_get
from app.main.forms import FeedbackForm
from .import main


@main.route('/')
def index():
    return render_template('user/index.html')


@main.route('/navbar')
def navbar():
    data = redis_get('INDEX_NAVBAR', 'ITEMS')
    if data is None:
        data = {}
        for scene_id in [2, 3, 4, 6]:   # 客厅 书房 卧室 餐厅
            scene = Scene.query.get(scene_id)
            if current_app.debug:
                item_list = statisitc.item_query.filter(Item.scene_id == scene_id).all()
                if not item_list:
                    items = []
                else:
                    items = [random.SystemRandom().choice(item_list) for _ in range(8)]
            else:
                items = current_app.config['ITEMS']['navbars'][str(scene_id)]
            data[scene.id] = {'scene': scene.scene, 'items': items_json(items)}
        data = json.dumps(data)
        redis_set('INDEX_NAVBAR', 'ITEMS', data, expire=86400)
    return Response(data, mimetype='application/json')


@main.route('/brands')
def brand_list():
    format = request.args.get('format', '', type=str)
    if format == 'json':
        data = redis_get('BRAND', 'ITEMS')
        if data is None:
            brands = statisitc.brands['available']
            data = {vendor_id: {'brand': brands[vendor_id]['brand']} for vendor_id in brands}
            for vendor_id in data:
                if current_app.debug:
                    item_list = Item.query.filter(Item.vendor_id == vendor_id, Item.is_deleted == False,
                                                  Item.is_component == False).all()
                    items = [random.SystemRandom().choice(item_list) for _ in range(5)]
                else:
                    items = current_app.config['ITEMS']['brands'][str(vendor_id)]
                data[vendor_id]['items'] = items_json(items)
            data = json.dumps(data)
            redis_set('BRAND', 'ITEMS', data, expire=86400)
        return Response(data, mimetype='application/json')
    return render_template('user/brands.html')


@main.route('/brands/<int:vendor_id>')
def vendor_detail(vendor_id):
    if not current_app.debug and vendor_id not in [12801, 12803, 12806, 12836]:
        abort(404)
    format = request.args.get('format', '', type=str)
    if format == 'json':
        data = redis_get('BRAND_ITEMS', vendor_id)
        if data is None:
            data = {}
            if current_app.debug:
                for scene_id in [2, 3, 4, 6]:
                    scene = Scene.query.get(scene_id)
                    item_list = statisitc.item_query.filter(Item.vendor_id == vendor_id, Item.scene_id == scene_id).all()
                    if not item_list:
                        continue
                    items = [random.SystemRandom().choice(item_list) for _ in range(10)]
                    data[scene_id] = {'scene': scene.scene, 'items': items_json(items)}
            else:
                for scene_id in current_app.config['ITEMS']['vendor_detail'][str(vendor_id)].keys():
                    scene = Scene.query.get(scene_id)
                    items = []
                    for item_id in current_app.config['ITEMS']['vendor_detail'][str(vendor_id)][scene_id]:
                        items.append(Item.query.get(item_id))
                    data[scene_id] = {'scene': scene.scene, 'items': items_json(items)}
            data = json.dumps(data)
            redis_set('BRAND_ITEMS', vendor_id, data, expire=86400)
        return Response(data, mimetype='application/json')
    return render_template('user/brand_detail.html')


@main.route('/furniture')
def furniture():
    format = request.args.get('format', '', type=str)
    if format == 'json':
        data = redis_get('STYLE', 'ITEMS')
        if data is None:
            styles = statisitc.styles['available']
            data = {style_id: {'style': styles[style_id]['style']} for style_id in styles}
            for style_id in data:
                if current_app.debug:
                    item_list = Item.query.filter(Item.style_id == style_id).all()
                    items = [random.SystemRandom().choice(item_list) for _ in range(8)]
                else:
                    items = []
                    for item_id in current_app.config['ITEMS']['furniture'][str(style_id)]:
                        items.append(Item.query.get(item_id))
                data[style_id]['items'] = items_json(items)
            data = json.dumps(data)
            redis_set('STYLE', 'ITEMS', data, expire=86400)
        return Response(data, mimetype='application/json')
    return render_template('user/furniture.html')


@main.route('/feedback', methods=['POST'])
def feedback():
    form = FeedbackForm()
    if form.validate():
        form.add_feedback()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': form.error2str()})


@main.route('/about')
def about():
    return render_template('user/about.html')

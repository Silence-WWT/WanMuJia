# -*- coding: utf-8 -*-
import json

from flask import current_app

from app import local_redis
from app.constants import CONFIRM_EMAIL, REGISTER_ACTION, IMAGE_CAPTCHA


def redis_set(content_type, key, value, expire=None, serialize=False):
    if serialize is True:
        value = json.dumps(value)
    key = '%s:%s' % (content_type, key)
    expire = expire if expire else current_app.config['%s_DURATION' % content_type]
    local_redis.set(key, value, expire)


def redis_get(content_type, key, delete=False, serialize=False):
    key = '%s:%s' % (content_type, key)
    value = local_redis.get(key)
    if value:
        value = value.decode()
        if delete:
            local_redis.delete(key)
    if serialize is True and value is not None:
        value = json.loads(value)
    return value


def redis_verify(content_type, key, value, delete=False):
    return value == redis_get(content_type, key, delete)

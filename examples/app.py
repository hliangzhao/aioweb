import logging
logging.basicConfig(level=logging.INFO)
from aiohttp import web
import os

from aioweb import config
from aioweb import orm
from aioweb.async_web import logger_factory
from aioweb.async_web import init_jinja2
from aioweb.async_web import response_factory
from aioweb.async_web import add_routes
from aioweb.async_web import add_static


import my_config


# 更新配置
configs = config.to_mydict(config.merge(my_config.configs))


async def init_db(app):
    """
    初始化数据库连接。
    """
    await orm.create_pool(
        host=configs.db.host,
        port=configs.db.port,
        user=configs.db.user,
        password=configs.db.password,
        db=configs.db.db
    )


_app = web.Application(middlewares=[logger_factory, response_factory])
init_jinja2(_app, path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
add_routes(_app, 'handlers')
add_static(_app, static_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
_app.on_startup.append(init_db)
web.run_app(_app, host=configs.host, port=configs.port)

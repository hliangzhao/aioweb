# -*- coding: UTF-8 -*-
"""
This module implements a simple async web framework by wrapping aiohttp.
"""
import os
import json
import asyncio
import functools
import inspect
import logging
from aiohttp import web
from urllib import parse
from custom_errors import APIError
from jinja2 import Environment
from jinja2 import FileSystemLoader


def get(path):
    """
    Let developer use "@get('/path')" to decorate controller.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper

    return decorator


def post(path):
    """
    Let developer use "@post('/path')" to decorate controller.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper

    return decorator


def get_required_kwargs(func):
    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


def get_named_kwargs(func):
    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kwargs(func):
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True
    return False


def has_var_kwarg(func):
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


def has_request_arg(func):
    sig = inspect.signature(func)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and
                      param.kind != inspect.Parameter.KEYWORD_ONLY and
                      param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' %
                             (func.__name__, str(sig)))
    return found


class RequestHandler:
    """
    The class wraps controllers, which gets parameters from "request", and returns web.Response instance by
    calling the corresponding controller asynchronously.
    """
    def __init__(self, app, func):
        self._app = app
        self._func = func
        self._has_request_arg = has_request_arg(func)
        self._has_var_kwarg = has_var_kwarg(func)
        self._has_named_kwargs = has_named_kwargs(func)
        self._named_kwargs = get_named_kwargs(func)
        self._required_kwargs = get_required_kwargs(func)

    async def __call__(self, request):
        kw = None
        if self._has_var_kwarg or self._has_named_kwargs or self._required_kwargs:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kwarg and self._named_kwargs:
                new_kw = dict()
                for name in self._named_kwargs:
                    if name in kw:
                        new_kw[name] = kw[name]
                kw = new_kw
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        if self._required_kwargs:
            for name in self._required_kwargs:
                if name not in kw:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.msg)


def add_static(app, static_path):
    """
    Register static to web app.
    """
    app.router.add_static('/static/', static_path)
    logging.info('add static %s ==> %s' % ('/static/', static_path))


def add_route(app, func):
    """
    Register a controller to web app.
    """
    method = getattr(func, '__method__', None)
    path = getattr(func, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(func))
    if not asyncio.iscoroutinefunction(func) and not inspect.isgeneratorfunction(func):
        func = asyncio.coroutine(func)
    logging.info('add route %s %s ==> %s(%s)' %
                 (method, path, func.__name__, ', '.join(inspect.signature(func).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, func))


def add_routes(app, module_name):
    """
    register all controllers in "module_name" to web app.
    """
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)


async def logger_factory(app, handler):
    """
    Pre-defined middlewares.
    """
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)
    return logger


async def response_factory(app, handler):
    """
    Pre-defined middlewares.
    """
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        logging.info("\n")
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            res = web.Response(body=r)
            res.content_type = 'application/octet-stream'
            return res
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            res = web.Response(body=r.encode('utf-8'))
            res.content_type = 'text/html;charset=utf-8'
            return res
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                res = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                res.content_type = 'application/json;charset=utf-8'
                return res
            else:
                res = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                res.content_type = 'text/html;charset=utf-8'
                return res
        if isinstance(r, int) and 100 <= r < 600:
            return web.Response(status=r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and 100 <= t < 600:
                return web.Response(status=t, text=str(m))
        res = web.Response(body=str(r).encode('utf-8'))
        res.content_type = 'text/plain;charset=utf-8'
        return res
    return response


def init_jinja2(app, **kwargs):
    logging.info("init jinja2...")
    options = dict(
        autoescape=kwargs.get('autoescape', True),
        block_start_string=kwargs.get('block_start_string', '{%'),
        block_end_string=kwargs.get('block_end_string', '%}'),
        variable_start_string=kwargs.get('variable_start_string', '{{'),
        variable_end_string=kwargs.get('variable_end_string', '}}'),
        auto_reload=kwargs.get('auto_reload', True)
    )
    path = kwargs.get('path', None) or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), extensions=['jinja2.ext.loopcontrols'], **options)
    filters = kwargs.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

# -*- coding: UTF-8 -*-
"""
This module implements async database operations by wrapping aiomysql with ORM.
"""
import logging
import aiomysql
import custom_errors


__pool = None


def _log(sql):
    logging.info('SQL: %s' % sql)


async def create_pool(**kwargs):
    """
    Create global database connection pool.
    """
    logging.info("create db connection pool...")
    global __pool
    __pool = await aiomysql.create_pool(
        host=kwargs.get('host', 'localhost'),
        # DB默认端口号为3306
        port=kwargs.get('port', 3306),
        user=kwargs['user'],
        password=kwargs['password'],
        db=kwargs['db'],
        charset=kwargs.get('charset', 'utf8'),
        autocommit=kwargs.get('autocommit', True),
        maxsize=kwargs.get('maxsize', 10),
        minsize=kwargs.get('minsize', 1),
    )
    logging.info("connection pool created successfully")


async def select(sql, args, size=None):
    """
    Execute "select".
    """
    _log(sql)
    global __pool
    if __pool is not None:
        async with __pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args or ())
                if size:
                    rows = await cur.fetchmany(size)
                else:
                    rows = await cur.fetchall()
            logging.info('rows returned: %s' % len(rows))
            return rows
    else:
        raise custom_errors.PoolNotFoundError('Connection pool is NoneType.')


async def execute(sql, args, autocommit=True):
    """
    Called by "update", "insert", and "delete".
    """
    _log(sql)
    global __pool
    if __pool is not None:
        async with __pool.acquire() as conn:
            if not autocommit:
                await conn.begin()
            try:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(sql.replace('?', '%s'), args)
                    affected = cur.rowcount
                if not autocommit:
                    await conn.commit()
            except custom_errors.SqlExecutionError:
                if not autocommit:
                    await conn.rollback()
                raise
            return affected
    else:
        raise custom_errors.PoolNotFoundError('Connection pool is NoneType.')


def create_args_str(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)


class Field:
    """
    A field in a database table.
    """
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s:%s, PK:%s>' % (
            self.__class__.__name__,
            self.column_type,
            'True' if self.primary_key else 'False'
        )


class StringField(Field):
    def __init__(self, name=None, ddl='varchar(100)', primary_key=False, default=None):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaClass(type):
    def __new__(mcs, name, bases, attrs):
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)

        table_name = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, table_name))

        mappings = {}
        primary_key = None
        fields = []
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('    found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primary_key:
                        raise custom_errors.DuplicatePrimaryKeyError('Table: %s, field: %s.' % (table_name, k))
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise custom_errors.PrimaryKeyNotFoundError('Table: %s.' % table_name)
        for k in mappings.keys():
            attrs.pop(k)

        attrs['__mappings__'] = mappings
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key
        attrs['__fields__'] = fields
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__select__'] = 'select `%s`, %s from `%s`' % \
                              (primary_key, ', '.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % \
                              (table_name, ', '.join(escaped_fields), primary_key, create_args_str(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % \
                              (table_name, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (table_name, primary_key)

        return type.__new__(mcs, name, bases, attrs)


class Model(dict, metaclass=ModelMetaClass):
    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'%s' object has no attribute '%s'" % (self.__class__.__name__, key))

    def get_value(self, key):
        return getattr(self, key, None)

    def get_value_with_default(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s in table %s' % (key, str(value), self.__table__))
                setattr(self, key, value)
        return value

    @classmethod
    async def find_all(cls, where=None, args=None, **kwargs):
        sql = [cls.__select__]

        if where:
            sql.append('where')
            sql.append(where)

        if args is None:
            args = []

        _order_by = kwargs.get('order_by', None)
        if _order_by:
            sql.append('order by')
            sql.append(_order_by)

        _lmt = kwargs.get('limit', None)
        if _lmt is not None:
            sql.append('limit')
            if isinstance(_lmt, int):
                sql.append('?')
                args.append(_lmt)
            elif isinstance(_lmt, tuple) and len(_lmt) == 2:
                sql.append('?, ?')
                args.extend(_lmt)
            else:
                raise ValueError('Invalid limit value: %s' % str(_lmt))

        rows = await select(' '.join(sql), args)
        return [cls(**r) for r in rows]

    @classmethod
    async def find_number(cls, selected_field, where=None, args=None):
        sql = ['select %s _num_ from `%s`' % (selected_field, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)

        rows = await select(' '.join(sql), args, 1)
        if len(rows) == 0:
            return None
        return rows[0]['_num_']

    @classmethod
    async def find(cls, primary_key):
        rows = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [primary_key], size=1)
        if len(rows) == 0:
            return None
        return cls(**rows[0])

    async def save_(self):
        args = list(map(self.get_value_with_default, self.__fields__))
        args.append(self.get_value_with_default(self.__primary_key__))
        affected = await execute(self.__insert__, args)
        if affected != 1:
            logging.warning('failed to insert record: affected rows: %s' % affected)

    async def update_(self):
        args = list(map(self.get_value, self.__fields__))
        args.append(self.get_value(self.__primary_key__))
        affected = await execute(self.__update__, args)
        if affected != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % affected)

    async def delete_(self):
        args = [self.get_value(self.__primary_key__)]
        affected = await execute(self.__delete__, args)
        if affected != 1:
            logging.warning('failed to delete by primary key: affected rows: %s' % affected)

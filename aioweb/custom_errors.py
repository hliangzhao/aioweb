# -*- coding: UTF-8 -*-
"""
Errors.
"""


class DBError(Exception):
    def __init__(self, error, msg=''):
        super(DBError, self).__init__(msg)
        self.error = error


class PoolNotFoundError(DBError):
    def __init__(self, msg=''):
        super(PoolNotFoundError, self).__init__('db connection pool: not found', msg)


class SqlExecutionError(DBError):
    def __init__(self, msg=''):
        super(SqlExecutionError, self).__init__('sql execution: error', msg)


class DuplicatePrimaryKeyError(DBError):
    def __init__(self, msg=''):
        super(DuplicatePrimaryKeyError, self).__init__('primary key: duplicate', msg)


class PrimaryKeyNotFoundError(Exception):
    def __init__(self, msg=''):
        super(PrimaryKeyNotFoundError, self).__init__('primary key: not found', msg)


class APIError(Exception):
    def __init__(self, error, data='', msg=''):
        super(APIError, self).__init__(msg)
        self.error = error
        self.data = data
        self.msg = msg


class APIValueError(APIError):
    """
    The input value is invalid.
    """
    def __init__(self, field, msg=''):
        super(APIValueError, self).__init__('value: invalid', field, msg)


class APIResourceNotFoundError(APIError):
    """
    The resource for input value is not found.
    """
    def __init__(self, field, msg=''):
        super(APIResourceNotFoundError, self).__init__('value: not found', field, msg)


class APIPermissionError(APIError):
    """
    The API has no permission.
    """
    def __init__(self, msg=''):
        super(APIPermissionError, self).__init__('permission: forbidden', 'permission', msg)

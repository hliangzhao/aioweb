# -*- coding: UTF-8 -*-
"""
Merge configurations.
"""
import config_default


class MyDict(dict):
    def __int__(self, names=(), values=(), **kwargs):
        super(MyDict, self).__init__(**kwargs)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError('Object %s of class %s has no attribute %s' % (self, self.__class__.__name__, key))

    def __setattr__(self, key, value):
        self[key] = value


def merge(override, default=config_default.configs):
    r = dict()
    for k, v in default.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(override[k], v)
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r


def to_mydict(d):
    res = MyDict()
    for k, v in d.items():
        if isinstance(v, dict):
            res[k] = to_mydict(v)
        else:
            res[k] = v
    return res

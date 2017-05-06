from pysyncobj import SyncObj
import functools

from . import *


class NestDict:
    META_PREFIX = "::"
    SEPARATOR = ":"

    def __init__(self, base=None, prefix="", mode="dict"):
        self.__base = base or {}
        self.__prefix = (prefix + NestDict.SEPARATOR if prefix else '')
        self.__keys = self.META_PREFIX + self.__prefix + 'keys'
        self.__len_key = self.META_PREFIX + self.__prefix + 'len'
        self.__mode = mode

        if self.__mode == "dict" and self.__keys not in self.__base:
            self.__base[self.__keys] = ''
        elif self.__mode == "list" and self.__len_key not in self.__base:
            self.__base[self.__len_key] = 0

    @property
    def __own_keys(self):
        """O(n)"""
        val = self.__base[self.__keys]
        return val.split(':') if val else []

    @property
    def __len(self):
        """O(1)"""
        return self.__base[self.__len_key]

    @__len.setter
    def __len(self, val):
        """O(1)"""
        self.__base[self.__len_key] = val

    def __remove_own_key(self, key):
        """O(n)"""
        keys = set(self.__own_keys)
        keys.remove(key)
        self.__base[self.__keys] = ':'.join(keys)

    def __add_own_key(self, key):
        """O(n)"""
        own_keys = self.__own_keys
        if key not in self.__own_keys:
            if len(own_keys):
                self.__base[self.__keys] += (':' + str(key))
            else:
                self.__base[self.__keys] = str(key)

    def __is_subdict_key(self, key):
        """O(1)"""
        return self.META_PREFIX + self.__prefix + str(key) + ':keys' in self.__base

    def __is_sublist_key(self, key):
        """O(1)"""
        return self.META_PREFIX + self.__prefix + str(key) + ':len' in self.__base

    def __del_subdict(self, key):
        """O(1)"""
        del self.__base[self.META_PREFIX + self.__prefix + str(key) + ':keys']

    def __del_sublist(self, key):
        """O(1)"""
        del self.__base[self.META_PREFIX + self.__prefix + str(key) + ':len']

    @functools.lru_cache(100)
    def __subdict(self, key):
        return NestDict(self.__base, self.__prefix + str(key))

    @functools.lru_cache(100)
    def __sublist(self, key):
        return NestList(self.__base, self.__prefix + str(key))

    def __mangle_key(self, key):
        # Handle negative indexing if necessary
        if self.__mode == "list" and key < 0:
            return self.__len + key
        elif self.__mode == "dict":
            return str(key)
        else:
            return key

    def _base(self):
        return self.__base

    def update(self, other):
        """O(k)"""
        for k, v in other.items():
            self[k] = v

    def extend(self, other):
        """O(k)"""
        for v in other:
            self.append(v)

    def get(self, key, default):
        """O(1)"""
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

    def set(self, key, value):
        """O(1)"""
        self[key] = value

    def append(self, value):
        """O(1)"""
        # TODO lock here
        self.__base[self.__prefix + str(self.__len)] = value
        self.__len += 1

    def insert(self, key, value):
        """O(n)"""
        key = self.__mangle_key(key)

        for i in range(self.__len-1, key-1, -1):
            self[i+1] = self[i]
        self[key] = value
        self.__len += 1

    def clear(self):
        """O(n)"""
        if self.__mode == "list":
            for i in range(self.__len):
                self.pop()
        elif self.__mode == "dict":
            for k in self.__own_keys:
                del self[k]

    def remove(self, value):
        """O(n)"""
        for i in range(self.__len):
            if self[i] == value:
                self.pop(i)
                return

    def pop(self, key=-1):
        """O(n)"""
        key = self.__mangle_key(key)

        res = self[key]
        for i in range(key, self.__len-1):
            self[i] = self[i+1]

        self.__len -= 1

        del self[self.__len]

        return res

    def items(self):
        """O(n)"""
        for k in self.__own_keys:
            yield k, self[k]

    def values(self):
        """O(n)"""
        for k in self.__own_keys:
            yield self[k]

    def keys(self):
        """O(n)"""
        return set(self.__own_keys)

    def __len__(self):
        """dict: O(n)
        list: O(1)"""
        if self.__mode == "dict":
            return len(self.__own_keys)
        elif self.__mode == "list":
            return self.__len

    def __iter__(self):
        """"O(n)"""
        if self.__mode == "dict":
            yield from self.__own_keys
        elif self.__mode == "list":
            for i in range(self.__len):
                yield self[i]

    def __delitem__(self, key):
        """O(n)"""
        key = self.__mangle_key(key)

        if self.__mode == "dict":
            self.__remove_own_key(key)

        if self.__is_subdict_key(key):
            self.__subdict(key).clear()
            self.__del_subdict(key)
        elif self.__is_sublist_key(key):
            self.__sublist(key).clear()
            self.__del_sublist(key)
        else:
            del self.__base[self.__prefix + str(key)]

    def __contains__(self, key):
        """O(n)"""
        if self.__mode == "list":
            for i in range(self.__len):
                if key == self[i]:
                    return True
            return False
        elif self.__mode == "dict":
            return key in self.__own_keys

    def __getitem__(self, key):
        """O(1)"""
        key = self.__mangle_key(key)

        if self.__is_subdict_key(key):
            return self.__subdict(key)
        elif self.__is_sublist_key(key):
            return self.__sublist(str(key))
        else:
            return self.__base[self.__prefix + str(key)]

    def __setitem__(self, key, value):
        """O(n) because it may call del.
        Could be made O(1) if we disallow reassignment of dicts and lists"""
        key = self.__mangle_key(key)

        if key in self.__own_keys \
            and (self.__is_subdict_key(key)
                 or self.__is_sublist_key(key)):
                del self[key]

        if self.__mode == "dict":
            self.__add_own_key(key)

        if isinstance(value, dict):
            subdict = self.__subdict(key)
            subdict.update(value)
        elif isinstance(value, list):
            sublist = self.__sublist(str(key))
            sublist.extend(value)
        else:
            self.__base[self.__prefix + str(key)] = value

    def __str__(self):
        if self.__mode == "dict":
            return "{" + ', '.join(("{0}: {1}".format(repr(k), repr(v)) for k, v in self.items())) + "}"
        elif self.__mode == "list":
            return "[" + ', '.join((str(v) for v in self)) + "]"

    def __repr__(self):
        return str(self)


class NestList(NestDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, mode="list", **kwargs)

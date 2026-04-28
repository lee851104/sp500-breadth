"""
diskcache 包裝層
提供 get / set / delete / clear 操作，TTL 以秒為單位
"""
import diskcache
from config import CACHE_DIR


_cache = diskcache.Cache(CACHE_DIR)


def get(key: str):
    return _cache.get(key)


def set(key: str, value, ttl: int):
    _cache.set(key, value, expire=ttl)


def delete(key: str):
    _cache.delete(key)


def clear_all():
    _cache.clear()

"""
    helper.py
    ~~~~~~~~
    助手函数集

    :author: Fufu, 2019/9/9
"""
import hashlib
import re
import sys
import time
from datetime import datetime
from functools import wraps
from itertools import chain
from threading import Thread

import requests
from flask import request
from requests.adapters import HTTPAdapter


def run_perf(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        res = fn(*args, **kwargs)
        end = time.perf_counter()
        print('\n~~~~~~\n{}.{} : {}\n~~~~~~\n'.format(fn.__module__, fn.__name__, end - start))
        return res

    return wrapper


def debug(*data, end='------\n', die=False):
    """输出调试信息"""
    from pprint import pprint
    for x in data:
        pprint(x)
    print('', end=end)
    die and sys.exit(1)


def get_plain_text(s):
    """
    获取纯文本内容
    清除 html 标签, 空白字符替换为一个空格, 去除首尾空白

    :param s: str
    :return: str
    """
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def get_uniq_list(data):
    """
    列表去重并保持顺序(数据量大时效率不高)

    :param data: list
    :return: list
    """
    ret = list(set(data))
    ret.sort(key=data.index)
    return ret


def list2dict(key, *value):
    """
    列表转换列表.字典(用于数据记录转字典列表)

    e.g.::

        list2dict(('a', 'b'), [(1, 2), (3, 4)], [('x', 22)])

    :param key: tuple, list, 元组或列表, 与每行数据元素个数相同
    :param value: list.tuple, 一组元组数据
    :return: list.dict
    """
    try:
        return [dict(zip(key, x)) for x in chain(*value)]
    except Exception:
        return []


def data2list(data, sep=','):
    """
    字符串转列表

    :param data: 非字符串和列表外, 其他类型返回空列表
    :param sep: 字符串分隔符
    :return: list
    """
    if isinstance(data, list):
        return data
    elif data and isinstance(data, str):
        return data.split(sep)
    else:
        return []


def get_int(s=None, default=None, sep=None):
    """
    检查是否为整数, 转换并返回 int 或 列表

    e.g.::

        # None
        get_int('1a')

        # 0
        get_int('1a', 0)

        # 123
        get_int(' 123   ')

        # [123, 456, 7]
        get_int('123, 456,, 7,, ,')

    :param s: str, 整数值或字符串
    :param default: 转换整数失败时的默认值(列表转换时无效)
    :param sep: str, 指定分隔符时返回 list, e.g. [1, 7]
    :return: int / list / default
    """
    if isinstance(s, int):
        return int(s)
    elif isinstance(s, str):
        s = s.strip()
        try:
            if sep:
                ret = [int(x) for x in s.split(sep) if x.strip() != '']
                ret = get_uniq_list(ret)
            else:
                ret = int(s)
        except ValueError:
            ret = [] if sep else default
    else:
        ret = [] if sep else default

    return ret


def get_domain(domain=None):
    """检查是否为域名, 清除域名前后空白后返回"""
    domain = domain.strip()
    patt = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return domain if re.match(patt, domain) else None


def get_date(dt=None, in_fmt='%Y-%m-%d', out_fmt='', default=True):
    """
    检查日期是否正确并返回日期

    e.g.::

        get_date('2018-10-10')
        get_date('2018-10-10 12:00:00', '%Y-%m-%d %H:%M:%S')

    :param dt: mixed, 输入的日期, 空/日期字符串/日期对象
    :param in_fmt: str, 源日期格式
    :param out_fmt: str, 返回的日期格式, 默认返回日期对象
    :param default: bool, True 源日期格式不正确时返回今天
    :return: datetime|None|str
    """
    if not isinstance(dt, datetime):
        try:
            dt = datetime.strptime(dt, in_fmt)
        except Exception:
            dt = datetime.now() if default else None

    return (datetime.strftime(dt, out_fmt) if out_fmt else dt) if dt else None


def get_hash(data=None, hash_name='md5', salt=''):
    """
    获取数据的摘要信息

    :param data: str, list, dict...
    :param hash_name: str, e.g. 'md5', 'sha1', 'sha224', 'sha256'...
    :param salt: str
    :return:
    """
    try:
        m = getattr(hashlib, hash_name)(salt if isinstance(salt, bytes) else bytes(str(salt), 'utf-8'))
        m.update(data if isinstance(data, bytes) else bytes(str(data), 'utf-8'))
        return m.hexdigest()
    except Exception:
        return ''


def is_accept_json(or_post=True):
    """
    用于确定是否返回 JSON 响应体
    替代 request.xhr

    :type or_post: bool, True 时 POST 请求也返回真
    :return: bool
    """
    return 'application/json' in str(request.accept_mimetypes) or \
           request.environ.get('HTTP_X_REQUESTED_WITH', '').lower() == 'xmlhttprequest' or \
           or_post and request.method == 'POST'


def get_large_file(url, file=None, chunk_size=4096, retries=3, timeout=(30, 30), throw=False, **kwargs):
    """
    下载大文件(流), 默认重试 3 次
    保存到文件或返回 requests 对象

    :param url: str, 下载链接
    :param file: str, 结果保存文件
    :param chunk_size: int, 文件保存时的块大小
    :param retries: int, 重试次数
    :param timeout: int | tuple 连接超时和读取超时
    :param throw: bool, 是否抛出异常
    :param kwargs: dict, requests 自定义参数
    :return: bool | requests
    """
    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        r = s.get(url, stream=True, timeout=timeout, **kwargs)
        if file:
            try:
                with open(file, 'wb+') as f:
                    for chunk in r.iter_content(chunk_size):
                        f.write(chunk)
                return True
            except Exception as e:
                if throw:
                    raise e
                return False
        return r
    except requests.exceptions.RequestException as e:
        if throw:
            raise e
        return False


def async_task(fn):
    """
    装饰器: 异步执行任务

    e.g.::

        @async_task
        def _async_send_mail():
            pass

    :param fn:
    :return:
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.start()

    return wrapper

"""
track718 API 核心客户端（物流商查询、数据结构定义）

该模块基于 requests，用于物流商查询（无 Akamai 反爬）。
追踪查询请使用 playwright.py（需要浏览器上下文）。
"""

import hashlib
from typing import Optional

import requests

API_BASE = "https://apigetway.track718.net"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Origin": "https://www.track718.us",
    "Referer": "https://www.track718.us/",
}


class Track718Error(Exception):
    """track718 API 异常"""


class Track718Client:
    """track718 基础客户端（requests-based）

    用于物流商查询等不需要浏览器上下文的操作。
    注意: real_query_multi 接口有 Akamai 反爬，请使用 playwright.py。
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._carriers: Optional[list[dict]] = None

    # ------------------------------------------------------------------
    # 物流商查询
    # ------------------------------------------------------------------

    def get_carriers(self, force_refresh: bool = False) -> list[dict]:
        """获取全部物流商列表

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            [{id, name, en_name, code, key, ...}, ...]
        """
        if self._carriers and not force_refresh:
            return self._carriers

        empty_md5 = hashlib.md5(b"").hexdigest()
        resp = self.session.post(
            f"{API_BASE}/track/cargo",
            json={"cargoDataMd5": empty_md5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status", {}).get("code") != 0:
            raise Track718Error(data.get("status", {}).get("msg", "查询物流商失败"))
        self._carriers = data.get("data", [])
        return self._carriers

    def find_carrier(self, keyword: str) -> Optional[dict]:
        """按名称或代号搜索物流商

        Args:
            keyword: 物流商名称/代号关键字

        Returns:
            匹配的物流商，或 None
        """
        carriers = self.get_carriers()
        keyword = keyword.lower()
        for c in carriers:
            if (keyword in c.get("name", "").lower()
                    or keyword in c.get("en_name", "").lower()
                    or keyword in c.get("code", "").lower()
                    or keyword in c.get("key", "").lower()):
                return c
        return None

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def extract_tracking_data(result: dict) -> list[dict]:
        """提取格式化的追踪信息列表

        Args:
            result: query_by_nums / query_tracks 的返回值

        Returns:
            [{
              "track": "单号",
              "carrier_key": "物流商代号",
              "from_code": "发件地代码",
              "to_code": "收件地代码",
              "latest": "最新状态文本",
              "latest_time": "最新状态时间",
              "statuses": [{"time", "status", "address"}, ...]
            }, ...]
        """
        output = []
        for item in result.get("data", []):
            statuses = item.get("from", []) + item.get("to", [])
            status_list = [
                {"time": s.get("ondate", ""), "status": s.get("status", ""), "address": s.get("address", "")}
                for s in statuses
            ]
            latest = item.get("latest", {})
            output.append({
                "track": item.get("track", ""),
                "carrier_key": item.get("fromKey", ""),
                "from_code": item.get("fromCode", ""),
                "to_code": item.get("toCode", ""),
                "latest": latest.get("status", ""),
                "latest_time": latest.get("ondate", ""),
                "statuses": status_list,
            })
        return output

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

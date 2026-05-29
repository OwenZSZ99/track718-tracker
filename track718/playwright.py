"""
track718 Playwright 客户端 - 快递追踪查询

该模块使用 Playwright 驱动真实浏览器，绕过 Akamai Bot Manager 反爬保护。
核心思路:
  1. Playwright 启动 Chrome 浏览器（有完整 TLS 指纹）
  2. 访问 track718 页面，自动获取 Akamai Cookie
  3. 拦截页面自动触发的 API 请求，获取追踪数据
  4. 自动分批（每批 20 个），汇总结果

使用方式:
    from track718.playwright import Track718Playwright

    with Track718Playwright(headless=True) as client:
        result = client.query_by_nums(["单号1", "单号2"])
        for item in result.get("data", []):
            print(item["track"], item.get("fromKey"))
"""

import json
import random
import time
from datetime import datetime
from typing import Optional

from playwright.sync_api import sync_playwright

API_BASE = "https://apigetway.track718.net"
BATCH_SIZE = 20  # API 单次查询上限约 25 个


class Track718Playwright:
    """Playwright 驱动的 track718 追踪客户端"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._browser = None
        self._page = None

    def start(self):
        p = sync_playwright().start()
        self._browser = p.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        return self

    def close(self):
        if self._browser:
            self._browser.close()

    # ------------------------------------------------------------------
    # 核心查询
    # ------------------------------------------------------------------

    def query_tracks(self, tracks: list[dict]) -> dict:
        """查询一批快递追踪信息

        Args:
            tracks: [{"track": "单号", "key": "物流商代号(留空自动识别)"}, ...]

        Returns:
            API 原始响应
        """
        nums_str = ",".join(t["track"] for t in tracks)
        page_url = f"https://www.track718.us/zh-CN/detail?nums={nums_str}"

        # 在浏览器内加载页面，拦截自动触发的 API 请求
        api_response = None

        def on_response(resp):
            nonlocal api_response
            if "real_query_multi" in resp.url and api_response is None:
                try:
                    api_response = resp.json()
                except Exception:
                    pass

        self._page.on("response", on_response)
        self._page.goto(page_url, wait_until="load", timeout=60000)

        # 等待 API 响应（最多 8 秒）
        for _ in range(16):
            if api_response is not None:
                break
            time.sleep(0.5)

        self._page.remove_listener("response", on_response)

        if api_response:
            return api_response

        return {"data": [], "status": {"code": -1, "msg": "intercept failed"}}

    def query_by_nums(self, nums: list[str], carrier_key: str = "") -> dict:
        """按单号列表批量查询（自动分批汇总）

        Args:
            nums: 快递单号列表
            carrier_key: 物流商代号（留空自动识别）

        Returns:
            汇总后的 API 响应
        """
        all_results = {
            "data": [],
            "packTracks": [],
            "errKey": [],
            "errTracks": [],
            "status": {"code": 0, "msg": "Success"},
        }

        for i in range(0, len(nums), BATCH_SIZE):
            batch = nums[i:i + BATCH_SIZE]
            tracks = [{"track": n, "key": carrier_key} for n in batch]
            try:
                result = self.query_tracks(tracks)
                sc = result.get("status", {})
                all_results["data"].extend(result.get("data", []))
                all_results["packTracks"].extend(result.get("packTracks", []))
                all_results["errKey"].extend(result.get("errKey", []))
                all_results["errTracks"].extend(result.get("errTracks", []))
                print(f"  批次 {i//BATCH_SIZE + 1}/{(len(nums)-1)//BATCH_SIZE + 1}: "
                      f"data={len(result.get('data', []))} "
                      f"code={sc.get('code')} {sc.get('msg', '')}")
            except Exception as e:
                print(f"  批次 {i//BATCH_SIZE + 1} 失败: {e}")

        return all_results

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()

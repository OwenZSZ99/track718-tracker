"""
API 请求捕获工具 - 用于分析 track718 页面的真实网络请求

运行后会打开浏览器访问 track718，捕获所有 POST 请求的 body 和 response。
主要用于逆向分析或调试 API 参数变化。

用法:
    python scripts/analyze.py --nums "单号"
    python scripts/analyze.py --nums "单号" --headless
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from playwright.sync_api import sync_playwright


def capture(nums: str, headless: bool = False):
    url = f"https://www.track718.us/zh-CN/detail?nums={nums}"
    result = {"url": url, "post_requests": [], "api_responses": {}}

    def on_request(request):
        if request.method != "POST":
            return
        host = urlparse(request.url).hostname
        if host and "track718" in host:
            result["post_requests"].append({
                "url": request.url,
                "post_data": request.post_data,
                "headers": dict(request.headers),
            })

    def on_response(response):
        if "real_query_multi" in response.url:
            try:
                result["api_responses"]["real_query_multi"] = response.json()
            except Exception:
                pass
        elif "track/cargo" in response.url:
            try:
                result["api_responses"]["cargo"] = response.json()
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.on("request", on_request)
        page.on("response", on_response)

        print(f"访问: {url}")
        page.goto(url, wait_until="load", timeout=60000)
        time.sleep(5)
        browser.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="捕获 track718 API 请求详情")
    parser.add_argument("--nums", default="61290349243121618775", help="快递单号(示例)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    args = parser.parse_args()

    result = capture(args.nums, headless=args.headless)

    print(f"\nPOST 请求 ({len(result['post_requests'])}):")
    for req in result["post_requests"]:
        path = urlparse(req["url"]).path
        print(f"\n  {req['method']} {path}")
        if req["post_data"]:
            try:
                parsed = json.loads(req["post_data"])
                print(f"  Body: {json.dumps(parsed, ensure_ascii=False, indent=4)}")
            except json.JSONDecodeError:
                print(f"  Body: {req['post_data']}")

    if "real_query_multi" in result["api_responses"]:
        data = result["api_responses"]["real_query_multi"]
        print(f"\nreal_query_multi 响应:")
        print(f"  status: {data.get('status')}")
        print(f"  data: {len(data.get('data', []))} 条")


if __name__ == "__main__":
    main()

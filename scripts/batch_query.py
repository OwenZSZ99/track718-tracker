"""
track718 快递批量查询入口

用法:
    python scripts/batch_query.py --nums "单号1,单号2"              # 命令行指定单号
    python scripts/batch_query.py --nums nums.txt                    # 从文件读取
    python scripts/batch_query.py --nums nums.txt --headless         # 无头模式
    python scripts/batch_query.py --nums nums.txt --output result.json  # 导出 JSON

示例:
    python scripts/batch_query.py --nums "LP123456789US"
    python scripts/batch_query.py --nums "LP123456789US,LP987654321US"
    python scripts/batch_query.py --nums nums.txt --headless --output result.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from track718.playwright import Track718Playwright


def format_result(data: dict) -> str:
    """格式化输出追踪结果"""
    status = data.get("status", {})
    lines = [
        f"状态: code={status.get('code')} {status.get('msg', '')}",
        f"成功: {len(data.get('data', []))} 条",
        f"失败: {len(data.get('errTracks', []))} 条",
    ]
    for item in data.get("data", []):
        track = item.get("track", "")
        latest = item.get("latest", {})
        statuses = item.get("from", []) + item.get("to", [])
        lines.append(f"\n[{track}]")
        lines.append(f"  物流商: {item.get('fromKey', '')}")
        if latest.get("status"):
            lines.append(f"  最新: [{latest.get('ondate', '')}] {latest.get('status', '')[:80]}")
        for s in statuses[-3:]:
            lines.append(f"  [{s.get('ondate', '')}] {s.get('status', '')[:80]}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="track718 快递批量查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
  %(prog)s --nums "LP123456789US"
  %(prog)s --nums "单号1,单号2,单号3"
  %(prog)s --nums nums.txt --headless --output result.json
  %(prog)s --nums nums.txt --headless --output result.json --no-progress
        """,
    )
    parser.add_argument("--nums", required=True, help="快递单号(逗号分隔) 或单号文件路径")
    parser.add_argument("--carrier", default="", help="物流商代号(留空自动识别)")
    parser.add_argument("--headless", action="store_true", help="无头模式(不弹出浏览器窗口)")
    parser.add_argument("--output", help="导出结果到 JSON 文件")
    parser.add_argument("--no-progress", action="store_true", help="不显示详细进度")
    args = parser.parse_args()

    # 读取单号
    if os.path.isfile(args.nums):
        with open(args.nums, encoding="utf-8") as f:
            nums_list = [line.strip() for line in f if line.strip()]
    else:
        nums_list = [n.strip() for n in args.nums.split(",") if n.strip()]

    if not nums_list:
        print("错误: 未提供有效单号")
        sys.exit(1)

    print(f"单号数: {len(nums_list)} 个")
    if args.carrier:
        print(f"物流商: {args.carrier}")
    else:
        print("物流商: 自动识别")
    print()

    # 执行查询
    with Track718Playwright(headless=args.headless) as client:
        result = client.query_by_nums(nums_list, carrier_key=args.carrier)

    # 输出结果
    print("\n" + "=" * 60)
    print(format_result(result))

    # 导出 JSON
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n已导出 → {args.output}")


if __name__ == "__main__":
    main()

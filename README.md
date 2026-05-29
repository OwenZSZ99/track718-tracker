# track718-tracker

track718.us 快递追踪 API 逆向工程 Python 客户端。支持批量查询、自动识别物流商、绕过 Akamai 反爬保护。

## 功能

- **批量查询** — 一次查询数百个快递单号（自动分批）
- **物流商自动识别** — 无需手动指定 FedEx / USPS / DHL 等
- **绕过 Akamai 反爬** — 使用 Playwright 驱动真实浏览器，自动处理 Cookie / TLS 指纹
- **导出结果** — 支持 JSON 格式导出，数据结构清晰
- **物流商查询** — 查询全部支持的物流商列表及其代号

## 原理

### 逆向过程

通过分析 [track718.us](https://www.track718.us) 前端页面，捕获了真实的 API 请求参数：

```
POST https://apigetway.track718.net/track/real_query_multi
Content-Type: application/json

{
  "tracks": [
    {"track": "快递单号", "key": "物流商代号（留空自动识别）"}
  ],
  "uuid": "随机数-时间戳",
  "noCache": false,
  "referrer": "来源页面 URL",
  "isChoose": false,
  "webDateTime": "YYYY-MM-DD HH:mm:ss"
}
```

### 反爬机制

该 API 使用了 **Akamai Bot Manager** 防护：

- `_abck` Cookie 绑定浏览器 TLS 指纹和请求特征
- Python `requests` 直接调用会被拦截（code=1 Request parameter format error）
- 必须在真实浏览器（Playwright/Chrome）上下文中发起请求

### 解决方案

1. Playwright 启动 Chrome 浏览器
2. 访问目标页面，自动获取 Akamai Cookie
3. 在浏览器内通过 `fetch()` 发起 API 请求
4. 拦截并解析 API 响应

## 安装

### 前置条件

- Python 3.10+
- Chrome 浏览器（Playwright 会自动管理）

### 步骤

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/track718-tracker.git
cd track718-tracker

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器
playwright install chromium
```

## 快速开始

### 查询单个快递

```bash
python scripts/batch_query.py --nums "61290349243121618775"
```

### 查询多个快递

```bash
python scripts/batch_query.py --nums "单号1,单号2,单号3"
```

### 从文件批量查询

准备 `nums.txt`，每行一个快递单号（示例）：

```
61290349243121618775
```

执行：

```bash
python scripts/batch_query.py --nums nums.txt
```

### 导出结果到 JSON

```bash
python scripts/batch_query.py --nums nums.txt --output result.json
```

### 无头模式（不弹窗）

```bash
python scripts/batch_query.py --nums nums.txt --headless
```

## API 参考

### track718 模块

```python
from track718 import Track718Client

# 查询物流商（无需浏览器，requests 即可）
client = Track718Client()
carriers = client.get_carriers()
print(f"共 {len(carriers)} 个物流商")
```

### track718.playwright 模块

```python
from track718.playwright import Track718Playwright

# 使用 Playwright 查询追踪信息
with Track718Playwright(headless=True) as client:
    result = client.query_by_nums(["61290349243121618775"])
    
    # 提取追踪信息
    for item in result.get("data", []):
        print(f"单号: {item['track']}")
        print(f"物流商: {item.get('fromKey', '')}")
        print(f"最新状态: {item.get('latest', {}).get('status', '')}")
        
        # 追踪记录
        for s in item.get("from", []):
            print(f"  [{s['ondate']}] {s['status']}")
```

### 返回数据格式

```json
{
  "data": [
    {
      "track": "61290349243121618775",
      "fromKey": "special.fedex.com",
      "fromCode": "US",
      "toCode": "US",
      "latest": {
        "ondate": "2026-05-28 16:02:00",
        "status": "PONTIAC MI DISTRIBUTION CENTER, On the way",
        "address": "PONTIAC MI DISTRIBUTION CENTER, US, 48340"
      },
      "from": [
        {"ondate": "...", "status": "...", "address": "..."}
      ],
      "to": []
    }
  ],
  "status": {"code": 0, "msg": "Success"}
}
```

状态码说明：

| code | 说明 |
|------|------|
| 0 | 查询成功，已返回完整数据 |
| 1 | 请求参数格式错误（检查参数） |
| 2 | 无追踪数据（单号不存在或已过期） |
| 3 | 数据抓取中（稍后重试） |

## 项目结构

```
track718-tracker/
├── README.md                    # 本文档
├── LICENSE                      # MIT 许可证
├── requirements.txt             # Python 依赖
├── .gitignore
├── track718/
│   ├── __init__.py              # 包入口
│   ├── api.py                   # 核心客户端（requests）
│   └── playwright.py            # Playwright 客户端（绕过反爬）
├── scripts/
│   ├── batch_query.py           # 批量查询入口
│   └── analyze.py               # API 请求捕获工具
├── examples/
│   └── nums.txt                 # 示例单号文件
└── result.json                  # 查询结果输出
```

## 常见问题

### 为什么不直接用 `requests`？

API 有 Akamai Bot Manager 防护，`requests` 的 TLS 指纹与浏览器不同，会被拦截。必须通过真实浏览器上下文发起请求。

### 查询太慢？

每批最多查 20 个单号，349 个单号需要约 3-4 分钟。这是 API 本身的限制。

### 返回 code=2？

表示该单号在系统中没有追踪数据（可能已过期、不存在、或物流商不对）。会正常跳过。

## 免责声明

本项目仅供学习和研究使用。请遵守 track718 的服务条款，不要高频请求。

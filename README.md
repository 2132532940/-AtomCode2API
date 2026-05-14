# AtomCode2API - 将 AtomCode CodingPlan 免费额度转发为 OpenAI 兼容 API

将 AtomCode CodingPlan 的免费模型额度转发为标准 OpenAI 格式 API，无需本地鉴权。

## 检测到的可用模型

| 模型名 | 类型 |
|--------|------|
| `deepseek-v4-flash` | AtomCode 独占 |
| `Qwen/Qwen3.6-35B-A3B` | AtomCode 独占 |
| `Qwen/Qwen3-VL-8B-Instruct` | AtomCode 独占 |

> 模型列表通过 `/v1/codingplan/models` 接口动态获取，`/v1/models` 自动同步。

## 前置条件

1. 安装 AtomCode（仅获取认证，不需运行）:
   ```powershell
   irm https://atomgit.com/atomgit_atomcode/atomcode/releases/download/v4.22.0/install.ps1 | iex
   ```

2. 登录并领取免费额度:
   ```bash
   atomcode login
   atomcode codingplan
   ```

## Python 版（推荐）

```bash
cd python
pip install -r requirements.txt
python server.py          # http://localhost:8000
```

## Node.js 版

```bash
cd node
npm install
node server.js            # http://localhost:8001
```

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /v1/chat/completions` | OpenAI 格式聊天补全（支持 stream） |
| `GET /v1/models` | 可用模型列表（从 CodingPlan 动态获取） |
| `GET /v1/models/{id}` | 单模型信息 |
| `GET /v1/codingplan/models` | CodingPlan 原始模型列表 |
| `GET /v1/codingplan/status` | CodingPlan 额度状态 |
| `GET /v1/health` | 健康检查 |

## 使用示例

### curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"你好"}]}'
```

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="any")

resp = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)
```

### 流式输出

```python
for chunk in client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "写一个快排"}],
    stream=True,
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ATOMCODE_API_KEY` | 自动从 ~/.atomcode 读取 | Access Token |
| `PROXY_HOST` | 0.0.0.0 | 监听地址 |
| `PROXY_PORT` | 8000(Python) / 8001(Node) | 监听端口 |
| `DEFAULT_MODEL` | deepseek-v4-flash | 默认模型 |

## 技术要点

- 上游 API: `https://api-ai.gitcode.com/v1`（OpenAI 兼容格式）
- 认证: Bearer Token + `User-Agent: atomcode/4.22.0`（独占模型需 AtomCode UA）
- Token 自动刷新: 通过 `acs.atomgit.com/oauth/refresh` 自动续期
- 无本地鉴权: 代理不设任何访问限制

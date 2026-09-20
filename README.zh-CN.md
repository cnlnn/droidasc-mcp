# droidasc-mcp

面向 [Droid ASC](https://github.com/MG1937/ASC) 的防御性 MCP 服务。它把 ASC 官方 CLI
封装为六个有明确参数、只读且结果受限的 MCP 工具。

每次分析都在独立子进程组中执行；只能读取配置目录内的 APK；类列表、源码、Manifest
和引用结果均支持分页，避免一次把大型 APK 的全部结果塞进模型上下文。

> 这是社区项目，与 Droid ASC 官方维护者无隶属或背书关系。

## 工具

| 工具 | 用途 |
| --- | --- |
| `asc_ping` | 查看适配器、ASC 版本和当前运行限制 |
| `asc_apk_info` | 返回文件大小、SHA-256、Manifest 和 DEX 条目 |
| `asc_get_manifest` | 解码并分页读取 `AndroidManifest.xml` |
| `asc_list_classes` | 按包名前缀分页列出类 |
| `asc_get_class_source` | 定位并反编译单个类 |
| `asc_find_refs` | 跨 DEX 查找字符串、类型、方法或字段引用 |

## 安装

需要 Python 3.10 或更高版本：

```bash
git clone https://github.com/cnlnn/droidasc-mcp.git
cd droidasc-mcp
python -m venv .venv
.venv/bin/pip install -e .
```

## 接入 Codex

```bash
codex mcp add droidasc \
  --env DROIDASC_MCP_ALLOWED_ROOTS=/APK所在目录 \
  -- /droidasc-mcp绝对路径/.venv/bin/droidasc-mcp
```

默认使用 stdio，不会监听网络端口。上述命令会修改 Codex 的 MCP 配置；它不是安装本项目
所必需的步骤。

## 其他 MCP Host

```json
{
  "mcpServers": {
    "droidasc": {
      "command": "/droidasc-mcp绝对路径/.venv/bin/droidasc-mcp",
      "env": {
        "DROIDASC_MCP_ALLOWED_ROOTS": "/APK所在目录"
      }
    }
  }
}
```

也可以启动 Streamable HTTP：

```bash
DROIDASC_MCP_ALLOWED_ROOTS=/APK所在目录 \
  .venv/bin/droidasc-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

端点为 `http://127.0.0.1:8000/mcp`。没有认证和 TLS 反向代理时，不要监听公网地址。

## 调用示例

```text
asc_apk_info(apk_path="/samples/app.apk")
asc_list_classes(apk_path="/samples/app.apk", prefix="com.example", limit=100)
asc_find_refs(apk_path="/samples/app.apk", kind="string", value="Authorization")
asc_get_class_source(apk_path="/samples/app.apk", class_name="com.example.MainActivity")
```

分页结果包含 `total`、`offset`、`limit` 和 `truncated`。继续读取时增加 `offset`。

## 安全边界

- `DROIDASC_MCP_ALLOWED_ROOTS`：允许读取的根目录。多目录在 Linux/macOS 用 `:` 分隔，
  Windows 用 `;` 分隔；未设置时仅允许服务当前工作目录。
- 不提供任意命令执行工具，不调用 shell。
- 路径经过真实路径解析后再检查，符号链接不能逃逸允许目录。
- 默认单次任务超时 180 秒、最多并行 2 个任务、单页最多 1000 行。
- 超时会终止整个 ASC 子进程组，而不只终止父进程。

ASC 及其依赖仍会解析不可信二进制数据。分析恶意 APK 时，应在无网络的容器或一次性虚拟机
中运行。本项目提供的是受控进程边界，不是完整恶意软件沙箱。

## 开发验证

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
```

## 许可证

Apache License 2.0。Droid ASC 是独立上游项目，其代码和版权归原作者所有。


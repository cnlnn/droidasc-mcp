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

需要 Python 3.10 或更高版本。0.1.1 已验证的平台是 Linux；Windows、macOS 暂属实验支持：

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

分页结果包含 `total`、`offset`、`limit`、`truncated` 和 `next_offset`。下一页直接使用
`next_offset`，为 `null` 时结束。响应预算可能缩短页面，不能直接加请求的 `limit`。
单行过大时明确报错，不静默丢弃。

引用结果来自 CLI 文本的尽力解析，字符串内换行可能拆分记录，`total` 是输出行数而非语义
引用数量。解码与排序仅做一次，之后直接对快照分页。结果缓存 60 秒、最多 8 条，合计按解码
后的字符串和元组指针内存计费；同一查询合并执行，不同查询和缓存命中不再等待全局计算锁。
缓存以查询、
文件身份、大小和时间戳标识，不是内容寻址证据库。翻页期间不要修改 APK。

## 安全边界

- `DROIDASC_MCP_ALLOWED_ROOTS`：允许读取的根目录。多目录在 Linux/macOS 用 `:` 分隔，
  Windows 用 `;` 分隔；未设置时仅允许服务当前工作目录。
- 不提供任意命令执行工具，不调用 shell。
- 路径经过真实路径解析后再检查，符号链接不能逃逸允许目录。
- 默认单次任务超时 180 秒、最多并行 2 个任务、单页最多 1000 行。
- stdout 在采集期间限制大小，stderr 上限 64 KiB；不再写入无上限的临时结果文件。
- 页内容保守限制在 256 KiB 预算内；APK 信息和哈希也在受监管的独立进程中执行。
- POSIX 下无论父进程是否已经退出，结束时都会清理进程组；排队和进程等待均有超时。
- Windows 进程树清理仍属尽力处理，当前 CI 未验证。客户端取消尚不能立即终止同步工具。
- 未限制解析器自身内存，应使用操作系统或容器资源限制处理不可信样本。
- 捕获缓冲区、正在构建的快照和活跃页面可与缓存同时存在；缓存预算不等于总 RSS 硬上限。

ASC 及其依赖仍会解析不可信二进制数据。分析恶意 APK 时，应在无网络的容器或一次性虚拟机
中运行。本项目提供的是受控进程边界，不是完整恶意软件沙箱。

## 开发验证

参见 [验收记录](docs/VALIDATION.md)：包含真实进程清理、输出限额、分页对照，以及 stdio/HTTP
实包验证的命令和证据边界。设置 `ASC_TEST_APK` 才会执行实包测试；没有样本时明确跳过。

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
uv build
# 使用 Python 3.12+ 验证源码包和 wheel：
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.1.1.tar.gz dist/droidasc_mcp-0.1.1-py3-none-any.whl
```

## 许可证

Apache License 2.0。Droid ASC 是独立上游项目，其代码和版权归原作者所有。

# droidasc-mcp

面向 [Droid ASC](https://github.com/MG1937/ASC) 的防御性 MCP 服务。它把 ASC 官方 CLI
封装为有明确参数、只读且结果受限的 MCP 工具。

每次分析都在独立子进程组中执行；只能读取配置目录内的输入文件；类列表、源码、Manifest
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
| `asc_find_refs` | 跨 DEX 查找字符串、类型、方法、字段引用；直接继承/实现查询（未发布） |
| `asc_analyze_dex` | 分析裸 DEX 或明确指定的 DEX 集合，保留来源和哈希（未发布） |

## 安装

需要 Python 3.10 或更高版本。CI 覆盖 Linux 和原生
Windows runner 的 Python 3.10-3.13，使用源码构建的[测试 APK](tests/fixtures/android/README.md)
验收 stdio/HTTP 全部 6 个工具及发布包安装；macOS 尚未验证。

Linux 安装固定版本的 GitHub 发布包：

```bash
python -m venv .venv
.venv/bin/python -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.2.2/droidasc_mcp-0.2.2-py3-none-any.whl
```

Windows（PowerShell）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.2.2/droidasc_mcp-0.2.2-py3-none-any.whl
```

Windows 的服务端命令为 `.venv\Scripts\droidasc-mcp.exe`。开发时改为克隆本仓库，
运行 `uv sync --locked --extra dev`。

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
asc_find_refs(apk_path="/samples/app.apk", kind="extends", value="android.app.Activity")
asc_find_refs(apk_path="/samples/app.apk", kind="impl", value="java.lang.Runnable")
asc_get_class_source(apk_path="/samples/app.apk", class_name="com.example.MainActivity")
```

分页结果包含 `total`、`offset`、`limit`、`truncated` 和 `next_offset`。下一页直接使用
`next_offset`，为 `null` 时结束。响应预算可能缩短页面，不能直接加请求的 `limit`。
单行过大时明确报错，不静默丢弃。

引用结果来自 CLI 文本的尽力解析，字符串内换行可能拆分记录，`total` 是输出行数而非语义
引用数量。`--help` 等值作为查询数据而非 CLI 选项；匹配仍遵循 ASC 语义，字符串和类型查询
支持正则表达式，无效表达式明确报错。上游 CLI 在参数解析前保留了精确值 `--gui`，
因此该值会明确报错。方法和字段的精确类名支持 Java 名称和 Dalvik 描述符，模糊类名保留原语义。

未发布的 `extends`、`impl` 查询只返回**直接**父类或接口声明，包括接口继承接口。
依赖要求已提高到 Droid ASC 0.1.2.post2，旧版本缺少这些命令。
通过 `value` 传入 Java 类名或 Dalvik 描述符，这两类查询不接受类名过滤参数。
记录包含 `dex`、`class_name`、`relation`、`target`、`raw`，并标记
`relation_scope="direct"`；不代表传递继承关系或运行时分派图。无法识别的文本只保留
`raw`。`asc_analyze_dex(operation="find_refs", ...)` 也支持这两类查询。

解码与排序仅做一次，之后直接对快照分页。结果缓存 60 秒、最多 8 条，合计按解码
后的字符串和元组指针内存计费；同一查询合并执行，不同查询和缓存命中不再等待全局计算锁。
缓存以查询、
文件身份、大小和时间戳标识，不是内容寻址证据库。翻页期间不要修改 APK。

## 裸 DEX 分析（未发布）

此功能需从源码运行，上方 v0.2.2 发布包尚不包含。输入为允许目录内的 1-64 个 `.dex`
文件路径，总大小受 `DROIDASC_MCP_MAX_APK_BYTES` 限制。不接收目录、APK、CompactDex
或 DEX 041 容器。

```text
asc_analyze_dex(dex_paths=["/samples/classes.dex", "/samples/classes2.dex"])
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="list_classes", prefix="com.example")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="get_class_source", class_name="com.example.Main")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="find_refs", kind="string", value="Authorization")
```

默认操作为 `info`。成功结果包含 `status="ok"` 和 `sources` 来源表，记录原路径、SHA-256、
文件大小、类数量及内部 `dex_entry`。类列表和源码返回 `dex_entry`，引用沿用尽力解析的
`dex` 字段。内部条目名称按输入顺序分配；翻页时保持顺序和原文件不变，并核对返回哈希。
每次调用重新导入与分析，不复用 APK 工具的跨请求缓存。

导入时校验标准小端 DEX 头（035/037/038/039/040）、固定 ID 表边界、文件大小、SHA-1
签名和 Adler-32 校验和。校验通过不代表方法体或运行时代码完整。原文件保持不变，仅在
私有临时目录中生成分析容器，在受监管进程内调用 ASC 公共模块入口；容器不是可安装 APK。
成功、失败、超时和取消后均清理临时文件。临时磁盘占用可能接近输入总大小的两倍，加 ZIP 开销。

重复类返回 `status="error", code="duplicate_class"`，最多展示 20 项冲突，不静默择一。
`get_manifest` 返回 `status="not_applicable", code="no_manifest"`。
输入、查询及引擎错误提供诊断码；成功但无引用为 `status="ok", total=0`。
路径策略、进程启动、超时、内存和外层输出限额失败仍为 MCP 工具错误。调用方需同时检查
MCP 错误和结构化 `status`。

本工具用于导出后的静态分析，不自动脱壳、不修复 DEX、不恢复缺失代码或运行时加密的方法体，
也不重建原始 Manifest 和资源。覆盖范围固定为 `supplied_files_only`，运行时完整性为
`unknown`。分析不可信 dump 仍需使用隔离环境。

## 安全边界

- `DROIDASC_MCP_ALLOWED_ROOTS`：允许读取的根目录。多目录在 Linux/macOS 用 `:` 分隔，
  Windows 用 `;` 分隔；未设置时仅允许服务当前工作目录。
- 不提供任意命令执行工具，不调用 shell。
- 路径经过真实路径解析后再检查，符号链接不能逃逸允许目录。
- 默认单次任务超时 180 秒、最多并行 2 个任务、单页最多 1000 行。
- `DROIDASC_MCP_MAX_WORKER_MEMORY_BYTES` 默认 `2147483648`。Windows 对整个 Job
  进程树限制提交内存；POSIX 在导入 ASC 前设置可继承的单进程 `RLIMIT_AS`，并每 50 ms
  检查进程树合计 RSS，越界时终止整棵树。
- stdout 在采集期间限制大小，stderr 上限 64 KiB；不再写入无上限的临时结果文件。
- 页内容保守限制在 256 KiB 预算内；APK 信息和哈希也在受监管的独立进程中执行。
- POSIX 下无论父进程是否已经退出，结束时都会清理进程组；排队和进程等待均有超时。
- Windows 在运行 ASC 前将工作进程加入 Job Object；结束时一并清理子孙进程，不依赖父进程
  仍然存活。Job 设置失败则不启动分析。原生 CI 覆盖孤儿清理、输出超限及重复调用资源释放。
- MCP 请求取消会传递到排队、共享快照等待和运行中的同步工具；服务端退出被取消任务前会清理
  对应进程树，同一会话随后仍可继续使用。
- 捕获缓冲区、正在构建的快照和活跃页面可与缓存同时存在；缓存预算不等于 MCP Host 总 RSS
  硬上限。POSIX 的单进程地址空间上限由内核强制，进程树 RSS 合计限制是采样 watchdog。

ASC 及其依赖仍会解析不可信二进制数据。分析恶意 APK 时，应在无网络的容器或一次性虚拟机
中运行。本项目提供的是受控进程边界，不是完整恶意软件沙箱。

## 开发验证

参见 [验收记录](docs/VALIDATION.md)：包含真实进程清理、输出限额、分页对照，以及 stdio/HTTP
实包验证的命令和证据边界。设置 `ASC_TEST_APK` 才会执行实包测试；没有样本时明确跳过。

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
uv run python scripts/validate_corpus.py /APK路径/one.apk /APK路径/two.apk
uv run python scripts/stability_check.py /APK路径/one.apk --duration 300 --workers 2
uv build
# 使用 Python 3.12+ 验证源码包和 wheel：
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.2.2.tar.gz dist/droidasc_mcp-0.2.2-py3-none-any.whl
```

## 许可证

Apache License 2.0。Droid ASC 是独立上游项目，其代码和版权归原作者所有。

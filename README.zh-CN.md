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
| `asc_open_dex_session` | 创建哈希绑定、容量受限的不可变 DEX 会话（未发布） |
| `asc_query_dex_session` | 查询指定会话，保留原始哈希和 DEX 来源（未发布） |
| `asc_close_dex_session` | 关闭会话并释放私有文件（未发布） |

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
依赖要求已提高到 Droid ASC 0.1.2.post3，包含精确方法 Smali 和调试信息输出。
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

## DEX 会话与精确方法（未发布）

用 `asc_open_dex_session(dex_paths=[...])` 创建会话，再把返回的 `session_id` 传给
`asc_query_dex_session`。查询参数与 `asc_analyze_dex` 一致，结束时调用 `asc_close_dex_session`。
`input_id` 绑定按输入顺序排列的 DEX SHA-256、Schema 和 ASC 版本；UUID 会话标识不依赖全局当前样本。
原文件修改或删除不会改变已有会话，查询参数每次重新执行。复用的是已验证容器，**不是常驻反编译引擎**。

默认最多 4 个打开或准备中的会话，空闲 1800 秒过期，最多每 30 秒清理一次；容量不足时淘汰最久未用的
空闲会话。正在查询的文件不会被淘汰。关闭会话后禁止新查询，已有查询结束再清理，返回字段
`cleanup_pending` 标明是否仍等待。MCP 正常退出会清理文件，进程被强杀时仍可能留下系统临时目录。
未知或过期 ID 返回 `session_not_found`，不会自动重新加载已变化的原文件。

可选精确方法后端需要官方 [JADX 1.5.5](https://github.com/skylot/jadx/releases/tag/v1.5.5) 和 JDK 17 以上版本。
设置 `DROIDASC_MCP_JADX_HOME` 为包含 `lib/` 的解压目录，`DROIDASC_MCP_JAVA` 为 JDK 的 `java` 路径
（也可使用 PATH）。仅有 JRE 不够。普通 ASC 功能不依赖 Java，安装 Python 包也不会下载 JADX。
显式指定 `source_format=smali` 直接调用 ASC 0.1.2.post3，不依赖 JVM/JADX；可同时设置
`debug_info=true` 返回调试指令。`auto` 和 `java` 仍使用可选后端。

```text
asc_query_dex_session(session_id="...", operation="list_methods", class_name="com.example.Main")
asc_query_dex_session(session_id="...", operation="get_method_source", method_descriptor="Lcom/example/Main;->check(I)Z")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="get_method_source", method_descriptor="Lcom/example/Main;->check(I)Z", source_format="smali")
```

方法清单由 dexlib2 直接读取 DEX 定义，包含构造函数、synthetic/bridge、native/abstract 方法、完整参数和
返回类型，按完整描述符排序分页。查询必须给出 `L类;->方法(参数)返回类型`，不存在的重载返回
`method_not_found`，不会按名称猜选或退到其他重载。当前入口是 DEX 文件或会话，不直接接收 APK 路径。

`source_format=auto` 通过 JADX 公开 API 精确查找 Java 方法；Java 未输出该方法（如省略的默认构造函数）
或引擎报错时，只反汇编同一个 dexlib2 方法对象。返回 `format`、`fell_back`、`fallback_reason`、后端版本、
原始哈希和 `dex_entry`。`java` 模式不自动回退，`smali` 模式始终返回该方法的反汇编。引擎错误和警告计数
不是 Java 语义正确性的证明；原 `find_refs` 仍保留 ASC 的名称级尽力解析结果。

新增 `find_field_refs`，通过完整 `field_descriptor`（如 `Lcom/example/Config;->enabled:Z`）
精确定位字段；`field_access` 可选 `all`（默认）、`read` 或 `write`。每条记录返回完整调用方法、
字段描述符、读写类型、静态/实例访问、指令、DEX 来源及方法内 code-unit 偏移。先过滤再分页，
同名不同类型字段不会混在一起；未使用或不存在的字段返回零匹配，外部字段引用保留空的目标 DEX。
定义查找按字面描述符进行，不解析继承字段；反射、JNI、方法句柄目标和编码初始值不计为直接读写。
该操作需要可选 JADX/dexlib2 后端，同时支持单次分析和 DEX 会话。

```python
asc_query_dex_session(
    session_id="...",
    operation="find_field_refs",
    field_descriptor="Lcom/example/Config;->enabled:Z",
    field_access="write",
)
```

新增 `find_method_refs`（谁引用该方法）和 `get_method_calls`（该方法引用谁），均要求完整方法描述符，
支持 DEX 文件和会话，使用上述可选后端。每条结果包含完整 `caller`、`callee`、调用者 `dex_entry`、
`opcode` 和 `instruction_offset`。偏移单位是从方法首条指令起算的 **16 位 code unit**，不是文件偏移。
`target_resolution`、`target_dex_entry` 表明操作数所指的方法是否定义在输入中。入向查询可查外部方法；
出向查询要求该方法存在。分页顺序固定为 DEX entry、类、调用者描述符和指令位置。

```text
asc_query_dex_session(session_id="...", operation="find_method_refs", method_descriptor="Lcom/example/Main;->check(I)Z")
asc_query_dex_session(session_id="...", operation="get_method_calls", method_descriptor="Lcom/example/Main;->check(I)Z")
```

结果统计扫描方法数、指令数、无代码声明、未定义操作数和动态调用位置；多态调用保留调用点原型，
动态位置最多返回 20 条诊断。`instruction_scan_complete` 仅指指定范围的指令解码完成，不代表完整运行时
调用图。虚调用分派、反射、JNI 和动态加载仍未解析；未知指令或解码失败直接报错，不返回伪完整结果。

未配置可选后端返回 `backend_unavailable`，非 1.5.5 版本会明确拒绝。每次可选后端查询启动一个受现有进程树限制的
JVM，最大堆 512 MiB，共享超时、内存、输出和取消清理约束，因此有启动开销。方法分页包含 `total`、
`offset`、`limit`、`next_offset`、`truncated` 和 `has_more`，超大结果明确报错而不是静默截断。

会话限制可通过 `DROIDASC_MCP_MAX_DEX_SESSIONS`、`DROIDASC_MCP_DEX_SESSION_TTL_SECONDS`、
`DROIDASC_MCP_MAX_DEX_SESSION_BYTES` 配置，默认分别为 `4`、`1800`、`4294967296`。
磁盘预算包含已有文件及并发准备阶段的预留空间；所有会话只属于当前服务进程，不跨重启恢复。

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

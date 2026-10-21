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
| `asc_list_apk_entries` | 分页列出 APK 内容、资源、assets 和 native ABI |
| `asc_read_apk_entry` | 有界读取 UTF-8/base64 内容，支持二进制 XML 解码 |
| `asc_manifest_summary` | 分页返回组件、Intent Filter 和权限来源 |
| `asc_get_manifest` | 解码并分页读取 `AndroidManifest.xml` |
| `asc_list_classes` | 按包名前缀分页列出类 |
| `asc_get_class_source` | 定位并反编译单个类 |
| `asc_find_refs` | 跨 DEX 查找字符串、类型、方法、字段引用；直接继承/实现查询 |
| `asc_analyze_dex` | 分析裸 DEX 或明确指定的 DEX 集合，保留来源和哈希 |
| `asc_open_dex_session` | 创建哈希绑定、容量受限的不可变 DEX 会话 |
| `asc_query_dex_session` | 查询指定会话，保留原始哈希和 DEX 来源 |
| `asc_close_dex_session` | 关闭会话并释放私有文件 |
| `asc_signing_inventory` | 签名容器与证书指纹清单，不执行密码学验签 |
| `asc_inspect_artifact` | APK/JAR/ZIP/AAR/AAB/APKS/XAPK 的 DEX、JVM 与 split 能力清单 |
| `asc_open_artifact_session` | 将所选容器中的直接 DEX 接入现有会话工作流 |
| `asc_diff_dex_sessions` | 对比哈希绑定版本的类、方法与字段声明身份 |
| `asc_secret_candidates` | 固定模式检索 DEX 字符串，返回脱敏候选与精确位置 |

容器、证书和版本审查的参数及覆盖边界见 [REVERSE_WORKFLOW.md](docs/REVERSE_WORKFLOW.md)。
发布门禁统一覆盖跨平台、MCP 传输及干净安装包验收。

0.4.0 在现有 DEX 查询工具中增加类搜索、结构、继承关系、字符串使用位置、指令文本检索、
结构化反汇编和源码 token 引用；补充 DEX 041 容器、一级嵌套 JAR 的 JVM 清单与身份对比、
资源字节续页、Manifest/类资源模板、版本对比提示和候选密钥原值的显式开关。
[逐项源码对照表](docs/COMPETITOR_API_AUDIT.md) 覆盖竞品全部 25 个工具、2 个资源、3 个提示及
87 个参数，同时列出接口差异和限制。功能工作流对齐不代表所有性能指标都优于竞品。

## 安装

需要 Python 3.10 或更高版本。CI 覆盖 Linux 和原生
Windows runner 的 Python 3.10-3.13，使用源码构建的[测试 APK](tests/fixtures/android/README.md)
验收 stdio/HTTP 全部 18 个工具及发布包安装；macOS 尚未验证。

Linux 安装固定版本的 GitHub 发布包：

```bash
python -m venv .venv
.venv/bin/python -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.4.0/droidasc_mcp-0.4.0-py3-none-any.whl
```

Windows（PowerShell）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.4.0/droidasc_mcp-0.4.0-py3-none-any.whl
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
asc_manifest_summary(apk_path="/samples/app.apk", limit=20)
asc_list_apk_entries(apk_path="/samples/app.apk", kind="resource", limit=100)
asc_read_apk_entry(apk_path="/samples/app.apk", entry_path="res/xml/config.xml")
asc_list_classes(apk_path="/samples/app.apk", prefix="com.example", limit=100)
asc_find_refs(apk_path="/samples/app.apk", kind="string", value="Authorization")
asc_find_refs(apk_path="/samples/app.apk", kind="extends", value="android.app.Activity")
asc_find_refs(apk_path="/samples/app.apk", kind="impl", value="java.lang.Runnable")
asc_get_class_source(apk_path="/samples/app.apk", class_name="com.example.MainActivity")
```

### APK 内容与组件研判

三个归档工具均返回 `apk_sha256`，跨资源、组件和代码关联时先核对哈希。
清单支持分类和区分大小写的字面路径前缀；其中 CRC 是 ZIP 声明值，不代表校验完成。
native 条目仅提供路径和 ABI，不等同于 ELF 分析。

条目读取默认返回 16 KiB，最多 128 KiB，二进制内容使用 base64；完整 XML 输入上限为 4 MiB。
`decoded`、`decoding_status`、`decoding_warnings`、`truncated`、`content_complete` 和
`crc_verified` 分别说明解码、告警、输出截断、内容完整性和 CRC 校验情况，不在文件系统解包。
资源 ID 尚不解析。正常的新 Android 属性也可能触发解码库告警，告警会保留，不直接判为加固。

结构化 Manifest 保留原始命名空间属性、组件顺序、Intent Filter、metadata、Provider 路径规则和
URI 授权规则，并标明权限来源。显式空权限清除继承要求；alias 未声明权限时不继承目标 Activity
或 application 权限。缺省 exported 和依赖资源的值保持未解析，不据此判定运行时可达或存在漏洞。
通过 `next_offset` 翻页；出现 `response_limit` 时降低页大小。
详见 [能力边界与验收](docs/ARCHIVE_WORKFLOW.md)。

分页结果包含 `total`、`offset`、`limit`、`truncated` 和 `next_offset`。下一页直接使用
`next_offset`，为 `null` 时结束。响应预算可能缩短页面，不能直接加请求的 `limit`。
单行过大时明确报错，不静默丢弃。

引用结果来自 CLI 文本的尽力解析，字符串内换行可能拆分记录，`total` 是输出行数而非语义
引用数量。`--help` 等值作为查询数据而非 CLI 选项；匹配仍遵循 ASC 语义，字符串和类型查询
支持正则表达式，无效表达式明确报错。上游 CLI 在参数解析前保留了精确值 `--gui`，
因此该值会明确报错。方法和字段的精确类名支持 Java 名称和 Dalvik 描述符，模糊类名保留原语义。

`extends`、`impl` 查询只返回**直接**父类或接口声明，包括接口继承接口。
依赖要求已提高到 Droid ASC 0.1.2.post3，包含精确方法 Smali 和调试信息输出。
通过 `value` 传入 Java 类名或 Dalvik 描述符，这两类查询不接受类名过滤参数。
记录包含 `dex`、`class_name`、`relation`、`target`、`raw`，并标记
`relation_scope="direct"`；不代表传递继承关系或运行时分派图。无法识别的文本只保留
`raw`。`asc_analyze_dex(operation="find_refs", ...)` 也支持这两类查询。

解码与排序仅做一次，之后直接对快照分页。结果缓存 60 秒、最多 8 条，合计按解码
后的字符串和元组指针内存计费；同一查询合并执行，不同查询和缓存命中不再等待全局计算锁。
缓存以查询、
文件身份、大小和时间戳标识，不是内容寻址证据库。翻页期间不要修改 APK。

## 裸 DEX 分析

自 v0.3.0 提供。输入为允许目录内的 1-64 个 `.dex`
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

## DEX 会话与精确方法

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

未配置可选后端返回 `backend_unavailable`，非 1.5.5 版本会明确拒绝。源码查询和未索引查询启动一个受现有进程树限制的
JVM，最大堆 512 MiB，共享超时、内存、输出和取消清理约束，因此有启动开销。方法分页包含 `total`、
`offset`、`limit`、`next_offset`、`truncated` 和 `has_more`，超大结果明确报错而不是静默截断。

会话限制可通过 `DROIDASC_MCP_MAX_DEX_SESSIONS`、`DROIDASC_MCP_DEX_SESSION_TTL_SECONDS`、
`DROIDASC_MCP_MAX_DEX_SESSION_BYTES` 配置，默认分别为 `4`、`1800`、`4294967296`。
磁盘预算包含已有文件及并发准备阶段的预留空间；所有会话只属于当前服务进程，不跨重启恢复。

### 索引与目标发现

`operation="get_call_graph"` 根据完整 `method_descriptor` 探索多跳静态调用图。
`direction=incoming|outgoing|both`，默认双向；`depth=1..5`，默认 2；
`max_nodes=1..500`，默认 200；`max_edges=1..1000`，默认 500。
首次调用会构建完整索引，大型应用可能需要数分钟，不代表冷查询提速；会话内后续调用复用索引。
节点保留最短跳数及定义 DEX；边保留每个独立调用点，重复调用、opcode、偏移及目标来源均保留。
循环和递归不会无限展开，外部方法操作数也可以作为根节点。
图内容另有 128 KiB 预算，`truncation_reasons` 分别报告深度、节点、边及输出字节边界。
`traversal_complete_within_depth` 只描述指定深度内的静态邻域。
可提高预算或以边界方法为新根继续探索；`offset` 必须为零，普通 `limit` 不控制图大小。
动态调用诊断仅统计返回节点，最多附 20 个示例；`invoke-custom` 不伪造目标边，虚调用运行时分派仍未解析。

`build_xref_index` 完整扫描所提供 DEX，成功后原子发布 SQLite 索引。之后精确方法/字段引用查询
无需再次启动 JVM。`find_type_refs` 自动建库或复用，`type_relation` 可选 `instruction`、
`declaration`、`annotation`、`all`，覆盖声明和嵌套注解类型值；数组按完整描述符匹配，不展开元素类型。

```python
asc_query_dex_session(session_id="...", operation="search_members", kind="method", value="->check(")
asc_query_dex_session(
    session_id="...",
    operation="find_type_refs",
    type_descriptor="Lcom/example/Main;",
    type_relation="annotation",
)
```

`search_members` 发现方法或字段声明，`kind` 必须为 `method` 或 `field`。`value` 是完整描述符的
区分大小写字面子串，不是正则；`class_name` 可限定精确所属类。返回的描述符可直接用于精确引用和
Smali 查询，不必猜重载。它不是 DEX 字符串池搜索，也不是运行时使用证明。
成员发现只读取声明，不再触发完整索引。`operation="search_strings", value="https://"` 搜索
DEX 字符串池，使用区分大小写的字面子串，返回 `dex_entry`、`string_index` 和 `value`；
字符串池中存在不等于代码使用。两种发现操作均返回 `instruction_scan_complete=false`。

会话内的发现与未建库精确引用查询支持相同查询页复用。磁盘 LRU 缓存最多 32 页、总计 4 MiB、
每页 256 KiB，与索引共用磁盘预留，完整建库前清空。缓存绑定不可变输入与后端哈希，换页可能
重新扫描；`query_cache.hit` 表示是否命中。仍保留独立工作进程，不常驻整份 APK 解析对象。

另有每会话最多 32 页、4 MiB 的常驻序列化页缓存，单页上限 256 KiB，命中时无需启动工作进程。
实现、引擎或索引文件身份变化后失效，不常驻 DEX 解析对象和工作进程。全部 18 个工具提供
MCP 类型化输出 Schema，覆盖嵌套结果行与诊断字段。

建库有前置时间和磁盘成本。`DROIDASC_MCP_MAX_XREF_INDEX_BYTES` 默认 256 MiB，从会话磁盘总额预留；
大应用可能需要显式调整索引配额、会话总额和超时。取消、配额耗尽和解码失败不会发布部分索引。
索引绑定输入哈希、Schema 和后端文件，会话关闭/过期或服务退出即删除工作副本；默认单次查询索引也是临时的。

需要跨会话和服务重启复用时，显式设置 `DROIDASC_MCP_XREF_CACHE_DIR` 到专用私有目录
（POSIX 权限 0700，Windows 配置私有 ACL）。持久缓存保留派生标识和关系，不保留原始 APK；
身份包含有序输入哈希、Schema、索引解析源码及后端 JAR 哈希。重新打开仍验证输入 DEX，
匹配的完整索引经校验和验证后复制进新会话。精确引用和成员发现会恢复已有索引，但缓存未命中
不触发完整建库。`index.durable_cache` 区分 `stored`、`restored`、`not_accessed`、`disabled`
和 `too_large`；工作副本本身仍为 `session_lifetime`。

持久缓存默认总额 1 GiB（`DROIDASC_MCP_MAX_XREF_CACHE_BYTES`）、最多 64 项、闲置七天
（`DROIDASC_MCP_XREF_CACHE_TTL_SECONDS`），独立于会话配额。跨进程串行读写，访问时执行
TTL/LRU 清理，校验和及原子发布防止使用中断写入结果；淘汰不影响已恢复的会话副本。
大型索引需要同时满足两处配额。手动删除专用缓存目录前先停止服务。

服务增加初始化指引、`droidasc://analysis-guide` 资源以及 `triage_apk` / `trace_exact_method` prompts。
样本字符串和反编译结果始终是非可信数据。与竞品的实测差距见[源码对比](docs/AIMARD_COMPARISON.md)。

### 可选 Rust ASC

安装 Rust 后执行 `uv run python scripts/setup_rust.py`，将 `DROIDASC_MCP_RUST_ASC` 设置为构建出的
`artifacts/rust_ASC/target/release/rust_ASC`，Windows 为 `rust_ASC.exe`。脚本固定源码与 radguard 提交。
Manifest、类列表、类源码和 APK 引用查询可显式选择 `backend="rust_asc"`；默认仍为 Python ASC，不静默切换。
Rust 路径不提供我们的精确 DEX 索引/Smali 查询或 `extends`/`impl`。上游引用扫描可能丢弃单个 DEX 的错误，
因此明确标记覆盖范围未核验，空结果不能证明没有引用。两种后端共享路径、并发和进程树预算。
详见[后端说明](docs/RUST_BACKEND.md)。

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
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.4.0.tar.gz dist/droidasc_mcp-0.4.0-py3-none-any.whl
```

## 许可证

Apache License 2.0。Droid ASC 是独立上游项目，其代码和版权归原作者所有。

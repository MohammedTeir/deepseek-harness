---
description: "预编译 Landlock 启动器与异步 POSIX flock 的 JavaScript 入口。"
kind: "package-library"
---
# @deepseek-ai/node-addon-system

[English](README.md) | 中文

`./landlock-run` 入口导出 Landlock 启动器路径、强制执行探测、授权参数和协议常量。独立的 `./flock` 入口导出 `tryLockExclusive(fd): Promise<void>`；导入任一入口都不会加载 `system.node`。包不提供根导出。

锁操作异步尝试 `LOCK_EX | LOCK_NB`。在完成前保持调用方拥有的描述符打开；竞争以 `EAGAIN`/`EWOULDBLOCK` 拒绝，其他系统调用失败也会拒绝，错误携带 code、值为正数的 errno 和 `syscall: 'flock'`。原生调用准备阶段的错误也会拒绝同一个 promise。关闭指向该打开文件描述的最后一个描述符即释放锁。绑定不打开、复制、关闭或显式解锁描述符。

可选操作系统/CPU 平台包携带二进制。它们的 `~x.y.z` 依赖范围允许同一次版本内的后续补丁版本。Linux 包含 `bin/landlock-run` 和分别用于两种 libc 的 `bin/glibc/system.node` / `bin/musl/system.node`；macOS 包含 `bin/system.node`。flock 绑定缺失或无法加载时，锁获取请求会被拒绝，不在安装时编译。Landlock 仍是遵循既有失败关闭协议的独立可执行文件；不支持的内核或平台探测结果为不可用。

Android ARM64 嵌入通过宿主原生库链接器命名空间延迟加载固定的 `libharness_system.so` SONAME。Android 宿主必须打包匹配的 Bionic Node-API 绑定及其 Node 依赖；npm 平台包不提供该绑定。加载失败会拒绝锁获取，不回退或直接授予锁。Android 探测使用此入口，但 Android Harness 会话持久化仍未验证。

`@deepseek-ai/node-addon-system/publish` 导出 `publishPreparedFileExclusive(source, destination)`。非 Android 调用方保留 fs.link 语义。Android ARM64 通过宿主固定的 libharness_atomic.so 与异步 Node-API v8 工作，在同一个规范化、归当前用户所有的 0700 目录内调用 renameat2(RENAME_NOREPLACE) 发布。暂存文件名必须不同，仅含小写 ASCII 字母、数字、点或连字符，且不超过 120 字节。Android 成功时消耗暂存路径，其他平台保留该路径。调用方在发布前 fsync 数据、发布后 fsync 目标目录，并在清理暂存路径时允许 ENOENT。EEXIST 不替换目标；加载、权限或不支持错误均拒绝且不回退。Node 将 errno 95 命名为 ENOTSUP（EOPNOTSUPP 的别名）。发布后的失败不表示回滚。同 UID 恶意修改暂存文件、跨目录发布及保留源文件的别名不属于此 API。Android 宿主提供匹配绑定，npm 平台包不提供。

三个 C 源文件随包分发以供审计。参见工作区[架构](../../docs/architecture.md)、[支持矩阵](../../docs/support-matrix.md)和 [CLI 约定](../../docs/cli-contract.md)。

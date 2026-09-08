# PTI Architecture Atlas

用户主入口已移至：`D:\项目架构图\总目录.html`。

本目录是 `D:\personal-tech-intelligence` 的 Archify 实际使用产物。

## PTI 视图

- [系统总览](pti/PTI_SYSTEM_OVERVIEW.html)：调度、Stage A、SQLite、Chancellor、能力库和人工入口。
- [发现到激活](pti/PTI_DISCOVERY_TO_ACTIVATION.html)：候选项目如何经过证据、策略和人工闸门。
- [运行时流程](pti/PTI_RUNTIME_FLOW.html)：任务计划程序、锁、pending 检查、Chancellor 和健康证据。
- 每张图旁边的 `.pti-receipt.json` 是对应的 Archify 收据。

## 边界说明

本轮只对 PTI 做了真实架构渲染。`D:\money` 未读取、未修改、未生成图；原因是当前受控 Archify wrapper 永久禁止该路径，且本轮没有来自用户直接消息的独立授权。

## 证据

- Archify pinned commit: `c6519401f7b91b9d43011657880893b0a8955548`
- 三张图均为 `compositionStatus=pass`、`errors=0`、`warnings=0`。

# CandleScope

一个在本机运行的中文 A 股日线复盘工作台。图表使用 [Vela / LuxAlgo](https://velacharts.dev)，行情按需通过 BaoStock 读取；不提供实时报价、交易功能或投资建议。

## 功能

- 沪深上市 A 股目录搜索、自选排序/过滤；北交所支持用户 CSV 导入。
- 日、周、月 K 线、成交量与成交额；MA、MACD、RSI。
- 趋势线、水平线、区间测量、Fib 自定义比例/延长/撤销重做；清空前应用内确认。
- 按证券及交易日期保存笔记、绘图历史和设置；本地 JSON 备份导出。
- 专注模式、范围预设、中文快捷键帮助；响应式布局。
- 磁盘缓存、失败保留旧行情和显式重试；手动启动的本项目进程管理与有界异常恢复。

## 运行

需 Node.js（支持 TypeScript strip-types 的版本，推荐 Node 24+）及 Python 3.12+（已验证 3.14）。

```sh
npm ci
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm run build
npm run service:start
```

打开 http://127.0.0.1:5178/ 。服务仅监听本机。`npm run service:status` 检查，`npm run service:stop` 停止。也可用 `npm start` 前台启动，Ctrl+C 停止；不要同时占用同一端口。启动器不安装系统服务或开机任务，电脑注销/重启后需手动启动。异常退出最多重启3次，2/4/6秒间隔；明确来源拒绝持久保存并停止联网，重启进程不会清除拒绝。

```sh
npm test
npm run test:server
npm run lint
npm run typecheck
npm run build
```

公开源码的测试使用合成输入，不附带真实行情 fixture。历史缺成交额可用 `npm run amount:backfill` 对**已有缓存**补取，每只缓存股一次原来源请求；只填存在交易日缺失的 amount，来源遗漏仍保留缺失，失败停止整批。

## 数据口径与限制

BaoStock 历史日线，人民币元、成交量股、成交额元，只支持不复权 adjustflag=3；日期采用 Asia/Shanghai。周/月 OHLCV、amount 从已存在交易日聚合，首末期可不完整；金额部分缺失单独标记，绝不按价格×成交量估算。停牌及非交易日不补虚构K线。CSV价格、复权及单位由用户提供；可选 amount 列缺失时明确显示缺失。示例界面用合成数据，与任何股票无关。

MACD(12,26,9)柱为 DIF−DEA（不乘2），RSI 为 Wilder 平滑，MA 为当前周期简单均线。不足期数的指标不绘制。数据源覆盖及可用性由来源决定；首次读取需网络，节假日没有新交易日属正常。

浏览器本地存储保存自选、CSV、笔记、图形和设置，磁盘 `cache/` 保存行情，`.runtime/` 保存服务状态和日志。请自行保管备份；当前提供备份导出，尚无应用内备份恢复导入流程。下载提示只表示浏览器已收到下载请求，实际落地应在浏览器下载列表核实。

仓库不包含用户记录、缓存、日志、凭证、真实行情数据或私有开发报告。代码许可证不授予行情数据再发布权；使用数据仍须遵守来源条件。

## 许可证与署名

项目源码采用 Apache-2.0；第三方包保持各自许可证。见 [LICENSE](LICENSE)、[NOTICE](NOTICE)、[第三方说明](third-party/README.md)。Vela 原始 LICENSE/NOTICE 已保留；所有图表模式都有可见 Vela 链接，请勿移除或遮挡。

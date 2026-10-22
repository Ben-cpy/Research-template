# 示例：重复查询是否值得先建集合？

本目录仅演示配置、结果记录和续跑，不是已被选定的研究方向或论文证据。
探索阶段不要求先运行它；探究循环与目录规则见 [workflow](../../docs/workflow.md)。
本文件是稳定使用说明，执行后不追加进度或实测结论；实际完成情况须核验运行产物。

问题：集合查询节省的时间，能否覆盖构建集合的成本？
基线：列表逐项查找。方法：每次调用先建集合再查询，计时包含构建成本。
验证：每个输入规模先检查两种方法的答案完全一致。
指标：相同输入、预热和重复次数下的中位耗时，以及列表耗时 / 集合耗时。

在项目根目录运行：

```bash
uv run python experiments/001_example/run.py --config experiments/001_example/config.json
uv run python experiments/001_example/plot.py --config experiments/001_example/config.json
```

结果位于 `results/default/`：`checkpoint.jsonl` 是逐项记录，`summary.json` 是汇总，
`speedup.png` 是图。`config.json` 和 `provenance.json` 保存完整配置、代码版本与环境。
运行前必须有本项目的初始 Git commit。

重复运行相同命令会跳过已完成的输入规模。代码、配置、输入或环境变化时，使用新的输出目录。
可在运行期间中断，再执行原命令观察续跑。

结果解读：CPU 小例子的结果不能推广到 GPU，可根据交叉点判断适用输入规模。
若用于实际探究，结论写入所属 research.md；正式实验的简短结论维护在 paper/exp_design.md。

学习脚本结构时可复制此目录，替换问题、配置、计算部分和输出路径。新探究放在
`AI-discover/<编号_主题>/`；确定可复用后再整理进 `src/`。不需要预先建立公共实验框架。
`record.py` 的代码快照范围由调用者传入，复制后需补齐实际执行源码、输入和设备环境记录，
不能把教学记录器当成所有研究任务的完整证据采集器。运行产物默认被 Git 忽略，须单独备份。

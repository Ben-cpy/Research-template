# 示例：重复查询是否值得先建集合？

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

结论：运行后填写实测结果及适用范围；CPU 小例子的结果不能推广到 GPU。
下一步：根据交叉点决定哪些输入规模适合采用集合查询。

模仿时复制此目录，替换问题、配置和计算部分。探究代码放在 `discover/`；
确定可复用后再整理进 `src/`。不需要预先建立公共实验框架。

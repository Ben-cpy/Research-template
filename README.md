# 科研项目模板

从探究、实现、实验到论文的一套轻量工作流程。先读 [流程说明](docs/workflow.md)，
再参照 [完整实验示例](experiments/001_example/README.md) 开始工作。

复制本目录到新项目位置，在新项目根目录运行：

```bash
git init
mkdir -p discover src paper/tex archive
uv sync
git add .
git commit -m "Initialize research project"
uv run python experiments/001_example/run.py --config experiments/001_example/config.json
uv run python experiments/001_example/plot.py --config experiments/001_example/config.json
```

目录用途：

```text
discover/       临时探究，编号递增，Git 忽略
src/            核心实现，初始为空
experiments/    每个目录一个独立实验，包含配置、脚本、结果和图
paper/          exp_design.md 逐项记录实验；plan.md 统一论文计划；tex/ 存放正文
docs/           用户流程说明
archive/        失效内容移到这里，Git 忽略
```

在 `AGENTS.md` 填写项目环境；随着项目形成，更新本 README 的安装、基线和核心实验命令。
`discover/`、`archive/` 和运行结果默认不提交，重要内容需另行备份；
需要随仓库保存的小型结果可用 `git add -f <结果路径>` 明确加入。

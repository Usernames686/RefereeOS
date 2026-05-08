# RefereeOS-AG2 项目介绍

## 1. 项目一句话

RefereeOS-AG2 是一个面向科研审稿场景的多智能体系统：输入一篇论文，输出一份包含核心主张、证据链、方法学风险、复现风险和 area-chair 综合意见的审稿准备包。

## 2. 为什么做这个项目

科研论文审稿通常有一个很重的前置工作：审稿人需要先读懂论文声称了什么、证据在哪里、方法是否可靠、结果能不能复现、有没有完整性风险。这个阶段很耗时间，而且不同审稿人的准备质量不稳定。

RefereeOS-AG2 的目标不是替代审稿人，而是给审稿人一个更好的起点。系统把论文拆成结构化 evidence board，再让不同 agent 分工处理，最后生成一份可以给真人编辑和审稿人使用的 reviewer packet。

## 3. 借鉴来源

本项目基于真实 GitHub 项目 [VJDiPaola/RefereeOS](https://github.com/VJDiPaola/RefereeOS) 改造。原项目已经具备科研论文解析、证据板、复现检查和前端展示等基础能力。我的 C5-AG2 改造重点是：保留原本稳定的 deterministic pipeline，并新增 AG2 Beta multi-agent reviewer layer。

## 4. 核心用户场景

一个编辑或审稿人拿到一篇论文后，可以把论文文本、PDF 或 LaTeX archive 输入系统。系统会先解析论文结构，抽取 central claims，然后检查方法、统计、完整性和复现相关风险。最后，AG2 Beta reviewer team 会生成一份人类可读的审稿准备包。

典型输出包括：

- 论文核心 claims
- 每个 claim 对应的 evidence
- 方法学和统计问题
- prompt injection 或可疑文本风险
- artifact / metric 复现检查结果
- 给编辑的 reviewer expertise 建议
- 最终 triage recommendation

## 5. 多智能体设计

系统分成两类 agent。

第一类是 deterministic agents：

- `intake_agent`：抽取论文 profile 和 claims
- `methods_statistics_agent`：检查方法和统计风险
- `integrity_agent`：检查 prompt injection 和完整性风险
- `novelty_literature_agent`：提示 novelty 和相关工作风险
- `reproducibility_agent`：运行 artifact probe 或本地 fallback

第二类是 AG2 Beta agents：

- `claim_extractor`：从论文片段中抽取 3-6 个 central scientific claims
- `method_critic`：像 skeptical reviewer 一样批判 methods、statistics 和 reproducibility
- `area_chair`：综合 claims、concerns 和 method critique，生成 reviewer packet

其中 `method_critic` 被注册成 `area_chair` 可调用的工具：

```python
method_critic.as_tool(name="critique_methods")
```

这就是本项目最重要的 AG2 加分点：agent 不是并排摆放，而是存在明确的编排关系和工具调用关系。

## 6. C5-AG2 改造点

我做的主要改造包括：

- 新增 `backend/agents/beta_review.py`
- 新增 `ag2_reviewer.py` 独立命令行入口
- 新增 DeepSeek / OpenRouter / OpenAI / Gemini provider detection
- 新增 `scripts/offline_demo.py`，没有 LLM key 也能演示
- 更新 `requirements.txt`，加入 `ag2[openai,gemini]>=0.9.0`
- 编写 `AI_LOG.md` 记录至少 5 轮 AI 迭代
- 编写 `ATTRIBUTION.md` 说明 fork 来源和借鉴内容
- 编写 `GROUP_SUBMISSION.md` 方便直接发群提交
- 扩展测试，覆盖 provider defaults 和 AG2 parsing helper

## 7. 如何演示

无 API key 演示：

```powershell
python scripts/offline_demo.py
python -m unittest discover -s tests -v
```

有 LLM key 演示：

```powershell
python ag2_reviewer.py --fixture clean
python ag2_reviewer.py --fixture suspicious
```

推荐 demo 讲法：

1. 说明这是 RefereeOS 的 C5-AG2 科研赛道 fork。
2. 展示 README、AI_LOG 和 ATTRIBUTION。
3. 运行 offline demo，证明没有 key 也能跑通。
4. 展示 AG2 Beta 代码：`claim_extractor`、`method_critic`、`area_chair`。
5. 强调 `area_chair` 通过 `Agent.as_tool(...)` 调用 `method_critic`。
6. 运行测试，证明项目不是只写文档。

## 8. 项目边界

RefereeOS-AG2 不做论文录用或拒稿决定。它只做审稿准备，把信息整理得更清楚，让真人编辑和审稿人更快进入高质量判断。

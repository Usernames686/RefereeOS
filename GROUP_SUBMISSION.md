# C5-AG2 Group Submission

## Short Version

My C5-AG2: https://github.com/Usernames686/RefereeOS  
Track: `scientific`  
Tagline: Turn a preprint into an auditable reviewer packet.

## Detailed Version

我做的是 RefereeOS-AG2，一个基于真实 GitHub 项目 [VJDiPaola/RefereeOS](https://github.com/VJDiPaola/RefereeOS) 改造的 C5-AG2 科研赛道作品。

它的目标是辅助科研审稿：输入一篇 scientific manuscript，系统会抽取论文核心 claims，建立 evidence board，检查方法学、统计、完整性和复现风险，最后生成一份给真人编辑/审稿人使用的 reviewer packet。

这不是“让 AI 直接决定接收或拒稿”，而是“让 AI 多智能体团队把审稿前准备工作做得更结构化、更可追踪”。

## What I Changed

原 RefereeOS 已经有论文解析、deterministic agents、证据板和复现检查能力。我在此基础上新增了 AG2 Beta multi-agent reviewer layer：

- `claim_extractor`：抽取 3-6 个 central scientific claims
- `method_critic`：像 skeptical methods reviewer 一样检查方法、统计、证据和复现风险
- `area_chair`：综合前面 agent 的结果，输出给人类编辑看的 reviewer packet

最重要的 AG2 编排点：

```python
method_critic.as_tool(name="critique_methods")
```

也就是说，`area_chair` 会通过 `Agent.as_tool(...)` 调用 `method_critic`，不是三个 agent 各说各话。

## Demo

无 LLM key 也可以先跑 deterministic demo：

```powershell
python scripts/offline_demo.py
python -m unittest discover -s tests -v
```

有 DeepSeek / OpenRouter / OpenAI / Gemini key 时可以跑 AG2 Beta reviewer：

```powershell
python ag2_reviewer.py --fixture clean
python ag2_reviewer.py --fixture suspicious
```

## Submission Files

- `README.md`：完整项目说明
- `PROJECT_INTRO.md`：中文项目介绍
- `AI_LOG.md`：AI 迭代记录
- `ATTRIBUTION.md`：fork 来源和借鉴说明
- `GROUP_SUBMISSION.md`：群提交文案

## C5-AG2 Fit

- Borrow and improve: fork 自真实 RefereeOS 项目
- Track: `scientific`
- Multi-agent: deterministic agents + AG2 Beta agents
- Bonus: 使用 `autogen.beta.Agent`
- Bonus: 使用 `Agent.as_tool(...)`
- Demo-friendly: 无 key 可跑 offline demo，有 key 可跑 AG2 Beta reviewer

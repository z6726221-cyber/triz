---
title: "搞不懂Skills？看看Claude Code内部工程师们是怎么玩的"
source: "https://mp.weixin.qq.com/s/STCdNggKNsW8PHCscLQ3Vw"
author:
published:
created: 2026-04-25
description: "系统化的经验。"
tags:
  - "clippings"
---
*2026年3月20日 13:00*

编译｜冷猫

你还在为你的龙虾笨笨的而烦恼吗？

你还在为找不到合适的 Skills 安装而焦头烂额吗？

你还在为网上找到的 Skills 可能不安全而心惊胆战吗？

养了这么久龙虾，是时候开始构建自己的 Skills 了。这时候，一篇来自 Anthropic 团队的 Skills 秘籍在外网广为流传，为想要构建 Skills 的开发者和智能体用户提供了绝佳的参考资料。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/5L8bhP5dIqEURPJKdZpDI0gIZVmksrgccRc98Hd8IeIo7uRDPSzdD4qjAFuWVSmqG9VTicwaoiaRH3MM9uBXmcX8GibEadu13JlOQZkF6h0ZHY/640?wx_fmt=png&from=appmsg&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=1)
- 博客标题：Lessons from Building Claude Code: How We Use Skills
- 博客链接：https://x.com/trq212/status/2033949937936085378

这篇文章来自于 Anthropic 的 Claude Code 团队工程师，Skills 功能核心参与者 Thariq Shihipar。内容大多是 Anthropic 内部使用 Skills 的实战经验和总结。

我们对该博客进行了全文编译，希望读者从中获取关于 Skills 制作、使用和推广分发相关的经验。

以下是博客全文：

Skills 已经成为 Claude Code 中使用最广泛的扩展方式之一。它们灵活、易于创建，也方便分发。

但这种灵活性也带来了一个问题：很难判断什么才是最佳实践。什么类型的 Skills 值得开发？写出一个优秀 Skill 的秘诀是什么？又应该在什么时候将它们分享给他人？

在 Anthropic 内部，我们已经在 Claude Code 中广泛使用 Skills，目前有数百个 Skills 在实际运行中。

这些是我们在使用 Skills 来加速开发过程中总结的一些经验。

什么是 Skills ？

如果你刚接触 Skills，建议先阅读我们的文档：

相关链接：https://code.claude.com/docs/en/skills

本文默认你已经对 Skills 有一定了解。

我们经常听到一个常见的误解：认为 Skills「只是一些 Markdown 文件」。但实际上，Skills 最有趣的地方在于 —— 它们并不仅仅是文本文件，而是一个文件夹，里面可以包含脚本、资源、数据等内容，供智能体进行发现、探索和操作。

在 Claude Code 中，Skills 还具备多种配置选项，包括注册动态钩子（hooks）等。

相关链接：https://code.claude.com/docs/en/skills#frontmatter-reference

我们发现，一些最有意思的 Skills，正是通过巧妙利用这些配置选项和文件结构来实现的。

Skills 类型

在整理我们所有 Skills 之后，我们发现它们大致可以分为几个常见的类别。

最好的 Skills 通常能够清晰地归类到一个类别中，而那些更为复杂或难以理解的 Skills，则可能跨越多个类别。这并不是一个权威的分类列表，但它为你判断在你的组织中是否缺少某些类型的 Skills 提供了一个很好的思路。

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

1\. 库与 API 参考

这些 Skills 解释如何正确使用库、CLI 或 SDK。这些 Skills 可以是针对内部库，也可以是针对 Claude Code 在使用常见库时遇到困难的库。它们通常包含一组参考代码片段，以及 Claude 在编写脚本时应避免的一些常见问题。

示例：

- billing-lib — 你的内部账单库：边缘情况、常见陷阱等
- internal-platform-cli — 你内部 CLI 包装器的每个子命令，并提供何时使用它们的示例
- frontend-design — 使 Claude 更好地理解你的设计系统

2\. 产品验证

这些 Skills 描述了如何测试或验证代码是否正常工作。它们通常与外部工具（如 Playwright、tmux 等）配合使用，以进行验证。

验证 Skills 对确保 Claude 输出正确非常有用。可能值得让工程师花一周时间，专注于提高验证 Skills 的质量。

考虑使用技术，例如让 Claude 记录它的输出视频，这样你就可以准确看到它测试了什么，或者在每个步骤上强制进行状态的程序化断言。这些通常通过在 Skills 中包含各种脚本来实现。

示例：

- signup-flow-driver — 在无头浏览器中运行注册 → 邮件验证 → 入职流程，并在每个步骤上进行状态断言
- checkout-verifier — 使用 Stripe 测试卡驱动结账界面，验证发票是否真正落入正确的状态
- tmux-cli-driver — 用于需要 TTY 的交互式 CLI 测试

3\. 数据抓取与分析

这些 Skills 连接到你的数据和监控系统。这些 Skills 可能包括库，用于通过凭证、特定的仪表盘 ID 等抓取数据，以及常见工作流或获取数据的方式说明。

示例：

- funnel-query — "我需要哪些事件来查看注册 → 激活 → 付费" 以及实际包含标准 user\_id 的表
- cohort-compare — 比较两个群体的留存率或转化率，标记统计显著的差异，链接到细分定义
- grafana — 数据源 UID、集群名称、问题 → 仪表盘查找表

4\. 业务流程与团队自动化

这些 Skills 将重复的工作流自动化为一个命令。虽然这些 Skills 通常是相对简单的指令，但可能有更复杂的依赖关系，涉及其他 Skills 或 MCP（多控制点）。

对于这些 Skills，将先前的结果保存在日志文件中有助于保持模型的一致性，并反映工作流的前期执行。

示例：

- standup-post — 汇总你的任务追踪器、GitHub 活动和 Slack 内容 → 格式化的站立会议，仅显示增量变化
- create--ticket — 强制执行模式（有效的枚举值、必填字段）以及创建后工作流（通知审阅者、在 Slack 中链接）
- weekly-recap — 合并的 PR + 关闭的票据 + 部署 → 格式化的周报

5\. 代码脚手架与模板

这些 Skills 用于生成代码库中特定功能的框架模板。你可以将这些 Skills 与可组合的脚本结合使用。它们在你的脚手架有自然语言要求，而这些要求无法仅通过代码覆盖时尤为有用。

示例：

- new--workflow — 使用你的注释脚手架一个新的服务 / 工作流 / 处理器
- new-migration — 你的迁移文件模板以及常见的坑
- create-app — 新的内部应用，预先配置你的认证、日志记录和部署

6\. 代码质量与审核

这些 Skills 强制执行你组织中的代码质量并帮助审查代码。它们可以包括确定性的脚本或工具，以确保最大程度的稳健性。你可能希望将这些 Skills 自动运行，作为钩子的一部分或 GitHub Actions 中的一部分。

示例：

- adversarial-review — 启动一个新鲜眼光的子智能体进行批评，实施修复，迭代直到反馈降级为小瑕疵
- code-style — 强制执行代码风格，特别是 Claude 默认处理不好的一些风格
- testing-practices — 关于如何编写测试以及需要测试什么的说明

7\. CI/CD 与部署

这些 Skills 帮助你在代码库内获取、推送和部署代码。这些 Skills 可能引用其他 Skills 以收集数据。

示例：

- babysit-pr — 监控 PR → 重试不稳定的 CI → 解决合并冲突 → 启用自动合并
- deploy- — 构建 → 烟雾测试 → 渐进式流量发布与错误率比较 → 回滚回退
- cherry-pick-prod — 隔离工作树 → 衍生选择 → 冲突解决 → 带模板的 PR

8\. 运行手册

这些 Skills 通过症状（如 Slack 线程、警报或错误签名），进行多工具调查，并生成结构化报告。

示例：

- \-debugging — 映射症状 → 工具 → 查询模式，适用于你最高流量的服务
- oncall-runner — 获取警报 → 检查常见问题 → 格式化结果
- log-correlator — 给定请求 ID，从可能涉及的所有系统中提取匹配的日志

9\. 基础设施操作

这些 Skills 执行常规的维护和操作程序，其中一些涉及需要有防护措施的破坏性操作。它们使工程师更容易遵循最佳实践，在关键操作中避免出错。

示例：

- \-orphans — 查找孤立的 pods/volumes → 发布到 Slack → 浸泡期 → 用户确认 → 级联清理
- dependency-management — 你组织的依赖审批工作流
- cost-investigation — "为什么我们的存储 / 出站流量账单突然飙升"，并提供具体的存储桶和查询模式

制作 Skills 的技巧

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

一旦你决定要制作某个 Skills，如何编写它呢？以下是我们总结的一些最佳实践、技巧和窍门。

我们最近还发布了 Skill Creator，使得在 Claude Code 中创建 Skills 变得更加容易。

相关链接：https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills

不要陈述显而易见的内容

Claude Code 已经了解很多关于你的代码库的信息，也了解很多编码的基础知识，包括许多默认的观点。如果你发布的 Skills 主要是关于知识的，尝试专注于那些能够让 Claude 脱离正常思维方式的信息。

示例：

前端设计 Skills 就是一个很好的例子 —— 它是由 Anthropic 的一位工程师通过与客户反复迭代，旨在提升 Claude 的设计品味，避免使用经典的设计模式（例如 Inter 字体和紫色渐变）。

相关链接：https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md

构建陷阱部分

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

在任何 Skills 中，Gotchas（常见陷阱）部分是最有价值的内容。这些部分应该基于 Claude 在使用 Skills 时遇到的常见失败点来构建。理想情况下，你应该随着时间的推移更新你的 Skills，捕捉这些常见问题，以确保 Skills 的有效性和准确性。

使用文件系统和渐进式披露

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

正如我们之前提到的，Skills 是一个文件夹，而不仅仅是一个 Markdown 文件。你应该将整个文件系统视为一种上下文工程和渐进式披露的方式。告诉 Claude 你的 Skills 包含哪些文件，它将在适当的时候读取它们。

渐进式披露的最简单形式是指向其他 Markdown 文件供 Claude 使用。例如，你可以将详细的函数签名和使用示例分离到 references/api.md 中。

另一个例子：如果你的最终输出是一个 Markdown 文件，你可以在 assets/ 文件夹中包括一个模板文件供 Claude 复制和使用。

你可以有多个文件夹来存储参考资料、脚本、示例等，这些都有助于 Claude 更有效地工作。

避免「束缚」 Claude

Claude 通常会尽量遵循你的指示，然而由于 Skills 的高度可复用性，你需要小心不要让指令过于具体。给予 Claude 必要的信息，同时也要留给它一定的灵活性以适应不同的情况。

例如：

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

思考 Skills 的设置

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

有些 Skills 可能需要用户提供上下文信息来完成设置。例如，如果你在制作一个将站立会议内容发布到 Slack 的 Skills，你可能希望 Claude 询问要发布到哪个 Slack 频道。

一种良好的做法是将这些设置的信息存储在 Skills 目录中的 config.json 文件中，如上例所示。如果配置尚未设置，智能体可以提示用户提供必要的信息。

如果你希望智能体呈现结构化的多选问题，可以指示 Claude 使用 AskUserQuestion 工具。

描述字段是给模型的

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

当 Claude Code 启动一个会话时，它会构建一个包含每个可用 Skills 及其描述的列表。这份列表是 Claude 用来决定「是否有 Skills 能解决这个请求？」的依据。因此，描述字段并不是 Skills 的总结，而是描述何时触发这个 Skills 的场景。

记忆与存储数据

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

有些 Skills 可以通过在其内部存储数据来实现一定的记忆功能。你可以将数据存储在简单的附加文本日志文件、JSON 文件，或者更复杂的 SQLite 数据库中。

例如：

一个 standup-post Skills 可能会保留一个 standups.log，记录每次发布的内容。这意味着下次运行时，Claude 可以读取自己的历史记录，并能够检测自昨天以来的变化。

需要注意的是，存储在 Skills 目录中的数据可能在 Skills 升级时被删除，因此你应当将数据存储在一个稳定的文件夹中。到目前为止，我们为每个插件提供了 ${CLAUDE\_PLUGIN\_DATA} 作为稳定存储数据的文件夹。

存储脚本与生成代码

提供代码是给 Claude 最强大的工具之一。将脚本和库交给 Claude，可以让它专注于组合和决策，而不是重新构建基础代码。

例如：

在你的数据科学 Skills 中，你可能有一组用于从事件源抓取数据的函数库。为了让 Claude 执行复杂的分析，你可以为它提供一套像这样的帮助函数：

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Claude 然后可以动态生成脚本，利用这些功能组合来执行更高级的分析，比如处理类似 「星期二发生了什么？」 这样的提示。

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

按需钩子（On Demand Hooks）

Skills 可以包括仅在 Skills 被调用时激活的钩子，并且这些钩子的作用仅持续到会话结束。这对于一些有强烈意见、但并不希望一直运行的钩子特别有用，它们在某些情况下会非常有价值。

例如：

- /careful — 通过 Bash 中的 PreToolUse 匹配器阻止 rm -rf、DROP TABLE、force-push、kubectl delete 等危险操作。你只希望在知道自己正在操作生产环境时才启用它，常开会让你疯狂。
- /freeze — 阻止在特定目录外的任何编辑 / 写入操作。非常有用，特别是当你想确保只有在特定文件夹中进行更改时才执行代码时。
- 调试时：「我想加日志，但我总是无意中‘修复’无关的内容。」 使用按需钩子，可以防止在不需要的情况下影响其他文件或代码片段。

这些钩子可以根据实际需要进行触发，而不是始终保持启用状态，从而避免不必要的干扰，同时在需要时提供强有力的功能。

Skills 分发

Skills 的最大优势之一是，你可以将它们与团队中的其他成员共享。

你有两种方式可以将 Skills 分享给别人：

1\. 将 Skills 检查到你的代码库中（在./.claude/skills 下）。

2\. 创建插件并拥有一个 Claude Code Plugin 市场，用户可以在其中上传和安装插件（有关更多信息，请参阅文档 https://code.claude.com/docs/en/plugin-marketplaces）。

对于在相对较少的代码库中工作的较小团队，将 Skills 检查到代码库中是一个不错的选择。但每个被检查进来的 Skills 都会增加一些模型的上下文。当团队规模扩大时，内部插件市场可以帮助你分发 Skills，并让团队成员决定哪些 Skills 需要安装。

管理市场

如何决定哪些 Skills 进入市场？人们如何提交它们？

我们没有一个集中式的团队来做决定；相反，我们尝试通过自然的方式找到最有用的 Skills。如果你有一个 Skills 想让大家尝试，你可以将它上传到 GitHub 的沙箱文件夹，并通过 Slack 或其他论坛将链接分享给大家。

当一个 Skills 获得一定的关注度（由 Skills 拥有者决定）后，他们可以提交一个 PR，将其移入市场。

警告：创建不必要的或冗余的 Skills 是非常容易的，因此在发布之前，确保你有一个筛选和策划的方法非常重要。

组合 Skills

你可能希望有一些 Skills 相互依赖。例如，你可能有一个文件上传 Skills，它上传文件；还有一个 CSV 生成 Skills，它生成 CSV 并上传文件。这类依赖管理目前在市场或 Skills 中并没有内建功能，但你可以直接通过名称引用其他 Skills，如果它们已被安装，模型会调用它们。

衡量 Skills 的效果

为了了解一个 Skills 的表现，我们使用了 PreToolUse 钩子，允许我们记录公司内 Skills 的使用情况（代码链接：https://gist.github.com/ThariqS/24defad423d701746e23dc19aace4de5）。

这意味着我们可以发现哪些 Skills 比较受欢迎，哪些 Skills 的触发率低于我们的预期。

结论

Skills 是极其强大且灵活的智能体工具，但目前仍处于早期阶段，我们还在不断摸索如何最好地使用它们。

可以将这篇文章看作是我们在使用过程中积累的一些有用提示，而非权威指南。理解 Skills 的最佳方式是开始实践，进行实验，看看什么最适合你。

我们的大多数 Skills 最初只是一行代码和一个「Gotcha」，随着 Claude 遇到新的边界情况，大家会不断进行完善。

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

© THE END

转载请联系本公众号获得授权

投稿或寻求报道：liyazhou@jiqizhixin.com

AI产业动态 · 目录

继续滑动看下一个

机器之心

向上滑动看下一个
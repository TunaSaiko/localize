# 冒烟测试样本

`source.zh.md`（8 行中文）与 `target.ja.md`（8 行日语，故意埋了错）。下表的行号是文件行号（第 1 行是标题）；`bilingual.md` 只收正文，它的 L1 对应这里的 L2。改 skill 或脚本后重跑，对照下表。

## 埋的错与期望

| 行 | 埋的错 | 期望由谁抓 | 期望级别 |
|---|---|---|---|
| L2 | 「已」「纯」「合作伙伴」三个限定词丢失 | 双语遍（信息颗粒） | major |
| L2 | 中黑用 U+00B7 | char_lint | minor |
| L3 | 收取→支払い（方向反了） | 双语遍 | critical |
| L3 | ¥ 原样保留（源文是人民币，译文读成日元） | fact_check（符号计数 + 「人民币」源1译0）+ 双语遍 | critical |
| L4 | 传闻→報じられている（确定性上调）；计划→将 | 双语遍 | major（提案材料 critical） |
| L5 | 转售→転売（假朋友，强负面） | 双语遍（语对包）+ 单语遍（褒贬） | major |
| L6 | ASCII ~ | char_lint | minor |
| L7 | 否定丢失，免责变承诺 | 双语遍（功能性文本） | critical |
| L8 | URL 擅自加 /ja/ 路径 | fact_check + 双语遍 | major（若路径不存在 critical） |
| 全篇 | 空格策略：JTF 下 7 处有空格 | char_lint 一致性计数 | minor（只求统一） |

### Markdown 文档型 fixture（`markdown-document.md`）

这份 fixture 专门防止 Joplin 暴露的格式误报：

| 行/场景 | 期望 |
|---|---|
| 表头 `id/source/target` | 不进入数据行统计 |
| 源文和译文都保留对应的 `**...**` | `deliverable_check` 不报 |
| 译文新增 `**...**`，源文没有 | `deliverable_check` 必报 |
| 链接目标里的 URL、点、括号、查询参数 | `distribution_check` / `char_lint` 不当正文符号 |
| 正文实际使用半角括号 | `char_lint` 仍报 |

## 脚本命令

```bash
cd ~/.claude/skills/localize/evals/smoke
S=~/.claude/skills/localize/scripts
python3 $S/fact_check.py source.zh.md target.ja.md
python3 $S/char_lint.py target.ja.md --locale ja-JP --space jtf
python3 $S/length_estimate.py source.zh.md target.ja.md --max-em 30
python3 $S/distribution_check.py bilingual.md --src-col 1 --tgt-col 2 --source-locale zh-CN --target-locale ja-JP
python3 $S/deliverable_check.py markdown-document.md --target-locale ja-JP --source-locale en-US --src-col 1 --tgt-col 2
python3 $S/distribution_check.py markdown-document.md --src-col 1 --tgt-col 2 --source-locale en-US --target-locale ja-JP
python3 $S/char_lint.py markdown-document.md --locale ja-JP --space ms --tgt-col 2
```

2026-09-03 首跑结果：fact_check 抓到 ¥ 保留、「人民币」丢失、URL 路径差异；char_lint 抓到 U+00B7、ASCII ~、空格 7 处；length 总宽度比 1.57。

## 2026-09-03 子 agent 首跑结果

- **双语遍（模板 B）**：发现 14 条，句数 源 8 / 译 8。埋的 9 处错全部命中：限定词 ×3（B-01/02/03）、U+00B7（B-04）、方向（B-05）、¥ 系统性（B-06）、确定性 ×2（B-07/08）、転売（B-10，并正确排除了二手车例外）、~（B-12）、免责否定丢失（B-13）、URL 路径（B-14）。额外报了「某」丢失（B-09）和「自行→自由に」（B-11），均合理。格式完全符合模板。
- **单语遍（模板 A）**：发现 19 条（头部误写 18）。在看不到源文的情况下，凭日本投资材料定型句抓到免责反转（A-17）、凭行业惯例抓到资金方向可疑（A-07）、転売 褒贬（A-14）、サービス料／加盟店 行话与同形词（A-08/09）、ローンチ 外来语语体（A-11）、谦让语缺失（A-18）、空格不统一（A-19）、标题与内容性质不符（A-01）。
- **教训**：主对话必须自己数条目数，头部计数只做校验（已写入 subagent-prompts.md §1）。
- **当时未做**：怀疑论者复核（模板 C）和 translate 入口（模板 D）这次冒烟没跑；两者之后都在真实材料上跑过。

## adapt/ 子目录（授权门与多对多事实映射）

3 句中文源文 → 2 段日语重构稿，**故意做成 3 源单元 → 2 目标单元的 2→1 合并**：单元数不等本身不是错，
是检验「N≠M 不等于漏译」这条合同的最小样本。事实账本 3 条、非空颗粒 19 个、落地表 19 行。

```bash
cd ~/.claude/skills/localize/evals/smoke/adapt
S=~/.claude/skills/localize/scripts
python3 $S/adapt_check.py gate --authorization authorization.md --structure structure-options.md \
  --conventions market-conventions.md --map adapt-map.md          # 期望 exit 0
python3 $S/adapt_check.py map --source source.zh.md --ledger fact-ledger.md --map adapt-map.md \
  --draft draft.ja.md --authorization authorization.md --glossary glossary.md   # 期望 exit 0，1 条 warn
```

正例之外的**反例不另存副本**，由 `evals/test_adapt_checks.py` 从这份样本变异生成
（删否定从句、换受益人、抽掉落地表某行、改账本哈希、加/减数字……）。
这样只有一份事实来源；样本一改而变异串对不上，测试会直接报「正例样本已漂移」，不会静默失效。
那条 warn 是故意留的：`导出次数` 在术语表里没有定译，脚本**如实说明这一条只验了落地、没验所指**。

`market-conventions.two-table.md` 是第二种惯例文件形状（样本单列一张表、惯例行引用 `S` 编号），
由 Joplin 真实材料逼出来——单表式记不下「原生/翻译」和「可否作依据」两栏。
脚本两种形状都认；测试覆盖「只引用了被判❌的翻译产物样本 → 仍算没有样本」。

## locales/ 子目录

四个 locale 的 char_lint 小样本（zh-CN / zh-TW / en-US / en-GB），2026-09-03 全部跑通；未知 locale（de-DE）走降级路径只跑通用检查。

## deliverable_check 冒烟

`bilingual.md` 由 source.zh.md 与 target.ja.md 按行合成。跑：
```bash
python3 ~/.claude/skills/localize/scripts/deliverable_check.py bilingual.md \
  --target-locale ja-JP --source-locale zh-CN --src-col 1 --tgt-col 2
```
`deliverable_check` 只查交付格式类问题（源文残留、占位、标签、占位符、空译文），这份样本在这几类上是干净的，预期"未发现问题"；埋的其他错由别的脚本和审校遍负责。列位指错时脚本会报「列位可能指错了」并打印实际列布局，不会刷屏。

## 自动化回归（2026-09-16）

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s ~/.claude/skills/localize/evals -p 'test_*.py' -v      # 25 markdown + 32 adapt = 57
```

`markdown-document.md` 的 deliverable 预期退出码为 **1**：L2 是故意新增强调，必须报出。其余 CLI 成功/解析失败的退出码由自动断言检查，不用管道的最后一个命令代替脚本退出码。
自动用例另覆盖链接文字中真括号、嵌套 URL 括号、转义/代码中的管道、en-US/en_GB、版本与扩展名、金额与「復元」、旧中文/日语表、空输入与错误列号。
注意：这里只提供常见 Markdown 的受限解析，不是完整 CommonMark；强调数量/标记类型一致不能证明强调对象没被改义。

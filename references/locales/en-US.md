# Locale 包：en-US（美国英语）

状态：**种子包**。

## 1. 样式表默认值

| 项目 | 默认 | 依据 |
|---|---|---|
| 拼写 | American（color, organize, center） | Google style："Use standard American spelling" |
| 序列逗号 | **用**（a, b, and c） | Microsoft Writing Style Guide Top 10 tips 第 8 条 "Remember the last comma" |
| 引号内外标点 | 句号逗号在引号**内**：Click "Edit Profile." | Microsoft en-US |
| 日期 | September 3, 2026；数字式 09/03/2026（歧义，对外材料避免） | |
| 时间 | 2:00 PM / 14:00 | |
| 数字 | 1,000.50；million / billion / trillion | |
| 货币 | $1,200（前置）；多币种时 US$ / USD | |
| 单位 | 英制为主（含公制并记） | |
| 姓名 | 名 姓；东亚人名按本人英文习惯，全篇一致 | |
| 电话 | (212) 555-0100 / 212-555-0100 | |
| 语气 | Microsoft："warm and relaxed, crisp and clear, ready to lend a hand" | |
| 缩写 | 首次出现展开 | |

## 2. 中/日译英的典型症状

见 `pairs/zh-en.md`（Pinkham 两类：多余的词、句子结构）和 `pairs/ja-en.md`（Knight 五缺：冠词、单复数、主语、时态、一致）。

## 3. 权威出处

| 名称 | URL | 备注 |
|---|---|---|
| Microsoft Writing Style Guide | https://learn.microsoft.com/en-us/style-guide/welcome/ | 免费 |
| Microsoft Global communications（面向可译性的写法） | https://learn.microsoft.com/en-us/style-guide/global-communications/writing-tips | |
| Google developer documentation style guide | https://developers.google.com/style | CC BY 4.0 |
| Apple Style Guide | https://support.apple.com/guide/applestyleguide/welcome/web | 注意 `help.apple.com/applestyleguide/` 是空壳 |
| Chicago Manual of Style 第 18 版 | https://www.chicagomanualofstyle.org/home.html | 付费 |
| Plain language | https://digital.gov/guides/plain-language | `plainlanguage.gov` 已迁移，完整版在 GitHub 归档 |
| ISO 24495-1:2023 Plain language | https://www.iplfederation.org/iso-standard/ | 付费 |

## 4. 与 char_lint.py 的对应

`--locale en-US`：报连续空格、标点前空格、直引号与弯引号混用计数、全角 ASCII、-ise 拼写计数（提示 en-GB 混入）。序列逗号无法可靠自动判，人工。

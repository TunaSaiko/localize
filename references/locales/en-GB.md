# Locale 包：en-GB（英国英语）

状态：**种子包**。

## 1. 样式表默认值（与 en-US 的差异）

| 项目 | en-GB | 依据 |
|---|---|---|
| 拼写 | colour, organise（或 -ize 牛津拼写，`en-GB-oed` 已注册），centre, programme（非软件） | RFC 5646 |
| 序列逗号 | **不用**：Microsoft en-GB "There should be no comma before the final 'and'" | Microsoft en-GB 指南（46 页） |
| 引号内外标点 | 句号在引号**外**：Click "Edit Profile". | Microsoft en-GB |
| 日期 | 3 September 2026（无逗号）；数字式 03/09/2026 | GOV.UK style guide |
| 介词 | Monday to Friday（非 through）；call us on（非 at）；different to/from（非 than） | Microsoft en-GB |
| 货币 | £1,200；GBP | |
| 单位 | 公制为主 | |
| 斜体 | GOV.UK："Do not use italics." | GOV.UK |

**关键**：同厂商同语言相反规则（序列逗号、引号标点），只做 -ise/-ize 替换永远发现不了。en-US 与 en-GB 必须作为两个 locale。

## 2. 权威出处

| 名称 | URL |
|---|---|
| Microsoft en-GB Localization Style Guide | https://learn.microsoft.com/en-us/globalization/reference/microsoft-style-guides （`eng-gbr-StyleGuide.pdf`） |
| GOV.UK style guide | https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/style-guides/ （旧 `gov.uk/guidance/style-guide` 已 301） |
| RFC 5646 / BCP 47 | https://www.rfc-editor.org/rfc/rfc5646.txt |
| CLDR en_001 设计说明 | https://cldr.unicode.org/development/development-process/design-proposals/english-inheritance |

## 3. 与 char_lint.py 的对应

`--locale en-GB`：同 en-US，另报 -ize/-ise 计数（提示混用）和 "Month D, YYYY" 型日期（提示 en-US 格式混入）。

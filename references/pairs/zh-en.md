# 语对包：zh → en（中文 → 英语）

状态：**种子包**。来源：Joan Pinkham《The Translator's Guide to Chinglish》的公开摘要（香港公务员事务局）、Microsoft Global communications 指南（反向使用）、模型知识；**未逐条核验出处**。目标 locale 必须先定（en-US / en-GB）。

## 1. 本方向的捷径

**词对词 + 中文语序。** 每个中文词都找一个英文词对上，句子结构原样保留。产出的英语语法正确但冗余、名词堆砌、缺主语、时态飘。

## 2. Pinkham 的两大类

来源：https://www.csb.gov.hk/hkgcsb/ol/news/no34/p04_8.pdf （"Chinglish features are grouped under two broad categories, namely unnecessary words and incorrect sentence structure"；"unnecessary words the hallmark of Chinglish"）

**A. 多余的词（the hallmark of Chinglish）**
| 类型 | 例 | 改 |
|---|---|---|
| 多余的名词/动词 | accelerate the pace of reform | accelerate the reform |
| 范畴词 | the work of planning / the problem of unemployment | planning / unemployment |
| 多余的修饰语 | actual fact / serious chaos / new innovation / final completion / advance planning | fact / chaos / innovation / completion / planning |
| 同义重复 | help and assist / views and opinions | help / views |
| 重复说同一件事 | 前后两句意思相同 | 删一句 |
| 弱动词 + 名词 | make an improvement in / carry out the task of | improve / do |

**B. 句子结构**
| 类型 | 例 | 改 |
|---|---|---|
| 名词瘟疫 | the realization of the modernization of | modernize |
| 无主句 | 应加强管理 | We must strengthen… / Management must be strengthened（选主语） |
| 话题-述题 → 主谓 | 这个问题，我们已经讨论过 | We have discussed this issue |
| 长前置定语 | 由…提供的、经…认证的、面向…的产品 | 后置从句或拆句 |
| 逻辑连接词泛滥 | 因此/然而/此外 每句都译 | 删或合并 |
| 四字格 | 求真务实、开拓创新 | 一个词或一个短语，或删 |
| 「相关」「有关」「进行」「开展」 | relevant / related / carry out | 常删 |

## 3. 必须决定的四样东西

时态、单复数、冠词、主语（中文都不显式标记）。决定后全篇一致，写进 `decisions.md`。

## 4. 数字与格式

- 万→10,000；亿→100 million；兆（万亿）→trillion；换算时用逗号分节。
- 人民币：RMB / CNY / ¥ 要标明；`¥` 单独出现在英文语境会被读成日元。
- 日期：en-US "September 3, 2026"；en-GB "3 September 2026"。
- 姓名顺序：中文姓前名后；英文材料按人物本人的英文习惯（Li Wei / Wei Li），全篇一致，必要时姓大写。
- 公司名：用注册英文名；法人后缀（Co., Ltd.）保留。

## 5. 常见误译词

| 中文 | 常见直译 | 更常见的英语 |
|---|---|---|
| 落地 | land | implement / roll out |
| 赋能 | empower | enable / support |
| 抓手 | grip / handle | lever / entry point |
| 打造 | build / create | develop / establish（或删） |
| 沉淀 | precipitate | accumulate / consolidate |
| 闭环 | closed loop | end-to-end / full cycle（商业语境） |
| 生态 | ecology | ecosystem |
| 领导 | leader | management / executives（按语境） |
| 单位 | unit | organization / employer |
| 宣传 | propaganda | publicity / promotion / communications |

## 6. 验证资源

- Pinkham 摘要：https://www.csb.gov.hk/hkgcsb/ol/news/no34/p04_8.pdf
- Microsoft Global communications（源文可译性写法，反向用作英语目标的清晰标准）：https://learn.microsoft.com/en-us/style-guide/global-communications/writing-tips
- Google style：https://developers.google.com/style
- 目标 locale 包：`locales/en-US.md` / `en-GB.md`

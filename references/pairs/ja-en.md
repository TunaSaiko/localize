# 语对包：ja → en（日语 → 英语）

状态：**种子包**。来源：Knight et al. 1995、JAT 翻译比赛评委讲评、Microsoft/Google 英文风格指南、模型知识；**未逐条核验出处**。目标 locale 必须先定（en-US / en-GB）。

## 1. 本方向的捷径

**逐句对应。** 保留日语的句子边界、信息顺序和省略习惯，英语读起来冗长、缺主语、缺冠词、时态飘。另一条并行捷径：把片假名外来语"还原"成英文原词（プログラム→program 而不是 computer programs；メリット→merit 而不是 benefit）。

## 2. 必须"凭空发明"的五样东西

Knight et al. 1995（https://arxiv.org/abs/cmp-lg/9506009 ）原文：日语 "no articles (a, an, the), no overt singular or plural marks, no agreement constraints, omitted subjects, no marked future tense"。日→英时每句都要决定：
1. **冠词** a / the / 零冠词
2. **单复数**
3. **主语**（是谁？我们、用户、系统、还是被动）
4. **时态**（日语「〜する」可能是现在、将来、习惯）
5. **一致**（主谓、代词）

决定后全篇一致，写进 `decisions.md`。

## 3. 定型句与敬语不直译

| 日语 | 直译（错） | 英语原生 |
|---|---|---|
| お世話になっております | We are indebted to you | （商务邮件开头省略，或 Thank you for your continued support 视语境） |
| よろしくお願いいたします | Please treat me well | Thank you. / Best regards. / We look forward to working with you. |
| 〜させていただきます | We will humbly do | We will… |
| ご確認ください | Please confirm | Please review / Please check |
| 検討します | We will consider | We'll look into it（注意：日语里常是委婉拒绝，译时保持中性不上调） |
| 弊社／当社 | our humble company | we / [公司名] |
| 〜と思われます | It is thought that | 直接陈述，或 We believe |
| など | etc.（每次） | JAT 评委：不必每个 など 都译；用 such as / including，或省 |

## 4. 片假名不要"还原"

| 片假名 | 直接还原（常错） | 英语应是 |
|---|---|---|
| メリット／デメリット | merit / demerit | benefit / drawback（advantage / disadvantage） |
| クレーム | claim | complaint |
| アンケート | enquete | survey / questionnaire |
| サービス（无料） | service | complimentary / free |
| プログラム | program | computer programs / software（JAT 讲评） |
| リストラ | restructuring | layoffs |
| マンション | mansion | apartment / condominium |
| スマート | smart | slim / stylish |

## 5. 句法

- 名詞止め（标题体）→ 英语用动词或完整句。
- 长句拆分：日语一句常拆成英语两三句；主题（は）不等于主语。
- 「〜性」「〜化」名词化 → 动词或形容词（効率化→improve efficiency，not "efficiency-ization"）。
- 被动「〜される」→ 英语常改主动。
- 数字：億→100 million / 0.1 billion；兆→trillion；确认单位换算与逗号。
- 日期：和暦→公历；YYYY年M月D日 → en-US "September 3, 2026" / en-GB "3 September 2026"。

## 6. Japanglish 常见症状

冗余（"in order to be able to"）、过度礼貌（"kindly", "humbly"）、"we think that…" 泛滥、逻辑连接词每句都有（however / therefore / in addition）、缺冠词、单复数随机、"etc." 泛滥。

## 7. 验证资源

- JAT 评委讲评：https://jat.org/news/twentieth_annual_jat_contest_commentaries_from_the_judges_part_3
- Microsoft Writing Style Guide（en-US）：https://learn.microsoft.com/en-us/style-guide/welcome/
- Microsoft en-GB 本地化指南：`eng-gbr-StyleGuide.pdf`（https://learn.microsoft.com/en-us/globalization/reference/microsoft-style-guides ）
- Google developer documentation style guide：https://developers.google.com/style
- 目标 locale 包：`locales/en-US.md` / `en-GB.md`

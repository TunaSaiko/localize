# Locale 包：zh-TW（台湾・繁体中文）

状态：**种子包**。

## 1. 样式表默认值

| 项目 | 默认 | 依据 |
|---|---|---|
| 引号 | 「」，嵌套『』（**先单后双，与大陆相反**） | 教育部《重訂標點符號手冊》修訂版（2008） |
| 标点 | 全角，置中（台湾排版习惯标点居中，字体决定） | 同上 |
| 省略号 | …… | 同上 |
| 连接号 | －、～ | 同上 |
| 数字 | 阿拉伯数字半角；公文可用国字 | |
| 日期 | 商务：西元 2026年9月3日；公文：民國115年9月3日 | |
| 货币 | 新台幣 / NT$ / 元 | |
| 中英空格 | 开关，全篇统一 | 同 zh-CN 逻辑 |
| 术语 | 用台湾通行词（軟體、伺服器、影片、網路、資料、程式） | 两岸差异库 |

## 2. 两岸用词差异

- 中華語文知識庫「兩岸差異用詞」：**4,814 组**，分 同實異名／同名異實／臺灣特有／大陸特有，免费免登录，**有可用 JSON 接口**（实测）：https://www.chinese-linguipedia.org/search_difference.html
- Microsoft zh-TW 指南（`zho-twn`，62 页）：https://aka.ms/chinese-traditional-styleguide
- 繁简转换陷阱：「軟體動物」误转「软件动物」（軟體→软件规则误触发）；「打斗」未转「打鬥」。参考：https://zh.wikipedia.org/wiki/Wikipedia:字词转换 。**不能靠转换表做本地化。**

## 3. 权威出处

| 名称 | URL |
|---|---|
| 重訂標點符號手冊 修訂版（教育部） | https://language.moe.gov.tw/001/upload/files/site_content/m0001/hau/Revised_Handbook_of_Punctuation.pdf |
| Microsoft zh-TW Style Guide | https://aka.ms/chinese-traditional-styleguide |
| 中華語文知識庫 | https://www.chinese-linguipedia.org/search_difference.html |

## 4. 与 char_lint.py 的对应

`--locale zh-TW`：同 zh-CN 规则，但 “” 出现记为 note（建议「」），「」不报。

## 5. zh-HK

不能用 zh-TW 套用：词汇更近大陆（網絡／短片），标点参照 GB/T 15834，Microsoft 无 zh-HK 指南。需要单独建包，目前**无包**，降级运行。

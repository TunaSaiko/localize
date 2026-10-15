# localize

Claude Code skill：把材料本地化到另一个语言市场，或审校已有译文。

不是"把 A 语言换成 B 语言"。是先把 A 还原成意思，再用 B 重新写一遍。
它的价值不在产出通顺的译文，模型本来就会；在于**抓住"通顺但错"的句子**，
并把每次判断沉淀成能复用的术语表、样式表和待确认清单。

## 安装

需要：`python3`（脚本只用标准库，不用装依赖）。

**Claude Code**

```bash
git clone https://github.com/TunaSaiko/localize.git ~/.claude/skills/localize
```

装完重开 Claude Code，说「帮我审校这份日语翻译」「把这份材料本地化成日语」之类的话，它会自动启用。

**Codex**

```bash
git clone https://github.com/TunaSaiko/localize.git ~/.agents/skills/localize
```

**更新**：进到上面的目录里跑 `git pull`。

文档里的示例命令按 `~/.claude/skills/localize` 写；装在别处时，把命令里的这段路径换成你的实际位置。skill 自己运行时会自动识别所在位置，不受影响。

## 怎么用

看 [USAGE.md](USAGE.md)。写给使用者的，不是给模型的。

## 三个入口

| 入口 | 什么时候用 | 产出 |
|---|---|---|
| `review` 审校 | 有源文、有译文 | 发现清单，不改你的文件 |
| `translate` 翻译 | 只有源文 | 译文 + 独立自审报告 |
| `adapt` 重构 | 作者明确授权按目标市场重写结构与体裁 | 重构稿 + 事实映射账本，不改事实和承诺 |

## 里面是什么

| 位置 | 作用 |
|---|---|
| `SKILL.md` | 内核：铁律、三个入口、严重度尺度、八道闸门 |
| `references/diagnostics.md` | 判断标准：三步法、五类只有双语对照才能发现的错误、表述强度两分法 |
| `references/severity-and-report.md` | 严重度定义、错误与偏好之分、报告格式 |
| `references/material-types.md` | 七类材料各自的风险重心、i18n 层、法规触发 |
| `references/pairs/` | 语对包。`zh-ja` 最扎实，其余五个方向是种子包 |
| `references/locales/` | 地区写法：ja-JP / zh-CN / zh-TW / en-US / en-GB |
| `scripts/` | 事实层检查（数字、日期、货币、URL、字符规范），stdlib only |
| `templates/` | 术语表、样式表、待确认清单、报告等模板 |
| `evals/` | 冒烟样本与自动测试：`cd evals && python3 -m unittest discover -p 'test_*.py'` |

## 验证到什么程度

- `review` 和 `translate`：在真实材料上做过回归测试和日本母语者盲测。
- `adapt`：机检闸门、对抗性篡改测试、独立审校通过；作者验收、真人任务测试、母语者通读尚未做，**不宣称通过**。

除 `zh-ja` 外，其余语对包是种子包，内容自身标着「未逐条核验出处」。

文中「实测」案例均来自真实项目，已脱敏：项目与产品不具名；引语、票数和统计数字是原始记录；标了「示意」的词例是替换过的。

**母语者终审替代不了。** 这条写死在内核里，任何自动化结果都不是上线许可。

## 许可证

[MIT](LICENSE) © 2026 TunaSaiko：可以自由使用、修改、转发、商用，保留署名即可。

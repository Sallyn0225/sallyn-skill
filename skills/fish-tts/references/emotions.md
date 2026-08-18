# Fish Audio 情绪与语气控制参考

> 来源：https://docs.fish.audio/developer-guide/core-features/emotions
> Fish Audio 模型支持 64+ 种情绪表达与语音风格，通过文本中的标记控制。
> 本文件是完整参考；日常使用看 SKILL.md 的「情绪与语气控制」一节即可。

## 目录

1. 工作原理与语法（S2 vs S1）
2. 基础情绪（24 种）
3. 高级情绪（25 种）
4. 语气标记（6 种）
5. 音效标记（11 种）
6. 特效标记
7. 放置规则
8. 进阶技巧（组合 / 过渡 / 背景音 / 强度修饰）
9. 语言支持
10. 最佳实践
11. 常见用法场景
12. 排错
13. 速查表（强度梯度 / 常见组合）

---

## 1. 工作原理与语法（S2 vs S1）

在文本里插入情绪/风格标记，模型会据此调整语音。**不同模型族语法不同，这是最容易踩坑的地方：**

| 模型族 | 语法 | 标签集 | 示例 |
|---|---|---|---|
| **S2 系列**（`s2.1-pro` / `s2.1-pro-free` / `s2-pro`） | `[方括号]` | **自由自然语言**，不限于固定标签 | `[happy]`、`[高兴]`、`[very excited and out of breath]` 都可 |
| **S1**（`s1`） | `(圆括号)` | **固定英文标签集**，见下表 | `(happy)`、`(sad)`、`(angry)` |

关键区别：

- **S2 用方括号且接受自由自然语言描述**。你可以写 `[happy]`，也可以写 `[非常激动，上气不接下气]` 这样的自由描述（中英文皆可）。标签不限于下表列出的固定集合。
- **S1 用圆括号且必须是固定的英文标签**（happy、sad、angry…），不能用中文 `(高兴)`，也不是自由描述。
- 因此：想用情绪控制又想用中文标签、自由描述，请用 S2 系列 + 方括号；只有用 s1 时才用圆括号英文标签。

> ⚠️ 旧版资料里常见的 `今天天气真不错(高兴)` 是**不可靠**的——`(高兴)` 不在 S1 固定英文标签集里。s1 的正确写法是 `今天天气真不错(happy)`；想要中文情绪描述请用 S2 系列：`今天天气真不错[高兴]`。

---

## 2. 基础情绪（24 种）

S2 写 `[tag]`，S1 写 `(tag)`（S1 必须用下列固定英文标签）。

| 情绪 | 标签 | 说明 | 适用场景 |
|---|---|---|---|
| Happy | `happy` | 开心、轻快 | 好消息、问候 |
| Sad | `sad` | 忧郁、低落 | 同情、坏消息 |
| Angry | `angry` | 愤怒、攻击 | 投诉、警告 |
| Excited | `excited` | 兴奋、热情 | 公告、庆祝 |
| Calm | `calm` | 平和、放松 | 指引、冥想 |
| Nervous | `nervous` | 紧张、不安 | 免责、道歉 |
| Confident | `confident` | 自信、笃定 | 演讲、销售 |
| Surprised | `surprised` | 惊讶、震惊 | 反应、发现 |
| Satisfied | `satisfied` | 满意、满足 | 确认、评价 |
| Delighted | `delighted` | 非常开心、喜悦 | 庆祝、赞美 |
| Scared | `scared` | 害怕、恐惧 | 警告、恐怖故事 |
| Worried | `worried` | 担心、忧虑 | 顾虑、提问 |
| Upset | `upset` | 烦躁、不安 | 投诉、问题 |
| Frustrated | `frustrated` | 气馁、无奈 | 技术故障、延误 |
| Depressed | `depressed` | 极度悲伤、绝望 | 严肃话题 |
| Empathetic | `empathetic` | 共情、关怀 | 安慰、咨询 |
| Embarrassed | `embarrassed` | 尴尬、难堪 | 道歉、失误 |
| Disgusted | `disgusted` | 厌恶、反感 | 负面评价 |
| Moved | `moved` | 感动 | 肺腑之言 |
| Proud | `proud` | 自豪、有成就感 | 成就、表扬 |
| Relaxed | `relaxed` | 轻松、随意 | 闲聊 |
| Grateful | `grateful` | 感激、感恩 | 致谢 |
| Curious | `curious` | 好奇、感兴趣 | 提问、探索 |
| Sarcastic | `sarcastic` | 讽刺、嘲弄 | 幽默、批评 |

## 3. 高级情绪（25 种）

| 情绪 | 标签 | 说明 | 适用场景 |
|---|---|---|---|
| Disdainful | `disdainful` | 鄙夷、不屑 | 批评、拒绝 |
| Unhappy | `unhappy` | 不满、不悦 | 投诉、反馈 |
| Anxious | `anxious` | 非常焦虑、不安 | 紧急事项 |
| Hysterical | `hysterical` | 歇斯底里、失控 | 极端反应 |
| Indifferent | `indifferent` | 漠不关心、中立 | 中性回应 |
| Uncertain | `uncertain` | 不确定、存疑 | 推测、提问 |
| Doubtful | `doubtful` | 怀疑、质疑 | 不信、质问 |
| Confused | `confused` | 困惑、茫然 | 请求澄清 |
| Disappointed | `disappointed` | 失望、未达预期 | 期望落空 |
| Regretful | `regretful` | 后悔、懊悔 | 道歉、失误 |
| Guilty | `guilty` | 内疚、有责任 | 坦白、道歉 |
| Ashamed | `ashamed` | 深感羞愧 | 严重失误 |
| Jealous | `jealous` | 嫉妒、怨恨 | 比较 |
| Envious | `envious` | 羡慕、渴望 | 带渴望的欣赏 |
| Hopeful | `hopeful` | 抱有希望 | 未来计划 |
| Optimistic | `optimistic` | 乐观 | 鼓励 |
| Pessimistic | `pessimistic` | 悲观 | 警告、疑虑 |
| Nostalgic | `nostalgic` | 怀旧、追忆 | 回忆、故事 |
| Lonely | `lonely` | 孤独、寂寞 | 情感内容 |
| Bored | `bored` | 无聊、厌倦 | 不感兴趣 |
| Contemptuous | `contemptuous` | 蔑视 | 强烈批评 |
| Sympathetic | `sympathetic` | 同情 | 哀悼 |
| Compassionate | `compassionate` | 深切关怀 | 支持、帮助 |
| Determined | `determined` | 坚决、果断 | 目标、承诺 |
| Resigned | `resigned` | 认命、无可奈何 | 放弃、接受 |

## 4. 语气标记（6 种）

这些不是情绪，而是控制**音量/强度/重音**。可放在文本任意位置；`[emphasis]` 放在要重读的词或短语前面。

| 语气 | 标签 | 说明 | 适用场景 |
|---|---|---|---|
| Hurried | `in a hurry tone` | 急促、仓促 | 时间紧迫信息 |
| Shouting | `shouting` | 大声、呼喊 | 引起注意 |
| Screaming | `screaming` | 极大声、惊恐 | 紧急、恐惧 |
| Whispering | `whispering` | 极轻、耳语 | 秘密、安静场景 |
| Soft | `soft tone` | 轻柔、温和 | 安抚、摇篮曲 |
| Emphasis | `emphasis` | 重读某词/短语 | 强调关键词 |

## 5. 音效标记（11 种）

加入自然人声效果，建议在标记后跟上对应的拟声文字。

| 音效 | 标签 | 说明 | 建议配文 |
|---|---|---|---|
| Laughing | `laughing` | 大笑 | Ha, ha, ha |
| Chuckling | `chuckling` | 轻笑 | Heh, heh |
| Sobbing | `sobbing` | 大哭 | （可省略配文） |
| Crying Loudly | `crying loudly` | 剧烈哭泣 | （可省略配文） |
| Sighing | `sighing` | 叹气（如释重负/无奈） | sigh |
| Groaning | `groaning` | 呻吟、懊恼 | ugh |
| Panting | `panting` | 喘气 | huff, puff |
| Gasping | `gasping` | 倒吸凉气 | gasp |
| Yawning | `yawning` | 打哈欠 | yawn |
| Snoring | `snoring` | 打鼾 | zzz |
| Clear Throat | `clear throat` | 清嗓子 | ahem |

> 不加标签时，也可以直接用自然拟声表达，例如 "Ha,ha,ha" 表示笑声。

## 6. 特效标记

用于营造氛围与环境：

| 特效 | 标签 | 说明 |
|---|---|---|
| Audience Laughter | `audience laughing` | 观众笑声 |
| Background Laughter | `background laughter` | 背景笑声 |
| Crowd Laughter | `crowd laughing` | 大群人笑声 |
| Short Pause | `break` | 短暂停顿 |
| Long Pause | `long-break` | 长停顿 |

---

## 7. 放置规则

**S2 系列：**
- 句子级情绪标记一般放在**句首**效果最好。
- 语气控制标记可放在文本任意位置。
- 音效标记可放在文本任意位置。
- 方括号内可写自然语言描述，不限于固定标签集。

**通用要点：**
- 把标记放在该情绪/效果应当**开始**的位置。
- 句子级情绪标记不要离它要控制的句子太远。

---

## 8. 进阶技巧（组合 / 过渡 / 背景音 / 强度修饰）

### 组合效果

可叠加多个情绪，形成复杂表达（建议每句不超过 3 个组合情绪）：

```
[angry][shouting] 停下！
[nervous][uncertain] 你确定要这样做吗？
```

### 情绪过渡

构造自然的情绪递进，在不同句子切换情绪：

```
[happy] 太好了，我们成功了！ [excited] 下一步我们要做更大的事！
```

### 背景音

加入氛围音效：

```
[whispering] 我有件事想悄悄告诉你。 [audience laughing]
```

### 强度修饰

用描述性修饰词微调情绪强度。S2 方括号支持自由描述：

```
[somewhat happy] 还不错吧。
[absolutely furious] 我受够了！
```

---

## 9. 语言支持

全部 13 种支持语言都能用情绪标记。句子级控制在以下语言中建议把标记放在**句首**：

英语、中文、日语、德语、法语、西班牙语、韩语、阿拉伯语、俄语、荷兰语、意大利语、波兰语、葡萄牙语。

---

## 10. 最佳实践

**建议做：**
- 每句用一个主情绪。
- 尝试不同的情绪组合。
- 让情绪与上下文逻辑匹配。
- 音效标记后跟上合适文字（如大笑后接 "Ha ha"）。
- 尽量用自然的拟声表达。
- 情绪切换之间留出间隔，更真实。

**避免：**
- 短文本里堆砌过多情绪标记。
- 混合相互冲突的情绪。
- 方括号描述写得太长，影响可读性。
- 漏写方括号/圆括号。
- 把句子级情绪标记放得离目标句子太远。

---

## 11. 常见用法场景

### 客服

```
[empathetic] 我理解您的困扰，[confident] 我们会马上帮您解决。
```

### 故事讲述

```
[whispering] 深夜，森林里静悄悄的…… [nervous] 突然听到一阵脚步声。
```

### 教育内容

```
[calm] 我们先来看基本概念。[confident] 掌握这个之后，后面的内容就很简单了。
```

### 营销/销售

```
[excited] 新品上市啦！ [confident] 品质值得信赖，[enthusiastic] 现在下单还有优惠！
```

> 上面 `[enthusiastic]` 是 S2 自由自然语言描述的示例（不在固定标签表里），仅 S2 系列可用。

---

## 12. 排错

### 情绪不生效？
1. **检查位置**——标记要放在情绪/效果该开始的地方。
2. **描述清晰**——用简洁的自然语言描述。
3. **用对语法**——S2 用方括号；S1 必须用圆括号且用固定英文标签。

### 声音不自然？
- 情绪切换拉开间隔。
- 用合适的强度。
- 换不同音色试试。
- 音效标记后补上上下文文字。

### 性能说明
- 情绪标记不计入 token 限制。
- 情绪处理不增加额外延迟。
- 所有情绪在各价格档均可用。
- 建议每句最多组合 3 个情绪。

---

## 13. 速查表

### 情绪强度梯度

| 基础情绪 | 轻度 | 中度 | 强烈 |
|---|---|---|---|
| Happy | satisfied | happy | delighted |
| Sad | disappointed | sad | depressed |
| Angry | frustrated | angry | furious |
| Scared | nervous | scared | terrified |
| Excited | interested | excited | ecstatic |

### 常见组合

| 场景 | 组合 | 示例 |
|---|---|---|
| 耳语秘密 | `[mysterious][whispering]` | "我有件事要告诉你……" |
| 愤怒呼喊 | `[angry][shouting]` | "停下！" |
| 悲伤叹息 | `[sad][sighing]` | "要是能不一样就好了。Sigh." |
| 兴奋大笑 | `[excited][laughing]` | "我们成功了！Ha ha!" |
| 紧张提问 | `[nervous][uncertain]` | "你确定要这样做吗？" |

> `furious`、`terrified`、`ecstatic`、`interested`、`mysterious` 等是 S2 自由自然语言描述可用的词，不在 S1 固定标签集里——用 s1 时请改用固定标签表里的词。
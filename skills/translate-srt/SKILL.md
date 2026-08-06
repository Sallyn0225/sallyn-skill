---
name: translate-srt
description: 翻译 SRT 字幕文件到指定语言——修正语音转录错误、联网补充背景知识、按术语表信达雅翻译并复核。Use when the user wants to translate an SRT/subtitle file (翻译字幕、字幕翻译、translate subtitles), or to fix a speech-to-text SRT before translating.
---

把一个由语音转文字生成的、不规范的外文 SRT,加工成规范的目标语言 SRT。文本层面的所有硬规则在 [`references/subtitle-rules.md`](references/subtitle-rules.md)(下称**规范**);派发的每个子代理都必须先 Read 规范。脚本路径以本 skill 目录为基准。

## 目录约定

为每部字幕建一个独立工作区,所有产出都在工作区内,外部原始字幕保持不动。以翻译 `how-to-code.srt` 为例:

```
<原 srt 同目录>/
  how-to-code.srt                  ← 原始字幕,保持不动
  how-to-code/                     ← 工作区(以原 srt 词干命名)
    how-to-code.srt                ← 原始副本(由脚本复制进来)
    how-to-code_fix.srt            ← 转录修正(原语言)
    how-to-code_zh.srt             ← 翻译初稿
    how-to-code_zh_fix.srt         ← 复核终稿
    AGENTS.md                      ← 工作区说明(脚本生成)
    _context/                      ← 背景资料区
      brief.md                     ← 背景简报(占位 → 第 2 步填实)
      glossary.md                  ← 术语表(占位 → 第 2 步填实)
      research/                    ← 调研子代理的原始调研文件
        01-voice-actors.md
        ...
```

语言后缀用 ISO 639-1(zh、ja、en…)。下文 `<stem>` 指原 srt 词干(如 `how-to-code`),`<lang>` 指目标语言代码。

## 第 1 步:建立工作目录

在原 srt 同目录建工作区。运行:

```
python <skill目录>/scripts/srt_tools.py init <原 srt 路径>
```

脚本会:以 `<stem>` 在原 srt 同目录建 `<stem>/`(已存在则报错退出,re-run 由你自行判断);把原 srt 复制进去;生成 `AGENTS.md`、`_context/`(含占位的 `brief.md`、`glossary.md` 和空的 `research/`)。

完成标准:脚本打印 OK,工作区内有原始副本、`AGENTS.md`、`_context/brief.md`、`_context/glossary.md`、`_context/research/`。

## 第 2 步:提问、通读、调研

**2a 向用户提问。** 用 AskUserQuestion 问清三件事:原始语言(可提供"自动检测"选项)、目标语言、字幕的主题与热词(人名、作品名、专有名词;用户可留空或明说"跳过搜索")。完成标准:原始语言与目标语言均已确定;主题要么拿到,要么用户明确跳过。

**2b 通读字幕,建立简报。** Read 工作区内的原始副本(过长则分段读完)。提炼:内容概述、出现的全部专名(人名/作品名/组织名)、疑似听录错误的词。

**2c 调研(用户跳过搜索则本步省略)。** 以用户给的主题为起点、结合字幕中读到的专名适当发散(例:声优名 → 其所属企划、参演作品、相关成员),并行派发 1~3 个联网搜索子代理,每个负责一个角度。**派发时由主代理指定每个子代理的编号与英文主题**(kebab-case,如 `01-voice-actors`),子代理不再以消息回报,而是把结果写入工作区内的 `_context/research/<编号>-<主题>.md`。每个调研文件固定两节:

- `## 事实要点` —— 与本字幕相关的事实要点;
- `## 术语表条目` —— 原语言写法 → 目标语言标准译名,查不到标"自拟"。

搜索结果若暴露出新的关键实体,可再派发一轮,新轮次按下一个编号继续落盘(总数仍按需控制,不刻意追求覆盖全部发散)。

**2d 汇总落盘。** 主代理 Read `_context/research/` 下全部调研文件,**不**合并成单一调研文件(避免信息漂移),而是据此编辑(替换占位内容)工作区内的 `_context/brief.md`(背景简报)和 `_context/glossary.md`(术语表)。术语表须覆盖字幕中出现的每个专名(查不到标"自拟")。

跳过搜索时,`_context/brief.md` 即主代理自己的通读总结,`_context/glossary.md` 由主代理拟定,同样写入这两个文件。

完成标准:`_context/research/` 下有若干调研文件(跳过搜索时为空);`_context/brief.md`、`_context/glossary.md` 已被填实;术语表覆盖字幕中每个专名。

## 第 3 步:修正转录错误 → `_fix.srt`

主代理亲自做(需要对照背景简报做同音/近音纠错,不外包)。逐条处理工作区内的原始副本,按规范执行:纠正听录错误(优先怀疑与术语表读音相近的词)、合并被拆开的句子(时间轴取并集)、把归属错位的句首/句尾词移到相邻条目、删除纯口语废句、精简句内重复口语词、`[]`→`()`。保持原语言,不翻译。写出 `<stem>/<stem>_fix.srt` 后运行:

```
python <skill目录>/scripts/srt_tools.py normalize <stem>/<stem>_fix.srt
```

完成标准:normalize 输出 OK,且原 srt 每一条都已处理(修正、合并、删除三者之一,多数条目原样保留也算已处理)。

## 第 4 步:翻译 → `_<lang>.srt`

**默认派发一个翻译子代理处理整份 `_fix.srt`**,不要拆分。理由:字幕是对话与叙事的连续体,人称、指代、称呼、语气常常跨条目绵延;整份交给同一子代理,它持有的上下文最完整、术语与风格自然一致,且只加载一次规范/简报/术语表、缓存命中最高。分块是降级手段,不是常态。

每个翻译子代理的 prompt 必须包含:`<stem>/<stem>_fix.srt` 路径,并要求**先 Read 规范、`_context/brief.md`、`_context/glossary.md` 再动手**(不再把简报/术语表内联进 prompt),以及:按信达雅翻译为目标语言,逐条输出,保持时间轴与编号不变,与 `_fix.srt` 的条目一一对应、不合并不拆条。

**只有当 `_fix.srt` 条目数明显超出单子代理的一次处理上限(参考阈值 ≈ 1200 条;接近或超过才考虑)时**,才回退到分块翻译,以避免单次输出撑爆上下文/输出限额。回退时的硬要求:

- 按 ~500~800 条一块切分,块要尽量大,不要切成 100 条的小块——块越大,拆分次数越少、上下文断点越少越好。
- 切分尽量沿自然段落边界(场景切换、长停顿、说话人轮换),不要机械按行号平切。
- 块首附上前一块**末尾 8~10 条**的原文与译文作衔接上下文(比 2~3 条更厚),并在 prompt 里明确告知:本块是续译,必须沿用前块已确立的人称、语气、术语译名与行文风格,不得另起一套。
- 各块子代理同样先 Read 规范、`_context/brief.md`、`_context/glossary.md`。
- 主代理拿到各块译文后按编号顺序拼接成完整 `<stem>/<stem>_<lang>.srt`,再统一跑 `clean`(不要让各块各自跑,避免编号/空行拼接错位)。

最终(单代理或分块拼接后)运行:

```
python <skill目录>/scripts/srt_tools.py clean -l <lang> <stem>/<stem>_<lang>.srt
```

完成标准:clean 输出 OK;条目数与 `_fix.srt` 一致(clean 删掉译后为空的条目除外,数量差需能说明原因);分块时各块编号无重叠无遗漏。

## 第 5 步:复核 → `_<lang>_fix.srt`

派发一个审查子代理,给它:`<stem>/<stem>_fix.srt`(原文基准)、`<stem>/<stem>_<lang>.srt`(待审译文),并要求先 Read 规范、`_context/brief.md`、`_context/glossary.md`。任务:逐条对照原文与译文,检出并直接修正漏译、错译、术语不一致、不符合规范的条目,写出 `<stem>/<stem>_<lang>_fix.srt` 后再跑一遍 `clean`,回报修正清单(条目号+改动原因)。

```
python <skill目录>/scripts/srt_tools.py clean -l <lang> <stem>/<stem>_<lang>_fix.srt
```

> `-l <lang>`(ISO 639-1)决定 clean 的标点风格:zh/ja/ko 走 cjk 风格(句中非成对标点转空格、句尾不留句号);其余拉丁/西里尔等走 western 风格(保留句中标点与句尾句号)。缺省为 cjk。

完成标准:子代理回报"逐条核对完成",附修正清单(可为空)。

## 第 6 步:总结

主代理抽查终稿的开头、中间、结尾各若干条,确认整体质量,然后向用户报告:工作区路径、三个产出文件(`_fix`/`_<lang>`/`_<lang>_fix`)的路径、`_context/` 内的背景资料(`brief.md`、`glossary.md` 及 `research/` 下调研文件)、修正要点(转录纠错了什么、复核改了什么)。
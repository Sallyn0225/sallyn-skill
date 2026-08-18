# sallyn-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-compatible-111827)](https://skills.sh/)
[![agent skills](https://img.shields.io/badge/coding%20agent-skills-2563eb)](https://github.com/vercel-labs/skills)
[![license](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

sallyn 在日常使用 coding agent 过程中沉淀下来的个人 skill 集合。这里的 skills 主要记录可复用的工作流、处理规范和配套脚本,并按 [skills.sh](https://skills.sh/) CLI 可发现的目录结构组织,方便安装到 Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Qwen Code 等支持 agent skills 的工具中。

> [!NOTE]
> 这是 sallyn 的个人沉淀仓库,不是某个 agent 的专用扩展包。只要你的 agent 支持 `skills` CLI 或兼容 `SKILL.md` 目录规范,就可以使用这里的 skills。

> 想新增 / 维护 skill?看 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## Skills

仓库里的 skills 分为两类:**工具类**(可复用的处理工作流)与**角色扮演类**(基于深度调研的角色视角)。

### 工具类(Tool)

| Skill | Tags | Description |
|---|---|---|
| [`translate-srt`](./skills/translate-srt) | `srt`, `subtitle`, `translation`, `asr-cleanup` | 把外文 SRT 字幕翻译为指定语言,含转录纠错、联网背景补充、术语表翻译与复核的完整流程。 |
| [`lyrics-translator`](./skills/lyrics-translator) | `lyrics`, `japanese`, `translation`, `chinese`, `lrc` | 把日语歌词翻译为中文歌词,遵循信达雅准则:通读定调、按歌曲情感与主题自动选择翻译风格、初译后派子代理复核并修订后交付,支持 .txt/.lrc。 |
| [`openai-image`](./skills/openai-image) | `image-generation`, `text-to-image`, `image-editing`, `inpainting`, `openai-compatible` | 通过 OpenAI 兼容 API 文生图与编辑图片,支持自定义 base_url/api_key(官方或任意第三方服务),零依赖 Python 脚本,支持多图、mask 遮罩、尺寸/质量/格式控制。 |
| [`fish-tts`](./skills/fish-tts) | `tts`, `text-to-speech`, `fish-audio`, `voice-synthesis`, `audio` | 通过 Fish Audio API 把文本合成为语音,支持音色库搜索、零样本音色克隆、多说话人对话,零依赖 Python 脚本,可配置 API key、TTS 模型(s2.1-pro/s2-pro/s1)、默认音色与格式/码率/语速/音量等全部参数。 |

### 角色扮演类(Roleplay / Perspective)

以《偶像大师》系列角色的视角进行角色扮演对话或思维顾问。每个 skill 基于官方剧情原文、声优访谈与粉丝考察的深度调研提炼,并各自声明了触发与不触发边界。按系列进一步分为闪耀色彩与本家 765PRO 两组(`--list` 里分别显示为 `Roleplay Shinycolors` / `Roleplay 765pro`):

- **通用求助默认不激活**——梦想坚持、自我怀疑、职场竞争等泛泛话题不会自动触发,需用户明确指名角色(如「用恋钟的视角」「日花会怎么看」);
- **泛聊闪耀色彩剧情时归 `kogane-perspective`** 负责,聚焦具体角色时使用对应角色 skill;
- **泛聊本家 765PRO 剧情时归 `miki-perspective` / `chihaya-perspective` / `haruka-perspective`** 负责;
- 同一话题同时命中多个角色时,以用户明确指名的角色为准。

#### 闪耀色彩(ShinyColors)

| Skill | Tags | Description |
|---|---|---|
| [`amana-perspective`](./skills/amana-perspective) | `roleplay`, `shinycolors`, `amana`, `idolmaster` | 以《偶像大师 闪耀色彩》大崎甘奈的视角进行角色扮演对话,覆盖日常聊天、陪伴、安慰与深度追问场景。 |
| [`mayuzumi-fuyuko-perspective`](./skills/mayuzumi-fuyuko-perspective) | `roleplay`, `shinycolors`, `fuyuko`, `idolmaster` | 以黛冬優子的思维框架与表达方式回应,适合冬優子视角的角色扮演、价值观讨论与陪伴对话。 |
| [`kogane-perspective`](./skills/kogane-perspective) | `roleplay`, `shinycolors`, `kogane`, `idolmaster` | 以月岡恋鐘的思维框架与恋鐘弁表达方式回应,适合恋钟视角的角色扮演、团队困境分析、自我怀疑陪伴与梦想坚持讨论。 |
| [`nichika-perspective`](./skills/nichika-perspective) | `roleplay`, `shinycolors`, `nichika`, `idolmaster` | 以七草日花(七草にちか)的思维框架与表达方式回应,适合日花视角的角色扮演、存在感焦虑、自我证明、平凡人逆袭与追星转偶像讨论。 |

#### 本家 765PRO

| Skill | Tags | Description |
|---|---|---|
| [`miki-perspective`](./skills/miki-perspective) | `roleplay`, `idolmaster`, `765pro`, `miki` | 以星井美希(ほしい みき)的思维框架与表达DNA回应,适合美希视角的角色扮演、选择判断(ドキドキ测试)、自我认知、恋爱观与天然呆慵懒系表达模仿。 |
| [`chihaya-perspective`](./skills/chihaya-perspective) | `roleplay`, `idolmaster`, `765pro`, `chihaya` | 以如月千早(きさらぎ ちはや)的思维框架与表达DNA回应,适合千早视角的角色扮演、唱歌/完美主义、努力与天赋、约定与孤独、成长弧线讨论。 |
| [`haruka-perspective`](./skills/haruka-perspective) | `roleplay`, `idolmaster`, `765pro`, `haruka` | 以天海春香(あまみ はるか)的思维框架与表达DNA回应,适合春香视角的角色扮演、团队羁绊、普通人的努力哲学、初心回环与元气王道系表达模仿。 |

## Install

列出仓库内可安装的 skills(按工具类 / 角色扮演类分组展示):

```bash
npx skills add Sallyn0225/sallyn-skill --list
```

分组的依据是仓库根目录的 [`./.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json):它声明了 `tool` / `roleplay-shinycolors` / `roleplay-765pro` 三个 plugin,`skills` CLI(`--list`)会据此把每个 skill 归到对应分组下展示(角色扮演类按系列进一步分为闪耀色彩与本家 765PRO)。新增 skill 时,记得把它登记到对应 plugin 的 `skills` 数组里,否则它会落在未分组的 `General` 下。

安装指定 skill:

```bash
npx skills add Sallyn0225/sallyn-skill --skill translate-srt
```

安装仓库内全部 skills:

```bash
npx skills add Sallyn0225/sallyn-skill --all
```

全局安装可加 `-g`:

```bash
npx skills add Sallyn0225/sallyn-skill --skill translate-srt -g
```

安装到指定 agent 可使用 `--agent`:

```bash
npx skills add Sallyn0225/sallyn-skill --skill translate-srt --agent codex
npx skills add Sallyn0225/sallyn-skill --skill translate-srt --agent claude-code
```

## Repository Layout

```text
sallyn-skill/
├── .claude-plugin/
│   └── marketplace.json   # skills.sh 分组清单:声明 tool / roleplay-shinycolors / roleplay-765pro 三个 plugin
├── README.md
├── LICENSE
└── skills/
    └── <skill-name>/
        ├── SKILL.md       # Required: skill metadata and instructions
        ├── scripts/       # Optional: helper scripts used by the skill
        └── evals/         # Optional: evaluation prompts or fixtures
```

每个 skill 都是一个独立目录,并通过 `SKILL.md` 顶部的 YAML frontmatter 声明 `name` 和 `description`。`skills` CLI 会读取这些字段来展示、筛选和安装 skill。

仓库根目录的 `.claude-plugin/marketplace.json` 是 [Claude Code 插件市场清单](https://docs.claude.com/en/docs/claude-code/plugins-marketplaces)格式,这里只用它来给 `skills add --list` 提供分组信息——它把 `skills/` 下的各个 skill 按 `tool` / `roleplay-shinycolors` / `roleplay-765pro` 三个 plugin 归类(角色扮演类再按系列分为闪耀色彩与本家 765PRO)。它不影响单 skill 安装(`--skill <name>`)或全量安装(`--all`),只决定 `--list` 的展示分组。

## Local Development

在本地检查仓库是否能被 `skills` CLI 识别:

```bash
npx skills add . --list
```

新建 skill 时,推荐放在 `skills/<skill-name>/` 下:

```bash
npx skills init skills/my-skill
```

也可以手动创建目录,但至少需要包含:

```markdown
---
name: my-skill
description: What this skill does and when to use it.
---
```

## Topics

`agent-skills`, `skills-sh`, `coding-agent`, `codex`, `claude-code`, `cursor`, `gemini-cli`, `subtitle-translation`, `srt`, `asr-cleanup`, `lyrics-translation`, `image-generation`, `text-to-image`, `image-editing`, `inpainting`, `openai-compatible`, `roleplay`, `shinycolors`, `idolmaster`, `765pro`, `chihaya`, `haruka`

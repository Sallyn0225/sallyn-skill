# sallyn-skill

[![skills.sh](https://img.shields.io/badge/skills.sh-compatible-111827)](https://skills.sh/)
[![agent skills](https://img.shields.io/badge/coding%20agent-skills-2563eb)](https://github.com/vercel-labs/skills)
[![license](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

sallyn 在日常使用 coding agent 过程中沉淀下来的个人 skill 集合。这里的 skills 主要记录可复用的工作流、处理规范和配套脚本,并按 [skills.sh](https://skills.sh/) CLI 可发现的目录结构组织,方便安装到 Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Qwen Code 等支持 agent skills 的工具中。

> [!NOTE]
> 这是 sallyn 的个人沉淀仓库,不是某个 agent 的专用扩展包。只要你的 agent 支持 `skills` CLI 或兼容 `SKILL.md` 目录规范,就可以使用这里的 skills。

## Skills

| Skill | Tags | Description |
|---|---|---|
| [`subtitle-translator`](./skills/subtitle-translator) | `srt`, `subtitle`, `translation`, `chinese`, `asr-cleanup` | 把外语 SRT 字幕翻译为中文,包含转录纠错、字幕结构规范化、标点与时间码规范化的完整流程。 |
| [`lyrics-translator`](./skills/lyrics-translator) | `lyrics`, `japanese`, `translation`, `chinese`, `lrc` | 把日语歌词翻译为中文歌词,遵循信达雅准则:通读定调、按歌曲情感与主题自动选择翻译风格、初译后派子代理复核并修订后交付,支持 .txt/.lrc。 |

## Install

列出仓库内可安装的 skills:

```bash
npx skills add Sallyn0225/sallyn-skill --list
```

安装指定 skill:

```bash
npx skills add Sallyn0225/sallyn-skill --skill subtitle-translator
```

安装仓库内全部 skills:

```bash
npx skills add Sallyn0225/sallyn-skill --all
```

全局安装可加 `-g`:

```bash
npx skills add Sallyn0225/sallyn-skill --skill subtitle-translator -g
```

安装到指定 agent 可使用 `--agent`:

```bash
npx skills add Sallyn0225/sallyn-skill --skill subtitle-translator --agent codex
npx skills add Sallyn0225/sallyn-skill --skill subtitle-translator --agent claude-code
```

## Repository Layout

```text
sallyn-skill/
├── README.md
├── LICENSE
└── skills/
    └── <skill-name>/
        ├── SKILL.md       # Required: skill metadata and instructions
        ├── scripts/       # Optional: helper scripts used by the skill
        └── evals/         # Optional: evaluation prompts or fixtures
```

每个 skill 都是一个独立目录,并通过 `SKILL.md` 顶部的 YAML frontmatter 声明 `name` 和 `description`。`skills` CLI 会读取这些字段来展示、筛选和安装 skill。

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

`agent-skills`, `skills-sh`, `coding-agent`, `codex`, `claude-code`, `cursor`, `gemini-cli`, `subtitle-translation`, `srt`, `asr-cleanup`

# sallyn-skill

[Claude Code](https://docs.claude.com/en/docs/claude-code/overview) / Claude Agent SDK 的个人 skill 集合。仓库按 [skills.sh](https://skills.sh/) CLI 可发现的结构组织，每个 `skills/<skill-name>/` 子目录是一个独立的 skill，包含 `SKILL.md` 以及该 skill 需要的 scripts、evals 等资源。

## Skill 一览

| 名称 | 简介 |
|---|---|
| [`subtitle-translator`](./skills/subtitle-translator) | 把外语 SRT 字幕(日语/英语/韩语等)翻译为中文,包含转录纠错、字幕结构规范化、标点与时间码规范化的完整四步流水线 |

## 安装

使用 `skills` CLI 从 GitHub 安装:

```bash
# 列出仓库内可安装的 skills
npx skills add Sallyn0225/sallyn-skill --list

# 安装指定 skill
npx skills add Sallyn0225/sallyn-skill --skill subtitle-translator

# 或安装仓库内全部 skills
npx skills add Sallyn0225/sallyn-skill --all
```

全局安装可加 `-g`。安装后,支持 skills 的 agent 会按各自 `SKILL.md` 头部 `description` 字段中描述的触发条件自动加载。

## 仓库结构

```
sallyn-skill/
├── README.md
├── LICENSE
├── .gitignore
└── skills/
    └── <skill-name>/
        ├── SKILL.md       # 必需:skill 元信息和正文
        ├── scripts/       # 可选:skill 调用的脚本
        └── evals/         # 可选:skill 的评测样例
```

每个 `SKILL.md` 头部使用 YAML frontmatter 声明 `name` 和 `description`,详见各 skill 目录。

## License

[MIT](./LICENSE)

# sallyn-skill

[Claude Code](https://docs.claude.com/en/docs/claude-code/overview) / Claude Agent SDK 的个人 skill 集合。每个子目录是一个独立的 skill，包含 `SKILL.md` 以及该 skill 需要的 scripts、evals 等资源。

## Skill 一览

| 名称 | 简介 |
|---|---|
| [`subtitle-translator`](./subtitle-translator) | 把外语 SRT 字幕(日语/英语/韩语等)翻译为中文,包含转录纠错、字幕结构规范化、标点与时间码规范化的完整四步流水线 |

## 安装

把想用的 skill 子目录复制(或软链)到 Claude 的 skill 搜索路径下,例如:

```bash
# 用户级(对所有项目可见)
cp -r subtitle-translator ~/.claude/skills/

# 或仓库级(只对当前项目可见)
cp -r subtitle-translator <your-repo>/.claude/skills/
```

Windows PowerShell:

```powershell
Copy-Item -Recurse subtitle-translator $HOME\.claude\skills\
```

安装后,在 Claude Code 会话里 skill 会按各自 `SKILL.md` 头部 `description` 字段中描述的触发条件自动加载,也可以用 `/<skill-name>` 显式调用。

## 仓库结构

```
sallyn-skill/
├── README.md
├── LICENSE
├── .gitignore
└── <skill-name>/
    ├── SKILL.md       # 必需:skill 元信息和正文
    ├── scripts/       # 可选:skill 调用的脚本
    └── evals/         # 可选:skill 的评测样例
```

每个 `SKILL.md` 头部使用 YAML frontmatter 声明 `name` 和 `description`,详见各 skill 目录。

## License

[MIT](./LICENSE)

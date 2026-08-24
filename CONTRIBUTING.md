# 维护指南

本仓库是 [sallyn](https://github.com/Sallyn0225) 的个人 skill 沉淀,按 [skills.sh](https://skills.sh/) CLI 可发现的目录结构组织,可安装到 Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Qwen Code 等支持 agent skills 的工具。

无论你是 sallyn 本人还是其他贡献者,新增或修改 skill 前请先读完本文。**最重要的一条:每加一个 skill 都要去 [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json) 登记,否则它不会出现在分组里**(详见下文「第 5 步」)。

---

## 目录结构

```text
sallyn-skill/
├── .claude-plugin/
│   └── marketplace.json       # skills.sh 分组清单:声明 tool / roleplay-shinycolors / roleplay-765pro 三个 plugin
├── CONTRIBUTING.md            # 本文件
├── README.md                  # 仓库主页与精选导航
├── LICENSE
└── skills/
    ├── <tool-skill-name>/     # 工具类 skill (平铺在 skills/ 下)
    │   ├── SKILL.md           # 必需:skill 元数据与使用说明
    │   ├── scripts/            # 可选:skill 用到的辅助脚本
    │   ├── references/        # 可选:skill 引用的参考文档
    │   └── evals/              # 可选:评测 prompt 或 fixtures
    ├── shinycolors/           # 🌟 闪耀色彩系列角色视角
    │   ├── README.md          # 闪耀色彩 28 位全角色索引与组合导航
    │   └── <idol>-perspective/
    │       └── SKILL.md
    └── 765pro/                # 👑 本家 765PRO 系列角色视角
        ├── README.md          # 765PRO 全角色索引
        └── <idol>-perspective/
            └── SKILL.md
```

每个 skill 是一个独立目录,目录名 = skill 名。`SKILL.md` 是唯一必需文件,其余按需添加。

## 分类

仓库里的 skill 分为工具类与角色扮演类,后者再按系列分为闪耀色彩与本家 765PRO(见 [README.md](./README.md#skills))。skills.sh 的 `--list` 只支持一级分组,所以「角色扮演类」在 CLI 里拆成两个平级 plugin 展示:

| 分类 | 存放目录 | plugin 名(`marketplace.json` 里的值) | `--list` 里显示的分组标题 | 适合什么 |
|---|---|---|---|---|
| 工具类 | `skills/<skill-name>/` | `tool` | **Tool** | 可复用的处理工作流:翻译、文生图、TTS 等有明确输入/输出与步骤的「工具」。 |
| 角色扮演类·闪耀色彩 | `skills/shinycolors/<idol>-perspective/` | `roleplay-shinycolors` | **Roleplay Shinycolors** | 《偶像大师 闪耀色彩》角色的思维框架 / 视角。 |
| 角色扮演类·本家 765PRO | `skills/765pro/<idol>-perspective/` | `roleplay-765pro` | **Roleplay 765pro** | 《偶像大师》本家 765PRO 角色的思维框架 / 视角。 |

**怎么判断新 skill 归哪类?** 看它「是什么」而不是「给谁用」——

- 它是一个**做事的流程** → `tool`,放在 `skills/<name>/`。
- 它是一套**以某角色视角说话/思考的方式** → `roleplay-*`,按角色所属系列放在 `skills/shinycolors/<name>/` 或 `skills/765pro/<name>/`。新系列(如《偶像大师》的其他分支)出来时,新建对应子目录并加一个 `roleplay-<系列>` plugin 即可。

> skills.sh 只支持一级分组,无法在 `Roleplay` 下面再嵌套「闪耀色彩 / 本家」子组。所以这里用 `roleplay-shinycolors` / `roleplay-765pro` 两个**平级** plugin 实现,`--list` 里会显示为两个独立分组头。

## 新增一个 skill(完整步骤)

### 1. 建目录

推荐用 skills CLI 生成骨架:

```bash
# 工具类
npx skills init skills/my-tool

# 闪耀色彩系列
npx skills init skills/shinycolors/my-idol-perspective

# 765PRO 系列
npx skills init skills/765pro/my-idol-perspective
```

也可手动建目录。目录名用 kebab-case,要和 `SKILL.md` 里的 `name` 一致。

### 2. 写 `SKILL.md` frontmatter

`SKILL.md` 顶部必须有 YAML frontmatter,`name` 和 `description` 缺一不可——`skills` CLI 靠它们发现、筛选、展示 skill。

```markdown
---
name: my-skill
description: 一句话说明这个 skill 做什么、什么时候该用它。触发词和「Use when…」用中英双语写,方便 agent 匹配。
---
```

要点:

- **`name`**:kebab-case,与目录名一致。
- **`description`**:既要写「做什么」,也要写「什么时候触发」。现有 skill 的惯例是**中文触发短语 + 英文 `Use when…` 子句**双语并存。描述较长时用 YAML 块标量(`|` 折行或 `>-` 折叠)。
- **`type`(可选)**:角色扮演类 skill 会加 `type: perspective` 表明它是视角类,这是仓库内部约定,`skills` CLI 不依赖它做分组(分组只看 `marketplace.json`)。
- **`调研时间`(可选)**:角色扮演类 skill 标注调研截止时间,方便日后判断是否需要重新调研。

> `skills` CLI 还支持 `metadata.internal: true` 把 skill 标记为内部(默认不安装、不展示,需 `INSTALL_INTERNAL_SKILLS=1` 才可见)。一般用不到,除非你想藏起来。

### 3. 写正文

frontmatter 以下是正文,写给 agent 看的「怎么做」。可以引用同目录下的 `references/`、`scripts/` 等文件。正文里所有相对路径都以**本 skill 目录**为基准。

### 4. 本地验证

在仓库根目录跑:

```bash
npx skills add . --list
```

确认你的 skill 出现在列表里、`name` / `description` 正常解析。

### 5. 登记分组(关键!)

打开 [`.claude-plugin/marketplace.json`](./.claude-plugin/marketplace.json),把新 skill 的路径加到对应 plugin 的 `skills` 数组:

```jsonc
{
  "plugins": [
    {
      "name": "tool",                       // 工具类
      "skills": [
        "./skills/translate-srt",
        "./skills/lyrics-translator",
        "./skills/my-tool"                   // ← 新增这一行
      ]
    },
    {
      "name": "roleplay-shinycolors",        // 闪耀色彩系列
      "skills": [
        "./skills/shinycolors/mano-perspective",
        "./skills/shinycolors/my-idol-perspective"  // ← 新增这一行
      ]
    },
    {
      "name": "roleplay-765pro",             // 本家 765PRO 系列
      "skills": [
        "./skills/765pro/miki-perspective"
      ]
    }
  ]
}
```

路径必须以 `./` 开头,指向 skill 目录(不含 `SKILL.md`)。

**为什么要登记?** `skills add --list` 是按 `marketplace.json` 里声明的 plugin 名分组的(`getPluginGroupings` 机制)。没登记的 skill 会被归到未分组的 `General` 下,而不是你期望的分组里。再跑一次 `npx skills add . --list` 确认它落在正确的分组标题下。

### 6. 更新 README 与索引页

- **工具类**:在 [README.md](./README.md) 的「工具类」表格中添加一行。
- **闪耀色彩**:在 [`skills/shinycolors/README.md`](./skills/shinycolors/README.md) 对应组合的表格中更新状态为已上线,并补充简介与链接。若为代表性角色,可同步更新主 README。
- **本家 765PRO**:在 [`skills/765pro/README.md`](./skills/765pro/README.md) 及主 README 表格中添加一行。

### 7. 提交

仓库使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <说明>
```

常见用法:

| type | 用于 |
|---|---|
| `feat(skills)` | 新增 skill |
| `fix(<skill-name>)` | 修某 skill 的 bug |
| `refactor(<skill-name>)` | 重构某 skill(不改行为) |
| `docs(readme)` | 改 README 文档 |
| `chore(skills)` | 目录结构 / 命名 / 清理类改动 |

## 改动 `.claude-plugin/marketplace.json` 时要注意

- 它是 [Claude Code 插件市场清单](https://docs.claude.com/en/docs/claude-code/plugins-marketplaces)格式,这里只用它给 `skills add --list` 提供分组信息。
- 三个 plugin 的 `name` 分别是 `tool`、`roleplay-shinycolors`、`roleplay-765pro`。
- 每条 skill 路径都要以 `./` 开头;路径会被校验是否落在仓库内(`isContainedIn`),写外部的会被忽略。
- 它**不影响**单 skill 安装(`--skill <name>`)或全量安装(`--all`),只决定 `--list` 的展示分组。

## 本地常用命令

```bash
# 列出仓库内所有 skill(按 plugin 分组展示)
npx skills add . --list

# 列出远端仓库的 skill
npx skills add Sallyn0225/sallyn-skill --list

# 安装单个 skill(本地)
npx skills add . --skill mano-perspective

# 安装全部 skill
npx skills add . --all
```

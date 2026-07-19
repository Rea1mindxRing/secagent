# SecAgent 协作规范

> 新手友好 · 简单明了 · 照做就行

> ⚠️ **GitHub 规则集已启用**：以下规则由 GitHub 强制实施，不照做的话 PR 合并按钮是灰色的。详见末尾「规则集速查」。

---

## 一、工作流程（每次必看）

```
更新代码 → 新建分支 → 改代码 → 提交 → 推送 → 提 Pull Request → 合并
```

**一句话：永远不要在 main 分支上直接改代码。**

---

## 二、详细步骤 + 实例

### 1️⃣ 每次开始前，先更新本地代码

```bash
git checkout main          # 切换到 main
git pull                   # 拉取最新代码
```

> ✅ 确保你的本地代码和远程仓库一致，避免冲突。

### 2️⃣ 新建一个分支来改代码

```bash
git checkout -b feat/add-login
```

**分支命名规范：**

| 前缀 | 含义 | 示例 |
|------|------|------|
| `feat/` | 新功能 | `feat/add-login` |
| `fix/` | 修 Bug | `fix/login-error` |
| `docs/` | 改文档 | `docs/update-readme` |
| `refactor/` | 重构代码 | `refactor/cleanup-config` |

### 3️⃣ 改代码，然后提交

```bash
# 查看改了什么
git status

# 添加改动
git add 文件名          # 添加单个文件
git add .              # 添加所有文件（慎用，检查一下）

# 提交
git commit -m "feat: 添加登录功能"
```

**提交信息规范：**

```
<类型>: <简短描述>
```

| 类型 | 何时用 |
|------|--------|
| `feat` | 新功能 |
| `fix` | 修 Bug |
| `docs` | 文档 |
| `refactor` | 重构 |
| `style` | 格式调整（空格、缩进） |

### 4️⃣ 推送到远程仓库

```bash
git push origin feat/add-login
```

### 5️⃣ 在 GitHub 上提 Pull Request

1. 打开浏览器，进入 GitHub 仓库页面
2. 你会看到一个黄色的提示条：**"feat/add-login had recent pushes"** → 点 **"Compare & pull request"**
3. 填写 PR 标题和说明：
   - **标题**：沿用 commit 信息，如 `feat: 添加登录功能`
   - **说明**：简单写改了啥，为什么改
4. 点 **"Create pull request"**
5. 让另一位朋友 **Review（审查）** 代码，点 **"Approve"**
6. 检查以下条件是否全部满足（否则**合并按钮是灰色的**）：
   - ✅ **至少 1 人批准** — 朋友点了 Approve
   - ✅ **CI 检查通过** — 显示绿色 ✓
   - ✅ **分支是最新的** — 没有 "This branch is out-of-date" 提示
   - ✅ **没有未解决的对话** — 评论都点 Resolve 了
7. 条件都满足后，点 **"Merge pull request"** → **"Confirm merge"**

> **如果提示 "This branch is out-of-date"：** 在 PR 页面点 **"Update branch"** 按钮，等 CI 重新跑完即可。

> **重要：** 合并后，切换到主分支更新本地代码：
> ```bash
> git checkout main
> git pull
> ```

---

## 三、常见场景（直接抄作业）

### 场景 A：朋友刚提交了代码，你要同步

```bash
git checkout main
git pull
git checkout 你的分支名
git merge main   # 把 main 的最新代码合并到你的分支
```

### 场景 B：改完发现改错了，想撤销

```bash
# 还没提交：撤销所有未提交的改动
git checkout -- .

# 已经提交但还没推送：撤销最后一次提交
git reset --soft HEAD~1
```

### 场景 C：不小心在 main 分支上改了代码

```bash
# 把你的改动带到新分支
git stash
git checkout -b feat/your-feature
git stash pop
```

---

## 四、禁止事项 ❌

| 行为 | 后果 | GitHub 规则集 |
|------|------|--------------|
| 直接在 `main` 上改代码 | 代码混乱，无法审查 | ⛔ **已禁止**，推不上去 |
| `git push origin main` 直接推 main | 绕过审查 | ⛔ **已禁止**，推不上去 |
| 没等朋友 Approve 就点合并 | 不合规 | ⛔ **已禁止**，合并按钮灰色 |
| CI 检查没通过就合并 | 可能有 Bug | ⛔ **已禁止**，合并按钮灰色 |
| 分支不是最新就合并 | 可能冲突 | ⛔ **已禁止**，合并按钮灰色 |
| `git add .` 不看改了啥就提交 | 容易把不该提交的文件带进去 | 建议 |
| 提交信息写 "aaa"、"fix"、"111" | 别人看不懂，以后自己也看不懂 | 建议 |
| 冲突了不会解决就硬推（`--force`） | 会覆盖别人的代码，**非常危险** | ⛔ **已禁止** |

---

## 五、新手速查表

```bash
# 日常用到的命令
git status           # 查看状态
git log --oneline    # 查看提交历史
git branch           # 查看当前分支
git checkout -b xxx  # 创建并切换到新分支
git add 文件名       # 添加文件
git commit -m "msg"  # 提交
git push origin xxx  # 推送分支
git pull             # 拉取最新代码
```

---

## 六、总结

```
         main（稳定版，不要直接改）
            │
            ├── feat/xxx（你改你的）
            ├── fix/xxx（他改他的）
            │
     通过 Pull Request 审查后合并回 main
```

**记住一条铁律：永远不在 main 上直接改，永远不直接 push main。**

---

## 七、规则集速查（GitHub 强制实施）

以下是你已在 GitHub 上开启的 `main` 分支规则，**不满足条件合并按钮就是灰色的**：

| 规则 | 说明 |
|------|------|
| 🔒 禁止直接 push `main` | 只能通过 PR 合并 |
| 🔒 需要 Pull Request | 所有改动必须走 PR |
| 🔒 至少 1 人批准 | 朋友必须点 Approve |
| 🔒 CI 必须通过 | 自动检查语法 + 跑测试 |
| 🔒 分支必须是最新的 | 落后 main 的话要先 Update branch |
| 🔒 禁止 force push | 防止覆盖别人的代码 |

> 这些规则在 GitHub 仓库 → **Settings** → **Rules** → **Rulesets** 里可以看到和修改。
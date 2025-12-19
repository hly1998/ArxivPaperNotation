# 📚 arXiv 个性化论文通知系统

自动爬取 arXiv 每日论文，根据你设置的关键词筛选最相关的论文，使用大模型生成中文总结，并通过邮件发送给你。

## ✨ 功能特点

- 🕷️ **每日爬取**: 自动爬取 arXiv 指定分类的最新论文
- 🔍 **智能匹配**: 使用 BM25 算法根据关键词计算相关性得分，支持关键词权重
- 🤖 **AI 总结**: 使用大模型（DeepSeek/GPT 等）生成结构化的中文论文解读
- 📧 **邮件通知**: 自动发送精美格式的论文日报邮件
- ⏰ **GitHub Actions**: 支持定时自动运行，无需本地部署
- 🔐 **安全配置**: 敏感信息通过环境变量/GitHub Secrets 配置

---

## 🚀 快速开始

### 方式一：GitHub Actions 自动运行（推荐）

无需本地环境，Fork 后配置 Secrets 即可自动运行。

#### 1. Fork 本项目

点击右上角 `Fork` 按钮，将项目复制到你的 GitHub 账号下。

#### 2. 配置 Secrets

进入你 Fork 的仓库，点击 `Settings` → `Secrets and variables` → `Actions`。

##### 必须配置的 Secrets（点击 "New repository secret"）

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxxxxxxx` |
| `LLM_MODEL` | 模型名称 | `gpt-4o` 或 `deepseek-chat` |
| `LLM_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `EMAIL_SMTP_SERVER` | SMTP 服务器地址 | `smtp.qq.com` |
| `EMAIL_SENDER` | 发送方邮箱 | `your-email@qq.com` |
| `EMAIL_PASSWORD` | 邮箱密码/授权码 | `xxxxxxxx`（QQ邮箱用授权码） |
| `EMAIL_RECIPIENTS` | 收件人列表（JSON格式） | `["a@example.com", "b@example.com"]` |
| `ARXIV_CATEGORIES` | arXiv 分类（JSON格式） | `["cs.CV", "cs.CL", "cs.AI"]` |
| `MATCHING_KEYWORDS` | 关键词及权重（JSON格式） | `{"rag": 2.0, "agent": 1.5, "LLM": 1.0}` |

##### 可选的 Variables（点击 "Variables" 标签页 → "New repository variable"）

| Variable 名称 | 说明 | 默认值 |
|--------------|------|--------|
| `MATCHING_THRESHOLD` | BM25 得分阈值 | `0.5` |
| `MATCHING_TOP_K` | 最大论文数量 | `10` |
| `LLM_BATCH_SIZE` | LLM 批量处理大小 | `3` |
| `EMAIL_SMTP_PORT` | SMTP 端口 | `587` |

#### 3. 启用 GitHub Actions

1. 进入仓库的 `Actions` 标签页
2. 如果看到提示，点击 "I understand my workflows, go ahead and enable them"
3. 点击左侧的 "Daily arXiv Paper Notification"

#### 4. 测试运行

1. 在 Actions 页面，点击 "Daily arXiv Paper Notification"
2. 点击右侧 "Run workflow" 按钮
3. 可以选择是否强制爬取、跳过爬取等选项
4. 点击绿色的 "Run workflow" 按钮开始运行

#### 5. 查看运行结果

- 运行成功后，你会收到论文日报邮件
- 可以在 Actions 运行记录中下载 Artifacts 查看日报和日志
- 默认每天 UTC 8:00（北京时间 16:00）自动运行

---

### 方式二：本地运行

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/ArxivPaperNotation.git
cd ArxivPaperNotation
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml，设置你的关键词、邮箱等
```

#### 4. 设置环境变量

```bash
export LLM_API_KEY="your-llm-api-key"
export EMAIL_PASSWORD="your-email-password"
```

#### 5. 运行

```bash
python main.py
```

---

## 📖 详细配置说明

### 环境变量配置

所有敏感配置都可以通过环境变量设置，环境变量优先级高于配置文件：

```bash
# arXiv 分类（JSON 数组格式）
export ARXIV_CATEGORIES='["cs.CV", "cs.CL", "cs.AI", "cs.LG"]'

# 关键词配置（JSON 对象格式，键为关键词，值为权重）
export MATCHING_KEYWORDS='{"rag": 2.0, "agent": 1.5, "LLM": 1.0, "transformer": 1.0}'

# 匹配参数
export MATCHING_THRESHOLD="3.0"
export MATCHING_TOP_K="10"

# LLM 配置
export LLM_MODEL="gpt-4o"
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-xxxxxxxx"
export LLM_BATCH_SIZE="3"

# 邮件配置
export EMAIL_SMTP_SERVER="smtp.qq.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_SENDER="your-email@qq.com"
export EMAIL_PASSWORD="your-authorization-code"
export EMAIL_RECIPIENTS='["recipient1@example.com", "recipient2@example.com"]'
```

### 配置文件 (config.yaml)

```yaml
# arXiv 分类配置
arxiv:
  categories:
    - cs.CV     # 计算机视觉
    - cs.CL     # 计算与语言
    - cs.AI     # 人工智能
    - cs.LG     # 机器学习

# 关键词匹配（支持权重）
matching:
  keywords:
    "rag": 2.0        # 高权重 - 非常感兴趣
    "agent": 1.5
    "LLM": 1.0
  threshold: 3.0      # BM25 得分阈值
  top_k: 10           # 最大论文数量

# LLM 配置
llm:
  model_name: "gpt-4o"
  base_url: "https://api.openai.com/v1"
  batch_size: 3       # 每次处理 3 篇论文

# 邮件配置
email:
  smtp_server: "smtp.qq.com"
  smtp_port: 587
  sender: "your-email@qq.com"
  recipients:
    - "recipient@example.com"
```

### 命令行参数

```bash
python main.py [选项]

选项:
  -c, --config FILE     配置文件路径 (默认: config.yaml)
  -d, --date DATE       指定日期 (YYYY-MM-DD)
  -s, --skip-crawl      跳过爬取，使用已有数据
  -f, --force           强制爬取（忽略日期检查）
  -k, --keywords WORDS  临时指定关键词（逗号分隔）
  -t, --threshold N     BM25 得分阈值
  --top-k N             最大论文数量
```

示例：

```bash
# 使用默认配置运行
python main.py

# 指定日期运行
python main.py --date 2024-01-15

# 跳过爬取，使用已有数据测试总结和邮件
python main.py --skip-crawl

# 强制重新爬取（今日已爬取过时使用）
python main.py --force

# 临时修改关键词和数量
python main.py --keywords "LLM,RAG,agent" --top-k 5
```

---

## 📧 邮箱配置指南

### QQ 邮箱

1. 登录 [QQ 邮箱](https://mail.qq.com)
2. 进入 `设置` → `账户`
3. 找到 `POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务`
4. 开启 `POP3/SMTP服务`
5. 点击 `生成授权码`，按提示发送短信验证
6. 复制生成的授权码（16位字母）

配置：
- SMTP 服务器: `smtp.qq.com`
- 端口: `587`
- 密码: 使用授权码，不是登录密码

### 163 邮箱

1. 登录 [163 邮箱](https://mail.163.com)
2. 进入 `设置` → `POP3/SMTP/IMAP`
3. 开启 `SMTP服务`
4. 设置客户端授权密码

配置：
- SMTP 服务器: `smtp.163.com`
- 端口: `587`

### Gmail

1. 开启 [两步验证](https://myaccount.google.com/security)
2. 生成 [应用专用密码](https://myaccount.google.com/apppasswords)
3. 选择 "邮件" 和 "其他"，生成密码

配置：
- SMTP 服务器: `smtp.gmail.com`
- 端口: `587`

---

## 📊 支持的 arXiv 分类

| 分类 | 说明 |
|-----|------|
| cs.CV | 计算机视觉与模式识别 |
| cs.CL | 计算与语言（NLP） |
| cs.AI | 人工智能 |
| cs.LG | 机器学习 |
| cs.IR | 信息检索 |
| cs.NE | 神经与进化计算 |
| cs.RO | 机器人学 |
| cs.SE | 软件工程 |
| stat.ML | 统计机器学习 |

完整分类列表: https://arxiv.org/category_taxonomy

---

## 📁 项目结构

```
ArxivPaperNotation/
├── .github/
│   └── workflows/
│       └── daily_arxiv.yml    # GitHub Actions 工作流
├── crawler/                    # Scrapy 爬虫模块
│   ├── spiders/
│   │   └── arxiv.py           # arXiv 爬虫
│   ├── pipelines.py           # 数据处理管道
│   └── settings.py            # Scrapy 配置
├── data/                       # 数据目录（自动创建）
│   ├── jsonl/                 # 爬取的论文数据
│   └── digests/               # 生成的日报
├── logs/                       # 日志目录
├── config.yaml                 # 配置文件
├── config.yaml.example         # 配置文件模板
├── main.py                     # 主程序入口
├── crawl.py                    # 爬虫主程序
├── matcher.py                  # BM25 关键词匹配模块
├── summarizer.py               # LLM 总结模块
├── email_sender.py             # 邮件发送模块
├── config_loader.py            # 配置加载器
├── logger_setup.py             # 日志模块
├── requirements.txt            # 依赖列表
└── README.md
```

---

## 🔧 常见问题

### Q: 爬取失败怎么办？

- 检查网络连接是否正常
- arXiv 有时会限制访问频率，等待几分钟后重试
- 使用 `--force` 参数强制重新爬取

### Q: LLM 总结失败？

- 检查 API 密钥是否正确设置
- 确认 API 余额充足
- 检查 `LLM_BASE_URL` 是否正确
- 查看日志文件获取详细错误信息

### Q: 邮件发送失败？

- 确认 SMTP 设置正确
- QQ/163 邮箱需要使用**授权码**，不是登录密码
- 检查收件人地址格式是否正确
- Gmail 需要使用应用专用密码

### Q: GitHub Actions 运行失败？

- 检查 Secrets 是否全部正确配置
- JSON 格式的值需要用双引号，如 `["cs.CV", "cs.CL"]`
- 查看 Actions 运行日志定位具体错误

### Q: 如何修改运行时间？

编辑 `.github/workflows/daily_arxiv.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 8 * * *'  # UTC 时间，北京时间需要 -8 小时
```

常用时间对照：
- `0 0 * * *` = UTC 00:00 = 北京时间 08:00
- `0 8 * * *` = UTC 08:00 = 北京时间 16:00
- `0 14 * * *` = UTC 14:00 = 北京时间 22:00

---

## 📄 License

MIT License

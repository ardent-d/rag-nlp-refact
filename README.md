# RAG-NLP 智能文档处理系统

## 项目概述

本项目是一个完全自主实现的 RAG 系统，通过模块化设计实现了文档加载、解析、分块、向量化、存储、检索和生成等完整的 RAG 流程。系统支持多种文档格式和解析工具，提供了灵活的参数配置和统一的输出格式。

### 核心特性

#### 📄 文档处理
- **多格式支持**：PDF、Markdown 文档解析
- **多种解析工具**：PyMuPDF、PyPDF、Unstructured、PDF Plumber、Camelot
- **智能解析策略**：全文提取、分页解析、标题分段、结构化解析
- **表格识别**：使用 Camelot 进行精确的 PDF 表格提取

#### 🔧 文档分块
- **多种分块策略**：固定大小、基于页面、基于标题、语义分块
- **自适应参数**：支持自定义块大小、重叠度等参数
- **元数据丰富**：保留页码、标题层级、块ID等结构化信息

#### 🧠 向量化存储
- **多模型支持**：OpenAI、HuggingFace、Bedrock 等嵌入模型
- **向量数据库**：支持 Milvus、Chroma 等多种向量数据库
- **索引管理**：自动创建、删除、查询集合

#### 🔍 智能检索
- **相似度搜索**：基于向量相似度的智能匹配
- **多维度过滤**：支持阈值过滤、词数过滤等
- **结果排序**：按相似度分数智能排序

#### 🤖 内容生成
- **多模型支持**：DeepSeek、OpenAI、HuggingFace 等生成模型
- **上下文增强**：基于检索结果进行 RAG 生成
- **结果保存**：支持生成结果的持久化存储

#### 🎨 用户界面
- **现代化 UI**：基于 React + Tailwind CSS 的响应式界面
- **实时预览**：解析、分块、检索结果的实时展示
- **参数配置**：灵活的解析和分块参数调整

## 技术架构

### 技术栈
- **后端**：Python 3.11+ + FastAPI
- **前端**：React 18 + Vite + Tailwind CSS
- **向量数据库**：Milvus、Chroma
- **文档处理**：PyMuPDF、Camelot、Unstructured
- **AI 模型**：OpenAI、HuggingFace、Bedrock

### 项目架构

#### 后端架构
```
backend/
├── main.py                    # FastAPI 主入口文件
├── services/                  # 核心服务层
│   ├── loading_service.py     # 文档加载服务
│   ├── parsing_service.py     # 文档解析服务
│   ├── chunking_service.py    # 文档分块服务
│   ├── embedding_service.py   # 向量嵌入服务
│   ├── vector_store_service.py # 向量存储服务
│   ├── search_service.py      # 检索服务
│   └── generation_service.py  # 内容生成服务
├── utils/                     # 工具模块
│   ├── config.py             # 配置管理
│   └── model_utils.py        # 模型工具
├── 01-loaded-docs/           # 加载文档存储
├── 01-chunked-docs/          # 分块文档存储
├── 02-embedded-docs/         # 嵌入向量存储
├── 03-vector-store/          # 向量数据库文件
├── 04-search-results/        # 搜索结果存储
└── 05-generation-results/    # 生成结果存储
```

#### 前端架构
```
frontend/
├── src/
│   ├── pages/                # 页面组件
│   │   ├── LoadFile.jsx      # 文档加载页面
│   │   ├── ParseFile.jsx     # 文档解析页面
│   │   ├── ChunkFile.jsx     # 文档分块页面
│   │   ├── EmbeddingFile.jsx # 向量化页面
│   │   ├── Indexing.jsx      # 索引管理页面
│   │   ├── Search.jsx        # 检索页面
│   │   └── Generation.jsx    # 生成页面
│   ├── components/           # 通用组件
│   │   ├── Sidebar.jsx       # 侧边栏组件
│   │   └── RandomImage.jsx   # 占位图片组件
│   └── config/               # 配置文件
│       └── config.js         # API 配置
├── public/                   # 静态资源
└── package.json             # 项目依赖配置
```

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- 8GB+ RAM（推荐）
- 支持 CUDA 的 GPU（可选，用于加速）

### 1. 克隆项目
```bash
git clone <repository-url>
cd rag-nlp-two
```

### 2. 后端部署

#### 安装 Python 依赖
```bash
# Windows
pip install -r requirements_win.txt

# Ubuntu/MacOS
pip install -r requirements_ubun.txt
```

#### 配置环境变量
```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export OPENAI_API_KEY="your-openai-api-key"
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

#### 启动后端服务
```bash
cd backend
uvicorn main:app --reload --port 8001 --host 0.0.0.0
```

### 3. 前端部署

#### 安装依赖
```bash
cd frontend
npm install
```

#### 配置 API 地址
编辑 `frontend/src/config/config.js`：
```javascript
const config = {
  development: {
    apiBaseUrl: 'http://localhost:8001'
  },
  production: {
    apiBaseUrl: 'http://your-api-domain:8001'
  }
};
```

#### 启动前端服务
```bash
npm run dev
```

访问 http://localhost:5173 即可使用系统。

## 使用指南

### 1. 文档加载 (Load File)
- 支持 PDF、Markdown 文件上传
- 选择加载工具（PyMuPDF、Unstructured 等）
- 配置加载策略和参数
- 自动保存到 `01-loaded-docs/` 目录

### 2. 文档解析 (Parse File)
- 支持 PDF 和 Markdown 解析
- 多种解析方法：全文、分页、标题分段、结构化
- Camelot 表格提取功能
- 统一 JSON 输出格式

### 3. 文档分块 (Chunk File)
- 多种分块策略：固定大小、基于页面、语义分块
- 可配置块大小、重叠度等参数
- 保留元数据信息
- 保存到 `01-chunked-docs/` 目录

### 4. 向量化 (Embedding File)
- 支持多种嵌入模型
- 批量处理文档块
- 生成向量表示
- 保存到 `02-embedded-docs/` 目录

### 5. 索引管理 (Indexing)
- 支持 Milvus、Chroma 向量数据库
- 创建和管理集合
- 查看索引统计信息
- 删除不需要的索引

### 6. 智能检索 (Search)
- 基于向量相似度搜索
- 支持多维度过滤
- 实时结果预览
- 保存搜索结果

### 7. 内容生成 (Generation)
- 基于检索结果的 RAG 生成
- 支持多种生成模型
- 上下文增强回答
- 保存生成历史

## 配置说明

### 向量数据库配置
系统支持多种向量数据库：

#### Milvus
```python
# 适用于生产环境，支持分布式部署
provider = "milvus"
host = "localhost"
port = 19530
```

#### Chroma
```python
# 轻量级本地向量数据库
provider = "chroma"
persist_directory = "./03-vector-store/chroma"
```

### 模型配置
支持多种 AI 模型：

#### 嵌入模型
- OpenAI: `text-embedding-ada-002`
- HuggingFace: `sentence-transformers/all-MiniLM-L6-v2`
- Bedrock: `amazon.titan-embed-text-v1`

#### 生成模型
- DeepSeek: `deepseek-chat`、`deepseek-r1`
- OpenAI: `gpt-3.5-turbo`、`gpt-4`
- HuggingFace: 各种开源模型

## 常见问题

### 1. 依赖安装问题
```bash
# 如果遇到依赖冲突，建议使用虚拟环境
conda create -n rag-nlp python=3.11
conda activate rag-nlp
pip install -r requirements_win.txt
```

### 2. 向量数据库连接问题
```bash
# Milvus 需要先启动服务
docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone

# Chroma 会自动创建本地文件
```

### 3. 内存不足问题
- 减少批处理大小
- 使用更小的嵌入模型
- 增加系统内存

### 4. API 密钥配置
确保正确设置环境变量：
```bash
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="sk-..."
```

### 开发环境设置
1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

### 代码规范
- 使用 Python 类型注解
- 遵循 PEP 8 代码风格
- 添加适当的文档字符串
- 编写单元测试



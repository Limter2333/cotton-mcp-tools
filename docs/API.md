# Cotton MCP Tools - API Documentation

> MCP (Model Context Protocol) 工具服务接口文档
>
> 版本: 0.1.0

## 目录

- [概述](#概述)
- [环境变量配置](#环境变量配置)
- [工具列表](#工具列表)
- [示例工具](#示例工具)
- [UI 分析工具](#ui-分析工具)
- [OCR 文字识别工具](#ocr-文字识别工具)
- [小红书爬取工具](#小红书爬取工具)
- [错误处理](#错误处理)
- [数据模型](#数据模型)

---

## 概述

Cotton MCP Tools 是一个 MCP 工具服务，提供以下功能模块：

| 模块 | 功能 | 工具数量 |
|------|------|----------|
| Sample | 示例工具 | 2 |
| UI Analyzer | UI 截图分析与代码生成 | 1 |
| OCR | 图片文字识别（支持多后端） | 4 |
| Xiaohongshu | 小红书内容爬取与分析 | 5 |

### MCP 调用方式

通过 MCP 协议调用工具，请求格式：

```json
{
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}
```

---

## 环境变量配置

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `COTTON_DEBUG` | 调试模式 | `false` | 否 |
| `COTTON_LOG_LEVEL` | 日志级别 | `INFO` | 否 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - | 视功能而定 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | - | 视功能而定 |
| `MULTIMODAL_PROVIDER` | 默认多模态提供商 | `openai` | 否 |
| `MULTIMODAL_MODEL` | 默认模型 | `gpt-4o` | 否 |
| `XHS_COOKIE` | 小红书登录 Cookie | - | 小红书功能必需 |
| `XHS_PROXY` | 小红书代理地址 | - | 否 |
| `OCR_BACKEND` | 默认 OCR 后端 | `llm` | 否 |
| `OCR_LANGUAGES` | OCR 语言设置 | `ch,en` | 否 |

---

## 工具列表

### 总览

| 工具名 | 模块 | 说明 |
|--------|------|------|
| `add` | Sample | 两数相加 |
| `greet` | Sample | 生成问候语 |
| `analyze_ui` | UI Analyzer | UI 截图分析生成代码 |
| `ocr_recognize_text` | OCR | 单张图片文字识别 |
| `ocr_recognize_batch` | OCR | 批量图片文字识别 |
| `ocr_detect_text_regions` | OCR | 检测文字位置坐标 |
| `ocr_list_backends` | OCR | 列出可用 OCR 后端 |
| `xhs_search_notes` | XHS | 搜索小红书笔记 |
| `xhs_get_note_detail` | XHS | 获取笔记详情 |
| `xhs_get_note_comments` | XHS | 获取笔记评论 |
| `xhs_get_creator_notes` | XHS | 获取创作者笔记 |
| `xhs_analyze_note_with_ocr` | XHS | 笔记图片 OCR 分析 |

---

## 示例工具

### `add`

两数相加。

**参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `a` | int | 是 | 第一个数 |
| `b` | int | 是 | 第二个数 |

**返回：** `int` - 两数之和

**调用示例：**

```json
{
  "name": "add",
  "arguments": { "a": 1, "b": 2 }
}
```

**返回示例：**

```
3
```

---

### `greet`

生成问候语。

**参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 要问候的名字 |

**返回：** `string` - 问候语

**调用示例：**

```json
{
  "name": "greet",
  "arguments": { "name": "World" }
}
```

**返回示例：**

```
Hello, World! Welcome to Cotton MCP Tools.
```

---

## UI 分析工具

### `analyze_ui`

分析 UI 截图并生成前端代码。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | string | 是 | - | 本地图片路径或 HTTP(S) URL |
| `prompt` | string | 否 | "Analyze this UI screenshot..." | 分析指令 |
| `framework` | string | 否 | `html` | 目标框架：`html`、`react`、`vue` |
| `model` | string | 否 | - | 模型覆盖（如 `gpt-4o`、`claude-3-opus`） |

**返回：** `string` - 生成的前端代码

**调用示例：**

```json
{
  "name": "analyze_ui",
  "arguments": {
    "image": "https://example.com/screenshot.png",
    "prompt": "Generate a responsive login page",
    "framework": "react"
  }
}
```

---

## OCR 文字识别工具

### `ocr_recognize_text`

从图片中识别文字内容。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | string | 是 | - | 本地图片路径或 HTTP(S) URL |
| `language` | string | 否 | `zh` | 语言代码：`zh`（中文）、`en`（英文）等 |
| `backend` | string | 否 | `llm` | OCR 后端：`llm`、`paddleocr`、`easyocr` |
| `model` | string | 否 | - | LLM 后端的模型覆盖 |

**返回：** JSON 格式的 OCR 结果

**调用示例：**

```json
{
  "name": "ocr_recognize_text",
  "arguments": {
    "image": "https://example.com/document.jpg",
    "language": "zh",
    "backend": "paddleocr"
  }
}
```

**返回示例：**

```json
{
  "texts": [
    {
      "content": "你好世界",
      "confidence": 0.95,
      "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]],
      "type": "body"
    },
    {
      "content": "这是一段测试文字",
      "confidence": 0.92,
      "bbox": [[10, 40], [200, 40], [200, 60], [10, 60]],
      "type": "body"
    }
  ],
  "full_text": "你好世界\n这是一段测试文字",
  "language": "zh",
  "has_text": true,
  "backend": "paddleocr"
}
```

---

### `ocr_recognize_batch`

批量识别多张图片中的文字。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `images` | string[] | 是 | - | 图片路径或 URL 列表 |
| `language` | string | 否 | `zh` | 语言代码 |
| `backend` | string | 否 | `llm` | OCR 后端 |
| `model` | string | 否 | - | LLM 后端的模型覆盖 |

**返回：** JSON 格式的批量 OCR 结果

**调用示例：**

```json
{
  "name": "ocr_recognize_batch",
  "arguments": {
    "images": [
      "https://example.com/img1.jpg",
      "https://example.com/img2.jpg"
    ],
    "backend": "paddleocr"
  }
}
```

**返回示例：**

```json
{
  "total": 2,
  "backend": "paddleocr",
  "results": [
    {
      "image": "https://example.com/img1.jpg",
      "texts": [...],
      "full_text": "...",
      "has_text": true,
      "backend": "paddleocr"
    },
    {
      "image": "https://example.com/img2.jpg",
      "texts": [...],
      "full_text": "...",
      "has_text": true,
      "backend": "paddleocr"
    }
  ]
}
```

---

### `ocr_detect_text_regions`

检测图片中的文字区域位置（返回坐标）。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | string | 是 | - | 本地图片路径或 HTTP(S) URL |
| `language` | string | 否 | `zh` | 语言代码 |
| `backend` | string | 否 | `paddleocr` | OCR 后端（仅支持 `paddleocr`、`easyocr`） |

**返回：** JSON 格式的文字区域坐标

**调用示例：**

```json
{
  "name": "ocr_detect_text_regions",
  "arguments": {
    "image": "https://example.com/document.jpg",
    "backend": "paddleocr"
  }
}
```

**返回示例：**

```json
{
  "regions": [
    {
      "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]],
      "confidence": 0.95
    },
    {
      "bbox": [[10, 40], [200, 40], [200, 60], [10, 60]],
      "confidence": 0.92
    }
  ],
  "total_regions": 2
}
```

---

### `ocr_list_backends`

列出可用的 OCR 后端及其状态。

**参数：** 无

**调用示例：**

```json
{
  "name": "ocr_list_backends",
  "arguments": {}
}
```

**返回示例：**

```json
{
  "total": 3,
  "backends": [
    {
      "name": "llm",
      "available": true,
      "description": "Multimodal LLM (OpenAI/Claude) - always available, best quality",
      "install_command": null
    },
    {
      "name": "paddleocr",
      "available": true,
      "description": "PaddleOCR - fast local inference, good for Chinese/English",
      "install_command": "pip install paddlepaddle paddleocr"
    },
    {
      "name": "easyocr",
      "available": false,
      "description": "EasyOCR - simple, supports 80+ languages",
      "install_command": "pip install easyocr"
    }
  ]
}
```

---

## 小红书爬取工具

### 前置条件

设置环境变量：

```bash
export XHS_COOKIE="your_xiaohongshu_cookie"  # 必需
export XHS_PROXY="http://proxy:8080"          # 可选，代理
```

---

### `xhs_search_notes`

按关键词搜索小红书笔记。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keyword` | string | 是 | - | 搜索关键词 |
| `page` | int | 否 | `1` | 页码 |
| `sort` | string | 否 | `general` | 排序：`general`、`latest`、`popularity_descending` |
| `note_type` | string | 否 | `all` | 类型：`all`、`video`、`image` |

**调用示例：**

```json
{
  "name": "xhs_search_notes",
  "arguments": {
    "keyword": "美食推荐",
    "page": 1,
    "sort": "popularity_descending",
    "note_type": "all"
  }
}
```

**返回示例：**

```json
{
  "keyword": "美食推荐",
  "page": 1,
  "total": 20,
  "notes": [
    {
      "note_id": "abc123",
      "title": "超好吃的餐厅推荐",
      "desc": "...",
      "type": "normal",
      "user": {
        "user_id": "user123",
        "nickname": "美食达人"
      },
      "image_list": ["https://..."],
      "video_url": "",
      "tag_list": ["美食", "餐厅"],
      "liked_count": 1000,
      "collected_count": 500,
      "comment_count": 200,
      "share_count": 100,
      "time": 1700000000,
      "last_update_time": 1700001000,
      "note_url": "https://www.xiaohongshu.com/explore/abc123"
    }
  ]
}
```

---

### `xhs_get_note_detail`

获取小红书笔记详情。

**参数：**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `note_id` | string | 是 | 笔记 ID |

**调用示例：**

```json
{
  "name": "xhs_get_note_detail",
  "arguments": {
    "note_id": "abc123"
  }
}
```

**返回示例：**

```json
{
  "note_id": "abc123",
  "title": "超好吃的餐厅推荐",
  "desc": "今天去了一家超好吃的餐厅...",
  "type": "normal",
  "user": {
    "user_id": "user123",
    "nickname": "美食达人"
  },
  "image_list": [
    "https://sns-img-bd.xhscdn.com/img1.jpg",
    "https://sns-img-bd.xhscdn.com/img2.jpg"
  ],
  "video_url": "",
  "tag_list": ["美食", "餐厅", "推荐"],
  "liked_count": 1000,
  "collected_count": 500,
  "comment_count": 200,
  "share_count": 100,
  "time": 1700000000,
  "last_update_time": 1700001000,
  "note_url": "https://www.xiaohongshu.com/explore/abc123"
}
```

---

### `xhs_get_note_comments`

获取小红书笔记评论。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `note_id` | string | 是 | - | 笔记 ID |
| `max_comments` | int | 否 | `20` | 最大返回评论数 |

**调用示例：**

```json
{
  "name": "xhs_get_note_comments",
  "arguments": {
    "note_id": "abc123",
    "max_comments": 10
  }
}
```

**返回示例：**

```json
{
  "note_id": "abc123",
  "total": 10,
  "comments": [
    {
      "comment_id": "comment_001",
      "content": "看起来好好吃！",
      "user": {
        "user_id": "user456",
        "nickname": "吃货小王"
      },
      "create_time": 1700002000,
      "like_count": 50,
      "sub_comment_count": 3,
      "parent_comment_id": "",
      "pictures": []
    }
  ]
}
```

---

### `xhs_get_creator_notes`

获取小红书创作者的笔记列表。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `user_id` | string | 是 | - | 创作者用户 ID |
| `max_notes` | int | 否 | `20` | 最大返回笔记数 |

**调用示例：**

```json
{
  "name": "xhs_get_creator_notes",
  "arguments": {
    "user_id": "user123",
    "max_notes": 10
  }
}
```

**返回示例：**

```json
{
  "user_id": "user123",
  "total": 10,
  "notes": [
    {
      "note_id": "abc123",
      "title": "...",
      "desc": "...",
      "type": "normal",
      "user": { "user_id": "user123", "nickname": "美食达人" },
      "image_list": ["..."],
      "video_url": "",
      "tag_list": ["..."],
      "liked_count": 1000,
      "collected_count": 500,
      "comment_count": 200,
      "share_count": 100,
      "time": 1700000000,
      "last_update_time": 1700001000,
      "note_url": "https://www.xiaohongshu.com/explore/abc123"
    }
  ]
}
```

---

### `xhs_analyze_note_with_ocr`

获取小红书笔记详情并使用 OCR 分析图片中的文字。

**参数：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `note_id` | string | 是 | - | 笔记 ID |
| `max_images` | int | 否 | `5` | 最大分析图片数 |
| `language` | string | 否 | `zh` | OCR 语言 |
| `model` | string | 否 | - | OCR 模型覆盖 |

**调用示例：**

```json
{
  "name": "xhs_analyze_note_with_ocr",
  "arguments": {
    "note_id": "abc123",
    "max_images": 3,
    "language": "zh"
  }
}
```

**返回示例：**

```json
{
  "note": {
    "note_id": "abc123",
    "title": "超好吃的餐厅推荐",
    "desc": "...",
    "type": "normal",
    "user": { "user_id": "user123", "nickname": "美食达人" },
    "image_list": ["https://...", "https://..."],
    "video_url": "",
    "tag_list": ["美食"],
    "liked_count": 1000,
    "collected_count": 500,
    "comment_count": 200,
    "share_count": 100,
    "time": 1700000000,
    "last_update_time": 1700001000,
    "note_url": "https://www.xiaohongshu.com/explore/abc123"
  },
  "ocr_analysis": {
    "total_images": 2,
    "analyzed_images": 2,
    "images_with_text": 1,
    "results": [
      {
        "texts": [...],
        "full_text": "图片中的文字内容",
        "has_text": true,
        "backend": "llm",
        "image_url": "https://...",
        "image_index": 1
      }
    ]
  },
  "summary": {
    "title": "超好吃的餐厅推荐",
    "description": "...",
    "tags": ["美食"],
    "ocr_text_count": 1,
    "combined_text": "标题: 超好吃的餐厅推荐\n\n描述: ...\n\n标签: 美食\n\n图片文字内容:\n图片中的文字内容",
    "engagement": {
      "likes": 1000,
      "collects": 500,
      "comments": 200,
      "shares": 100
    }
  }
}
```

---

## 错误处理

### 错误响应格式

所有工具在出错时返回字符串格式的错误信息：

```
Error: <错误描述>
```

或 JSON 格式的错误：

```json
{
  "error": "错误描述",
  "has_text": false
}
```

### 常见错误类型

| 错误 | 说明 | 解决方案 |
|------|------|----------|
| `XHS cookie is required` | 小红书 Cookie 未配置 | 设置 `XHS_COOKIE` 环境变量 |
| `Backend 'xxx' is not installed` | OCR 后端未安装 | 安装对应依赖 |
| `Invalid backend 'xxx'` | 无效的 OCR 后端 | 使用 `llm`、`paddleocr`、`easyocr` |
| `Image file not found` | 图片文件不存在 | 检查文件路径 |
| `Note not found` | 笔记不存在 | 检查笔记 ID |
| `XHS account security restriction` | 账号受限 | 更换 Cookie 或等待 |

---

## 数据模型

### NoteData（笔记数据）

```typescript
interface NoteData {
  note_id: string;          // 笔记 ID
  title: string;            // 标题
  desc: string;             // 描述
  type: string;             // 类型: "normal" | "video"
  user: {
    user_id: string;        // 用户 ID
    nickname: string;       // 昵称
  };
  image_list: string[];     // 图片 URL 列表
  video_url: string;        // 视频 URL
  tag_list: string[];       // 标签列表
  liked_count: number;      // 点赞数
  collected_count: number;  // 收藏数
  comment_count: number;    // 评论数
  share_count: number;      // 分享数
  time: number;             // 发布时间戳
  last_update_time: number; // 最后更新时间戳
  note_url: string;         // 笔记链接
}
```

### CommentData（评论数据）

```typescript
interface CommentData {
  comment_id: string;       // 评论 ID
  content: string;          // 评论内容
  user: {
    user_id: string;        // 用户 ID
    nickname: string;       // 昵称
  };
  create_time: number;      // 创建时间戳
  like_count: number;       // 点赞数
  sub_comment_count: number;// 子评论数
  parent_comment_id: string;// 父评论 ID
  pictures: string[];       // 评论图片
}
```

### OCRResult（OCR 结果）

```typescript
interface OCRResult {
  texts: TextBlock[];       // 文字块列表
  full_text: string;        // 完整文字
  language: string;         // 语言
  has_text: boolean;        // 是否有文字
  backend: string;          // 使用的后端
}

interface TextBlock {
  content: string;          // 文字内容
  confidence: number;       // 置信度 (0-1)
  bbox?: number[][];        // 坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
  type: string;             // 类型: "header" | "body" | "caption"
}
```

---

## OCR 后端对比

| 后端 | 安装 | 速度 | 质量 | 坐标 | 语言 |
|------|------|------|------|------|------|
| `llm` | 已内置 | 慢 | ⭐⭐⭐⭐⭐ | ❌ | 全部 |
| `paddleocr` | `pip install paddlepaddle paddleocr` | 快 | ⭐⭐⭐⭐ | ✅ | 中英文 |
| `easyocr` | `pip install easyocr` | 中 | ⭐⭐⭐ | ✅ | 80+ |

---

## 快速开始

### 1. 启动服务

```bash
# 安装
pip install -e .

# 设置环境变量
export OPENAI_API_KEY="your_key"
export XHS_COOKIE="your_cookie"  # 小红书功能需要

# 启动
cotton-mcp-tools
```

### 2. MCP 客户端配置

```json
{
  "mcpServers": {
    "cotton-mcp-tools": {
      "command": "cotton-mcp-tools",
      "env": {
        "OPENAI_API_KEY": "your_key",
        "XHS_COOKIE": "your_cookie"
      }
    }
  }
}
```

### 3. 调用示例

```python
# Python MCP 客户端示例
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # 搜索小红书笔记
        result = await session.call_tool(
            "xhs_search_notes",
            arguments={"keyword": "美食", "page": 1}
        )
        print(result)

        # OCR 识别
        result = await session.call_tool(
            "ocr_recognize_text",
            arguments={"image": "https://example.com/img.jpg", "backend": "llm"}
        )
        print(result)
```

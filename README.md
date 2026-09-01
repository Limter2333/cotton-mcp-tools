# Cotton MCP Tools

棉花 MCP 工具集 - 一个 Model Context Protocol (MCP) 工具服务项目

## 项目简介

Cotton MCP Tools 是一个基于 Python 的 MCP 服务项目，提供各种实用工具供 AI 助手调用。

## 快速开始

### 环境要求

- Python >= 3.10

### 安装依赖

```bash
pip install -e .
```

开发模式安装（包含开发依赖）：

```bash
pip install -e ".[dev]"
```

### 启动服务

```bash
# 通过命令行入口
cotton-mcp-tools

# 或直接运行
python -m cotton_mcp_tools.main
```

## 项目结构

```
cotton-mcp-tools/
├── src/
│   └── cotton_mcp_tools/
│       ├── __init__.py          # 包初始化
│       ├── main.py              # MCP 服务入口
│       ├── tools/               # MCP 工具模块
│       │   ├── __init__.py      # 工具注册入口
│       │   └── sample.py        # 示例工具
│       └── utils/               # 工具函数
│           ├── __init__.py
│           └── config.py        # 配置管理
├── tests/                       # 测试文件
│   ├── __init__.py
│   └── test_sample.py           # 示例工具测试
├── pyproject.toml               # 项目配置与依赖
├── .gitignore
└── README.md
```

## MCP 工具列表

| 工具 | 说明 |
|------|------|
| `add` | 两数相加 |
| `greet` | 生成问候语 |

## 开发指南

### 添加新工具

1. 在 `src/cotton_mcp_tools/tools/` 下创建新模块
2. 实现工具函数并使用 `@server.tool()` 装饰器
3. 在 `tools/__init__.py` 中注册新工具

示例：

```python
# src/cotton_mcp_tools/tools/my_tool.py
from mcp.server.fastmcp import FastMCP

def register_my_tools(server: FastMCP) -> None:
    @server.tool()
    def my_tool(param: str) -> str:
        """工具描述。

        Args:
            param: 参数说明

        Returns:
            返回值说明
        """
        return f"Result: {param}"
```

然后在 `tools/__init__.py` 中添加注册：

```python
from cotton_mcp_tools.tools.my_tool import register_my_tools

def register_all_tools(server: FastMCP) -> None:
    register_sample_tools(server)
    register_my_tools(server)  # 添加这行
```

### 运行测试

```bash
pytest
```

### 代码检查

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## 许可证

MIT License

## 联系方式

- 作者: Sheven

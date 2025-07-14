#!/usr/bin/env python3
"""
测试新的解析功能
"""

import os
import sys
import json
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.parsing_service import ParsingService

def test_pdf_parsing():
    """测试PDF解析功能"""
    print("=== 测试PDF解析功能 ===")
    
    # 检查是否有测试PDF文件
    test_pdf = "temp/test.pdf"
    if not os.path.exists(test_pdf):
        print(f"测试文件不存在: {test_pdf}")
        return
    
    parsing_service = ParsingService()
    metadata = {
        "filename": "test.pdf",
        "original_file_size": 1024,
        "processing_date": datetime.now().isoformat()
    }
    
    try:
        # 测试PyMuPDF解析
        print("\n1. 测试PyMuPDF解析...")
        result = parsing_service.parse_document(
            file_path=test_pdf,
            file_type="pdf",
            tool="pymupdf",
            method="all_text",
            metadata=metadata
        )
        print(f"解析成功: {len(result['content'])} 个内容块")
        print(f"元数据: {result['metadata']}")
        
        # 测试Camelot解析
        print("\n2. 测试Camelot解析...")
        result = parsing_service.parse_document(
            file_path=test_pdf,
            file_type="pdf",
            tool="camelot",
            method="text_and_tables",
            metadata=metadata
        )
        print(f"解析成功: {len(result['content'])} 个内容块")
        print(f"元数据: {result['metadata']}")
        
    except Exception as e:
        print(f"PDF解析测试失败: {str(e)}")

def test_markdown_parsing():
    """测试Markdown解析功能"""
    print("\n=== 测试Markdown解析功能 ===")
    
    # 创建测试Markdown文件
    test_md = "temp/test.md"
    test_content = """# 测试文档

这是一个测试Markdown文档。

## 第一章

这是第一章的内容。

### 1.1 小节

- 列表项1
- 列表项2
- 列表项3

## 第二章

```python
def hello_world():
    print("Hello, World!")
```

这是第二章的内容。
"""
    
    # 写入测试文件
    os.makedirs("temp", exist_ok=True)
    with open(test_md, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    parsing_service = ParsingService()
    metadata = {
        "filename": "test.md",
        "original_file_size": len(test_content),
        "processing_date": datetime.now().isoformat()
    }
    
    try:
        # 测试Markdown结构化解析
        print("\n1. 测试Markdown结构化解析...")
        result = parsing_service.parse_document(
            file_path=test_md,
            file_type="markdown",
            tool="markdown",
            method="structured",
            metadata=metadata
        )
        print(f"解析成功: {len(result['content'])} 个内容块")
        print(f"元数据: {result['metadata']}")
        
        # 显示解析结果
        for i, item in enumerate(result['content']):
            print(f"\n内容块 {i+1}:")
            print(f"  类型: {item['type']}")
            if 'level' in item:
                print(f"  级别: {item['level']}")
            print(f"  内容: {item['content'][:100]}...")
        
    except Exception as e:
        print(f"Markdown解析测试失败: {str(e)}")
    
    # 清理测试文件
    if os.path.exists(test_md):
        os.remove(test_md)

def main():
    """主测试函数"""
    print("开始测试新的解析功能...")
    
    # 测试PDF解析
    test_pdf_parsing()
    
    # 测试Markdown解析
    test_markdown_parsing()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main() 
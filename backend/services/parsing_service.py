import logging
from typing import Dict, List
import fitz  # PyMuPDF
import pandas as pd
from datetime import datetime
import re
import camelot  # 用于PDF表格提取

logger = logging.getLogger(__name__)

class ParsingService:
    """
    文档解析服务类
    
    该类提供多种解析策略来提取和构建文档内容，包括：
    - PDF文档解析（全文提取、逐页解析、基于标题的分段、文本和表格混合解析）
    - Markdown文档解析（标题、段落、代码块、列表等结构化内容）
    - PDF表格提取（使用Camelot进行精确表格识别）
    """

    def parse_document(self, file_path: str, file_type: str, tool: str, method: str, metadata: dict) -> dict:
        """
        根据文件类型和工具选择解析方法

        参数:
            file_path (str): 文件路径
            file_type (str): 文件类型 ('pdf', 'markdown')
            tool (str): 解析工具 ('pymupdf', 'camelot', 'markdown')
            method (str): 解析方法
            metadata (dict): 文档元数据

        返回:
            dict: 解析后的文档数据，包括元数据和结构化内容
        """
        try:
            if file_type == "pdf":
                if tool == "camelot":
                    return self.parse_pdf_with_camelot(file_path, method, metadata)
                else:
                    # 使用现有的PDF解析逻辑
                    return self.parse_pdf(file_path, method, metadata)
            elif file_type == "markdown":
                return self.parse_markdown(file_path, method, metadata)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            logger.error(f"Error in parse_document: {str(e)}")
            raise

    def parse_pdf_with_camelot(self, file_path: str, method: str, metadata: dict) -> dict:
        """
        使用Camelot解析PDF文档，专门提取表格和文本

        参数:
            file_path (str): PDF文件路径
            method (str): 解析方法
            metadata (dict): 文档元数据

        返回:
            dict: 解析后的文档数据
        """
        try:
            # 使用PyMuPDF提取文本内容
            doc = fitz.open(file_path)
            page_map = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                page_map.append({
                    "page": page_num + 1,
                    "text": text
                })
            
            doc.close()
            
            # 使用Camelot提取表格
            tables = camelot.read_pdf(file_path, pages='all')
            
            parsed_content = []
            
            if method == "tables_only":
                # 仅提取表格
                for table in tables:
                    parsed_content.append({
                        "type": "table",
                        "content": table.df.to_dict('records'),
                        "accuracy": table.accuracy,
                        "whitespace": table.whitespace,
                        "page": table.page
                    })
            elif method == "text_and_tables":
                # 提取文本和表格
                # 先添加文本内容
                for page in page_map:
                    parsed_content.append({
                        "type": "text",
                        "content": page["text"],
                        "page": page["page"]
                    })
                
                # 再添加表格内容
                for table in tables:
                    parsed_content.append({
                        "type": "table",
                        "content": table.df.to_dict('records'),
                        "accuracy": table.accuracy,
                        "whitespace": table.whitespace,
                        "page": table.page
                    })
            else:
                # 默认使用现有的PDF解析方法
                return self.parse_pdf(file_path, method, metadata)
            
            # 创建文档级元数据
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "total_pages": len(page_map),
                    "parsing_method": method,
                    "parsing_tool": "camelot",
                    "total_tables": len(tables),
                    "timestamp": datetime.now().isoformat()
                },
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_pdf_with_camelot: {str(e)}")
            raise

    def parse_markdown(self, file_path: str, method: str, metadata: dict) -> dict:
        """
        解析Markdown文档，提取结构化内容

        参数:
            file_path (str): Markdown文件路径
            method (str): 解析方法 ('all_text', 'by_sections', 'structured')
            metadata (dict): 文档元数据

        返回:
            dict: 解析后的文档数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_content = []
            
            if method == "all_text":
                parsed_content = self._parse_markdown_all_text(content)
            elif method == "by_sections":
                parsed_content = self._parse_markdown_by_sections(content)
            elif method == "structured":
                parsed_content = self._parse_markdown_structured(content)
            else:
                raise ValueError(f"Unsupported markdown parsing method: {method}")
            
            # 创建文档级元数据
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "parsing_method": method,
                    "parsing_tool": "markdown",
                    "content_length": len(content),
                    "timestamp": datetime.now().isoformat()
                },
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_markdown: {str(e)}")
            raise

    def _parse_markdown_all_text(self, content: str) -> list:
        """
        将Markdown文档作为纯文本提取

        参数:
            content (str): Markdown文档内容

        返回:
            list: 包含文本内容的字典列表
        """
        return [{
            "type": "text",
            "content": content,
            "section": "all"
        }]

    def _parse_markdown_by_sections(self, content: str) -> list:
        """
        按章节解析Markdown文档

        参数:
            content (str): Markdown文档内容

        返回:
            list: 包含章节内容的字典列表
        """
        sections = []
        lines = content.split('\n')
        current_section = {"title": "Introduction", "content": []}
        
        for line in lines:
            # 检测标题行
            if line.startswith('#'):
                # 保存前一个章节
                if current_section["content"]:
                    sections.append({
                        "type": "section",
                        "title": current_section["title"],
                        "content": '\n'.join(current_section["content"]),
                        "level": current_section.get("level", 1)
                    })
                
                # 开始新章节
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {"title": title, "content": [], "level": level}
            else:
                current_section["content"].append(line)
        
        # 添加最后一个章节
        if current_section["content"]:
            sections.append({
                "type": "section",
                "title": current_section["title"],
                "content": '\n'.join(current_section["content"]),
                "level": current_section.get("level", 1)
            })
        
        return sections

    def _parse_markdown_structured(self, content: str) -> list:
        """
        结构化解析Markdown文档，识别标题、段落、代码块、列表等

        参数:
            content (str): Markdown文档内容

        返回:
            list: 包含结构化内容的字典列表
        """
        structured_content = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测标题
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                structured_content.append({
                    "type": "heading",
                    "content": title,
                    "level": level
                })
            
            # 检测代码块
            elif line.startswith('```'):
                code_block = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_block.append(lines[i])
                    i += 1
                
                if code_block:
                    structured_content.append({
                        "type": "code_block",
                        "content": '\n'.join(code_block),
                        "language": line[3:] if len(line) > 3 else ""
                    })
            
            # 检测列表项
            elif line.startswith(('- ', '* ', '+ ')) or re.match(r'^\d+\.', line):
                list_items = []
                while i < len(lines) and (lines[i].strip().startswith(('- ', '* ', '+ ')) or 
                                        re.match(r'^\d+\.', lines[i].strip())):
                    list_items.append(lines[i].strip())
                    i += 1
                
                if list_items:
                    structured_content.append({
                        "type": "list",
                        "content": list_items,
                        "list_type": "ordered" if re.match(r'^\d+\.', list_items[0]) else "unordered"
                    })
                    continue
            
            # 检测段落
            elif line:
                paragraph_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '- ', '* ', '+ ', '```')) and not re.match(r'^\d+\.', lines[i].strip()):
                    paragraph_lines.append(lines[i])
                    i += 1
                
                if paragraph_lines:
                    structured_content.append({
                        "type": "paragraph",
                        "content": '\n'.join(paragraph_lines)
                    })
                    continue
            
            i += 1
        
        return structured_content

    def parse_pdf(self, file_path: str, method: str, metadata: dict) -> dict:
        """
        使用指定方法解析PDF文档

        参数:
            file_path (str): PDF文件路径
            method (str): 解析方法 ('all_text', 'by_pages', 'by_titles', 或 'text_and_tables')
            metadata (dict): 文档元数据，包括文件名和其他属性

        返回:
            dict: 解析后的文档数据，包括元数据和结构化内容

        异常:
            ValueError: 当page_map为空或指定了不支持的解析方法时抛出
        """
        try:
            # 使用PyMuPDF提取页面内容
            doc = fitz.open(file_path)
            page_map = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                page_map.append({
                    "page": page_num + 1,
                    "text": text
                })
            
            doc.close()
            
            if not page_map:
                raise ValueError("No content extracted from PDF.")
            
            parsed_content = []
            total_pages = len(page_map)
            
            if method == "all_text":
                parsed_content = self._parse_all_text(page_map)
            elif method == "by_pages":
                parsed_content = self._parse_by_pages(page_map)
            elif method == "by_titles":
                parsed_content = self._parse_by_titles(page_map)
            elif method == "text_and_tables":
                parsed_content = self._parse_text_and_tables(page_map)
            else:
                raise ValueError(f"Unsupported parsing method: {method}")
                
            # Create document-level metadata
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "total_pages": total_pages,
                    "parsing_method": method,
                    "parsing_tool": "pymupdf",
                    "timestamp": datetime.now().isoformat()
                },
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_pdf: {str(e)}")
            raise

    def _parse_all_text(self, page_map: list) -> list:
        """
        将文档中的所有文本内容提取为连续流

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带页码的文本内容的字典列表
        """
        return [{
            "type": "Text",
            "content": page["text"],
            "page": page["page"]
        } for page in page_map]

    def _parse_by_pages(self, page_map: list) -> list:
        """
        逐页解析文档，保持页面边界

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带页码的分页内容的字典列表
        """
        parsed_content = []
        for page in page_map:
            parsed_content.append({
                "type": "Page",
                "page": page["page"],
                "content": page["text"]
            })
        return parsed_content

    def _parse_by_titles(self, page_map: list) -> list:
        """
        通过识别标题来解析文档并将内容组织成章节

        使用简单的启发式方法识别标题：
        长度小于60个字符且全部大写的行被视为章节标题

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带标题和页码的分章节内容的字典列表
        """
        parsed_content = []
        current_title = None
        current_content = []

        for page in page_map:
            lines = page["text"].split('\n')
            for line in lines:
                # Simple heuristic: consider lines with less than 60 chars and all caps as titles
                if len(line.strip()) < 60 and line.isupper():
                    if current_title:
                        parsed_content.append({
                            "type": "section",
                            "title": current_title,
                            "content": '\n'.join(current_content),
                            "page": page["page"]
                        })
                    current_title = line.strip()
                    current_content = []
                else:
                    current_content.append(line)

        # Add the last section
        if current_title:
            parsed_content.append({
                "type": "section",
                "title": current_title,
                "content": '\n'.join(current_content),
                "page": page["page"]
            })

        return parsed_content

    def _parse_text_and_tables(self, page_map: list) -> list:
        """
        通过分离文本和表格内容来解析文档

        使用基本的表格检测启发式方法（存在'|'或制表符）
        来识别潜在的表格内容

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含分离的文本和表格内容（带页码）的字典列表
        """
        parsed_content = []
        for page in page_map:
            # Extract tables using tabula-py or similar library
            # For this example, we'll just simulate table detection
            content = page["text"]
            if '|' in content or '\t' in content:
                parsed_content.append({
                    "type": "table",
                    "content": content,
                    "page": page["page"]
                })
            else:
                parsed_content.append({
                    "type": "text",
                    "content": content,
                    "page": page["page"]
                })
        return parsed_content 
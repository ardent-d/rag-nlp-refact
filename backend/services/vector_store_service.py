import os
from datetime import datetime
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
from pymilvus import connections, utility
from pymilvus import Collection, DataType, FieldSchema, CollectionSchema
from utils.config import VectorDBProvider, MILVUS_CONFIG, CHROMA_CONFIG  # Updated import
from pypinyin import lazy_pinyin, Style
import re
# 新增Chroma导入
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)

class VectorDBConfig:
    """
    向量数据库配置类，用于存储和管理向量数据库的配置信息
    """
    def __init__(self, provider: str, index_mode: str):
        self.provider = provider
        self.index_mode = index_mode
        self.milvus_uri = MILVUS_CONFIG["uri"]
        self.chroma_persist_dir = CHROMA_CONFIG["persist_directory"]

    def _get_milvus_index_type(self, index_mode: str) -> str:
        return MILVUS_CONFIG["index_types"].get(index_mode, "FLAT")
    def _get_milvus_index_params(self, index_mode: str) -> Dict[str, Any]:
        return MILVUS_CONFIG["index_params"].get(index_mode, {})
    def _get_chroma_index_params(self, index_mode: str) -> Dict[str, Any]:
        return CHROMA_CONFIG["index_modes"].get(index_mode, {})

class VectorStoreService:
    def __init__(self):
        self.initialized_dbs = {}
        os.makedirs("03-vector-store", exist_ok=True)

    def _init_chroma_client(self):
        if chromadb is None:
            raise ImportError("chromadb 未安装，请先安装 chromadb")
        client = chromadb.Client(ChromaSettings(
            persist_directory=CHROMA_CONFIG["persist_directory"]
        ))
        return client

    def _sanitize_collection_name(self, name: str) -> str:
        # 只保留字母、数字、下划线、短横线
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # 去掉连续的下划线
        name = re.sub(r'_+', '_', name)
        # 去掉开头非字母数字
        name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
        # 去掉结尾非字母数字
        name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
        # 长度限制
        if len(name) < 3:
            name = (name + 'abc')[:3]
        if len(name) > 63:
            name = name[:63]
        return name

    def index_embeddings(self, embedding_file: str, config: VectorDBConfig) -> Dict[str, Any]:
        start_time = datetime.now()
        embeddings_data = self._load_embeddings(embedding_file)
        if config.provider == VectorDBProvider.MILVUS:
            result = self._index_to_milvus(embeddings_data, config)
        elif config.provider == VectorDBProvider.CHROMA:
            result = self._index_to_chroma(embeddings_data, config)
        else:
            raise ValueError(f"不支持的向量数据库: {config.provider}")
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        return {
            "database": config.provider,
            "index_mode": config.index_mode,
            "total_vectors": len(embeddings_data["embeddings"]),
            "index_size": result.get("index_size", "N/A"),
            "processing_time": processing_time,
            "collection_name": result.get("collection_name", "N/A")
        }

    def _load_embeddings(self, file_path: str) -> Dict[str, Any]:
        """
        加载embedding文件，返回配置信息和embeddings
        
        参数:
            file_path: 嵌入向量文件路径
            
        返回:
            包含嵌入向量和元数据的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loading embeddings from {file_path}")
                
                if not isinstance(data, dict) or "embeddings" not in data:
                    raise ValueError("Invalid embedding file format: missing 'embeddings' key")
                    
                # 返回完整的数据，包括顶层配置
                logger.info(f"Found {len(data['embeddings'])} embeddings")
                return data
                
        except Exception as e:
            logger.error(f"Error loading embeddings from {file_path}: {str(e)}")
            raise

    def _index_to_milvus(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到Milvus数据库
        
        参数:
            embeddings_data: 嵌入向量数据
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        try:
            filename = embeddings_data.get("filename", "")
            base_name = filename.replace('.pdf', '') if filename else "doc"
            base_name = ''.join(lazy_pinyin(base_name, style=Style.NORMAL))
            base_name = base_name.replace('-', '_')
            # 新增：集合名合法化
            base_name = self._sanitize_collection_name(base_name)
            embedding_provider = embeddings_data.get("embedding_provider", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            collection_name = f"{base_name}_{embedding_provider}_{timestamp}"
            collection_name = self._sanitize_collection_name(collection_name)
            
            # 连接到Milvus
            connections.connect(
                alias="default", 
                uri=config.milvus_uri
            )
            
            # 从顶层配置获取向量维度
            vector_dim = int(embeddings_data.get("vector_dimension"))
            if not vector_dim:
                raise ValueError("Missing vector_dimension in embedding file")
            
            logger.info(f"Creating collection with dimension: {vector_dim}")
            
            # 定义字段
            fields = [
                {"name": "id", "dtype": "INT64", "is_primary": True, "auto_id": True},
                {"name": "content", "dtype": "VARCHAR", "max_length": 5000},
                {"name": "document_name", "dtype": "VARCHAR", "max_length": 255},
                {"name": "chunk_id", "dtype": "INT64"},
                {"name": "total_chunks", "dtype": "INT64"},
                {"name": "word_count", "dtype": "INT64"},
                {"name": "page_number", "dtype": "VARCHAR", "max_length": 10},
                {"name": "page_range", "dtype": "VARCHAR", "max_length": 10},
                # {"name": "chunking_method", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_provider", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_model", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_timestamp", "dtype": "VARCHAR", "max_length": 50},
                {
                    "name": "vector",
                    "dtype": "FLOAT_VECTOR",
                    "dim": vector_dim,
                    "params": self._get_milvus_index_params(config)
                }
            ]
            
            # 准备数据为列表格式
            entities = []
            for emb in embeddings_data["embeddings"]:
                entity = {
                    "content": str(emb["metadata"].get("content", "")),
                    "document_name": embeddings_data.get("filename", ""),  # 使用 filename 而不是 document_name
                    "chunk_id": int(emb["metadata"].get("chunk_id", 0)),
                    "total_chunks": int(emb["metadata"].get("total_chunks", 0)),
                    "word_count": int(emb["metadata"].get("word_count", 0)),
                    "page_number": str(emb["metadata"].get("page_number", 0)),
                    "page_range": str(emb["metadata"].get("page_range", "")),
                    # "chunking_method": str(emb["metadata"].get("chunking_method", "")),
                    "embedding_provider": embeddings_data.get("embedding_provider", ""),  # 从顶层配置获取
                    "embedding_model": embeddings_data.get("embedding_model", ""),  # 从顶层配置获取
                    "embedding_timestamp": str(emb["metadata"].get("embedding_timestamp", "")),
                    "vector": [float(x) for x in emb.get("embedding", [])]
                }
                entities.append(entity)
            
            logger.info(f"Creating Milvus collection: {collection_name}")
            
            # 创建collection
            # field_schemas = [
            #     FieldSchema(name=field["name"], 
            #                dtype=getattr(DataType, field["dtype"]),
            #                is_primary="is_primary" in field and field["is_primary"],
            #                auto_id="auto_id" in field and field["auto_id"],
            #                max_length=field.get("max_length"),
            #                dim=field.get("dim"),
            #                params=field.get("params"))
            #     for field in fields
            # ]

            field_schemas = []
            for field in fields:
                extra_params = {}
                if field.get('max_length') is not None:
                    extra_params['max_length'] = field['max_length']
                if field.get('dim') is not None:
                    extra_params['dim'] = field['dim']
                if field.get('params') is not None:
                    extra_params['params'] = field['params']
                field_schema = FieldSchema(
                    name=field["name"], 
                    dtype=getattr(DataType, field["dtype"]),
                    is_primary=field.get("is_primary", False),
                    auto_id=field.get("auto_id", False),
                    **extra_params
                )
                field_schemas.append(field_schema)

            schema = CollectionSchema(fields=field_schemas, description=f"Collection for {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            
            # 插入数据
            logger.info(f"Inserting {len(entities)} vectors")
            insert_result = collection.insert(entities)
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": self._get_milvus_index_type(config),
                "params": self._get_milvus_index_params(config)
            }
            collection.create_index(field_name="vector", index_params=index_params)
            collection.load()
            
            return {
                "index_size": len(insert_result.primary_keys),
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Error indexing to Milvus: {str(e)}")
            raise
        
        finally:
            connections.disconnect("default")

    def _index_to_chroma(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        client = self._init_chroma_client()
        filename = embeddings_data.get("filename", "")
        base_name = filename.replace('.pdf', '') if filename else "doc"
        base_name = ''.join(lazy_pinyin(base_name, style=Style.NORMAL))
        base_name = base_name.replace('-', '_')
        # 新增：集合名合法化
        base_name = self._sanitize_collection_name(base_name)
        embedding_provider = embeddings_data.get("embedding_provider", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        collection_name = f"{base_name}_{embedding_provider}_{timestamp}"
        collection_name = self._sanitize_collection_name(collection_name)
        # 删除同名集合（如果存在）
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        # 创建集合
        collection = client.create_collection(name=collection_name)
        # 添加数据
        documents = []
        metadatas = []
        embeddings = []
        ids = []
        for i, emb in enumerate(embeddings_data["embeddings"]):
            documents.append(str(emb["metadata"].get("content", "")))
            metadatas.append(emb["metadata"])
            embeddings.append([float(x) for x in emb.get("embedding", [])])
            ids.append(f"doc_{i}")
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        # client.persist()  # 兼容 chromadb 0.5.3，删除此行
        return {
            "index_size": len(documents),
            "collection_name": collection_name
        }

    def list_collections(self, provider: str) -> List[str]:
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collections = utility.list_collections()
                return collections
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            client = self._init_chroma_client()
            return [c.name for c in client.list_collections()]
        return []

    def delete_collection(self, provider: str, collection_name: str) -> bool:
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                utility.drop_collection(collection_name)
                return True
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            client = self._init_chroma_client()
            try:
                client.delete_collection(collection_name)
                # client.persist()  # 兼容 chromadb 0.5.3，删除此行
                return True
            except Exception as e:
                logger.error(f"Chroma 删除集合失败: {str(e)}")
                return False
        return False

    def get_collection_info(self, provider: str, collection_name: str) -> Dict[str, Any]:
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collection = Collection(collection_name)
                return {
                    "name": collection_name,
                    "num_entities": collection.num_entities,
                    "schema": collection.schema.to_dict()
                }
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            client = self._init_chroma_client()
            try:
                collection = client.get_collection(collection_name)
                count = collection.count()
                return {
                    "name": collection_name,
                    "num_entities": count,
                    "schema": {"fields": ["content", "embedding", "metadata"]}
                }
            except Exception as e:
                logger.error(f"Chroma 获取集合信息失败: {str(e)}")
                return {}
        return {}
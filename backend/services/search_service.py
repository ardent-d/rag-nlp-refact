from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pymilvus import connections, Collection, utility
from services.embedding_service import EmbeddingService
from utils.config import VectorDBProvider, MILVUS_CONFIG, CHROMA_CONFIG
import os
import json
# 新增Chroma导入
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.milvus_uri = MILVUS_CONFIG["uri"]
        self.chroma_persist_dir = CHROMA_CONFIG["persist_directory"]
        self.search_results_dir = "04-search-results"
        os.makedirs(self.search_results_dir, exist_ok=True)

    def _init_chroma_client(self):
        if chromadb is None:
            raise ImportError("chromadb 未安装，请先安装 chromadb")
        client = chromadb.Client(ChromaSettings(
            persist_directory=self.chroma_persist_dir
        ))
        return client

    def get_providers(self) -> List[Dict[str, str]]:
        return [
            {"id": VectorDBProvider.MILVUS.value, "name": "Milvus"},
            {"id": VectorDBProvider.CHROMA.value, "name": "Chroma"}
        ]

    def list_collections(self, provider: str = VectorDBProvider.MILVUS.value) -> List[Dict[str, Any]]:
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(
                    alias="default",
                    uri=self.milvus_uri
                )
                collections = []
                collection_names = utility.list_collections()
                for name in collection_names:
                    try:
                        collection = Collection(name)
                        collections.append({
                            "id": name,
                            "name": name,
                            "count": collection.num_entities
                        })
                    except Exception as e:
                        logger.error(f"Error getting info for collection {name}: {str(e)}")
                return collections
            except Exception as e:
                logger.error(f"Error listing collections: {str(e)}")
                raise
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            client = self._init_chroma_client()
            collections = []
            for c in client.list_collections():
                try:
                    collection = client.get_collection(c.name)
                    collections.append({
                        "id": c.name,
                        "name": c.name,
                        "count": collection.count()
                    })
                except Exception as e:
                    logger.error(f"Chroma 获取集合信息失败: {str(e)}")
            return collections
        else:
            return []

    async def search(self, 
                    query: str, 
                    collection_id: str, 
                    top_k: int = 3, 
                    threshold: float = 0.7,
                    word_count_threshold: int = 20,
                    save_results: bool = False,
                    provider: str = VectorDBProvider.MILVUS.value) -> Dict[str, Any]:
        if provider == VectorDBProvider.MILVUS:
            return await self._search_milvus(query, collection_id, top_k, threshold, word_count_threshold, save_results)
        elif provider == VectorDBProvider.CHROMA:
            return await self._search_chroma(query, collection_id, top_k, threshold, word_count_threshold, save_results)
        else:
            raise ValueError(f"不支持的向量数据库: {provider}")

    async def _search_milvus(self, query, collection_id, top_k, threshold, word_count_threshold, save_results):
        # 原有Milvus搜索逻辑
        connections.connect(
            alias="default",
            uri=self.milvus_uri
        )
        collection = Collection(collection_id)
        collection.load()
        sample_entity = collection.query(
            expr="id >= 0", 
            output_fields=["embedding_provider", "embedding_model"],
            limit=1
        )
        if not sample_entity:
            raise ValueError(f"Collection {collection_id} is empty")
        query_embedding = self.embedding_service.create_single_embedding(
            query,
            provider=sample_entity[0]["embedding_provider"],
            model=sample_entity[0]["embedding_model"]
        )
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        results = collection.search(
            data=[query_embedding],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["content", "document_name", "chunk_id", "total_chunks", "word_count", "page_number", "page_range", "embedding_provider", "embedding_model", "embedding_timestamp"]
        )
        hits = results[0]
        filtered = []
        for hit in hits:
            if hit.score >= threshold and hit.entity.get("word_count", 0) >= word_count_threshold:
                filtered.append({
                    "score": hit.score,
                    "text": hit.entity.get("content", ""),
                    "metadata": {
                        "source": hit.entity.get("document_name", ""),
                        "page": hit.entity.get("page_number", ""),
                        "chunk": hit.entity.get("chunk_id", "")
                    }
                })
        if save_results:
            filepath = self.save_search_results(query, collection_id, filtered)
            return {"results": filtered, "saved_filepath": filepath}
        return {"results": filtered}

    async def _search_chroma(self, query, collection_id, top_k, threshold, word_count_threshold, save_results):
        client = self._init_chroma_client()
        collection = client.get_collection(collection_id)
        # 这里假设所有embedding都用同一个provider/model
        # 取第一个元数据
        metadatas = collection.get(include=['metadatas'])['metadatas']
        if not metadatas or not metadatas[0]:
            raise ValueError(f"Chroma集合 {collection_id} 没有元数据")
        provider = metadatas[0].get("embedding_provider", "openai")
        model = metadatas[0].get("embedding_model", "text-embedding-ada-002")
        query_embedding = self.embedding_service.create_single_embedding(query, provider=provider, model=model)
        # Chroma 查询
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        filtered = []
        for i in range(len(results["documents"][0])):
            score = 1 - results["distances"][0][i]  # Chroma 距离转为相似度分数
            meta = results["metadatas"][0][i]
            if score >= threshold and meta.get("word_count", 0) >= word_count_threshold:
                filtered.append({
                    "score": score,
                    "text": results["documents"][0][i],
                    "metadata": {
                        "source": meta.get("document_name", ""),
                        "page": meta.get("page_number", ""),
                        "chunk": meta.get("chunk_id", "")
                    }
                })
        if save_results:
            filepath = self.save_search_results(query, collection_id, filtered)
            return {"results": filtered, "saved_filepath": filepath}
        return {"results": filtered}

    def save_search_results(self, query: str, collection_id: str, results: List[Dict[str, Any]]) -> str:
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            collection_base = os.path.basename(collection_id)
            filename = f"search_{collection_base}_{timestamp}.json"
            filepath = os.path.join(self.search_results_dir, filename)
            search_data = {
                "query": query,
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            logger.info(f"Saving search results to: {filepath}")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved search results to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving search results: {str(e)}")
            raise 
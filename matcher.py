"""
关键词匹配模块 - 使用BM25算法进行论文匹配
"""
import json
import re
import math
from pathlib import Path
from typing import List, Dict, Tuple, Union
from dataclasses import dataclass


@dataclass
class Paper:
    """论文数据类"""
    id: str
    title: str
    summary: str
    authors: List[str]
    categories: List[str]
    pdf_url: str
    abs_url: str
    comment: str = ""
    relevance_score: float = 0.0


class BM25Matcher:
    """BM25关键词匹配器，支持关键词权重"""
    
    # BM25 参数
    K1 = 1.5  # 词频饱和参数
    B = 0.75  # 文档长度归一化参数
    
    # 位置权重
    TITLE_WEIGHT = 3.0  # 标题匹配的额外权重
    
    def __init__(self, keywords: Union[List[str], Dict[str, float]]):
        """
        初始化匹配器
        
        Args:
            keywords: 关键词列表或关键词权重字典
                - 列表形式: ["LLM", "transformer"]，权重默认为1.0
                - 字典形式: {"LLM": 2.0, "transformer": 1.5}，指定每个关键词的权重
        """
        # 解析关键词和权重
        if isinstance(keywords, dict):
            self.keywords = {kw.lower(): weight for kw, weight in keywords.items()}
        else:
            self.keywords = {kw.lower(): 1.0 for kw in keywords}
        
        # 预编译关键词正则表达式（词边界匹配）
        self.keyword_patterns = {
            kw: re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in self.keywords.keys()
        }
        
        # 文档统计（用于IDF计算）
        self.doc_count = 0
        self.keyword_doc_freq = {kw: 0 for kw in self.keywords.keys()}
        self.avg_doc_len = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        return text.lower().split()
    
    def _count_keyword_matches(self, text: str, keyword: str) -> int:
        """统计关键词在文本中的匹配次数"""
        pattern = self.keyword_patterns.get(keyword)
        if pattern:
            return len(pattern.findall(text))
        return 0
    
    def _build_corpus_stats(self, papers: List[Paper]):
        """构建语料库统计信息（用于IDF计算）"""
        self.doc_count = len(papers)
        total_len = 0
        
        # 重置文档频率
        self.keyword_doc_freq = {kw: 0 for kw in self.keywords.keys()}
        
        for paper in papers:
            # 合并标题和摘要
            text = f"{paper.title} {paper.summary}".lower()
            total_len += len(self._tokenize(text))
            
            # 统计包含每个关键词的文档数
            for keyword in self.keywords.keys():
                if self._count_keyword_matches(text, keyword) > 0:
                    self.keyword_doc_freq[keyword] += 1
        
        self.avg_doc_len = total_len / max(self.doc_count, 1)
    
    def _calculate_idf(self, keyword: str) -> float:
        """计算关键词的IDF值"""
        doc_freq = self.keyword_doc_freq.get(keyword, 0)
        # BM25 IDF公式
        idf = math.log((self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1)
        return max(idf, 0)  # 确保非负
    
    def _calculate_bm25_score(self, text: str, doc_len: int) -> Tuple[float, List[str]]:
        """
        计算文本的BM25得分
        
        Returns:
            (得分, 匹配到的关键词列表)
        """
        score = 0.0
        matched_keywords = []
        
        for keyword, weight in self.keywords.items():
            # 计算词频
            tf = self._count_keyword_matches(text, keyword)
            
            if tf > 0:
                matched_keywords.append(keyword)
                
                # IDF
                idf = self._calculate_idf(keyword)
                
                # BM25 TF归一化
                tf_normalized = (tf * (self.K1 + 1)) / (
                    tf + self.K1 * (1 - self.B + self.B * doc_len / max(self.avg_doc_len, 1))
                )
                
                # 最终得分 = IDF * TF_normalized * 关键词权重
                score += idf * tf_normalized * weight
        
        return score, matched_keywords
    
    def score_paper(self, paper: Paper) -> Tuple[float, Dict]:
        """
        计算单篇论文的相关性得分
        
        Args:
            paper: 论文对象
        
        Returns:
            (得分, 匹配详情)
        """
        title_tokens = self._tokenize(paper.title)
        abstract_tokens = self._tokenize(paper.summary)
        
        # 标题得分（带权重加成）
        title_score, title_keywords = self._calculate_bm25_score(
            paper.title.lower(), len(title_tokens)
        )
        title_score *= self.TITLE_WEIGHT
        
        # 摘要得分
        abstract_score, abstract_keywords = self._calculate_bm25_score(
            paper.summary.lower(), len(abstract_tokens)
        )
        
        # 合并匹配到的关键词
        all_matched = list(set(title_keywords + abstract_keywords))
        
        # 总得分
        total_score = title_score + abstract_score
        
        # 如果同时在标题和摘要中匹配，额外加分
        overlap = set(title_keywords) & set(abstract_keywords)
        if overlap:
            # 计算重叠关键词的权重总和
            overlap_weight = sum(self.keywords.get(kw, 1.0) for kw in overlap)
            total_score *= (1.0 + 0.1 * overlap_weight)
        
        match_details = {
            'title_keywords': title_keywords,
            'abstract_keywords': abstract_keywords,
            'all_matched': all_matched,
            'title_score': title_score,
            'abstract_score': abstract_score,
            'keyword_weights': {kw: self.keywords.get(kw, 1.0) for kw in all_matched}
        }
        
        return total_score, match_details
    
    def match_papers(
        self, 
        papers: List[Paper], 
        threshold: float = 0.5,
        top_k: int = None
    ) -> List[Tuple[Paper, Dict]]:
        """
        匹配论文并返回得分超过阈值的论文
        
        Args:
            papers: 论文列表
            threshold: 得分阈值
            top_k: 最大返回论文数量（None表示不限制）
        
        Returns:
            [(论文, 匹配详情), ...] 列表，按相关性得分降序排列
        """
        # 构建语料库统计信息
        self._build_corpus_stats(papers)
        
        scored_papers = []
        
        for paper in papers:
            score, details = self.score_paper(paper)
            if score >= threshold:
                paper.relevance_score = score
                scored_papers.append((paper, details))
        
        # 按得分降序排序
        scored_papers.sort(key=lambda x: x[0].relevance_score, reverse=True)
        
        # 限制返回数量
        if top_k is not None and top_k > 0:
            scored_papers = scored_papers[:top_k]
        
        return scored_papers


# 保持向后兼容
KeywordMatcher = BM25Matcher


def load_papers_from_jsonl(jsonl_path: str) -> List[Paper]:
    """
    从JSONL文件加载论文数据
    
    Args:
        jsonl_path: JSONL文件路径
    
    Returns:
        论文列表
    """
    papers = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                paper = Paper(
                    id=data.get('id', ''),
                    title=data.get('title', ''),
                    summary=data.get('summary', ''),
                    authors=data.get('authors', []),
                    categories=data.get('categories', []),
                    pdf_url=data.get('pdf', ''),
                    abs_url=data.get('abs', ''),
                    comment=data.get('comment', '')
                )
                papers.append(paper)
            except json.JSONDecodeError as e:
                print(f"解析JSON行失败: {e}")
                continue
    
    return papers


def load_papers_from_directory(data_dir: str) -> List[Paper]:
    """
    从数据目录加载所有分类的论文
    
    Args:
        data_dir: 数据根目录
    
    Returns:
        论文列表
    """
    papers = []
    jsonl_dir = Path(data_dir) / "jsonl"
    
    if not jsonl_dir.exists():
        return papers
    
    # 遍历所有分类目录
    for category_dir in jsonl_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        # 直接查找 papers.jsonl 文件
        jsonl_file = category_dir / "papers.jsonl"
        if jsonl_file.exists():
            papers.extend(load_papers_from_jsonl(str(jsonl_file)))
    
    # 去重（同一篇论文可能出现在多个分类中）
    seen_ids = set()
    unique_papers = []
    for paper in papers:
        if paper.id not in seen_ids:
            seen_ids.add(paper.id)
            unique_papers.append(paper)
    
    return unique_papers


def find_relevant_papers(
    data_dir: str,
    keywords: Union[List[str], Dict[str, float]],
    threshold: float = 0.5,
    top_k: int = None
) -> List[Tuple[Paper, Dict]]:
    """
    查找与关键词相关的论文
    
    Args:
        data_dir: 数据目录
        keywords: 关键词列表或关键词权重字典
        threshold: 得分阈值
        top_k: 最大论文数量（None表示不限制）
    
    Returns:
        相关论文列表
    """
    # 加载论文
    papers = load_papers_from_directory(data_dir)
    
    if not papers:
        print(f"未找到论文数据，请先运行爬取")
        return []
    
    print(f"加载了 {len(papers)} 篇论文")
    
    # BM25匹配
    matcher = BM25Matcher(keywords)
    relevant_papers = matcher.match_papers(papers, threshold, top_k)
    
    # 显示结果信息
    if top_k is not None:
        print(f"找到 {len(relevant_papers)} 篇相关论文 (阈值: {threshold}, 最大: {top_k})")
    else:
        print(f"找到 {len(relevant_papers)} 篇相关论文 (阈值: {threshold})")
    
    return relevant_papers

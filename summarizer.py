"""
LLM论文总结模块 - 使用大模型生成高质量论文报告
"""
import os
from typing import List, Dict, Tuple, Optional, Union
from openai import OpenAI

from matcher import Paper


class PaperSummarizer:
    """论文总结器 - 生成高质量的论文解读报告"""
    
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str = "",
        base_url: str = "https://api.deepseek.com"
    ):
        """
        初始化总结器
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
        """
        self.model = model
        self.api_key = api_key or os.environ.get('LLM_API_KEY', '')
        self.base_url = base_url
        
        if not self.api_key:
            raise ValueError("未提供LLM API密钥，请设置LLM_API_KEY环境变量或在配置中指定")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """调用LLM"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"生成失败: {str(e)}"
    
    def summarize_paper_batch(
        self, 
        papers: List[Paper], 
        keywords: Union[List[str], Dict[str, float]]
    ) -> List[str]:
        """
        批量生成多篇论文的详细解读（一次LLM调用）
        
        Args:
            papers: 论文列表（建议不超过5篇）
            keywords: 用户关注的关键词
        
        Returns:
            每篇论文的解读列表
        """
        # 处理关键词格式
        if isinstance(keywords, dict):
            kw_list = list(keywords.keys())
        else:
            kw_list = keywords
        
        # 构建多篇论文的输入
        papers_text = ""
        for i, paper in enumerate(papers, 1):
            papers_text += f"""
---
## 论文 {i}
**标题**: {paper.title}
**摘要**: {paper.summary}
---
"""
        
        system_prompt = """你是一位资深的AI/ML研究员，擅长用通俗易懂的中文解读学术论文。
你的解读应该简洁、专业、有深度。"""

        user_prompt = f"""请对以下 {len(papers)} 篇arXiv论文分别进行简要解读。

**用户关注领域**: {', '.join(kw_list)}

{papers_text}

请对每篇论文从以下两个方面进行解读：

1. **研究背景与挑战**（300-350字）：这个领域的现状是什么？论文要解决什么问题？

2. **方法与实验结论**（300-350字）：论文提出了什么方法？取得了什么效果？

**输出格式要求**：
- 每篇论文之间用 "===论文N===" 分隔（N为论文序号1,2,3...）
- 每篇论文包含两个段落，段落之间空一行
- 不需要加粗或标题，直接写内容

示例输出格式：
===论文1===
这个领域目前面临...研究背景与挑战的描述...

该论文提出了...方法与实验结论的描述...
===论文2===
...
"""

        # 根据论文数量调整 max_tokens
        max_tokens = min(1200 * len(papers), 4000)
        result = self._call_llm(system_prompt, user_prompt, max_tokens=max_tokens)
        
        # 解析结果，按论文分割
        summaries = []
        parts = result.split("===论文")
        
        for part in parts[1:]:  # 跳过第一个空部分
            # 移除论文序号标记
            content = part.strip()
            if content and content[0].isdigit():
                # 移除 "1===" 这样的前缀
                idx = content.find("===")
                if idx != -1:
                    content = content[idx + 3:].strip()
                elif len(content) > 1:
                    content = content[1:].strip()  # 只移除数字
            summaries.append(content)
        
        # 如果解析失败，尝试使用简单分割
        if len(summaries) != len(papers):
            # 回退：均分结果
            lines = result.split('\n')
            chunk_size = max(len(lines) // len(papers), 1)
            summaries = []
            for i in range(len(papers)):
                start = i * chunk_size
                end = start + chunk_size if i < len(papers) - 1 else len(lines)
                summaries.append('\n'.join(lines[start:end]))
        
        return summaries
    
    def _generate_paper_table(self, summaries: List[Dict]) -> str:
        """
        生成论文汇总表格
        
        Args:
            summaries: 论文总结列表
        
        Returns:
            Markdown格式的表格
        """
        if not summaries:
            return ""
        
        # 表头
        table = "| # | 标题 | 作者 | 匹配关键词 | 得分 |\n"
        table += "|:---:|:---|:---|:---|:---:|\n"
        
        # 表格内容
        for i, item in enumerate(summaries, 1):
            paper = item['paper']
            details = item['match_details']
            
            # 完整标题
            title = paper.title
            
            # 完整作者列表
            authors_str = ', '.join(paper.authors)
            
            # 匹配关键词
            matched = details.get('all_matched', [])
            matched_str = ', '.join(matched) if matched else "-"
            
            # 得分
            score = f"{paper.relevance_score:.2f}"
            
            table += f"| {i} | {title} | {authors_str} | {matched_str} | {score} |\n"
        
        return table
    
    def generate_daily_overview(
        self, 
        papers: List[Tuple[Paper, Dict]], 
        keywords: Union[List[str], Dict[str, float]]
    ) -> str:
        """
        生成今日论文的整体总结
        
        Args:
            papers: 论文列表
            keywords: 关键词
        
        Returns:
            今日研究方向总结
        """
        # 处理关键词格式
        if isinstance(keywords, dict):
            kw_list = list(keywords.keys())
        else:
            kw_list = keywords
        
        # 构建论文摘要列表
        paper_briefs = []
        for i, (paper, details) in enumerate(papers[:10], 1):  # 最多取前10篇
            matched = details.get('all_matched', [])
            paper_briefs.append(f"{i}. 《{paper.title}》\n   匹配关键词: {', '.join(matched)}")
        
        papers_text = '\n'.join(paper_briefs)
        
        system_prompt = """你是一位学术领域的资深分析师，擅长从多篇论文中提炼研究趋势和方向。
你的总结应该：
- 高屋建瓴，把握整体方向
- 指出今日论文的共同主题和热点
- 对读者的研究工作有启发意义"""

        user_prompt = f"""今日筛选出了 {len(papers)} 篇与用户研究方向相关的论文。

**用户关注领域**: {', '.join(kw_list)}

**今日论文列表**:
{papers_text}

请用200-300字总结今日论文的整体情况：
1. 今日论文主要聚焦在哪些研究方向？
2. 有什么值得关注的研究趋势或热点？
3. 对从事相关研究的读者有什么建议？

请直接输出总结内容，语气专业但不失亲和。"""

        return self._call_llm(system_prompt, user_prompt, max_tokens=800)
    
    
    def summarize_papers(
        self,
        papers: List[Tuple[Paper, Dict]],
        keywords: Union[List[str], Dict[str, float]],
        batch_size: int = 3
    ) -> List[Dict]:
        """
        批量总结论文（使用批量LLM调用提高效率）
        
        Args:
            papers: [(论文, 匹配详情), ...] 列表
            keywords: 关键词
            batch_size: 每次LLM调用处理的论文数量
        
        Returns:
            [{'paper': Paper, 'summary': str, 'match_details': dict}, ...]
        """
        results = []
        total = len(papers)
        
        # 按批次处理
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_papers = papers[batch_start:batch_end]
            
            # 显示进度
            paper_nums = f"{batch_start+1}-{batch_end}"
            titles = [p[0].title[:30] + "..." for p in batch_papers]
            print(f"📝 正在解读论文 [{paper_nums}/{total}]:")
            for t in titles:
                print(f"   - {t}")
            
            # 批量调用LLM
            batch_paper_objs = [p[0] for p in batch_papers]
            summaries = self.summarize_paper_batch(batch_paper_objs, keywords)
            
            # 组装结果
            for i, ((paper, details), summary) in enumerate(zip(batch_papers, summaries)):
                results.append({
                    'paper': paper,
                    'summary': summary,
                    'match_details': details
                })
        
        return results
    
    def generate_digest(
        self,
        summaries: List[Dict],
        keywords: Union[List[str], Dict[str, float]],
        date: str
    ) -> str:
        """
        生成完整的论文报告
        
        报告结构：
        1. 标题
        2. 今日论文整体总结
        3. 各论文详细解读（按相关性排序）
        
        Args:
            summaries: 论文总结列表
            keywords: 关键词
            date: 日期
        
        Returns:
            完整的报告（Markdown格式）
        """
        # 处理关键词显示
        if isinstance(keywords, dict):
            kw_display = ', '.join(f"{k}({v})" for k, v in keywords.items())
            kw_list = list(keywords.keys())
        else:
            kw_display = ', '.join(keywords)
            kw_list = keywords
        
        if not summaries:
            return f"""# arXiv 论文日报 - {date}

今日没有找到与您关注领域相关的论文。
"""
        
        # 重建 papers 列表用于生成概览
        papers = [(item['paper'], item['match_details']) for item in summaries]
        
        # 1. 生成今日概览
        print("📊 正在生成今日论文概览...")
        daily_overview = self.generate_daily_overview(papers, keywords)
        
        # 2. 生成论文汇总表格
        paper_table = self._generate_paper_table(summaries)
        
        # 3. 构建完整报告
        report = f"""# arXiv 论文日报

**日期**: {date}

**关注领域**: {kw_display}

**今日推荐**: {len(summaries)} 篇相关论文

---

## 今日概览

{daily_overview}

### 论文一览表

{paper_table}

---

## 论文详解

"""
        # 添加每篇论文的详细解读
        for i, item in enumerate(summaries, 1):
            paper = item['paper']
            summary = item['summary']
            
            # 全部作者
            authors_str = ', '.join(paper.authors)
            
            report += f"""### {i}. {paper.title} [[查看论文]]({paper.abs_url})

**作者**: {authors_str}

{summary}

"""
        
        return report


def summarize_relevant_papers(
    papers: List[Tuple[Paper, Dict]],
    keywords: Union[List[str], Dict[str, float]],
    date: str,
    model: str = "deepseek-chat",
    api_key: str = "",
    base_url: str = "https://api.deepseek.com",
    batch_size: int = 3
) -> str:
    """
    总结相关论文并生成报告
    
    Args:
        papers: 相关论文列表
        keywords: 关键词（列表或带权重字典）
        date: 日期
        model: LLM模型
        api_key: API密钥
        base_url: API基础URL
        batch_size: 每次LLM调用处理的论文数量
    
    Returns:
        完整的论文报告
    """
    summarizer = PaperSummarizer(model=model, api_key=api_key, base_url=base_url)
    summaries = summarizer.summarize_papers(papers, keywords, batch_size=batch_size)
    return summarizer.generate_digest(summaries, keywords, date)

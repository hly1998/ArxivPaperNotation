"""
数据处理管道 - 保存论文元数据到JSONL文件
"""
import arxiv
import os
import json
from datetime import datetime


class DailyArxivPipeline:
    """arXiv论文数据处理管道"""

    def __init__(self):
        self.client = arxiv.Client(page_size=100)
        self.today = os.environ.get('TARGET_DATE', datetime.now().strftime("%Y-%m-%d"))
        self.base_dir = os.environ.get('BASE_DATA_DIR', '../data')
        self.category_files = {}  # 缓存文件句柄

    def _fetch_paper_metadata(self, arxiv_id):
        """从arXiv API获取论文元数据"""
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(self.client.results(search))
        return {
            'authors': [a.name for a in paper.authors],
            'title': paper.title,
            'categories': paper.categories,
            'comment': paper.comment,
            'summary': paper.summary
        }

    def _get_file_path(self, category):
        """获取分类对应的文件路径（不再按日期区分）"""
        category_short = category.split('.')[-1]
        data_dir = f"{self.base_dir}/jsonl/{category_short}"
        os.makedirs(data_dir, exist_ok=True)
        return f"{data_dir}/papers.jsonl"

    def process_item(self, item: dict, spider):
        """处理单个论文条目"""
        # 添加URL
        item["pdf"] = f"https://arxiv.org/pdf/{item['id']}"
        item["abs"] = f"https://arxiv.org/abs/{item['id']}"
        item["pdf_urls"] = [item["pdf"]]

        # 获取论文元数据
        metadata = self._fetch_paper_metadata(item['id'])
        item.update(metadata)

        # 保存到文件
        self._save_to_file(item)
        return item

    def _save_to_file(self, item):
        """保存论文数据到对应分类的文件"""
        if not item.get('categories'):
            print(f"警告: 论文 {item['id']} 没有分类信息")
            return

        # 使用主分类
        primary_category = item['categories'][0]
        file_path = self._get_file_path(primary_category)

        # 打开或复用文件句柄
        if file_path not in self.category_files:
            self.category_files[file_path] = open(file_path, 'a', encoding='utf-8')

        # 写入数据
        json.dump(item, self.category_files[file_path], ensure_ascii=False)
        self.category_files[file_path].write('\n')
        self.category_files[file_path].flush()

        print(f"✅ 保存论文 {item['id']} 到 {file_path}")

    def close_spider(self, spider):
        """关闭所有文件句柄"""
        for file_handle in self.category_files.values():
            file_handle.close()
        self.category_files.clear()

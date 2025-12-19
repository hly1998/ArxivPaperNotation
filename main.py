#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv个性化论文通知系统 - 主程序

功能流程:
1. 爬取arXiv每日论文（标题、摘要等）
2. 根据关键词匹配最相关的top-k篇论文
3. 使用LLM总结论文
4. 通过邮件发送论文摘要
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目目录到路径
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from config_loader import get_config
from logger_setup import setup_logger, get_logger
from crawl import CrawlConfig, ArxivCrawler
from matcher import find_relevant_papers
from summarizer import summarize_relevant_papers
from email_sender import send_paper_digest


class ArxivNotifier:
    """arXiv论文通知器"""
    
    def __init__(self, config_path: str = None, date: str = None):
        """
        初始化通知器
        
        Args:
            config_path: 配置文件路径
            date: 指定日期 (YYYY-MM-DD)
        """
        self.config = get_config(config_path)
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        
        # 设置日志
        self.config.ensure_directories()
        log_file = self.config.get_log_file('arxiv_notifier')
        self.logger = setup_logger(
            name="arxiv_notifier",
            log_file=log_file,
            level=self.config.log_level
        )
    
    def step1_crawl(self, force: bool = False) -> bool:
        """
        步骤1: 爬取论文
        
        Args:
            force: 是否强制爬取（忽略日期检查）
        """
        print("\n" + "=" * 60)
        print("📥 步骤 1/4: 爬取arXiv论文")
        print("=" * 60)
        
        try:
            crawl_config = CrawlConfig(date=self.date)
            crawler = ArxivCrawler(crawl_config)
            success = crawler.run(force=force)
            
            if success:
                self.logger.info("论文爬取完成")
            else:
                self.logger.error("论文爬取失败")
            
            return success
        except Exception as e:
            self.logger.exception(f"爬取异常: {e}")
            print(f"❌ 爬取异常: {e}")
            return False
    
    def step2_match(self):
        """步骤2: 关键词匹配"""
        print("\n" + "=" * 60)
        print("🔍 步骤 2/4: 关键词匹配")
        print("=" * 60)
        
        keywords = self.config.keywords
        if not keywords:
            print("⚠️ 未配置关键词，将返回所有论文")
            self.logger.warning("未配置关键词")
        else:
            # 显示关键词和权重
            if isinstance(keywords, dict):
                kw_display = ', '.join(f"{k}({v})" for k, v in keywords.items())
            else:
                kw_display = ', '.join(keywords)
            print(f"关键词: {kw_display}")
            print(f"BM25阈值: {self.config.threshold}")
            if self.config.top_k:
                print(f"最大论文数: {self.config.top_k}")
        
        relevant_papers = find_relevant_papers(
            data_dir=self.config.base_data_dir,
            keywords=keywords,
            threshold=self.config.threshold,
            top_k=self.config.top_k
        )
        
        if relevant_papers:
            print(f"\n✅ 找到 {len(relevant_papers)} 篇相关论文:")
            for i, (paper, details) in enumerate(relevant_papers, 1):
                print(f"   {i}. [{paper.relevance_score:.2f}] {paper.title[:60]}...")
                print(f"      匹配: {', '.join(details.get('all_matched', []))}")
        else:
            print("⚠️ 未找到相关论文")
        
        self.logger.info(f"关键词匹配完成，找到 {len(relevant_papers)} 篇相关论文")
        return relevant_papers
    
    def step3_summarize(self, papers) -> str:
        """步骤3: LLM总结"""
        print("\n" + "=" * 60)
        print("🤖 步骤 3/4: AI总结论文")
        print("=" * 60)
        
        if not papers:
            print("⚠️ 没有论文需要总结")
            return ""
        
        if not self.config.llm_api_key:
            print("⚠️ 未配置LLM API密钥，跳过总结")
            self.logger.warning("未配置LLM API密钥")
            # 生成简单报告
            return self._generate_simple_report(papers)
        
        print(f"📦 批量处理大小: 每次 {self.config.llm_batch_size} 篇")
        
        try:
            digest = summarize_relevant_papers(
                papers=papers,
                keywords=self.config.keywords,
                date=self.date,
                model=self.config.llm_model,
                api_key=self.config.llm_api_key,
                base_url=self.config.llm_base_url,
                batch_size=self.config.llm_batch_size
            )
            
            print("\n✅ 论文总结生成完成")
            self.logger.info("论文总结生成完成")
            return digest
            
        except Exception as e:
            self.logger.exception(f"LLM总结异常: {e}")
            print(f"❌ LLM总结异常: {e}")
            return self._generate_simple_report(papers)
    
    def _generate_simple_report(self, papers) -> str:
        """生成简单报告（无LLM时使用）"""
        report = f"""# 📚 arXiv论文日报 - {self.date}

关注关键词: **{', '.join(self.config.keywords)}**

今日为您筛选了 **{len(papers)}** 篇相关论文：

---

"""
        for i, (paper, details) in enumerate(papers, 1):
            matched_kw = ', '.join(details.get('all_matched', []))
            
            report += f"""## {i}. {paper.title}

**作者**: {', '.join(paper.authors[:5])}{'...' if len(paper.authors) > 5 else ''}

**分类**: {', '.join(paper.categories)}

**匹配关键词**: {matched_kw}

**摘要**: {paper.summary[:500]}...

📄 [查看论文]({paper.abs_url}) | 📥 [下载PDF]({paper.pdf_url})

---

"""
        return report
    
    def step4_send_email(self, digest: str) -> bool:
        """步骤4: 发送邮件"""
        print("\n" + "=" * 60)
        print("📧 步骤 4/4: 发送邮件")
        print("=" * 60)
        
        if not digest:
            print("⚠️ 没有内容需要发送")
            return False
        
        # 检查邮件配置
        if not all([
            self.config.email_smtp_server,
            self.config.email_sender,
            self.config.email_password,
            self.config.email_recipients
        ]):
            print("⚠️ 邮件配置不完整，跳过发送")
            print("   请在配置文件中设置邮件相关参数")
            self.logger.warning("邮件配置不完整")
            
            # 保存到本地文件
            self._save_digest_locally(digest)
            return False
        
        try:
            success = send_paper_digest(
                smtp_server=self.config.email_smtp_server,
                smtp_port=self.config.email_smtp_port,
                sender_email=self.config.email_sender,
                password=self.config.email_password,
                recipients=self.config.email_recipients,
                digest_content=digest,
                date=self.date
            )
            
            if success:
                self.logger.info(f"邮件发送成功，收件人: {self.config.email_recipients}")
            else:
                self._save_digest_locally(digest)
            
            return success
            
        except Exception as e:
            self.logger.exception(f"邮件发送异常: {e}")
            print(f"❌ 邮件发送异常: {e}")
            self._save_digest_locally(digest)
            return False
    
    def _save_digest_locally(self, digest: str):
        """保存摘要到本地文件"""
        output_dir = os.path.join(self.config.base_data_dir, "digests")
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f"{self.date}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(digest)
        
        print(f"📄 摘要已保存到: {output_file}")
        self.logger.info(f"摘要保存到本地: {output_file}")
    
    def run(self, skip_crawl: bool = False, force_crawl: bool = False) -> bool:
        """
        运行完整流程
        
        Args:
            skip_crawl: 是否跳过爬取步骤（使用已有数据）
            force_crawl: 是否强制爬取（忽略日期检查）
        """
        print("\n" + "=" * 60)
        print("🚀 arXiv个性化论文通知系统")
        print("=" * 60)
        print(f"📅 日期: {self.date}")
        print(f"📂 分类: {', '.join(self.config.categories)}")
        # 显示关键词
        kw = self.config.keywords
        if kw:
            kw_count = len(kw) if isinstance(kw, dict) else len(kw)
            print(f"🔑 关键词: {kw_count} 个")
        else:
            print(f"🔑 关键词: 未设置")
        print(f"📊 BM25阈值: {self.config.threshold}")
        if self.config.top_k:
            print(f"📑 最大论文数: {self.config.top_k}")
        
        # 步骤1: 爬取
        if not skip_crawl:
            if not self.step1_crawl(force=force_crawl):
                print("\n❌ 爬取失败，流程终止")
                return False
        else:
            print("\n⏭️ 跳过爬取步骤，使用已有数据")
        
        # 步骤2: 匹配
        relevant_papers = self.step2_match()
        
        if not relevant_papers:
            print("\n⚠️ 未找到相关论文，流程结束")
            return True
        
        # 步骤3: 总结
        digest = self.step3_summarize(relevant_papers)
        
        # 步骤4: 发送邮件
        self.step4_send_email(digest)
        
        print("\n" + "=" * 60)
        print("✅ 流程完成!")
        print("=" * 60)
        
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="arXiv个性化论文通知系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                          # 使用默认配置运行
  python main.py --config my_config.yaml  # 使用自定义配置
  python main.py --date 2024-01-15        # 指定日期
  python main.py --skip-crawl             # 跳过爬取，使用已有数据
  python main.py --force                  # 强制爬取（今日已爬取时可用）
  python main.py --keywords "LLM,transformer,attention"  # 临时指定关键词
"""
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    parser.add_argument(
        "--date", "-d",
        help="指定处理日期 (YYYY-MM-DD格式，默认: 今天)"
    )
    parser.add_argument(
        "--skip-crawl", "-s",
        action="store_true",
        help="跳过爬取步骤，使用已有数据"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制爬取，忽略日期检查（今日已爬取过时可用）"
    )
    parser.add_argument(
        "--keywords", "-k",
        help="临时指定关键词（逗号分隔，会覆盖配置文件中的设置）"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        help="得分阈值，只返回得分 >= threshold 的论文"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="最大论文数量（在阈值过滤后再限制数量）"
    )
    
    args = parser.parse_args()
    
    # 切换到脚本目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        notifier = ArxivNotifier(config_path=args.config, date=args.date)
        
        # 命令行参数覆盖配置
        if args.keywords:
            notifier.config.keywords = [k.strip() for k in args.keywords.split(',')]
        if args.threshold is not None:
            notifier.config.threshold = args.threshold
        if args.top_k is not None:
            notifier.config.top_k = args.top_k
        
        success = notifier.run(skip_crawl=args.skip_crawl, force_crawl=args.force)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


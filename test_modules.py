#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块测试脚本 - 分步测试各个模块功能

使用方法:
    python test_modules.py crawl      # 测试爬取
    python test_modules.py match      # 测试匹配
    python test_modules.py summarize  # 测试LLM总结
    python test_modules.py email      # 测试邮件发送
    python test_modules.py all        # 测试全部流程
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目目录到路径
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)


def test_config():
    """测试配置加载"""
    print("\n" + "=" * 60)
    print("🔧 测试配置加载")
    print("=" * 60)
    
    try:
        from config_loader import get_config
        config = get_config()
        
        print("✅ 配置加载成功")
        print(f"   📂 分类: {config.categories}")
        print(f"   📁 数据目录: {config.base_data_dir}")
        # 显示关键词数量和权重
        kw = config.keywords
        if isinstance(kw, dict):
            print(f"   🔑 关键词: {len(kw)} 个（带权重）")
            for k, v in list(kw.items())[:5]:
                print(f"      - {k}: {v}")
            if len(kw) > 5:
                print(f"      ... 还有 {len(kw) - 5} 个")
        else:
            print(f"   🔑 关键词: {kw}")
        print(f"   📊 BM25阈值: {config.threshold}")
        print(f"   🤖 LLM模型: {config.llm_model}")
        print(f"   🔗 LLM Base URL: {config.llm_base_url}")
        print(f"   🔐 LLM API Key: {'已设置' if config.llm_api_key else '未设置'}")
        print(f"   📧 SMTP服务器: {config.email_smtp_server or '未设置'}")
        print(f"   📮 发件人: {config.email_sender or '未设置'}")
        print(f"   📬 收件人: {config.email_recipients or '未设置'}")
        
        return config
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_crawl():
    """测试爬取功能"""
    print("\n" + "=" * 60)
    print("🕷️ 测试爬取功能")
    print("=" * 60)
    
    config = test_config()
    if not config:
        return False
    
    try:
        from crawl import CrawlConfig, ArxivCrawler
        
        # 初始化爬取配置
        crawl_config = CrawlConfig()
        print(f"\n📅 爬取日期: {crawl_config.date}")
        print(f"📂 目标分类: {crawl_config.CATEGORIES}")
        
        # 创建爬虫实例
        crawler = ArxivCrawler(crawl_config)
        
        # 执行爬取
        print("\n🚀 开始爬取...")
        success = crawler.crawl_papers()
        
        if success:
            crawler.check_duplicates()
            crawler.show_results()
            print("\n✅ 爬取测试通过")
            return True
        else:
            print("\n❌ 爬取失败")
            return False
            
    except Exception as e:
        print(f"❌ 爬取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_match():
    """测试关键词匹配功能"""
    print("\n" + "=" * 60)
    print("🔍 测试关键词匹配功能")
    print("=" * 60)
    
    config = test_config()
    if not config:
        return None
    
    try:
        from matcher import find_relevant_papers, load_papers_from_directory
        
        # 先检查是否有数据
        print(f"\n📁 数据目录: {config.base_data_dir}")
        kw = config.keywords
        if isinstance(kw, dict):
            print(f"🔑 关键词: {len(kw)} 个（带权重）")
        else:
            print(f"🔑 关键词: {kw}")
        
        # 加载论文
        papers = load_papers_from_directory(config.base_data_dir)
        print(f"\n📚 加载论文数量: {len(papers)}")
        
        if not papers:
            print("⚠️ 未找到论文数据，请先运行爬取测试")
            return None
        
        # 显示前3篇论文信息
        print("\n📝 论文示例:")
        for i, paper in enumerate(papers[:3], 1):
            print(f"   {i}. {paper.title[:60]}...")
        
        # 执行匹配
        if not config.keywords:
            print("\n⚠️ 未配置关键词，跳过匹配测试")
            return [(p, {}) for p in papers[:10]]  # 返回前10篇
        
        print(f"\n🔍 执行关键词匹配 (阈值: {config.threshold})...")
        relevant_papers = find_relevant_papers(
            data_dir=config.base_data_dir,
            keywords=config.keywords,
            threshold=config.threshold
        )
        
        if relevant_papers:
            print(f"\n✅ 找到 {len(relevant_papers)} 篇相关论文:")
            for i, (paper, details) in enumerate(relevant_papers, 1):
                print(f"\n   {i}. [BM25: {paper.relevance_score:.2f}] {paper.title[:50]}...")
                # 显示匹配的关键词和权重
                kw_weights = details.get('keyword_weights', {})
                kw_display = ', '.join(f"{k}({v})" for k, v in kw_weights.items())
                print(f"      匹配: {kw_display}")
            print("\n✅ BM25匹配测试通过")
        else:
            print("\n⚠️ 未找到匹配的论文")
        
        return relevant_papers
        
    except Exception as e:
        print(f"❌ 匹配测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_summarize(papers=None):
    """测试LLM总结功能"""
    print("\n" + "=" * 60)
    print("🤖 测试LLM总结功能")
    print("=" * 60)
    
    config = test_config()
    if not config:
        return None
    
    # 检查API密钥
    if not config.llm_api_key:
        print("\n⚠️ 未设置LLM API密钥")
        print("   请设置环境变量: export LLM_API_KEY='your-api-key'")
        print("   或在config.yaml中配置llm.api_key")
        return None
    
    try:
        from summarizer import PaperSummarizer
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 如果没有传入论文，先执行匹配
        if papers is None:
            papers = test_match()
        
        if not papers:
            print("⚠️ 没有论文可供总结")
            return None
        
        # 只总结前2篇进行测试
        test_papers = papers[:2]
        print(f"\n📝 测试总结 {len(test_papers)} 篇论文...")
        
        # 创建总结器
        summarizer = PaperSummarizer(
            model=config.llm_model,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
        
        # 总结论文
        summaries = summarizer.summarize_papers(test_papers, config.keywords)
        
        # 生成报告
        digest = summarizer.generate_digest(summaries, config.keywords, today)
        
        print("\n" + "-" * 40)
        print("📄 生成的摘要预览:")
        print("-" * 40)
        # 只显示前1500字符
        print(digest[:1500] + "..." if len(digest) > 1500 else digest)
        
        print("\n✅ LLM总结测试通过")
        return digest
        
    except Exception as e:
        print(f"❌ LLM总结测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_email(digest: str = None):
    """测试邮件发送功能"""
    print("\n" + "=" * 60)
    print("📧 测试邮件发送功能")
    print("=" * 60)
    
    config = test_config()
    if not config:
        return False
    
    # 检查邮件配置
    missing = []
    if not config.email_smtp_server:
        missing.append("smtp_server")
    if not config.email_sender:
        missing.append("sender")
    if not config.email_password:
        missing.append("password (环境变量 EMAIL_PASSWORD)")
    if not config.email_recipients:
        missing.append("recipients")
    
    if missing:
        print("\n⚠️ 邮件配置不完整，缺少以下配置:")
        for item in missing:
            print(f"   - {item}")
        print("\n   请在config.yaml中配置邮件参数")
        return False
    
    try:
        from email_sender import EmailSender
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 如果没有传入摘要，使用测试内容
        if digest is None:
            digest = f"""# 📚 arXiv论文日报 - {today} (测试邮件)

这是一封测试邮件，用于验证邮件发送功能是否正常。

## 测试论文 1

**标题**: Test Paper Title

**作者**: Author1, Author2

**摘要**: This is a test abstract for email sending functionality.

---

> 本邮件由 arXiv 论文通知系统自动生成（测试）
"""
        
        print(f"\n📮 发件人: {config.email_sender}")
        print(f"📬 收件人: {config.email_recipients}")
        print(f"🔒 SMTP: {config.email_smtp_server}:{config.email_smtp_port}")
        
        # 创建发送器
        sender = EmailSender(
            smtp_server=config.email_smtp_server,
            smtp_port=config.email_smtp_port,
            sender_email=config.email_sender,
            password=config.email_password
        )
        
        # 发送测试邮件
        print("\n📤 正在发送测试邮件...")
        success = sender.send_email(
            recipients=config.email_recipients,
            subject=f"📚 arXiv论文日报 - {today} (测试)",
            content=digest,
            is_markdown=True
        )
        
        if success:
            print("\n✅ 邮件发送测试通过")
        else:
            print("\n❌ 邮件发送失败")
        
        return success
        
    except Exception as e:
        print(f"❌ 邮件发送测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all():
    """测试完整流程"""
    print("\n" + "=" * 60)
    print("🚀 测试完整流程")
    print("=" * 60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 步骤1: 爬取
    print("\n" + "=" * 60)
    print("📥 步骤 1/4: 爬取")
    print("=" * 60)
    if not test_crawl():
        print("\n⚠️ 爬取失败，继续使用已有数据...")
    
    # 步骤2: 匹配
    print("\n" + "=" * 60)
    print("🔍 步骤 2/4: 匹配")
    print("=" * 60)
    papers = test_match()
    
    if not papers:
        print("\n❌ 无论文数据，流程终止")
        return False
    
    # 步骤3: 总结
    print("\n" + "=" * 60)
    print("🤖 步骤 3/4: 总结")
    print("=" * 60)
    digest = test_summarize(papers)
    
    if not digest:
        print("\n⚠️ 总结失败，使用简单报告...")
        # 生成简单报告
        from config_loader import get_config
        config = get_config()
        digest = f"# arXiv论文日报 - {today}\n\n找到 {len(papers)} 篇相关论文。"
    
    # 步骤4: 发送邮件
    print("\n" + "=" * 60)
    print("📧 步骤 4/4: 发送邮件")
    print("=" * 60)
    test_email(digest)
    
    print("\n" + "=" * 60)
    print("✅ 完整流程测试结束")
    print("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="模块测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试命令:
  python test_modules.py config     # 测试配置加载
  python test_modules.py crawl      # 测试爬取
  python test_modules.py match      # 测试关键词匹配
  python test_modules.py summarize  # 测试LLM总结
  python test_modules.py email      # 测试邮件发送
  python test_modules.py all        # 测试完整流程
"""
    )
    
    parser.add_argument(
        "module",
        choices=["config", "crawl", "match", "summarize", "email", "all"],
        help="要测试的模块"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 arXiv论文通知系统 - 模块测试")
    print("=" * 60)
    
    if args.module == "config":
        test_config()
    elif args.module == "crawl":
        test_crawl()
    elif args.module == "match":
        test_match()
    elif args.module == "summarize":
        test_summarize()
    elif args.module == "email":
        test_email()
    elif args.module == "all":
        test_all()


if __name__ == "__main__":
    main()


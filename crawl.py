#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv论文爬取器 - 独立的论文数据爬取工具
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

from config_loader import get_config
from logger_setup import setup_logger, get_logger

# 添加主项目目录到路径以导入共享模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# =============================================================================
# 配置区域
# =============================================================================


class CrawlConfig:
    """爬取配置类"""

    def __init__(self, date=None, config_path=None):
        """
        初始化配置

        Args:
            date: 指定的日期
            config_path: 配置文件路径
        """
        self.date = date or datetime.now().strftime("%Y-%m-%d")

        # 从配置文件加载配置
        self.yaml_config = get_config(config_path)

        # 从配置文件读取设置
        self.CATEGORIES = self.yaml_config.categories
        self.BASE_DATA_DIR = self.yaml_config.base_data_dir
        self.DOWNLOAD_PDF = self.yaml_config.download_pdf
        self.PDF_TIMEOUT = self.yaml_config.pdf_timeout
        self.PDF_MAX_SIZE_MB = self.yaml_config.pdf_max_size_mb
        self.CONCURRENT_DOWNLOADS = self.yaml_config.concurrent_downloads


# =============================================================================
# 主程序类
# =============================================================================

class ArxivCrawler:
    """arXiv论文爬取器"""

    def __init__(self, config: CrawlConfig):
        self.config = config
        self.today = config.date
        self.logger = get_logger()
        # 记录爬取日期的文件路径
        self.last_crawl_file = Path(self.config.BASE_DATA_DIR) / ".last_crawl_date"
        self.setup_environment()

    def _get_last_crawl_date(self) -> str:
        """获取上次爬取的日期"""
        if self.last_crawl_file.exists():
            try:
                return self.last_crawl_file.read_text().strip()
            except Exception:
                return ""
        return ""

    def _save_crawl_date(self):
        """保存当前爬取日期"""
        try:
            self.last_crawl_file.parent.mkdir(parents=True, exist_ok=True)
            self.last_crawl_file.write_text(self.today)
        except Exception as e:
            print(f"⚠️ 无法保存爬取日期: {e}")

    def check_should_crawl(self, force: bool = False) -> bool:
        """
        检查是否需要爬取
        
        Args:
            force: 是否强制爬取
            
        Returns:
            是否应该继续爬取
        """
        if force:
            print("🔄 强制爬取模式，跳过日期检查")
            return True
        
        last_date = self._get_last_crawl_date()
        if last_date == self.today:
            print(f"⏭️ 今日({self.today})已爬取过，跳过重复爬取")
            print(f"   如需强制爬取，请使用 --force 参数")
            return False
        
        if last_date:
            print(f"📅 上次爬取日期: {last_date}，今日: {self.today}，开始新的爬取")
        else:
            print(f"📅 首次爬取，日期: {self.today}")
        
        return True

    def _get_category_short(self, category):
        """提取分类短名称: cs.IR -> IR"""
        return category.split('.')[-1]

    def _get_category_paths(self, category_short):
        """获取分类的数据路径（不再按日期区分）"""
        base = self.config.BASE_DATA_DIR
        return {
            'jsonl': f"{base}/jsonl/{category_short}",
        }

    def setup_environment(self):
        """设置环境变量和创建目录"""
        os.environ["CATEGORIES"] = ",".join(self.config.CATEGORIES)
        os.environ["TARGET_DATE"] = self.today
        os.environ["BASE_DATA_DIR"] = self.config.BASE_DATA_DIR

        # 为每个分类创建目录
        for category in self.config.CATEGORIES:
            category_short = self._get_category_short(category)
            paths = self._get_category_paths(category_short)
            Path(paths['jsonl']).mkdir(parents=True, exist_ok=True)

    def print_config(self):
        """显示当前配置"""
        print("=" * 60)
        print("🕷️  arXiv论文爬取器")
        print("=" * 60)
        print("📋 当前配置:")
        print(f"   分类: {', '.join(self.config.CATEGORIES)}")
        print(f"   日期: {self.today}")
        print(f"   数据目录: {self.config.BASE_DATA_DIR}")
        print(f"   下载PDF: {self.config.DOWNLOAD_PDF}")
        print()

    def _get_data_file(self, category_short):
        """获取分类的数据文件路径"""
        paths = self._get_category_paths(category_short)
        return f"{paths['jsonl']}/papers.jsonl"

    def crawl_papers(self):
        """爬取论文数据"""
        print("🚀 开始爬取arXiv论文...")

        # 清空所有分类的数据目录
        for category in self.config.CATEGORIES:
            category_short = self._get_category_short(category)
            paths = self._get_category_paths(category_short)
            jsonl_dir = Path(paths['jsonl'])
            if jsonl_dir.exists():
                # 清空目录下所有文件
                for file in jsonl_dir.glob("*"):
                    if file.is_file():
                        print(f"🗑️ 清理旧数据: {file}")
                        file.unlink()

        # 执行爬取
        try:
            cmd = ["scrapy", "crawl", "arxiv"]
            print(f"执行命令: {' '.join(cmd)}")

            subprocess.run(
                cmd, cwd="crawler", capture_output=True, text=True, check=True
            )
            print("✅ 爬取完成")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ 爬取失败: {e}\n错误输出: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ 错误: 未找到scrapy命令\n请确保已安装scrapy: pip install scrapy")
            return False

    def check_duplicates(self):
        """检查去重"""
        print("🔍 执行去重检查...")
        try:
            result = subprocess.run(
                ["python", "crawler/check_stats.py"],
                capture_output=True, text=True
            )

            if result.returncode in [0, 1]:
                msg = "有新内容" if result.returncode == 0 else "无新内容，但数据已保存"
                print(f"✅ 去重检查完成，{msg}")
                return True
            else:
                print(f"❌ 去重检查错误: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 去重检查异常: {e}")
            return False

    def _print_category_stats(self, category):
        """打印单个分类的统计信息"""
        category_short = self._get_category_short(category)
        paths = self._get_category_paths(category_short)
        data_file = self._get_data_file(category_short)

        print(f"\n📁 {category} 分类结果:")
        print(f"   📂 数据目录: {paths['jsonl']}/")

        # 统计论文数
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                count = sum(1 for _ in f)
            print(f"   ✅ 论文数据: {os.path.basename(data_file)} ({count} 篇)")

    def _print_sample_paper(self, category):
        """打印单个分类的示例论文"""
        category_short = self._get_category_short(category)
        data_file = self._get_data_file(category_short)

        if not os.path.exists(data_file):
            return

        print(f"\n📝 {category} 示例论文:")
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                sample = json.loads(f.readline())
                print(f"   ID: {sample.get('id', 'N/A')}")
                print(f"   标题: {sample.get('title', 'N/A')[:80]}...")
                print(f"   作者: {', '.join(sample.get('authors', [])[:3])}...")
        except Exception as e:
            print(f"   无法显示示例: {e}")

    def show_results(self):
        """显示爬取结果"""
        print("\n" + "=" * 60)
        print("🎉 爬取完成")
        print("=" * 60)

        # 显示每个分类的统计信息
        for category in self.config.CATEGORIES:
            self._print_category_stats(category)

        # 显示示例论文
        for category in self.config.CATEGORIES:
            self._print_sample_paper(category)

    def run(self, force: bool = False):
        """
        运行完整流程
        
        Args:
            force: 是否强制爬取（忽略日期检查）
        """
        self.print_config()
        
        # 检查是否需要爬取
        if not self.check_should_crawl(force=force):
            return True  # 跳过但不算失败
        
        success = (
            self.crawl_papers()
            and self.check_duplicates()
        )
        
        if success:
            # 保存爬取日期
            self._save_crawl_date()
            self.show_results()
        
        return success


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="arXiv论文爬取器")
    parser.add_argument("--date", help="指定处理日期 (YYYY-MM-DD)")
    parser.add_argument("--config", help="配置文件路径", default="./config.yaml")
    parser.add_argument("--force", action="store_true", help="强制爬取，忽略日期检查")
    args = parser.parse_args()

    print("🚀 启动arXiv论文爬取器...")

    # 加载配置
    try:
        yaml_config = get_config(args.config)
        yaml_config.ensure_directories()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return False

    # 设置日志
    log_file = yaml_config.get_log_file('daily_arxiv')
    logger = setup_logger(
        name="daily_arxiv",
        log_file=log_file,
        level=yaml_config.log_level,
        enable_rotation=yaml_config.enable_log_rotation,
        max_bytes=yaml_config.log_max_bytes,
        backup_count=yaml_config.log_backup_count
    )
    logger.info("启动arXiv论文爬取器")

    # 检查依赖
    if not os.path.exists("crawler"):
        print("❌ 错误: 缺少必要目录 crawler")
        logger.error("缺少必要目录 crawler")
        return False

    try:
        config = CrawlConfig(date=args.date, config_path=args.config)
        crawler = ArxivCrawler(config)
        success = crawler.run(force=args.force)

        if success:
            print("\n🎉 爬取任务完成！")
            logger.info("爬取任务完成")
        else:
            print("\n❌ 爬取过程中出现错误")
            logger.error("爬取过程中出现错误")
        return success

    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断了程序")
        logger.warning("用户中断了程序")
        return False
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        logger.exception(f"未预期的错误: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

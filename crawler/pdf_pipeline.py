"""
PDF下载和验证管道
"""
import os
import requests
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 用于跟踪PDF下载统计
_download_stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0
}


class PDFDownloadPipeline:
    """PDF下载管道 - 下载arXiv论文的PDF文件"""

    def __init__(self, base_dir='../data', download_timeout=30, max_file_size=50 * 1024 * 1024):
        """初始化PDF下载管道"""
        self.base_dir = base_dir
        self.download_timeout = download_timeout
        self.max_file_size = max_file_size
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
        }

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫设置中获取配置"""
        settings = crawler.settings
        base_dir = os.environ.get('BASE_DATA_DIR', '../data')
        return cls(
            base_dir=base_dir,
            download_timeout=settings.get('PDF_DOWNLOAD_TIMEOUT', 30),
            max_file_size=settings.get('PDF_MAX_FILE_SIZE', 50 * 1024 * 1024),
        )

    def _get_pdf_path(self, item):
        """获取PDF存储路径"""
        if not item.get('categories'):
            logger.warning(f"论文 {item['id']} 没有分类信息")
            return None

        category_short = item['categories'][0].split('.')[-1]
        today = os.environ.get('TARGET_DATE', datetime.now().strftime("%Y-%m-%d"))
        pdf_dir = f"{self.base_dir}/pdf/{category_short}/{today}"
        os.makedirs(pdf_dir, exist_ok=True)
        return os.path.join(pdf_dir, f"{item['id']}.pdf")

    def process_item(self, item, spider):
        """处理每个item，下载PDF文件"""
        global _download_stats
        _download_stats['total'] += 1

        # 检查是否需要下载PDF
        if not getattr(spider, 'download_pdf', True):
            logger.info(f"PDF下载已禁用，跳过 {item['id']}")
            _download_stats['skipped'] += 1
            return item

        pdf_url = item.get('pdf')
        if not pdf_url:
            logger.warning(f"论文 {item['id']} 没有PDF URL")
            item['pdf_download_status'] = 'no_url'
            _download_stats['skipped'] += 1
            return item

        try:
            local_path = self._get_pdf_path(item)
            if not local_path:
                item['pdf_download_status'] = 'no_category'
                _download_stats['skipped'] += 1
                return item

            # 检查文件是否已存在
            if os.path.exists(local_path):
                logger.info(f"PDF文件已存在: {local_path}")
                item['pdf_local_path'] = local_path
                item['pdf_download_status'] = 'already_exists'
                _download_stats['skipped'] += 1
                return item

            # 下载PDF文件
            logger.info(f"开始下载PDF: {pdf_url}")
            if self._download_pdf(pdf_url, local_path):
                item['pdf_local_path'] = local_path
                item['pdf_download_status'] = 'success'
                logger.info(f"✅ PDF下载成功: {local_path}")
                _download_stats['success'] += 1
            else:
                item['pdf_download_status'] = 'failed'
                logger.error(f"❌ PDF下载失败: {pdf_url}")
                _download_stats['failed'] += 1

        except Exception as e:
            logger.error(f"处理PDF下载时出错 {item['id']}: {str(e)}")
            item['pdf_download_status'] = 'error'
            item['pdf_error'] = str(e)
            _download_stats['failed'] += 1

        return item

    def _validate_response(self, response, url):
        """验证响应"""
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and 'octet-stream' not in content_type:
            logger.warning(f"可能不是PDF文件: {url}, content-type: {content_type}")

        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > self.max_file_size:
            logger.error(f"文件过大: {url}, 大小: {content_length} 字节")
            return False
        return True

    def _validate_downloaded_file(self, local_path):
        """验证下载的文件"""
        file_size = os.path.getsize(local_path)

        # 检查文件大小
        if file_size < 1024:
            logger.error(f"文件过小，可能是错误页面: {local_path}")
            os.remove(local_path)
            return False

        # 验证PDF文件头
        with open(local_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                logger.warning(f"文件可能不是有效的PDF: {local_path}")

        return True

    def _download_pdf(self, url, local_path):
        """下载PDF文件"""
        try:
            response = requests.get(
                url, headers=self.headers,
                timeout=self.download_timeout, stream=True
            )
            response.raise_for_status()

            # 验证响应
            if not self._validate_response(response, url):
                return False

            # 下载文件
            downloaded_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        if downloaded_size > self.max_file_size:
                            logger.error(f"下载文件过大: {url}")
                            os.remove(local_path)
                            return False

            # 验证下载的文件
            if not self._validate_downloaded_file(local_path):
                return False

            logger.info(f"PDF下载完成: 大小 {downloaded_size} 字节")
            return True

        except requests.RequestException as e:
            logger.error(f"下载PDF网络错误: {url}, {str(e)}")
            return False
        except Exception as e:
            logger.error(f"下载PDF错误: {url}, {str(e)}")
            return False

    def close_spider(self, spider):
        """爬虫关闭时输出统计信息"""
        global _download_stats
        logger.info(
            f"PDF下载统计: 总计={_download_stats['total']}, "
            f"成功={_download_stats['success']}, "
            f"失败={_download_stats['failed']}, "
            f"跳过={_download_stats['skipped']}"
        )


class PDFValidationPipeline:
    """PDF验证管道 - 验证下载的PDF文件的完整性"""

    def process_item(self, item, spider):
        """验证PDF文件"""
        pdf_path = item.get('pdf_local_path')
        if not pdf_path or not os.path.exists(pdf_path):
            return item

        try:
            item['pdf_file_size'] = os.path.getsize(pdf_path)
            item['pdf_md5'] = self._calculate_md5(pdf_path)
            item['pdf_is_valid'] = self._validate_pdf(pdf_path)

            if not item['pdf_is_valid']:
                logger.warning(f"PDF文件可能损坏: {pdf_path}")

        except Exception as e:
            logger.error(f"验证PDF文件时出错 {pdf_path}: {str(e)}")
            item['pdf_validation_error'] = str(e)

        return item

    def _calculate_md5(self, file_path):
        """计算文件MD5哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _validate_pdf(self, file_path):
        """验证PDF文件"""
        try:
            with open(file_path, 'rb') as f:
                # 检查PDF文件头
                if not f.read(8).startswith(b'%PDF-'):
                    return False

                # 检查EOF标记
                f.seek(-1024, 2)
                if b'%%EOF' not in f.read():
                    logger.warning(f"PDF文件可能不完整（缺少EOF标记）: {file_path}")
                    return False

            return True
        except Exception:
            return False

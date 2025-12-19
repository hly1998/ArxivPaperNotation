# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DailyArxivItem(scrapy.Item):
    # 基本信息 / Basic information
    id = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    categories = scrapy.Field()
    comment = scrapy.Field()
    summary = scrapy.Field()

    # URL信息 / URL information
    pdf = scrapy.Field()
    abs = scrapy.Field()

    # PDF下载相关 / PDF download related
    pdf_urls = scrapy.Field()  # PDF文件URL列表
    pdf_files = scrapy.Field()  # 下载的PDF文件信息
    pdf_local_path = scrapy.Field()  # 本地PDF路径
    pdf_download_status = scrapy.Field()  # PDF下载状态

# Scrapy settings for nga_monitor project
BOT_NAME = "ngamonitor"

SPIDER_MODULES = ["ngamonitor.spiders"]
NEWSPIDER_MODULE = "ngamonitor.spiders"

# 用户代理设置
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'

# 反爬策略配置
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 5  # 严格遵守15秒请求间隔

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0  # 初始延迟
AUTOTHROTTLE_MAX_DELAY = 10.0   # 最大延迟
AUTOTHROTTLE_TARGET_CONCURRENCY = 3.0  # 目标并发数

COOKIES_ENABLED = True  # 必须启用Cookies

# 请求头设置
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

# 中间件配置
DOWNLOADER_MIDDLEWARES = {
    'ngamonitor.middlewares.CustomHeadersMiddleware': 544,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
}

# 管道配置
ITEM_PIPELINES = {
    'ngamonitor.pipelines.NgaMonitorPipeline': 300,
}

# 重试设置
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408]

# 启用HTTP缓存（避免重复下载相同内容）
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # 1小时缓存

# 其他设置
FEED_EXPORT_ENCODING = 'utf-8'


CLOSESPIDER_ITEMCOUNT = 500

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
]
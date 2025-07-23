# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

from urllib.parse import urlencode
import random
import os

        
class NgaMonitorSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # maching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class NgaMonitorDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
        
# 新增代理中间件
class RandomProxyMiddleware:
    def __init__(self):
        # 从环境变量获取代理列表
        proxy_str = os.getenv('PROXY_LIST', '')
        
        # 处理代理格式
        if proxy_str:
            self.proxy_list = [p.strip() for p in proxy_str.split(',') if p.strip()]
        else:
            self.proxy_list = []
        
        # 添加日志输出
        print(f"Loaded proxies: {len(self.proxy_list)} available")
        
        self.proxy_usage = {p: 0 for p in self.proxy_list}
    
    def process_request(self, request, spider):
        if not self.proxy_list:
            spider.logger.debug("No proxies available, skipping proxy middleware")
            return  # 无可用代理时跳过
        
        # 选择使用次数最少的代理
        proxy = min(self.proxy_usage, key=self.proxy_usage.get)
        request.meta['proxy'] = proxy
        self.proxy_usage[proxy] += 1
        spider.logger.debug(f"Using proxy: {proxy} (used {self.proxy_usage[proxy]} times)")

# 增强的请求头中间件
class CustomHeadersMiddleware:
    def process_request(self, request, spider):
        # 添加用户代理轮换
        user_agents = spider.settings.getlist('USER_AGENTS', [])
        if user_agents:
            request.headers['User-Agent'] = random.choice(user_agents)
               
        request.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'Referer': 'https://bbs.nga.cn/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        })
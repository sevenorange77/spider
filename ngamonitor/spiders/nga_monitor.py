import scrapy
import time
import random
import json
import pandas as pd
from urllib.parse import urlencode
from datetime import datetime
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.exporters import BaseItemExporter
from twisted.internet.error import ConnectionRefusedError

class NgaMonitorSpider(scrapy.Spider):
    name = 'nga_monitor'
    allowed_domains = ['bbs.nga.cn']
    custom_settings = {
        'ITEM_PIPELINES': {
            'ngamonitor.pipelines.NgaMonitorPipeline': 300,
        },
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS': 4,
        'RETRY_TIMES': 2,
        'COOKIES_ENABLED': True,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    }

    def __init__(self, fid='7', pages='5', uid='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fid = fid
        self.pages = int(pages)  # 确保是整数
        self.uid = kwargs.get('uid', '')  # 改为从参数获取

        # 添加Cookie有效性检查
        if not uid or not uid.isdigit():
            self.logger.error("未设置有效的用户UID，请检查配置")
            raise CloseSpider("无效的用户UID配置")
        
        self.uid = uid
        self.cookies = {
            'ngaPassportUid': self.uid,
            'lastvisit': str(int(time.time()) - 300),
            'guestJs': str(int(time.time())),
        }
        self.fid_list = [7]

    async def start(self):
        """替代旧的 start_requests 方法"""
        for page in range(1, self.pages + 1):
            url = f"https://bbs.nga.cn/thread.php?fid={self.fid}&page={page}"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers=self.get_dynamic_headers(),
                meta={'page': page}
            )

    def parse_forum(self, response):
        fid = response.meta['fid']
        current_page = response.meta['page']
        
        if current_page >= 5 or not data['data'].get('__next__', False):  # 明确限制5页
            self.logger.info(f"已完成板块{fid}的5页爬取")  # 修复为 self.logger
            return
        
        if 'login.php' in response.url:
            self.logger.error(f"需要重新登录！当前Cookies已失效")
            return

        try:
            data = response.json()
            threads = data['data']['__T']
            
            for thread in threads:
                item = {
                    'fid': fid,
                    'post_id': thread['tid'],
                    'title': thread['subject'],
                    'url': f"https://bbs.nga.cn/read.php?tid={thread['tid']}",
                    'author': thread['author'],
                    'reply_count': thread.get('replies', 0),
                    'post_time': datetime.fromtimestamp(thread['postdate']).strftime('%Y-%m-%d %H:%M:%S'),
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                yield scrapy.Request(
                    url=item['url'],
                    cookies=self.cookies,
                    headers=self.get_dynamic_headers(),
                    callback=self.parse_post,
                    meta={'item': item},
                    priority=1
                )

            if current_page < 5 and data['data']['__next__']:
                next_page = current_page + 1
                params = {
                    'fid': fid,
                    'page': next_page,
                    '__uid': self.uid,
                    '__timestamp': int(time.time()),
                    '__output': '11'
                }
                next_url = f"https://bbs.nga.cn/thread.php?{urlencode(params)}"
                yield scrapy.Request(
                    url=next_url,
                    cookies=self.cookies,
                    headers=self.get_dynamic_headers(),
                    callback=self.parse_forum,
                    meta={'fid': fid, 'page': next_page},
                    errback=self.handle_error
                )
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"JSON解析失败: {e}, URL: {response.url}")
        except Exception as e:
            self.logger.error(f"解析失败: {e}\n响应内容: {response.text[:500]}")
            yield None

    def parse_post(self, response):
        item = response.meta['item']
        # 修正后
        item['content'] = ' '.join(response.css('#postcontent0 ::text').getall()).strip()
        
        comments = []
        for i, floor in enumerate(response.css('div.postbox.reply')[:20]): 
            if i >= 20: break
            comments.append({
                'post_id': item['post_id'],
                'author': floor.css('a.author::text').get(),
                'content': ''.join(floor.css('.postcontent ::text').getall()).strip(),
                'floor': floor.css('span.floor::text').get('').replace('#', ''),
                'post_time': floor.css('span.postInfo::text').re_first(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
            })
        item['comments'] = comments
        yield item

    def get_dynamic_headers(self):
        headers = {
            'User-Agent': self.settings.get('USER_AGENT'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://bbs.nga.cn/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
        }
        return headers    

    def handle_error(self, failure):
        self.logger.error(f"请求失败: {failure.request.url}")
        
        if failure.check(HttpError):
            response = failure.value.response
            if response.status == 403:
                self.logger.warning("触发403限制，建议更换IP或更新Cookies")
        elif failure.check(ConnectionRefusedError):
            self.logger.warning("连接被拒绝，请检查代理设置")
        
        retry_times = failure.request.meta.get('retry_times', 0)
        if retry_times < self.settings.getint('RETRY_TIMES'):
            retryreq = failure.request.copy()
            retryreq.meta['retry_times'] = retry_times + 1
            retryreq.dont_filter = True
            return retryreq
        
        self.logger.error(f"放弃重试: {failure.request.url}")
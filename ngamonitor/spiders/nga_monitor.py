import scrapy
import time
import random
import json
from urllib.parse import urlencode
from datetime import datetime
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import ConnectionRefusedError

class NgaMonitorSpider(scrapy.Spider):
    name = 'nga_monitor'
    allowed_domains = ['bbs.nga.cn']
    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS': 4,
        'RETRY_TIMES': 3,
        'COOKIES_ENABLED': True,
        'CLOSESPIDER_ITEMCOUNT': 100,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = kwargs.get('uid', '17454557')
        self.cookies = {
            'ngaPassportUid': self.uid,
            'lastvisit': str(int(time.time()) - 300),
            'guestJs': str(int(time.time())),
        }
        self.fid_list = [7, 459, 422, 624]

    def start_requests(self):
        for fid in self.fid_list:
            params = {
                'fid': fid,
                'page': 1,
                '__uid': self.uid,
                '__timestamp': int(time.time()),
                '__output': '11'
            }
            url = f"https://bbs.nga.cn/thread.php?{urlencode(params)}"
        
            yield scrapy.Request(
                url=url,
                cookies=self.cookies,
                headers=self.get_dynamic_headers(),
                callback=self.parse_forum,
                meta={'fid': fid, 'page': 1},
                errback=self.handle_error
            )

    def parse_forum(self, response):
        fid = response.meta['fid']
        current_page = response.meta['page']
        
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

            if current_page < 3 and data['data'].get('__next__'):
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

    def parse_post(self, response):
        item = response.meta['item']
        content_parts = response.css('#postcontent0 ::text').getall()
        item['content'] = ''.join(content_parts).strip()
        
        comments = []
        for floor in response.css('div.postbox.reply'):
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
        return {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0'
            ]),
            'Referer': f'https://bbs.nga.cn/thread.php?fid={random.choice(self.fid_list)}',
            'X-Request-Time': str(int(time.time() * 1000)),
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
        }

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
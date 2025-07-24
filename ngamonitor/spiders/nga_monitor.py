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
        # 支持外部cookie字符串
        cookie_str = kwargs.get('cookie')
        if cookie_str:
            # 解析cookie字符串为字典
            self.cookies = {kv.split('=')[0].strip(): kv.split('=')[1].strip() for kv in cookie_str.split(';') if '=' in kv}
        else:
            self.cookies = {
                'ngaPassportUid': self.uid,
                'lastvisit': str(int(time.time()) - 300),
                'guestJs': str(int(time.time())),
            }
        # 支持单fid或逗号分隔的多个fid
        fid_arg = kwargs.get('fid')
        if fid_arg:
            self.fid_list = [int(f) for f in str(fid_arg).split(',') if f.strip()]
        else:
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
        # 兼容NGA多种回帖结构，采集主楼以外所有楼层
        # 1. 先尝试div[id^="post"]，主楼通常id=post1
        floors = response.css('div[id^="post"]')
        for floor in floors:
            post_id_attr = floor.attrib.get('id', '')
            if post_id_attr == 'post1':
                continue
            # 兼容部分页面主楼id可能不是post1，跳过第一个楼层
            if post_id_attr and floors.index(floor) == 0:
                continue
            # 只采集有内容的楼层
            content = ''.join(floor.css('.postcontent ::text').getall()).strip()
            if not content:
                continue
            author = floor.css('a.author::text').get() or floor.css('.author::text').get()
            floor_num = floor.css('span.floor::text').get('')
            post_time = floor.css('span.postInfo::text').re_first(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
            comments.append({
                'post_id': item['post_id'],
                'author': author,
                'content': content,
                'floor': floor_num.replace('#', '') if floor_num else '',
                'post_time': post_time
            })
        # 2. 如果上面没采到，尝试div.reply/postbox.reply等其它常见结构
        if not comments:
            for floor in response.css('div.reply,div.postbox.reply'):
                content = ''.join(floor.css('.postcontent ::text').getall()).strip()
                if not content:
                    continue
                author = floor.css('a.author::text').get() or floor.css('.author::text').get()
                floor_num = floor.css('span.floor::text').get('')
                post_time = floor.css('span.postInfo::text').re_first(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
                comments.append({
                    'post_id': item['post_id'],
                    'author': author,
                    'content': content,
                    'floor': floor_num.replace('#', '') if floor_num else '',
                    'post_time': post_time
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
                self.logger.warning("触发403限制，建议更新Cookies")
        elif failure.check(ConnectionRefusedError):
            self.logger.warning("连接被拒绝")
        
        retry_times = failure.request.meta.get('retry_times', 0)
        if retry_times < self.settings.getint('RETRY_TIMES'):
            retryreq = failure.request.copy()
            retryreq.meta['retry_times'] = retry_times + 1
            retryreq.dont_filter = True
            return retryreq
        
        self.logger.error(f"放弃重试: {failure.request.url}")
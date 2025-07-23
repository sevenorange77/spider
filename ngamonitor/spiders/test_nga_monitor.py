# 修改 parse_post 使 comments 变为字符串，适合 CSV 导出
def parse_post(self, response):
    item = response.meta['item']
    item['content'] = ' '.join(response.css('#postcontent0 ::text').getall()).strip()

    comments = []
    for i, floor in enumerate(response.css('div.postbox.reply')[:20]):
        if i >= 20: break
        comment = {
            'author': floor.css('a.author::text').get(),
            'content': ''.join(floor.css('.postcontent ::text').getall()).strip(),
            'floor': (floor.css('span.floor::text').get() or '').replace('#', ''),
            'post_time': floor.css('span.postInfo::text').re_first(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
        }
        # 用分隔符拼接为字符串
        comments.append(f"{comment['floor']}F {comment['author']}: {comment['content']} ({comment['post_time']})")
    # 用换行分隔所有评论
    item['comments'] = "\n".join(comments)
    yield item
import scrapy

class PostItem(scrapy.Item):
    fid = scrapy.Field()          # 板块ID
    post_id = scrapy.Field()      # 帖子ID
    title = scrapy.Field()        # 标题
    url = scrapy.Field()          # 链接
    author = scrapy.Field()       # 发帖人
    content = scrapy.Field()      # 内容
    reply_count = scrapy.Field()  # 回复数
    post_time = scrapy.Field()    # 发帖时间
    sentiment = scrapy.Field()    # 情感值
    risk_level = scrapy.Field()   # 风险等级

class CommentItem(scrapy.Item):
    post_id = scrapy.Field()      # 所属帖子ID
    author = scrapy.Field()       # 评论人
    content = scrapy.Field()      # 评论内容
    floor = scrapy.Field()        # 楼层
    post_time = scrapy.Field()    # 评论时间
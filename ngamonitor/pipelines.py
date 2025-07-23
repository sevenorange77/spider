import json
import re
from snownlp import SnowNLP

class NgaMonitorPipeline:
    # 风险关键词库（需动态更新）
    RISK_KEYWORDS = [
        'bug', '故障', '诈骗', '退款', '封号', '补偿', '垃圾', '卸载'
    ]
    
    def process_item(self, item, spider):
        if 'content' in item:
            content = item['content']
            try:
                # 处理长文本的分块分析
                if len(content) > 500:
                    chunks = [content[i:i+500] for i in range(0, len(content), 500)]
                    sentiments = [SnowNLP(chunk).sentiments for chunk in chunks]
                    item['sentiment'] = sum(sentiments) / len(sentiments)
                else:
                    item['sentiment'] = SnowNLP(content).sentiments
            except Exception as e:
                spider.logger.error(f"情感分析失败: {str(e)}")
                item['sentiment'] = 0.5
            
            # 风险关键词匹配
            item['risk_level'] = 0
            for keyword in self.RISK_KEYWORDS:
                if keyword in content:
                    item['risk_level'] += 1
                    
            # 高风险内容即时预警
            if item['sentiment'] < 0.3 or item['risk_level'] >= 2:
                self.send_alert(item)
        return item

    def send_alert(self, item):
        """通过企业微信机器人发送警报"""
        alert_msg = f"⚠️ NGA高风险内容告警\n标题：{item['title']}\n情感值：{item['sentiment']:.2f}\n关键词命中：{item['risk_level']}次\n链接：{item['url']}"
        # 实际使用时替换为你的机器人Webhook
        # requests.post("https://qyapi.weixin.qq.com/robot/send?key=YOUR_KEY", 
        #              json={"msgtype": "text", "text": {"content": alert_msg}})
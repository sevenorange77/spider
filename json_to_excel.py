import pandas as pd
import json

# 读取JSON文件
with open('output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 将JSON数据转换为DataFrame
df = pd.json_normalize(data)

# 保存为Excel文件
df.to_excel('nga_posts.xlsx', index=False, engine='openpyxl')

print("Excel文件已生成：nga_posts.xlsx")
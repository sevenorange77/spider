NGA论坛监控与数据分析工具

本项目是一个基于Scrapy的NGA论坛爬虫，集成了数据情感分析、风险内容预警、可视化界面和一键导出Excel等功能，适合对NGA论坛内容进行自动化采集、监控和分析。

目录结构

spider/
├── crawl.bat                  # 一键启动爬虫脚本
├── data/
│   └── output.json            # 爬虫输出数据
├── json_to_excel.py           # JSON转Excel脚本
├── nga_monitor_gui.py         # 可视化监控与分析界面
├── nga_sample.html            # NGA页面示例
├── ngamonitor/
│   ├── items.py               # Scrapy Item定义
│   ├── middlewares.py         # Scrapy中间件
│   ├── pipelines.py           # 数据处理与预警
│   ├── settings.py            # Scrapy配置
│   └── spiders/
│       ├── nga_monitor.py     # NGA爬虫主程序
│       └── test_nga_monitor.py# 爬虫测试
├── output.json                # 主输出数据
├── scrapy.cfg                 # Scrapy全局配置
├── 运行可视化窗口.bat         # 一键启动GUI脚本
├── requirements.txt           # Python依赖库列表
└── install_dependencies.bat   # Windows一键安装依赖

快速开始

1. 安装依赖

方法一：一键安装（推荐）

Windows用户：
双击运行 install_dependencies.bat

方法二：手动安装

请确保已安装Python，然后运行：

pip install -r requirements.txt

或单独安装：

pip install scrapy pandas openpyxl snownlp matplotlib

2. 启动可视化界面

推荐通过GUI操作，无需命令行：

Windows下双击运行
运行可视化窗口.bat
或命令行启动
python nga_monitor_gui.py

3. 启动爬虫（命令行方式）

如需手动运行爬虫：

scrapy crawl nga_monitor

可通过参数自定义板块、Cookie等：

scrapy crawl nga_monitor -a fid=7,459 -a uid=你的UID -a cookie="ngaPassportUid=xxx; ..."

4. 数据导出为Excel

GUI界面内点击"导出Excel"按钮，或命令行运行：

python json_to_excel.py

功能简介

- NGA论坛爬虫：自动采集指定板块的帖子及评论，支持多板块、分页、登录Cookie等自定义参数。
- 情感分析与风险预警：对帖子内容进行情感分析，自动标记风险关键词，支持企业微信机器人推送高风险内容。
- 可视化界面：内置Tkinter GUI，支持一键启动爬虫、数据浏览、统计分析、日志查看、参数设置等。
- 数据导出：支持将采集到的数据一键导出为Excel表格，便于后续分析。
- 灵活配置：支持自定义爬取板块、页数、用户ID、请求间隔、并发数、Cookie等参数。

数据结构

主数据字段如下（见ngamonitor/items.py）：

- fid：板块ID
- post_id：帖子ID
- title：标题
- url：帖子链接
- author：发帖人
- content：内容
- reply_count：回复数
- post_time：发帖时间
- sentiment：情感值（0-1，越低越负面）
- risk_level：风险等级（命中关键词次数）

风险内容预警

- 关键词命中或情感值过低时，自动触发预警（可对接企业微信机器人，详见ngamonitor/pipelines.py）。
- 预警内容包括标题、情感值、关键词命中次数、帖子链接。

配置说明

- 所有Scrapy参数可在ngamonitor/settings.py中调整。
- GUI界面支持动态设置爬虫参数，无需手动修改配置文件。

适用场景

- NGA论坛内容监控与分析
- 风险舆情自动预警
- 数据采集与可视化分析

常见问题

- 若爬虫无法采集数据，请检查Cookie是否有效，或适当调整请求间隔、并发数。
- 若GUI界面无法显示，请确保已安装Tkinter和matplotlib。
- 若依赖安装失败，请确保Python已安装，并尝试升级pip：python -m pip install --upgrade pip

如需定制开发或遇到问题，欢迎反馈！ 
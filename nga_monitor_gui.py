import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import os
import sys
import subprocess
import time
import signal
import atexit
import queue

# 添加Scrapy项目路径到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class NgaMonitorGUI:
    def __init__(self, root):
        self.log_queue = queue.Queue()
        self.log_timer_id = None
        self.root = root
        self.root.title("NGA论坛监控工具")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # 初始化数据
        self.settings = {
            'fid': '7',
            'pages': '5',
            'uid': '17454557',
            'proxies': "http://user:pass@proxy1.example.com:8080\nhttp://user:pass@proxy2.example.com:8080"
        }
        self.posts = []
        self.crawler_process = None
        self.crawler_running = False
        self.crawler_thread = None
        self.output_file = "output.json"
        
        # 创建UI
        self.create_widgets()
        
        # 注册退出清理
        atexit.register(self.cleanup)
        
        # 加载示例数据
        self.load_sample_data()
    
    def create_widgets(self):
        # 创建顶部控制面板
        control_frame = ttk.LabelFrame(self.root, text="爬虫控制")
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 控制按钮
        self.start_btn = ttk.Button(control_frame, text="启动爬虫", command=self.start_crawler, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="停止爬虫", command=self.stop_crawler, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.export_btn = ttk.Button(control_frame, text="导出Excel", command=self.export_excel, width=15)
        self.export_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.settings_btn = ttk.Button(control_frame, text="设置", command=self.open_settings, width=15)
        self.settings_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="状态: 就绪")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 创建主内容区域 - 使用Notebook实现多标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 数据表格标签页
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="帖子数据")
        self.create_data_tab()
        
        # 分析面板标签页
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="数据分析")
        self.create_analysis_tab()
        
        # 日志标签页
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="操作日志")
        self.create_log_tab()
    
    def create_data_tab(self):
        # 创建表格
        columns = ("post_id", "title", "author", "post_time", "sentiment", "risk_level")
        self.data_tree = ttk.Treeview(self.data_frame, columns=columns, show="headings", height=20)
        
        # 设置列宽
        self.data_tree.column("post_id", width=80, anchor=tk.CENTER)
        self.data_tree.column("title", width=300)
        self.data_tree.column("author", width=100)
        self.data_tree.column("post_time", width=120, anchor=tk.CENTER)
        self.data_tree.column("sentiment", width=80, anchor=tk.CENTER)
        self.data_tree.column("risk_level", width=80, anchor=tk.CENTER)
        
        # 设置列标题
        self.data_tree.heading("post_id", text="帖子ID")
        self.data_tree.heading("title", text="标题")
        self.data_tree.heading("author", text="作者")
        self.data_tree.heading("post_time", text="发帖时间")
        self.data_tree.heading("sentiment", text="情感值")
        self.data_tree.heading("risk_level", text="风险等级")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.data_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加详情查看功能
        self.data_tree.bind("<Double-1>", self.show_post_detail)
    
    def create_analysis_tab(self):
        # 创建画布用于显示图表
        self.figure = plt.Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.analysis_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建风险帖子列表
        risk_frame = ttk.LabelFrame(self.analysis_frame, text="高风险帖子")
        risk_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        self.risk_tree = ttk.Treeview(risk_frame, columns=("post_id", "title", "risk_level"), 
                                     show="headings", height=5)
        self.risk_tree.column("post_id", width=80, anchor=tk.CENTER)
        self.risk_tree.column("title", width=300)
        self.risk_tree.column("risk_level", width=100, anchor=tk.CENTER)
        
        self.risk_tree.heading("post_id", text="帖子ID")
        self.risk_tree.heading("title", text="标题")
        self.risk_tree.heading("risk_level", text="风险等级")
        
        scrollbar = ttk.Scrollbar(risk_frame, orient=tk.VERTICAL, command=self.risk_tree.yview)
        self.risk_tree.configure(yscrollcommand=scrollbar.set)
        
        self.risk_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件
        self.risk_tree.bind("<Double-1>", self.show_post_detail)
    
    def create_log_tab(self):
        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, width=100, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_text.configure(state=tk.DISABLED)
        
        # 添加初始日志
        self.add_log("系统启动成功")
        self.add_log("就绪")
    
    def load_sample_data(self):
        # 加载示例数据
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.posts = data
                    self.update_data_table()
                    self.update_analysis()
                    self.add_log(f"加载数据成功，共{len(data)}条记录")
        except Exception as e:
            self.add_log(f"加载数据失败: {str(e)}")
    
    def update_data_table(self):
        # 清空现有数据
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        # 添加新数据
        for post in self.posts:
            sentiment = f"{post.get('sentiment', 0.5):.2f}" if 'sentiment' in post else "0.50"
            risk_level = post.get('risk_level', 0)
            
            # 根据风险等级设置标签颜色
            tags = ()
            if risk_level >= 2:
                tags = ('high_risk',)
            elif risk_level == 1:
                tags = ('medium_risk',)
            
            self.data_tree.insert("", "end", values=(
                post['post_id'],
                post['title'],
                post['author'],
                post['post_time'],
                sentiment,
                risk_level
            ), tags=tags)
        
        # 配置标签样式
        self.data_tree.tag_configure('high_risk', background='#ffcccc')
        self.data_tree.tag_configure('medium_risk', background='#ffffcc')
    
    def update_analysis(self):
        if not self.posts:
            return
            
        # 更新图表
        self.figure.clear()
        
        # 情感分布分析
        sentiments = [post.get('sentiment', 0.5) for post in self.posts]
        ax1 = self.figure.add_subplot(221)
        ax1.hist(sentiments, bins=10, color='skyblue', edgecolor='black')
        ax1.set_title('情感值分布')
        ax1.set_xlabel('情感值')
        ax1.set_ylabel('帖子数量')
        
        # 风险等级分布
        risk_levels = [post.get('risk_level', 0) for post in self.posts]
        risk_counts = {0:0, 1:0, 2:0}
        for rl in risk_levels:
            if rl >= 2:
                risk_counts[2] += 1
            elif rl == 1:
                risk_counts[1] += 1
            else:
                risk_counts[0] += 1
        
        ax2 = self.figure.add_subplot(222)
        ax2.bar(['无风险', '低风险', '高风险'], 
                [risk_counts[0], risk_counts[1], risk_counts[2]],
                color=['green', 'yellow', 'red'])
        ax2.set_title('风险等级分布')
        ax2.set_ylabel('帖子数量')
        
        # 高风险帖子词云（示例）
        ax3 = self.figure.add_subplot(212)
        if risk_counts[2] > 0:
            ax3.text(0.5, 0.5, "高风险关键词词云\n(实际实现需要jieba和wordcloud库)", 
                    ha='center', va='center', fontsize=12)
        else:
            ax3.text(0.5, 0.5, "未检测到高风险内容", 
                    ha='center', va='center', fontsize=12)
        ax3.axis('off')
        ax3.set_title('高风险关键词分析')
        
        self.canvas.draw()
        
        # 更新高风险帖子列表
        for item in self.risk_tree.get_children():
            self.risk_tree.delete(item)
        
        high_risk_posts = [p for p in self.posts if p.get('risk_level', 0) >= 1]
        for post in high_risk_posts:
            self.risk_tree.insert("", "end", values=(
                post['post_id'],
                post['title'],
                post['risk_level']
            ))
    
    def show_post_detail(self, event):
        # 获取选中的帖子
        tree = event.widget
        item = tree.selection()[0]
        values = tree.item(item, "values")
        post_id = values[0]
        
        # 查找帖子详情
        post = next((p for p in self.posts if str(p['post_id']) == post_id), None)
        if post:
            self.show_detail_window(post)
    
    def show_detail_window(self, post):
        # 创建详情窗口
        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"帖子详情 - {post['title']}")
        detail_win.geometry("800x600")
        
        # 创建框架
        frame = ttk.Frame(detail_win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(frame, text=post['title'], font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # 元信息
        meta_frame = ttk.Frame(frame)
        meta_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(meta_frame, text=f"作者: {post['author']}").pack(side=tk.LEFT, padx=10)
        ttk.Label(meta_frame, text=f"发布时间: {post['post_time']}").pack(side=tk.LEFT, padx=10)
        ttk.Label(meta_frame, text=f"回复数: {post.get('reply_count', 'N/A')}").pack(side=tk.LEFT, padx=10)
        
        # 情感和风险信息
        risk_frame = ttk.Frame(frame)
        risk_frame.pack(fill=tk.X, pady=5)
        
        sentiment = f"{post.get('sentiment', 0.5):.2f}" if 'sentiment' in post else "0.50"
        risk_level = post.get('risk_level', 0)
        
        ttk.Label(risk_frame, text=f"情感值: {sentiment}").pack(side=tk.LEFT, padx=10)
        
        risk_text = "无风险"
        risk_color = "green"
        if risk_level == 1:
            risk_text = "低风险"
            risk_color = "orange"
        elif risk_level >= 2:
            risk_text = "高风险"
            risk_color = "red"
        
        risk_label = ttk.Label(risk_frame, text=f"风险等级: {risk_text}", foreground=risk_color)
        risk_label.pack(side=tk.LEFT, padx=10)
        
        # 内容区域
        content_frame = ttk.LabelFrame(frame, text="内容")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        content_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, width=80, height=20)
        content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        content_text.insert(tk.END, post.get('content', '内容不可用'))
        content_text.configure(state=tk.DISABLED)
        
        # 评论区域（如果有）
        if 'comments' in post and post['comments']:
            comments_frame = ttk.LabelFrame(frame, text=f"评论 ({len(post['comments'])}条)")
            comments_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            comments_tree = ttk.Treeview(comments_frame, columns=("author", "content"), show="headings", height=5)
            comments_tree.column("author", width=100)
            comments_tree.column("content", width=400)
            comments_tree.heading("author", text="作者")
            comments_tree.heading("content", text="内容")
            
            for comment in post['comments']:
                comments_tree.insert("", "end", values=(
                    comment['author'],
                    comment['content'][:100] + "..." if len(comment['content']) > 100 else comment['content']
                ))
            
            scrollbar = ttk.Scrollbar(comments_frame, orient=tk.VERTICAL, command=comments_tree.yview)
            comments_tree.configure(yscrollcommand=scrollbar.set)
            
            comments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def start_crawler(self):
        if not self.crawler_running:
            
            # 添加UID有效性检查
            if not self.settings.get('uid') or not self.settings['uid'].isdigit():
                messagebox.showerror("配置错误", "请设置有效的用户UID")
                self.add_log("错误：未设置有效的用户UID")
                return
                
            self.crawler_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("状态: 爬取中...")
            self.add_log("爬虫启动")
            
            # 启动爬虫线程
            self.crawler_thread = threading.Thread(target=self.run_crawler, daemon=True)
            self.crawler_thread.start()
    
    def run_crawler(self):
        """运行Scrapy爬虫"""
        try:
            # 删除旧数据文件
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            
            # 构建命令
            command = [
                "scrapy",
                "crawl",
                "nga_monitor",
                "-a", f"fid={self.settings['fid']}",
                "-a", f"pages={self.settings['pages']}",
                "-a", f"uid={self.settings['uid']}",  # 添加UID参数
                "-o",
                self.output_file
            ]
                
            # 在Windows上使用CREATE_NEW_PROCESS_GROUP
            creationflags = 0
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            
            # 启动爬虫进程
            self.crawler_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                bufsize=1,  # 行缓冲
                universal_newlines=True  # 文本模式
            )
        
            self.add_log(f"爬虫进程已启动 (PID: {self.crawler_process.pid})")
        
             # 启动日志处理线程
            stdout_thread = threading.Thread(
                 target=self.read_output, 
                 args=(self.crawler_process.stdout, False),
                 daemon=True
             )
            stderr_thread = threading.Thread(
                  target=self.read_output, 
                  args=(self.crawler_process.stderr, True),
                  daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()
        
            # 启动定时检查数据文件更新
            self.log_timer_id = self.root.after(1000, self.check_data_update)
            
            # 监控进程状态
            while self.crawler_running:
                if self.crawler_process.poll() is not None:
                    break
                time.sleep(0.5)
        
             # 等待输出线程结束
            stdout_thread.join(timeout=2.0)
            stderr_thread.join(timeout=2.0)
        
             # 读取剩余输出
            self.read_output(self.crawler_process.stdout, False)
            self.read_output(self.crawler_process.stderr, True)
            
             # 加载最终数据
            if os.path.exists(self.output_file):
                self.load_data_from_file()
            
            # 更新状态
            return_code = self.crawler_process.returncode
            if return_code == 0:
                self.add_log("爬虫正常结束")
                self.status_var.set("状态: 爬取完成")
            else:
                self.add_log(f"爬虫异常结束，返回码: {return_code}")
                self.status_var.set("状态: 错误")


        except Exception as e:
            self.add_log(f"爬虫运行出错: {str(e)}")
            self.status_var.set("状态: 错误")
        finally:
             if self.log_timer_id:
                self.root.after_cancel(self.log_timer_id)
                self.log_timer_id = None
                self.crawler_running = False
                self.root.after(0, self.update_buttons_state)
    
    def load_data_from_file(self):
        """从文件加载数据并更新UI"""
        if os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.root.after(0, lambda: self.safe_update_data(data))
                    self.add_log(f"已加载 {len(data)} 条帖子数据")
            except Exception as e:
                self.add_log(f"加载数据失败: {str(e)}")
        else:
            self.add_log("数据文件为空")
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.posts = data
                self.root.after(0, lambda: self.safe_update_data(data))
                self.root.after(0, self.update_data_table)
                self.root.after(0, self.update_analysis)
                self.add_log(f"已加载 {len(data)} 条帖子数据")
        except Exception as e:
            self.add_log(f"加载数据失败: {str(e)}")

    def safe_update_data(self, data):
        self.posts = data
        self.update_data_table()
        self.update_analysis()

    def update_buttons_state(self):
        """更新按钮状态"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def stop_crawler(self):
        if self.crawler_running and self.crawler_process:
            self.add_log("正在停止爬虫...")
            self.crawler_running = False
            
            # 发送终止信号
            try:
                if os.name == 'nt':
                    # Windows使用CTRL_BREAK_EVENT
                    self.crawler_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # Unix使用SIGINT
                    self.crawler_process.send_signal(signal.SIGINT)
                
                # 等待进程结束
                self.crawler_process.wait(timeout=10)
            except Exception as e:
                self.add_log(f"停止爬虫时出错: {str(e)}")
            
            self.add_log("爬虫已停止")
            self.status_var.set("状态: 已停止")
            self.update_buttons_state()
    
    def cleanup(self):
        """清理资源"""
        if self.crawler_running and self.crawler_process:
            self.stop_crawler()
    
    def export_excel(self):
        if not self.posts:
            messagebox.showwarning("导出失败", "没有数据可导出")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            title="保存为Excel"
        )
        
        if file_path:
            try:
                df = pd.DataFrame(self.posts)
                
                # 选择需要的列
                columns = ['post_id', 'title', 'author', 'post_time', 'reply_count', 'sentiment', 'risk_level', 'content']
                df = df[[col for col in columns if col in df.columns]]
                
                df.to_excel(file_path, index=False, engine='openpyxl')
                self.add_log(f"数据已导出到: {file_path}")
                messagebox.showinfo("导出成功", f"数据已成功导出到:\n{file_path}")
            except Exception as e:
                self.add_log(f"导出失败: {str(e)}")
                messagebox.showerror("导出失败", f"导出过程中发生错误:\n{str(e)}")
    
    def open_settings(self):
        # 创建设置窗口
        settings_win = tk.Toplevel(self.root)
        settings_win.title("爬虫设置")
        settings_win.geometry("500x400")
        
        # 创建选项卡
        notebook = ttk.Notebook(settings_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 基本设置
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="基本设置")
        
        ttk.Label(basic_frame, text="用户ID (UID):").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        uid_entry = ttk.Entry(basic_frame, width=30)
        uid_entry.grid(row=0, column=1, padx=10, pady=10)
        uid_entry.insert(0, self.settings.get('uid', '17454557'))
        
        ttk.Label(basic_frame, text="板块ID (FID):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        fid_entry = ttk.Entry(basic_frame, width=30)
        fid_entry.grid(row=1, column=1, padx=10, pady=10)
        fid_entry.insert(0, self.settings.get('fid', '7'))
        
        ttk.Label(basic_frame, text="爬取页数:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        pages_entry = ttk.Entry(basic_frame, width=30)
        pages_entry.grid(row=2, column=1, padx=10, pady=10)
        pages_entry.insert(0, self.settings.get('pages', '5'))
        
        # 代理设置
        proxy_frame = ttk.Frame(notebook)
        notebook.add(proxy_frame, text="代理设置")
        
        ttk.Label(proxy_frame, text="代理列表 (每行一个):").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        proxy_text = scrolledtext.ScrolledText(proxy_frame, width=50, height=10)
        proxy_text.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        proxy_text.insert(tk.END, self.settings.get('proxies', ''))
        
        # 保存按钮
        save_btn = ttk.Button(settings_win, text="保存设置", command=lambda: self.save_settings(
            uid_entry.get(),
            fid_entry.get(),
            pages_entry.get(),
            proxy_text.get("1.0", tk.END)
        ))
        save_btn.pack(pady=10)
    
    def save_settings(self, uid, fid, pages, proxies):
        """保存设置到self.settings字典"""
        self.settings['uid'] = uid
        self.settings['fid'] = fid
        self.settings['pages'] = pages
        self.settings['proxies'] = proxies.strip()

        # 设置环境变量（代理中间件会使用）
        os.environ['PROXY_LIST'] = ','.join(
            [p.strip() for p in proxies.split('\n') if p.strip()]
        )

        self.add_log(f"设置已保存: UID={uid}, FID={fid}, 页数={pages}")
        messagebox.showinfo("设置保存", "设置已成功保存")
    
    def add_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.yview(tk.END)  # 滚动到底部
    def read_output(self, pipe, is_error):
        """读取输出流并添加到日志队列"""
        try:
            for line in iter(pipe.readline, ''):
             if line.strip():
                # 将输出放入队列供主线程处理
                self.log_queue.put((line.strip(), is_error))
        except ValueError:
         pass  # 管道已关闭

    def check_data_update(self):
        """定时检查数据文件更新"""
        if self.crawler_running:
            # 检查日志队列
            while not self.log_queue.empty():
                try:
                    line, is_error = self.log_queue.get_nowait()
                    prefix = "错误: " if is_error else ""
                    self.add_log(f"{prefix}{line}")
                except queue.Empty:
                    break
        
            # 检查数据文件更新
            if os.path.exists(self.output_file):
                try:
                    mod_time = os.path.getmtime(self.output_file)
                    if not hasattr(self, 'last_mod_time') or mod_time > self.last_mod_time:
                        self.last_mod_time = mod_time
                        self.load_data_from_file()
                except Exception as e:
                    self.add_log(f"检查数据更新失败: {str(e)}")
        
            # 每1秒检查一次
            self.log_timer_id = self.root.after(1000, self.check_data_update)

    # 修改 safe_update_data 方法
    def safe_update_data(self, data):
        """安全更新数据并显示进度"""
        try:
            self.posts = data
            self.update_data_table()
            self.update_analysis()
        
            # 在日志中显示进度
            self.add_log(f"已加载 {len(data)} 条帖子数据")
        except Exception as e:
            self.add_log(f"更新数据失败: {str(e)}")

# 主程序入口
if __name__ == "__main__":
    root = tk.Tk()
    app = NgaMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()
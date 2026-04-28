# 岛读风格爬虫 - 使用说明

## 快速开始

### 1. 安装Python依赖

脚本只依赖Python内置库，**无需额外安装**（PIL即Pillow是Python内置的）。

但如果运行时报错缺少 Pillow，可以手动安装：
```bash
pip install Pillow
```

### 2. 配置Pexels API Key

脚本需要Pexels的API Key来下载高清图片。

**获取方式：**
1. 访问 https://www.pexels.com/api/
2. 注册账号（用Google或邮箱都行）
3. 创建新应用，获取API Key（免费额度：每月500张图）

**配置方法：**
打开 `content_scraper.py`，找到第18行：
```python
PEXELS_API_KEY = "YOUR_PEXELS_API_KEY"
```
把 `YOUR_PEXELS_API_KEY` 替换成你的真实Key。

### 3. 运行脚本

```bash
cd e:\wmq\write-tool
python content_scraper.py
```

运行后会：
- 创建 `images/` 目录
- 爬取句子和图片
- 生成 `daily_content.json`

---

## 输出格式

```json
[
  {
    "id": 1,
    "text": "所有句子都会按照这个格式存储",
    "image": "images/01.jpg"
  }
]
```

---

## Windows定时任务设置（每天凌晨自动运行）

### 步骤1：确认Python路径

打开CMD，输入：
```bash
where python
```

会显示类似 `C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\python.exe` 的路径，**复制这个路径**。

### 步骤2：确认脚本路径

脚本全路径是：`e:\wmq\write-tool\content_scraper.py`

### 步骤3：创建定时任务

**方法一：使用任务计划程序图形界面**

1. 按 `Win键 + R`，输入 `taskschd.msc`，回车
2. 右侧点 **"创建基本任务"**
3. 名称填写：`岛读内容爬虫`（随意）
4. 触发器选择：**每天** → 时间设为 `00:30`（凌晨）
5. 操作选择：**启动程序**
6. 程序/脚本填写（注意去掉空格）：
   ```
   C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\python.exe
   ```
7. 参数填写：
   ```
   e:\wmq\write-tool\content_scraper.py
   ```
8. 完成

**方法二：使用命令行（更快捷）**

打开CMD，粘贴以下命令（**需要修改你的Python路径**）：

```bash
schtasks /create /tn "岛读内容爬虫" /tr "C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\python.exe e:\wmq\write-tool\content_scraper.py" /sc daily /st 00:30
```

**查看已创建的任务：**
```bash
schtasks /query /tn "岛读内容爬虫"
```

**删除任务（如果不需要了）：**
```bash
schtasks /delete /tn "岛读内容爬虫" /f
```

---

## 常见问题

### Q: 运行时提示 "PIL module not found"
**A:** 运行 `pip install Pillow`

### Q: 一言/句子控请求失败
**A:** 这些是免费API，可能不稳定。脚本已有重试机制，如果持续失败，检查网络或稍后再试。

### Q: Pexels图片下载失败
**A:**
1. 检查API Key是否正确
2. 检查是否达到每月500张额度
3. 网络可能不稳定，脚本会自动重试

### Q: 图片太大了
**A:** 脚本会自动压缩到500KB以内。如果还是太大，可能是原图分辨率不够，这不是bug。

### Q: 想要手动触发一次
**A:** 直接双击 `content_scraper.py` 或者在文件夹地址栏输入 `cmd` 后运行 `python content_scraper.py`

---

## 文件结构

```
e:\wmq\write-tool\
├── content_scraper.py   ← 主脚本
├── daily_content.json   ← 输出内容（运行后生成）
└── images\              ← 图片目录（自动创建）
    ├── 01.jpg
    ├── 02.jpg
    └── ...
```

---

## 定时任务运行日志

如果脚本执行失败，可以在CMD中手动运行一次查看错误信息。如果定时任务执行不正常，可以在任务计划程序中勾选"无论是否登录都要运行"，并设置最大运行时间。
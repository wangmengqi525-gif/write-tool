"""
岛读风格文艺内容爬虫
- 自动爬取一言、句子控的治愈/哲思短句
- 自动从Pexels爬取意境风景图
- 自动压缩、裁剪图片（9:16竖图，≤500KB）
- 输出 daily_content.json
"""

import os
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from pathlib import Path

# 图片处理库（Python内置，无需额外安装）
from PIL import Image

# ============================================================
# 配置区
# ============================================================

# Pexels API Key（免费额度：每月500张图）
# 申请地址：https://www.pexels.com/api/
PEXELS_API_KEY = "Fav8gxlnnn6pm6R5Cp841d4Uzd1d29scPG608T6yTS2Wlv1zHxCDGJjX"

# 爬取数量配置
TARGET_SENTENCES = 20       # 最终保留的好句数量
TARGET_IMAGES = 10          # 需要的图片数量（多爬一些备用）

# 图片要求
IMAGE_WIDTH = 1080           # 目标宽度
IMAGE_QUALITY = 85          # JPEG压缩质量（1-100）
MAX_FILE_SIZE = 500 * 1024  # 最大500KB

# 一言API（无需Key，直接可用）
YIYAN_API = "https://v1.hitokoto.cn?encode=json&c=s&c=i&c=k"

# 句子控页面（无需Key）
JUZI_KONG_URL = "https://www.juzikong.com"

# 请求间隔（秒），防止被封
MIN_DELAY = 1
MAX_DELAY = 3

# 目录
OUTPUT_DIR = Path(__file__).parent
IMAGES_DIR = OUTPUT_DIR / "images"
OUTPUT_FILE = OUTPUT_DIR / "daily_content.json"


# ============================================================
# 工具函数
# ============================================================

def log(msg: str):
    """打印带时间戳的日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def safe_request(url: str, headers: dict = None, max_retries: int = 3) -> requests.Response:
    """
    安全的HTTP请求，带重试机制
    - max_retries: 最大重试次数
    - 返回: Response对象
    - 失败时抛出异常
    """
    headers = headers or {}
    # 默认User-Agent
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            log(f"请求失败（第{attempt + 1}次）: {url} → {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))  # 失败后等久一点
            else:
                raise


def random_delay():
    """随机等待，避免请求过快"""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def compute_text_hash(text: str) -> str:
    """计算句子哈希值，用于去重"""
    return hashlib.md5(text.strip().encode()).hexdigest()


# ============================================================
# 句子爬取
# ============================================================

def fetch_from_yiyan(count: int = 50) -> list[str]:
    """
    从一言API获取句子
    - hitokoto.cn 是一个免费的开源一言API
    - c=s,i,k 表示获取诗词、动画、名言分类（偏文艺）
    """
    sentences = []
    seen = set()

    log("正在从一言API获取句子...")

    # 一言API每次请求只返回1条，需要循环获取
    while len(sentences) < count:
        try:
            response = safe_request(YIYAN_API)
            data = response.json()

            # hitokoto字段是句子内容，from字段是出处
            text = data.get("hitokoto", "").strip()
            source = data.get("from", "").strip()

            # 过滤太短或太长的句子（岛读风格通常是100-300字）
            if 10 <= len(text) <= 500 and text not in seen:
                # 去除末尾的莫名奇妙标点和空格
                text = text.rstrip("。！？.,!?")
                if source:
                    text = f"{text} ——{source}"
                sentences.append(text)
                seen.add(text)
                log(f"  抓取: {text[:30]}...")

            random_delay()

        except Exception as e:
            log(f"一言API请求异常: {e}")
            time.sleep(3)

    log(f"一言获取完成，共{len(sentences)}条")
    return sentences


def fetch_from_juzikong(count: int = 50) -> list[str]:
    """
    从句子控网站获取句子
    - 由于句子控没有公开API，我们解析其公开页面
    - 如果页面结构变化，这个函数可能需要调整
    """
    sentences = []
    seen = set()

    log("正在从句子控获取句子...")

    # 句子控的分类页面
    # 我们尝试多个分类：治愈、哲思、文艺
    categories = ["zhili", "zhexue", "wenyi"]

    for cat in categories:
        if len(sentences) >= count:
            break

        try:
            # 句子控的API接口（公开的）
            api_url = f"https://api.juzikong.com/sentence/list?category={cat}&page=1&size=50"
            response = safe_request(api_url)
            data = response.json()

            # 解析返回的句子
            items = data.get("data", {}).get("list", []) if isinstance(data, dict) else []

            for item in items:
                if len(sentences) >= count:
                    break

                text = item.get("content", "").strip() if isinstance(item, dict) else str(item).strip()

                # 过滤：去重、长度检查
                if 10 <= len(text) <= 500 and text not in seen:
                    sentences.append(text)
                    seen.add(text)
                    log(f"  抓取: {text[:30]}...")

            random_delay()

        except Exception as e:
            log(f"句子控[{cat}]请求异常: {e}")
            continue

    log(f"句子控获取完成，共{len(sentences)}条")
    return sentences


def deduplicate_sentences(sentences: list[str]) -> list[str]:
    """
    去重句子
    - 使用哈希集合去除完全重复的内容
    - 去除包含特殊符号或明显低质量的内容
    """
    seen_hashes = set()
    unique = []

    # 低质量关键词（这些句子通常太水，不适合岛读风格）
    bad_keywords = ["哈哈哈", "哈哈哈哈哈", "呵呵", "哈哈哈哈", "卧槽", "牛逼", "666", "牛批"]

    for text in sentences:
        # 计算哈希
        h = compute_text_hash(text)

        # 跳过重复
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        # 跳过包含低质关键词的
        if any(kw in text for kw in bad_keywords):
            continue

        # 跳过全是英文或符号的
        english_ratio = sum(1 for c in text if c.isascii()) / max(len(text), 1)
        if english_ratio > 0.7:
            continue

        unique.append(text)

    log(f"去重完成，保留{len(unique)}条")
    return unique


# ============================================================
# 图片爬取（从Pexels）
# ============================================================

def search_pexels_photos(query: str, per_page: int = 15) -> list[dict]:
    """
    搜索Pexels图片
    - query: 搜索关键词
    - per_page: 每页数量（最大80）
    - 返回: 图片信息列表
    """
    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",  # 竖图（9:16）
        "size": "large"  # 大图，便于压缩
    }

    try:
        response = safe_request(url, headers=headers)
        data = response.json()
        photos = data.get("photos", [])

        log(f"  Pexels[{query}] 找到 {len(photos)} 张图")
        return photos

    except Exception as e:
        log(f"  Pexels[{query}] 请求失败: {e}")
        return []


def download_image(url: str, save_path: Path) -> bool:
    """
    下载单张图片
    - url: 图片URL
    - save_path: 保存路径
    - 返回: 是否成功
    """
    try:
        response = safe_request(url)
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        log(f"  图片下载失败: {e}")
        return False


def process_image(input_path: Path, output_path: Path, target_width: int = 1080) -> bool:
    """
    处理图片：裁剪、压缩
    - 裁剪为9:16竖图
    - 压缩到500KB以下
    - 使用PIL（Python内置）
    """
    try:
        with Image.open(input_path) as img:
            # 转换RGBA为RGB（JPEG不支持透明）
            if img.mode == "RGBA":
                img = img.convert("RGB")

            # 计算9:16裁剪
            w, h = img.size
            target_ratio = 9 / 16
            current_ratio = w / h

            if current_ratio > target_ratio:
                # 图片太宽，裁剪左右
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                # 图片太高，裁剪上下
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))

            # 缩放到目标宽度
            img = img.resize((target_width, int(target_width / target_ratio)), Image.LANCZOS)

            # 逐步降低质量直到满足大小要求
            quality = 90
            while quality > 30:
                img.save(output_path, "JPEG", quality=quality, optimize=True)
                if output_path.stat().st_size <= MAX_FILE_SIZE:
                    break
                quality -= 10

            return True

    except Exception as e:
        log(f"  图片处理失败: {e}")
        return False


def fetch_images(count: int = 10) -> list[str]:
    """
    从Pexels获取意境图片
    - 搜索多个关键词以获得不同风格的图片
    """
    # 意境关键词列表（岛读风格偏治愈、文艺）
    queries = [
        "mist fog morning",      # 晨雾
        "rain window",          # 雨天
        "forest path",          # 森林
        "lake reflection",      # 湖面
        "light sunbeam",        # 光影
        "minimalist landscape", # 极简
        "sea fog",              # 海雾
        "mountain clouds",      # 山云
        "snowy trees",          # 雪景
        "starry night",         # 星空
    ]

    downloaded_paths = []
    temp_dir = IMAGES_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)

    log("正在从Pexels获取意境图片...")

    # 随机打乱关键词顺序
    random.shuffle(queries)

    for query in queries:
        if len(downloaded_paths) >= count:
            break

        photos = search_pexels_photos(query, per_page=5)

        for photo in photos:
            if len(downloaded_paths) >= count:
                break

            # 获取大图URL
            src = photo.get("src", {})
            original_url = src.get("original") or src.get("large2x") or src.get("large")

            if not original_url:
                continue

            # 下载到临时目录
            temp_file = temp_dir / f"{random.randint(1000, 9999)}.jpg"

            if download_image(original_url, temp_file):
                # 生成正式文件名
                idx = len(downloaded_paths) + 1
                output_file = IMAGES_DIR / f"{idx:02d}.jpg"

                # 处理并保存
                if process_image(temp_file, output_file):
                    downloaded_paths.append(str(output_file))
                    log(f"  保存: {output_file.name} ({output_file.stat().st_size // 1024}KB)")

                # 删除临时文件
                try:
                    temp_file.unlink()
                except:
                    pass

            random_delay()

    # 清理临时目录
    try:
        temp_dir.rmdir()
    except:
        pass

    log(f"图片获取完成，共{len(downloaded_paths)}张")
    return downloaded_paths


# ============================================================
# 主流程
# ============================================================

def main():
    """主函数：协调整个爬取流程"""
    log("=" * 50)
    log("岛读风格内容爬虫启动")
    log("=" * 50)

    # 确保图片目录存在
    IMAGES_DIR.mkdir(exist_ok=True)

    all_sentences = []

    # 1. 爬取一言句子
    try:
        yiyan_sentences = fetch_from_yiyan(count=30)
        all_sentences.extend(yiyan_sentences)
    except Exception as e:
        log(f"一言爬取失败: {e}")

    random_delay()

    # 2. 爬取句子控句子
    try:
        juzi_sentences = fetch_from_juzikong(count=30)
        all_sentences.extend(juzi_sentences)
    except Exception as e:
        log(f"句子控爬取失败: {e}")

    # 3. 去重过滤
    unique_sentences = deduplicate_sentences(all_sentences)

    # 取目标数量
    target_sentences = unique_sentences[:TARGET_SENTENCES]

    # 4. 爬取图片
    image_paths = []
    try:
        image_paths = fetch_images(count=TARGET_IMAGES)
    except Exception as e:
        log(f"图片爬取失败: {e}")

    # 5. 组合内容
    content = []

    # 配对句子和图片（交替或随机）
    random.shuffle(target_sentences)

    for i, sentence in enumerate(target_sentences):
        image_path = image_paths[i % len(image_paths)] if image_paths else None

        item = {
            "id": i + 1,
            "text": sentence,
            "image": os.path.basename(image_path) if image_path else None
        }
        content.append(item)

    # 6. 保存JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    log("=" * 50)
    log(f"完成！输出 {len(content)} 条内容到 {OUTPUT_FILE}")
    log("=" * 50)

    # 打印结果预览
    print("\n--- 内容预览 ---")
    for item in content[:3]:
        print(f"[{item['id']}] {item['text'][:40]}...")
        print(f"      图片: {item['image']}")
        print()


if __name__ == "__main__":
    main()
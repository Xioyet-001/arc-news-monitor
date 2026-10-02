import requests
import json
import os
import time
from requests.adapters import HTTPAdapter, Retry

# 配置
FEED_URL = "https://arcraiders.com/news"
SCT_KEY = os.environ.get("SCT_SENDKEY", "")
STATE_FILE = "seen_state.json"

def load_seen():
    """加载已经推送过的新闻链接"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen(seen_set):
    """保存已推送链接到本地文件，供cache缓存保存"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_set), f, ensure_ascii=False)

def send_wechat(title, content):
    """调用Server酱推送微信"""
    if not SCT_KEY:
        print("未配置SCT_SENDKEY，跳过推送")
        return
    url = f"https://sctapi.ftqq.com/{SCT_KEY}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        resp = requests.post(url, data=data, timeout=15)
        print("推送返回：", resp.text)
    except Exception as e:
        print("推送异常：", str(e))

def get_news_list():
    # 增加重试机制，应对GitHub网络波动
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    resp = session.get(FEED_URL, headers=headers, timeout=(10,30))
    resp.raise_for_status()
    html = resp.text

    # 简易提取新闻链接标题（根据页面a标签href="/news/*"）
    import re
    pattern = re.compile(r'<a href="(/news[^"]*)".*?>(.*?)</a>', re.S)
    items = pattern.findall(html)
    news = []
    for href, title_raw in items:
        full_url = "https://arcraiders.com" + href
        title_clean = title_raw.strip().replace("\n","").replace("\r","")
        if full_url not in [x["url"] for x in news]:
            news.append({"title": title_clean, "url": full_url})
    return news


def main():
    seen = load_seen()
    print(f"当前已记录已推送新闻数量：{len(seen)}")
    try:
        news_list = get_news_list()
    except Exception as e:
        print(f"抓取官网失败：{str(e)}")
        save_seen(seen)
        return

    new_news = []
    for item in news_list:
        url = item["url"]
        title = item["title"]
        if url not in seen:
            new_news.append(item)

    if not new_news:
        print("没有发现新新闻，结束运行")
        save_seen(seen)
        return

    print(f"发现 {len(new_news)} 条新新闻，准备推送")
    for n in new_news:
        title_msg = f"ARC Raiders 新新闻：{n['title']}"
        desp_msg = f"标题：{n['title']}\n链接：{n['url']}"
        send_wechat(title_msg, desp_msg)
        seen.add(n["url"])

    # 更新保存记录！非常关键
    save_seen(seen)
    print("已更新已推送记录文件")

if __name__ == "__main__":
    main()

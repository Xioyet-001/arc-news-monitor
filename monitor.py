import requests
import json
import os
from bs4 import BeautifulSoup

# ==========配置（已填好你的信息）==========
NEWS_URL = "https://arcraiders.com/news"
SERVERCHAN_KEY = "SCT431841T0bK5nJE4zqKFzbZLtfcPqVlX"
PUSH_API = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
CACHE_FILE = "pushed.json"
TIMEOUT = 15
# =========================================


def load_pushed():
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("urls", []))
    except Exception as e:
        print(f"[警告]读取缓存失败:{e}，以空集合继续运行")
        return set()


def save_pushed(pushed_set):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": list(pushed_set)}, f, ensure_ascii=False, indent=2)


def fetch_news():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    resp = requests.get(NEWS_URL, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    news_list = []

    # 解析新闻列表 a标签，提取标题+相对链接转绝对链接
    for a_tag in soup.select("a[href^='/news/']"):
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href")
        if not title or not href:
            continue
        full_url = "https://arcraiders.com" + href
        news_list.append({"title": title, "url": full_url})

    # 去重：同一个url只保留一条
    seen = set()
    dedup = []
    for item in news_list:
        if item["url"] not in seen:
            seen.add(item["url"])
            dedup.append(item)
    return dedup


def send_wechat(title, content):
    payload = {"title": title, "desp": content}
    r = requests.post(PUSH_API, data=payload, timeout=TIMEOUT)
    res = r.json()
    print(f"[推送返回] {res}")
    if res.get("code") != 0:
        raise Exception(f"Server酱推送失败: {res}")


def main():
    pushed_urls = load_pushed()
    news_list = fetch_news()

    new_news = [n for n in news_list if n["url"] not in pushed_urls]

    if not new_news:
        print("✅没有发现新新闻，程序结束")
        return

    print(f"🔥检测到 {len(new_news)} 条新新闻，准备推送")
    for item in new_news:
        send_wechat(
            title=f"ARC Raiders｜{item['title']}",
            content=f"[点击查看原文]({item['url']})"
        )
        pushed_urls.add(item["url"])

    save_pushed(pushed_urls)
    print("✅处理完成，已更新推送记录缓存")


if __name__ == "__main__":
    main()

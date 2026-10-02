#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Raiders 官网新闻监控
=======================
- 抓取 https://arcraiders.com/news（国内可直连，不用翻墙）
- 解析全部新闻（标题 + 日期 + 链接）
- 与本地记录比对，发现新文章时通过 Server酱（方糖）推送到微信
- 首次运行只建立基线，不推送旧闻
"""

import re
import json
import os
import html
import urllib.parse
import urllib.request

NEWS_URL = "https://arcraiders.com/news"
STATE_FILE = "seen_state.json"
SENDKEY = os.environ.get("SCT_SENDKEY", "")

# 匹配新闻列表里的每一条：<a href="/news/xxx"> ... 标题 ... 日期 ... </a>
ROW_RE = re.compile(
    r'<a class="news-article-row_row__[^"]*"[^>]*href="(/news/[^"]+)"[^>]*>.*?'
    r'news-article-row_title__e__gM">(.*?)</span>\s*'
    r'<span class="news-article-row_date__Z6Ego">(.*?)</span>',
    re.S,
)


def fetch(url):
    """抓取页面 HTML"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def parse_news(text):
    """从 HTML 中提取所有新闻条目（按出现顺序去重）"""
    items = []
    for m in ROW_RE.finditer(text):
        url = "https://arcraiders.com" + m.group(1)
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        date = html.unescape(m.group(3)).strip()
        items.append({"url": url, "title": title, "date": date})
    seen, out = set(), []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            out.append(it)
    return out


def load_state():
    """读取已见新闻 URL 集合"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("seen", []))
        except Exception:
            return set()
    return set()


def save_state(seen):
    """保存已见新闻 URL 集合"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen": sorted(seen)}, f, ensure_ascii=False)


def push_wechat(news_items):
    """通过 Server酱推送新文章到微信"""
    if not SENDKEY:
        print("[!] 未配置环境变量 SCT_SENDKEY，跳过微信推送（本地调试可忽略）")
        return
    title = "ARC官网更新 %d 篇" % len(news_items)
    lines = []
    for it in news_items:
        lines.append("%s\n%s\n%s" % (it["date"], it["title"], it["url"]))
    desp = "\n\n".join(lines)
    payload = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    url = "https://sctapi.ftqq.com/%s.send" % SENDKEY
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def main():
    print("正在抓取：", NEWS_URL)
    text = fetch(NEWS_URL)
    news = parse_news(text)
    print("解析到新闻 %d 条" % len(news))

    seen = load_state()

    # 首次运行 / 无历史记录：只建立基线，不推送
    if not seen:
        save_state({it["url"] for it in news})
        print("首次运行：已建立基线，记录现有新闻 %d 条，本次不推送" % len(news))
        return

    new_items = [it for it in news if it["url"] not in seen]
    if not new_items:
        print("无新文章，监控正常。")
        return

    for it in new_items:
        seen.add(it["url"])
    save_state(seen)

    print("发现新文章 %d 篇：" % len(new_items))
    for it in new_items:
        print("  - %s | %s | %s" % (it["date"], it["title"], it["url"]))

    result = push_wechat(new_items)
    print("微信推送结果：", result[:200])


if __name__ == "__main__":
    main()

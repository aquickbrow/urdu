# -*- coding: utf-8 -*-
"""
UrduNewsDaily MOBILE — Android & iOS port
Built for: Dr. Naveed Ullah Hashmi (Neo)
Stack: Python + Kivy + KivyMD-free (pure Kivy) + feedparser + requests

Same brain as the desktop v2.1:
- On-demand fetch from 16 Urdu + world sources
- Category filter: All / Pakistan / World / Business / Sports / Sci-Tech
- RTL Nastaliq rendering (bundled Noto Nastaliq font)
- English sources auto-translated to Urdu (free Google endpoint)
- Optional AI summary + "impact for you" (Anthropic, key entered in-app)
- Bookmarks saved on-device, open-in-browser, share/copy
- No background polling — user taps Refresh
"""

import os
import re
import json
import time
import socket
import threading
import urllib.parse
import webbrowser
from datetime import datetime

import requests
import feedparser

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.utils import platform

# ------------------------------------------------------------------
# RTL / Arabic shaping — pure-Python, NO external libraries.
# (arabic_reshaper / python-bidi have no Android build recipe, so we
#  ship our own shaper in urdu_shaper.py and import it directly.)
# ------------------------------------------------------------------
try:
    from urdu_shaper import shape_urdu
except Exception:
    def shape_urdu(text):
        return text or ""


USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)
socket.setdefaulttimeout(15)

VERSION = "2.1-mobile"

# ------------------------------------------------------------------
# Storage — Android/iOS sandbox safe
# ------------------------------------------------------------------
def app_dir():
    try:
        from kivy.app import App as _A
        d = _A.get_running_app().user_data_dir
        if d:
            return d
    except Exception:
        pass
    d = os.path.join(os.path.expanduser("~"), "UrduNewsDaily")
    os.makedirs(d, exist_ok=True)
    return d


def _store_path(name):
    return os.path.join(app_dir(), name)


def load_json(name, default):
    try:
        p = _store_path(name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(name, data):
    try:
        with open(_store_path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ------------------------------------------------------------------
# SOURCES  (ported verbatim from desktop v2.1)
# ------------------------------------------------------------------
def _gnews_ur(query):
    return ("https://news.google.com/rss/search?q="
            + urllib.parse.quote(query) + "&hl=ur&gl=PK&ceid=PK:ur")


def _gnews_en(query):
    return ("https://news.google.com/rss/search?q="
            + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en")


SOURCES = {
    "Dawn Urdu": {
        "Pakistan": ["https://www.dawnnews.tv/feeds/pakistan", _gnews_ur("site:dawnnews.tv pakistan")],
        "World":    ["https://www.dawnnews.tv/feeds/world", _gnews_ur("site:dawnnews.tv world")],
        "Business": ["https://www.dawnnews.tv/feeds/business", _gnews_ur("site:dawnnews.tv business")],
        "Sports":   ["https://www.dawnnews.tv/feeds/sports", _gnews_ur("site:dawnnews.tv sports")],
        "Sci-Tech": ["https://www.dawnnews.tv/feeds/sci-tech", _gnews_ur("site:dawnnews.tv technology")],
    },
    "Jang": {
        "Pakistan": ["https://jang.com.pk/rss/1", _gnews_ur("site:jang.com.pk pakistan")],
        "World":    ["https://jang.com.pk/rss/4", _gnews_ur("site:jang.com.pk world")],
        "Business": ["https://jang.com.pk/rss/3", _gnews_ur("site:jang.com.pk business")],
        "Sports":   ["https://jang.com.pk/rss/2", _gnews_ur("site:jang.com.pk sports")],
        "Sci-Tech": ["https://jang.com.pk/rss/14", _gnews_ur("site:jang.com.pk technology")],
    },
    "Express": {
        "Pakistan": ["https://www.express.pk/feed/pakistan/", _gnews_ur("site:express.pk pakistan")],
        "World":    ["https://www.express.pk/feed/world/", _gnews_ur("site:express.pk world")],
        "Business": ["https://www.express.pk/feed/business/", _gnews_ur("site:express.pk business")],
        "Sports":   ["https://www.express.pk/feed/sports/", _gnews_ur("site:express.pk sports")],
        "Sci-Tech": ["https://www.express.pk/feed/science/", _gnews_ur("site:express.pk technology")],
    },
    "Geo Urdu": {
        "Pakistan": ["https://urdu.geo.tv/rss/1/1", _gnews_ur("site:urdu.geo.tv pakistan")],
        "World":    ["https://urdu.geo.tv/rss/1/4", _gnews_ur("site:urdu.geo.tv world")],
        "Business": ["https://urdu.geo.tv/rss/1/3", _gnews_ur("site:urdu.geo.tv business")],
        "Sports":   ["https://urdu.geo.tv/rss/1/2", _gnews_ur("site:urdu.geo.tv sports")],
        "Sci-Tech": ["https://urdu.geo.tv/rss/1/14", _gnews_ur("site:urdu.geo.tv technology")],
    },
    "BBC Urdu": {
        "Pakistan": [_gnews_ur("site:bbc.com/urdu pakistan"), "https://feeds.bbci.co.uk/urdu/pakistan/rss.xml"],
        "World":    [_gnews_ur("site:bbc.com/urdu world"), "https://feeds.bbci.co.uk/urdu/world/rss.xml"],
        "Business": [_gnews_ur("site:bbc.com/urdu business")],
        "Sports":   [_gnews_ur("site:bbc.com/urdu sport")],
        "Sci-Tech": [_gnews_ur("site:bbc.com/urdu science")],
    },
    "VOA Urdu": {
        "Pakistan": [_gnews_ur("site:urduvoa.com pakistan")],
        "World":    [_gnews_ur("site:urduvoa.com world")],
        "Business": [_gnews_ur("site:urduvoa.com business")],
        "Sports":   [_gnews_ur("site:urduvoa.com sports")],
        "Sci-Tech": [_gnews_ur("site:urduvoa.com technology")],
    },
    "DW Urdu": {
        "Pakistan": [_gnews_ur("site:dw.com/ur pakistan"), "https://rss.dw.com/xml/rss-urd-pak"],
        "World":    [_gnews_ur("site:dw.com/ur world"), "https://rss.dw.com/xml/rss-urd-world"],
        "Business": [_gnews_ur("site:dw.com/ur business")],
        "Sports":   [_gnews_ur("site:dw.com/ur sports")],
        "Sci-Tech": [_gnews_ur("site:dw.com/ur science")],
    },
    "ARY Urdu": {
        "Pakistan": [_gnews_ur("site:arynews.tv pakistan")],
        "World":    [_gnews_ur("site:arynews.tv world")],
        "Business": [_gnews_ur("site:arynews.tv business")],
        "Sports":   [_gnews_ur("site:arynews.tv sports")],
        "Sci-Tech": [_gnews_ur("site:arynews.tv technology")],
    },
    "Samaa Urdu": {
        "Pakistan": [_gnews_ur("site:samaa.tv/urdu pakistan")],
        "World":    [_gnews_ur("site:samaa.tv/urdu world")],
        "Business": [_gnews_ur("site:samaa.tv/urdu business")],
        "Sports":   [_gnews_ur("site:samaa.tv/urdu sports")],
        "Sci-Tech": [_gnews_ur("site:samaa.tv/urdu technology")],
    },
    "BBC News": {
        "World":    ["https://feeds.bbci.co.uk/news/world/rss.xml", _gnews_en("site:bbc.com world")],
        "Business": ["https://feeds.bbci.co.uk/news/business/rss.xml", _gnews_en("site:bbc.com business")],
        "Sports":   ["https://feeds.bbci.co.uk/sport/rss.xml", _gnews_en("site:bbc.com sport")],
        "Sci-Tech": ["https://feeds.bbci.co.uk/news/technology/rss.xml", _gnews_en("site:bbc.com technology")],
    },
    "The Guardian": {
        "Pakistan": ["https://www.theguardian.com/world/pakistan/rss"],
        "World":    ["https://www.theguardian.com/world/rss"],
        "Business": ["https://www.theguardian.com/uk/business/rss"],
        "Sports":   ["https://www.theguardian.com/sport/rss"],
        "Sci-Tech": ["https://www.theguardian.com/technology/rss"],
    },
    "Al Jazeera": {
        "World":    ["https://www.aljazeera.com/xml/rss/all.xml", _gnews_en("site:aljazeera.com")],
        "Business": [_gnews_en("site:aljazeera.com business")],
        "Sports":   [_gnews_en("site:aljazeera.com sports")],
    },
    "Reuters": {
        "World":    [_gnews_en("site:reuters.com world")],
        "Business": [_gnews_en("site:reuters.com business")],
        "Sports":   [_gnews_en("site:reuters.com sports")],
        "Sci-Tech": [_gnews_en("site:reuters.com technology")],
    },
    "NYT": {
        "World":    ["https://rss.nytimes.com/services/xml/rss/nyt/World.xml"],
        "Business": ["https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"],
        "Sports":   ["https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml"],
        "Sci-Tech": ["https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"],
    },
    "CNN": {
        "World":    ["http://rss.cnn.com/rss/edition_world.rss", _gnews_en("site:cnn.com world")],
        "Business": ["http://rss.cnn.com/rss/money_news_international.rss"],
        "Sports":   ["http://rss.cnn.com/rss/edition_sport.rss"],
        "Sci-Tech": ["http://rss.cnn.com/rss/edition_technology.rss"],
    },
    "Associated Press": {
        "World":    [_gnews_en("site:apnews.com world")],
        "Business": [_gnews_en("site:apnews.com business")],
        "Sports":   [_gnews_en("site:apnews.com sports")],
    },
}

CATEGORIES = ["All", "Pakistan", "World", "Business", "Sports", "Sci-Tech"]

GOLD = (0.831, 0.686, 0.216, 1)      # #D4AF37
GOLD_DIM = (0.545, 0.459, 0, 1)
BG = (0.059, 0.059, 0.059, 1)        # #0F0F0F
CARD = (0.102, 0.102, 0.102, 1)
TEXT = (0.929, 0.929, 0.929, 1)
DIM = (0.6, 0.6, 0.6, 1)


# ------------------------------------------------------------------
# Helpers ported from desktop
# ------------------------------------------------------------------
def detect_urdu(text):
    if not text:
        return False
    arabic_range = letters = 0
    for c in text:
        if c.isalpha() or ('\u0600' <= c <= '\u06FF'):
            letters += 1
            if ('\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
                    or '\uFB50' <= c <= '\uFDFF' or '\uFE70' <= c <= '\uFEFF'):
                arabic_range += 1
    if letters < 5:
        return False
    return (arabic_range / letters) > 0.5


_translate_cache = {}


def translate_to_urdu(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text in _translate_cache:
        return _translate_cache[text]
    try:
        url = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl=en&tl=ur&dt=t&q=" + urllib.parse.quote(text))
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            out = "".join(chunk[0] for chunk in data[0] if chunk[0])
            _translate_cache[text] = out
            return out
    except Exception:
        pass
    return text


def fetch_feed(source, category, urls):
    if isinstance(urls, str):
        urls = [urls]
    for url in urls:
        articles = []
        try:
            sep = "&" if "?" in url else "?"
            fresh = f"{url}{sep}_t={int(time.time())}"
            headers = {
                "User-Agent": USER_AGENT,
                "Cache-Control": "no-cache",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "ur,en;q=0.9",
            }
            resp = requests.get(fresh, headers=headers, timeout=12)
            feed = feedparser.parse(resp.content if resp.status_code == 200
                                    else url)
            if not feed.entries:
                continue
            for entry in feed.entries[:15]:
                raw = entry.get("summary", "").strip()
                clean = re.sub(r"<[^>]+>", "", raw)
                clean = re.sub(r"\s+", " ", clean).strip()
                title = entry.get("title", "").strip()
                if " - " in title:
                    title = re.sub(r"\s+-\s+[^-]+$", "", title)
                pub = entry.get("published", "") or entry.get("updated", "")
                ts = 0
                ps = entry.get("published_parsed") or entry.get("updated_parsed")
                if ps:
                    try:
                        ts = time.mktime(ps)
                    except Exception:
                        ts = 0
                articles.append({
                    "source": source, "category": category,
                    "title": title, "summary": clean[:400],
                    "link": entry.get("link", ""),
                    "published": pub, "ts": ts,
                })
            if articles:
                return articles, "ok"
        except Exception:
            continue
    return [], "fail"


# ------------------------------------------------------------------
# UI widgets
# ------------------------------------------------------------------
class ArticleCard(BoxLayout):
    def __init__(self, article, app, **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         padding=dp(12), spacing=dp(6), **kw)
        self.article = article
        self.app = app
        self.bind(minimum_height=self.setter("height"))

        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            self._c = Color(*CARD)
            self._r = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._upd, size=self._upd)

        title = article["title"]
        summ = article["summary"]
        # English-source -> translate to Urdu on demand for the card line
        display_title = title
        if not detect_urdu(title):
            display_title = translate_to_urdu(title) or title

        lbl = Label(text=shape_urdu(display_title), color=GOLD,
                    font_name="UrduFont", font_size=dp(19),
                    halign="right", valign="top", size_hint_y=None,
                    text_size=(Window.width - dp(48), None))
        lbl.bind(texture_size=lambda i, v: setattr(lbl, "height", v[1]))
        self.add_widget(lbl)

        meta = Label(text=f"{article['source']}  •  {article['category']}",
                     color=DIM, font_size=dp(12), halign="right",
                     size_hint_y=None, height=dp(18),
                     text_size=(Window.width - dp(48), None))
        self.add_widget(meta)

        if summ:
            ds = summ if detect_urdu(summ) else (translate_to_urdu(summ) or summ)
            body = Label(text=shape_urdu(ds), color=TEXT, font_name="UrduFont",
                         font_size=dp(15), halign="right", valign="top",
                         size_hint_y=None,
                         text_size=(Window.width - dp(48), None))
            body.bind(texture_size=lambda i, v: setattr(body, "height", v[1]))
            self.add_widget(body)

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        b_open = Button(text="Open", background_color=GOLD_DIM,
                        color=(1, 1, 1, 1), font_size=dp(13))
        b_open.bind(on_release=lambda *_: self._open())
        b_save = Button(text="Save", background_color=(0.16, 0.16, 0.16, 1),
                        color=GOLD, font_size=dp(13))
        b_save.bind(on_release=lambda *_: self.app.bookmark(article))
        b_ai = Button(text="AI", background_color=(0.16, 0.16, 0.16, 1),
                      color=GOLD, font_size=dp(13))
        b_ai.bind(on_release=lambda *_: self.app.ai_summary(article))
        row.add_widget(b_open)
        row.add_widget(b_save)
        row.add_widget(b_ai)
        self.add_widget(row)

    def _upd(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size

    def _open(self):
        link = self.article.get("link")
        if not link:
            return
        try:
            if platform == "android":
                from jnius import autoclass, cast
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_VIEW)
                intent.setData(Uri.parse(link))
                cur = cast("android.app.Activity", PythonActivity.mActivity)
                cur.startActivity(intent)
            else:
                webbrowser.open(link)
        except Exception:
            webbrowser.open(link)


class UrduNewsApp(App):
    def build(self):
        Window.clearcolor = BG
        self.title = "Urdu News Daily"
        self.bookmarks = load_json("bookmarks.json", [])
        self.config_data = load_json("config.json", {})
        self.current_cat = "All"

        root = BoxLayout(orientation="vertical")

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8),
                           spacing=dp(8))
        title = Label(text=shape_urdu("اردو نیوز ڈیلی"), color=GOLD,
                      font_name="UrduFont", font_size=dp(24), halign="center")
        header.add_widget(title)
        root.add_widget(header)

        # Controls
        ctrl = BoxLayout(size_hint_y=None, height=dp(48), padding=dp(8),
                         spacing=dp(8))
        self.cat_spin = Spinner(text="All", values=CATEGORIES,
                                background_color=(0.16, 0.16, 0.16, 1),
                                color=GOLD, size_hint_x=0.5)
        self.cat_spin.bind(text=self._cat_changed)
        refresh = Button(text="↻ Refresh", background_color=GOLD_DIM,
                         color=(1, 1, 1, 1), size_hint_x=0.3)
        refresh.bind(on_release=lambda *_: self.refresh())
        saved = Button(text="★", background_color=(0.16, 0.16, 0.16, 1),
                       color=GOLD, size_hint_x=0.2)
        saved.bind(on_release=lambda *_: self.show_bookmarks())
        ctrl.add_widget(self.cat_spin)
        ctrl.add_widget(refresh)
        ctrl.add_widget(saved)
        root.add_widget(ctrl)

        self.status = Label(text="Tap Refresh to load news",
                            color=DIM, size_hint_y=None, height=dp(22),
                            font_size=dp(12))
        root.add_widget(self.status)

        self.scroll = ScrollView()
        self.feed_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                  padding=dp(8), spacing=dp(10))
        self.feed_box.bind(minimum_height=self.feed_box.setter("height"))
        self.scroll.add_widget(self.feed_box)
        root.add_widget(self.scroll)

        return root

    def _cat_changed(self, spinner, value):
        self.current_cat = value

    def refresh(self):
        self.status.text = "Loading…"
        self.feed_box.clear_widgets()
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        cat = self.current_cat
        cats = [c for c in CATEGORIES if c != "All"] if cat == "All" else [cat]
        all_articles = []
        for source, catmap in SOURCES.items():
            for c in cats:
                if c in catmap:
                    arts, _ = fetch_feed(source, c, catmap[c])
                    all_articles.extend(arts)
        # newest first
        all_articles.sort(key=lambda a: a.get("ts", 0), reverse=True)
        # de-dupe by title
        seen, deduped = set(), []
        for a in all_articles:
            k = a["title"][:60]
            if k and k not in seen:
                seen.add(k)
                deduped.append(a)
        self._render(deduped[:60])

    @mainthread
    def _render(self, articles):
        self.feed_box.clear_widgets()
        if not articles:
            self.status.text = "No news found — check connection & retry"
            return
        self.status.text = f"{len(articles)} articles  •  {datetime.now():%I:%M %p}"
        for a in articles:
            self.feed_box.add_widget(ArticleCard(a, self))

    def bookmark(self, article):
        if article not in self.bookmarks:
            self.bookmarks.append(article)
            save_json("bookmarks.json", self.bookmarks)
            self._toast("Saved ★")
        else:
            self._toast("Already saved")

    def show_bookmarks(self):
        self.feed_box.clear_widgets()
        if not self.bookmarks:
            self.status.text = "No saved articles yet"
            return
        self.status.text = f"{len(self.bookmarks)} saved"
        for a in self.bookmarks:
            self.feed_box.add_widget(ArticleCard(a, self))

    def ai_summary(self, article):
        key = self.config_data.get("anthropic_key", "").strip()
        if not key:
            self._ask_key()
            return
        self._toast("Thinking…")
        threading.Thread(target=self._ai_worker, args=(article, key),
                         daemon=True).start()

    def _ai_worker(self, article, key):
        try:
            prompt = (
                "Given this Urdu news item:\n"
                f"HEADLINE: {article['title']}\nSUMMARY: {article['summary']}\n\n"
                "Respond as JSON only: {\"urdu_summary\":\"<one tight Urdu "
                "sentence>\",\"impact\":\"<one English sentence: what this means "
                "for an Islamabad academic + small business owner>\"}"
            )
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001",
                      "max_tokens": 300,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=30)
            data = resp.json()
            txt = data["content"][0]["text"].strip()
            txt = re.sub(r"^```(json)?|```$", "", txt).strip()
            parsed = json.loads(txt)
            self._show_ai_popup(parsed.get("urdu_summary", ""),
                                parsed.get("impact", ""))
        except Exception as e:
            self._toast(f"AI failed: {e}")

    @mainthread
    def _show_ai_popup(self, urdu, impact):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(Label(text=shape_urdu(urdu), color=GOLD,
                             font_name="UrduFont", font_size=dp(18),
                             halign="right", text_size=(dp(280), None)))
        box.add_widget(Label(text=impact, color=TEXT, font_size=dp(14),
                             halign="left", text_size=(dp(280), None)))
        Popup(title="AI Insight", content=box,
              size_hint=(0.9, 0.5)).open()

    def _ask_key(self):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(Label(text="Paste Anthropic API key for AI summaries:",
                             color=TEXT, font_size=dp(13)))
        ti = TextInput(password=True, multiline=False, size_hint_y=None,
                       height=dp(40))
        box.add_widget(ti)
        save = Button(text="Save", size_hint_y=None, height=dp(40),
                      background_color=GOLD_DIM, color=(1, 1, 1, 1))
        box.add_widget(save)
        pop = Popup(title="AI Setup", content=box, size_hint=(0.9, 0.4))

        def _save(*_):
            self.config_data["anthropic_key"] = ti.text.strip()
            save_json("config.json", self.config_data)
            pop.dismiss()
            self._toast("Key saved")
        save.bind(on_release=_save)
        pop.open()

    @mainthread
    def _toast(self, msg):
        self.status.text = msg


def _ensure_urdufont_registered():
    """Guarantee the 'UrduFont' name always resolves, so no Label crashes."""
    try:
        # If already registered, nothing to do.
        if "UrduFont" in LabelBase._fonts:
            return
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    for fpath in (os.path.join(here, "NotoNastaliqUrdu-Regular.ttf"),
                  "NotoNastaliqUrdu-Regular.ttf"):
        try:
            if os.path.exists(fpath):
                LabelBase.register(name="UrduFont", fn_regular=fpath)
                return
        except Exception:
            continue
    # Could not find the TTF — alias UrduFont to Kivy's default so labels
    # using font_name="UrduFont" still render (just not in Nastaliq).
    try:
        LabelBase.register(name="UrduFont",
                           fn_regular=LabelBase._fonts['Roboto']['regular'])
    except Exception:
        pass


# Run the guarantee at import time, before any widget is built.
_ensure_urdufont_registered()


# Register bundled Urdu font (file shipped alongside main.py)
def _register_font():
    # On Android the cwd is NOT the app dir; resolve paths relative to THIS file.
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "NotoNastaliqUrdu-Regular.ttf"),
        os.path.join(here, "urdu.ttf"),
        "NotoNastaliqUrdu-Regular.ttf",
        "urdu.ttf",
    ]
    for fpath in candidates:
        try:
            if os.path.exists(fpath):
                LabelBase.register(name="UrduFont", fn_regular=fpath)
                return
        except Exception:
            continue
    # Last resort: register the default font FILE if we can find it, else
    # just alias UrduFont to the built-in 'Roboto' name WITHOUT a file path.
    try:
        from kivy.core.text import DEFAULT_FONT
        LabelBase.register(name="UrduFont",
                           fn_regular=LabelBase._fonts.get(DEFAULT_FONT, {}).get(
                               'regular', None) or "Roboto")
    except Exception:
        # If even that fails, don't crash — Kivy will use its default for
        # any label whose font_name can't be resolved.
        pass


def _write_crash(exc_text):
    """Write a crash reason to a readable file so we can diagnose."""
    try:
        d = os.path.join(os.path.expanduser("~"), "UrduNewsDaily")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "last_crash.txt"), "w", encoding="utf-8") as f:
            f.write(exc_text)
    except Exception:
        pass


if __name__ == "__main__":
    import traceback
    try:
        _register_font()
    except Exception:
        _write_crash("FONT REGISTRATION FAILED:\n" + traceback.format_exc())
        # Carry on — a missing custom font must never block launch.
    try:
        UrduNewsApp().run()
    except Exception:
        _write_crash("APP RUN FAILED:\n" + traceback.format_exc())
        raise

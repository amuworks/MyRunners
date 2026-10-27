# 馬ごとの公開ページを1日1回確認し、変化があればntfyに通知する
import json, os, re, time, urllib.request
from bs4 import BeautifulSoup

BASE = "https://db.netkeiba.com/horse/{}/"
UA = "Mozilla/5.0 (personal hobby watcher; low frequency)"

def fetch(hid):
    req = urllib.request.Request(BASE.format(hid), headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=30).read()
    for enc in ("euc-jp", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "ignore")

def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()

def facts(html):
    s = BeautifulSoup(html, "html.parser")
    f = {}
    title = s.select_one(".horse_title")
    f["title"] = clean(title.get_text(" ")) if title else clean(s.title.get_text() if s.title else "")
    for tr in s.select("table.db_prof_table tr"):
        th, td = tr.find("th"), tr.find("td")
        if th and td:
            f["prof:" + clean(th.get_text())] = clean(td.get_text(" "))
    row = s.select_one("table.db_h_race_results tbody tr")
    f["latest_race"] = clean(row.get_text(" ")) if row else ""
    return f

def notify(msg):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC未設定:", msg)
        return
    req = urllib.request.Request("https://ntfy.sh/" + topic, data=msg.encode("utf-8"),
                                 headers={"Title": "Horse Watch".encode("utf-8")})
    urllib.request.urlopen(req, timeout=30)

def main():
    horses = json.load(open("horses.json", encoding="utf-8"))
    try:
        old = json.load(open("status.json", encoding="utf-8"))
    except Exception:
        old = {}
    new = {}
    for h in horses:
        hid = h["id"]
        try:
            f = facts(fetch(hid))
        except Exception as e:
            print("取得失敗", h["name"], e)
            new[hid] = old.get(hid, {})
            continue
        print("---", h["name"])
        for k, v in f.items():
            print(k, "=", v[:120])
        new[hid] = f
        if hid in old and old[hid] != f:
            diffs = [k for k in set(f) | set(old[hid]) if f.get(k) != old[hid].get(k)]
            notify(h["name"] + " に変更: " + ", ".join(diffs))
        time.sleep(5)
    json.dump(new, open("status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

main()

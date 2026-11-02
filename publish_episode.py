#!/usr/bin/env python3
"""Publish an episode to the 认知提升课 podcast.
Usage: publish_episode.py SCRIPT.txt "TITLE" [-d DESC] [--audio EXISTING.mp3] [--no-push]
       publish_episode.py --rebuild   (regenerate feed.xml from episodes.json)"""
import argparse, json, os, shutil, subprocess, tempfile, email.utils, time
from xml.sax.saxutils import escape
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://masanshi11-bot.github.io/learning-podcast/"
MAN = os.path.join(ROOT, "episodes.json")
TTS = os.path.expanduser("~/.local/bin/edge-tts")

def load(): return json.load(open(MAN)) if os.path.exists(MAN) else []
def dur(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())
def hms(s): s=int(round(s)); return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

def feed(eps):
    items=[]
    for e in reversed(eps):
        items.append(f"""  <item>
    <title>{escape(e['title'])}</title>
    <description>{escape(e['description'])}</description>
    <itunes:summary>{escape(e['description'])}</itunes:summary>
    <enclosure url="{BASE}{e['file']}" length="{e['bytes']}" type="audio/mpeg"/>
    <guid isPermaLink="false">learning-podcast-ep{e['num']:03d}</guid>
    <pubDate>{e['pubDate']}</pubDate>
    <itunes:duration>{hms(e['duration'])}</itunes:duration>
    <itunes:episode>{e['num']}</itunes:episode>
    <itunes:explicit>false</itunes:explicit>
  </item>""")
    x=f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>认知提升课</title>
  <link>{BASE}</link>
  <atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/>
  <description>每节约10分钟：投资金融、区块链、科技、人生规划、健康饮食、身体锻炼、英语学习，长期复利提升认知。</description>
  <language>zh-cn</language>
  <itunes:author>Sanshi</itunes:author>
  <itunes:owner><itunes:name>Sanshi</itunes:name></itunes:owner>
  <itunes:image href="{BASE}cover.jpg"/>
  <image><url>{BASE}cover.jpg</url><title>认知提升课</title><link>{BASE}</link></image>
  <itunes:category text="Education"/>
  <itunes:explicit>false</itunes:explicit>
  <itunes:type>serial</itunes:type>
  <itunes:block>yes</itunes:block>
  <lastBuildDate>{email.utils.formatdate(usegmt=True)}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
"""
    open(os.path.join(ROOT,"feed.xml"),"w").write(x)

def git(msg, push):
    subprocess.check_call(["git","-C",ROOT,"add","-A"])
    subprocess.call(["git","-C",ROOT,"commit","-qm",msg])
    if push: subprocess.check_call(["git","-C",ROOT,"push","-q","origin","main"])

def main():
    a=argparse.ArgumentParser(); a.add_argument("script",nargs="?"); a.add_argument("title",nargs="?")
    a.add_argument("-d","--description"); a.add_argument("--audio"); a.add_argument("--no-push",action="store_true")
    a.add_argument("--rebuild",action="store_true"); o=a.parse_args()
    eps=load()
    if o.rebuild: feed(eps); git("Rebuild feed", not o.no_push); return
    n=max([e["num"] for e in eps],default=0)+1
    rel=f"episodes/ep{n:03d}.mp3"; out=os.path.join(ROOT,rel)
    os.makedirs(os.path.dirname(out),exist_ok=True)
    text=open(o.script,encoding="utf-8").read().strip()
    shutil.copy(o.script, out[:-4]+".txt") if os.path.abspath(o.script)!=os.path.abspath(out[:-4]+".txt") else None
    src=o.audio
    if not src:
        src=tempfile.mktemp(suffix=".mp3")
        subprocess.check_call([TTS,"--voice","zh-CN-XiaoxiaoNeural","--rate=-8%","-f",out[:-4]+".txt","--write-media",src])
    subprocess.check_call(["ffmpeg","-y","-loglevel","error","-i",src,"-ac","1","-b:a","64k","-ar","24000",
        "-metadata",f"title={o.title}","-metadata","artist=认知提升课",out])
    desc=o.description or text[:150].replace("\n"," ")+"…"
    eps.append(dict(num=n,title=o.title,description=desc,file=rel,bytes=os.path.getsize(out),
        duration=dur(out),pubDate=email.utils.formatdate(time.time()+n,usegmt=True)))
    json.dump(eps,open(MAN,"w"),ensure_ascii=False,indent=2)
    feed(eps); git(f"Add episode {n}: {o.title}", not o.no_push)
    print(f"Published ep{n:03d} {o.title} {hms(eps[-1]['duration'])}")
main()

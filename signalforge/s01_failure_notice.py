"""Bangkok-only, independently receipted S01 AI usage-limit notices."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess

ROOT=Path("/srv/signalforge/state/s01-failure-notices")

def send(day: str, completed: int, total: int, *, root: Path=ROOT, transport=None) -> dict:
    day=date.fromisoformat(day).isoformat()
    if not 0 <= completed <= total <= 10000 or total < 1:
        raise ValueError("Invalid S01 progress counts")
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=root/(day+"-AI_USAGE_LIMIT.json")
    with path.with_suffix(".lock").open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=json.loads(path.read_text()) if path.is_file() else {}
        if state.get("status")=="SUCCESS":
            return {**state,"status":"ALREADY_SENT"}
        if state.get("status") in ("PENDING","UNKNOWN"):
            raise RuntimeError("S01 notice outcome unresolved; reconcile before retry")
        def save():
            temp=path.with_suffix(".tmp")
            temp.write_text(json.dumps(state,ensure_ascii=False)+"\n")
            temp.replace(path)
        text=(f"⚠️ S01 新闻日报处理未完成｜{day}\n"
              "原因：AI 推理额度受限。\n"
              f"已完成并校验的中文处理：{completed}/{total} 条。\n"
              "本次 PDF 和 Digest 尚未投递。处理进度已保留，额度恢复后继续。\n"
              "这是失败状态通知，不代表日报已送达；同一日同类事件仅通知一次。")
        if transport is None:
            from tools import newspaper_telegram_transport as transport
        token,chat=transport._credentials()
        state={"date":day,"failure_class":"AI_USAGE_LIMIT","status":"PENDING",
               "completed_articles":completed,"total_articles":total}
        save()
        try:
            message_id=transport._send_text(token,chat,text)
        except Exception as exc:
            import re
            state["status"]="FAILED" if re.search(r"Telegram HTTP 4\d\d",str(exc)) else "UNKNOWN"
            save()
            raise
        state.update(status="SUCCESS",message_id=message_id,
                     sent_at=datetime.now(timezone.utc).isoformat())
        save()
        return state

def notify_from_mac(day: str, completed: int, total: int) -> dict:
    day=date.fromisoformat(day).isoformat()
    result=subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","vps-bangkok",
        "env","PYTHONPATH=/srv/signalforge/active","/srv/signalforge/active/.venv/bin/python",
        "-m","signalforge.s01_failure_notice","--date",day,
        "--completed",str(completed),"--total",str(total)],
        capture_output=True,text=True,timeout=45,check=True)
    return json.loads(result.stdout)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--date",required=True)
    p.add_argument("--completed",type=int,required=True)
    p.add_argument("--total",type=int,required=True)
    args=p.parse_args()
    print(json.dumps(send(args.date,args.completed,args.total),ensure_ascii=False))

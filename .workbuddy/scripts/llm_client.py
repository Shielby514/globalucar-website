# -*- coding: utf-8 -*-
"""
llm_client.py —— MiniMax LLM 调用封装（Anthropic Messages 协议）

用途
  博客流水线（24/25/27）在服务器上直接调用 LLM 生成文章正文，
  不需要人工介入，也不依赖任何外部 SaaS。

鉴权
  凭据只从文件读，**永远不进命令行、不进日志、不进 git**：
    1) 优先读 G:\\ucars\\.workbuddy\\secrets\\llm-credential.txt（可放独立 API Key，UTF-8 无 BOM）
    2) 回落到 C:\\Users\\admin\\.minimax\\local-runtime.auth.json 的 auth.accessToken
  鉴权头是 Authorization: Bearer <token>（不是 x-api-key）。

用法
  from llm_client import LLMClient
  cli = LLMClient(model="MiniMax-M3")
  text = cli.chat("写一篇关于 X 的文章", system="你是 B2B 汽配行业编辑")

CLI（自检用）
  python llm_client.py --check
"""
from __future__ import annotations

import json
import os
import random
import sys
import time

try:
    import requests
except ImportError:
    sys.stderr.write("requests is required (python -m pip install requests)\n")
    raise

BASE_URL = "https://agent.minimax.cn/mavis/api/v1/llm/v1"
MODEL_DEFAULT = "MiniMax-M3"
MODELS = ("MiniMax-M3", "MiniMax-M3.1-Flash", "MiniMax-M2.7-highspeed")

SECRET_FILE = r"G:\ucars\.workbuddy\secrets\llm-credential.txt"
RUNTIME_AUTH = r"C:\Users\admin\.minimax\local-runtime.auth.json"

TIMEOUT = (30, 300)          # (connect, read) seconds
MAX_RETRY = 4
RETRY_BASE_SLEEP = 4.0


class LLMError(RuntimeError):
    """LLM 调用失败（鉴权 / 网络 / 协议层）。"""


class LLMClient:
    def __init__(self, model=MODEL_DEFAULT, proxy=None, timeout=TIMEOUT, verbose=False):
        self.model = model if model in MODELS else MODEL_DEFAULT
        self.timeout = timeout
        self.verbose = verbose
        self._token = None
        self._proxy = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
        self._session = requests.Session()
        if self._proxy:
            self._session.proxies = {"http": self._proxy, "https": self._proxy}
        self.usage_total = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

    # ── 凭据 ────────────────────────────────────────────
    def _load_token(self):
        if self._token:
            return self._token
        # 1) 独立凭据文件
        if os.path.exists(SECRET_FILE):
            try:
                raw = open(SECRET_FILE, encoding="utf-8-sig").read().strip()
                if raw:
                    self._token = raw
                    return self._token
            except Exception:
                pass
        # 2) 运行时授权文件
        if os.path.exists(RUNTIME_AUTH):
            try:
                d = json.load(open(RUNTIME_AUTH, encoding="utf-8"))
                tok = (d.get("auth") or {}).get("accessToken") or ""
                if tok:
                    self._token = tok
                    return self._token
            except Exception:
                pass
        raise LLMError(
            "no credential found: expected %s or %s" % (SECRET_FILE, RUNTIME_AUTH))

    # ── 调用 ────────────────────────────────────────────
    def _post(self, body):
        token = self._load_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
            "anthropic-version": "2023-06-01",
        }
        url = BASE_URL.rstrip("/") + "/messages"
        last = None
        direct = False
        for attempt in range(1, MAX_RETRY + 1):
            try:
                sess = self._session
                if direct:
                    sess = requests.Session()          # 代理不通时直连兜底
                r = sess.post(url, headers=headers, json=body, timeout=self.timeout)
            except Exception as e:
                last = "network: %s" % type(e).__name__
                if not direct and self._proxy:
                    direct = True                      # 代理不可用 → 下一轮直连
                    continue
            else:
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except Exception as e:
                        raise LLMError("bad json from LLM: %s" % type(e).__name__)
                    u = data.get("usage") or {}
                    self.usage_total["input_tokens"] += u.get("input_tokens") or 0
                    self.usage_total["output_tokens"] += u.get("output_tokens") or 0
                    self.usage_total["calls"] += 1
                    out = []
                    for blk in data.get("content") or []:
                        if blk.get("type") == "text":
                            out.append(blk.get("text") or "")
                    return "\n".join(out)
                # 401/403 不重试：凭据问题，重试无意义
                if r.status_code in (401, 403):
                    raise LLMError("LLM auth failed (HTTP %s) - credential invalid or expired" % r.status_code)
                last = "HTTP %s: %s" % (r.status_code, (r.text or "")[:200])
                if r.status_code not in (408, 409, 429, 500, 502, 503, 504):
                    break
            if attempt < MAX_RETRY:
                sleep = RETRY_BASE_SLEEP * (2 ** (attempt - 1)) + random.uniform(0, 2)
                if self.verbose:
                    print("  llm retry %d/%d in %.1fs (%s)" % (attempt, MAX_RETRY, sleep, last))
                time.sleep(sleep)
        raise LLMError("LLM call failed after %d attempts: %s" % (MAX_RETRY, last))

    def chat(self, prompt, system=None, max_tokens=8000, temperature=0.5, retries=0):
        """单轮对话。retries>0 时对失败再重试若干轮（跨轮次重试用于长文生成的瞬时错误）。"""
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        last_exc = None
        for i in range(retries + 1):
            try:
                return self._post(body)
            except LLMError as e:
                last_exc = e
                if "auth failed" in str(e):
                    break
                if i < retries:
                    time.sleep(RETRY_BASE_SLEEP * (i + 1))
        raise last_exc

    def chat_json(self, prompt, system=None, max_tokens=8000, temperature=0.3, retries=1):
        """要求模型输出 JSON。自动剥掉 markdown 代码围栏并做容错解析。"""
        raw = self.chat(prompt, system=system, max_tokens=max_tokens,
                        temperature=temperature, retries=retries)
        return parse_json_loose(raw)


def parse_json_loose(raw):
    """从模型输出里稳健地抠出 JSON。"""
    if not raw:
        raise LLMError("empty LLM response")
    s = raw.strip()
    # 去掉 ```json 围栏
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.strip("`").strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    # 抠出最外层 {...} 或 [...]
    for op, cl in (("{", "}"), ("[", "]")):
        i = s.find(op)
        j = s.rfind(cl)
        if i >= 0 and j > i:
            try:
                return json.loads(s[i:j + 1])
            except Exception:
                continue
    raise LLMError("cannot parse JSON from LLM output (head=%r)" % s[:120])


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="LLM client self-check")
    ap.add_argument("--check", action="store_true", help="send a tiny ping and report status")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    args = ap.parse_args()
    if not args.check:
        ap.print_help()
        return 0
    cli = LLMClient(model=args.model, verbose=True)
    try:
        out = cli.chat("Reply with exactly: PING-OK", max_tokens=32, temperature=0)
    except LLMError as e:
        print("LLM CHECK FAILED: %s" % e)
        return 2
    print("LLM CHECK OK  model=%s  reply=%r  usage=%s" % (cli.model, out[:60], cli.usage_total))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())

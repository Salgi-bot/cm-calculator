# ============================================================
#  Copyright (c) 2025 (주)아이팝엔지니어링
#  All rights reserved.
#  본 소프트웨어는 (주)아이팝엔지니어링의 지적 재산입니다.
#  무단 복제, 배포, 수정을 금지합니다.
#  Unauthorized copying, distribution, or modification
#  of this software is strictly prohibited.
# ============================================================

import streamlit as st
import math
import os
import json
import random
import string
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

st.set_page_config(
    page_title="건설사업관리 인월수 산출 Ver 1.1",
    page_icon="🏗️",
    layout="wide"
)

# ── 저작권 / 도메인 잠금 ──────────────────────────────────────
_ALLOWED_DOMAIN = "salgi-bot.github.io"
try:
    import streamlit.components.v1 as _stc
    _stc.html(f"""
    <script>
    (function(){{
        var host = window.location.hostname;
        if (host !== "" && host !== "localhost" && host !== "127.0.0.1"
            && !host.endsWith("{_ALLOWED_DOMAIN}")
            && !host.endsWith("streamlit.app")
            && !host.endsWith("streamlit.io")) {{
            document.body.innerHTML = "<div style='display:flex;align-items:center;justify-content:center;"
                + "height:100vh;font-family:sans-serif;background:#0f172a;color:#fff;'>"
                + "<div style='text-align:center;'>"
                + "<div style='font-size:48px;'>🔒</div>"
                + "<h2>접근이 제한된 페이지입니다</h2>"
                + "<p style='color:#94a3b8;'>Copyright &copy; 2025 (주)아이팝엔지니어링<br>무단 복제 및 재배포를 금합니다.</p>"
                + "</div></div>";
        }}
    }})();
    </script>
    """, height=0)
except Exception:
    pass

# ── Footer 워터마크 ────────────────────────────────────────────
try:
    import streamlit.components.v1 as _stc2
    _stc2.html("""
    <style>
    #cm-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: rgba(255,255,255,0.95);
        border-top: 1px solid #e2e8f0;
        text-align: center; padding: 5px 0;
        font-size: 11px; color: #94a3b8;
        z-index: 9999; pointer-events: none;
    }
    </style>
    <script>
    (function(){
        function injectFooter(){
            if(document.getElementById('cm-footer')) return;
            var el = document.createElement('div');
            el.id = 'cm-footer';
            el.innerHTML = 'Copyright &copy; ' + new Date().getFullYear()
                + ' (주)아이팝엔지니어링 &nbsp;|&nbsp; 건설사업관리 인월수 산출 Ver 1.1 &nbsp;|&nbsp; All Rights Reserved.';
            document.body.appendChild(el);
        }
        if(document.readyState === 'loading'){
            document.addEventListener('DOMContentLoaded', injectFooter);
        } else { injectFooter(); }
        new MutationObserver(injectFooter).observe(document.body, {childList:true, subtree:false});
    })();
    </script>
    """, height=0)
except Exception:
    pass

# ═══════════════════════════════════════════
# GitHub 파일 CRUD
# ═══════════════════════════════════════════
def _gh_read(filename):
    try:
        gh_token = st.secrets.get("GITHUB_TOKEN", "")
        gh_repo  = st.secrets.get("GITHUB_REPO", "")
        url = f"https://api.github.com/repos/{gh_repo}/contents/{filename}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {gh_token}",
            "Accept": "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return base64.b64decode(d["content"]).decode("utf-8"), d.get("sha", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "", ""
        return "", ""
    except Exception:
        return "", ""

def _gh_write(filename, content, sha="", msg="update"):
    try:
        gh_token = st.secrets.get("GITHUB_TOKEN", "")
        gh_repo  = st.secrets.get("GITHUB_REPO", "")
        url = f"https://api.github.com/repos/{gh_repo}/contents/{filename}"
        payload = {"message": msg, "content": base64.b64encode(content.encode()).decode()}
        if sha:
            payload["sha"] = sha
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="PUT",
            headers={"Authorization": f"token {gh_token}",
                     "Content-Type": "application/json",
                     "Accept": "application/vnd.github.v3+json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

# ═══════════════════════════════════════════
# 텔레그램
# ═══════════════════════════════════════════
def _tg_send(token, chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": str(chat_id), "text": text, "parse_mode": "HTML"
        }).encode()
        urllib.request.urlopen(url, data=data, timeout=10)
        return True
    except Exception:
        return False

def _tg_get_updates(token):
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100&offset=-100"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        users = {}
        for upd in data.get("result", []):
            msg = upd.get("message", {})
            if msg:
                u = msg.get("from", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if chat_id:
                    users[chat_id] = {
                        "chat_id": chat_id,
                        "first_name": u.get("first_name", ""),
                        "last_name":  u.get("last_name", ""),
                        "username":   u.get("username", ""),
                        "text":       msg.get("text", "")
                    }
        return list(users.values())
    except Exception:
        return []

def _gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ═══════════════════════════════════════════
# 코드 관리
# ═══════════════════════════════════════════
def _get_codes_dict():
    content, sha = _gh_read("cm_access_codes.txt")
    codes = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":", 1)
        codes[parts[0].upper()] = parts[1] if len(parts) > 1 else ""
    return codes, sha

def _add_code(code, name=""):
    codes, sha = _get_codes_dict()
    codes[code.upper()] = name
    content = "\n".join(f"{k}:{v}" for k, v in codes.items()) + "\n"
    return _gh_write("cm_access_codes.txt", content, sha, f"코드추가:{code}")

def _use_code(code):
    codes, sha = _get_codes_dict()
    if code.upper() in codes:
        del codes[code.upper()]
        content = "\n".join(f"{k}:{v}" for k, v in codes.items()) + "\n"
        _gh_write("cm_access_codes.txt", content, sha, f"코드사용:{code}")

# ═══════════════════════════════════════════
# 기기 토큰 관리 (30일 유효기간)
# ═══════════════════════════════════════════
def _get_device_tokens():
    content, sha = _gh_read("cm_device_tokens.txt")
    tokens = {}
    today = datetime.now().date()
    valid_lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            tok, expiry_str = parts[0], parts[1]
            name = parts[2] if len(parts) > 2 else ""
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if expiry >= today:
                    tokens[tok] = {"expiry": expiry_str, "name": name}
                    valid_lines.append(line)
            except Exception:
                pass
    return tokens, sha, "\n".join(valid_lines) + "\n" if valid_lines else ""

def _add_device_token(token, name="", days=30):
    tokens, sha, clean_content = _get_device_tokens()
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    new_line = f"{token}|{expiry}|{name}"
    new_content = clean_content + new_line + "\n"
    _gh_write("cm_device_tokens.txt", new_content, sha, "기기토큰추가")

def _check_device_token(token):
    if not token:
        return False
    tokens, _, _ = _get_device_tokens()
    return token in tokens

# ═══════════════════════════════════════════
# 사용 로그 / 통계
# ═══════════════════════════════════════════
def _log_usage(name=""):
    try:
        content, sha = _gh_read("cm_usage_log.txt")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_content = (content or "") + f"{now}|{name}\n"
        _gh_write("cm_usage_log.txt", new_content, sha, f"로그:{datetime.now().strftime('%Y-%m-%d')}")
    except Exception:
        pass

def _parse_log():
    content, _ = _gh_read("cm_usage_log.txt")
    if not content:
        return []
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if parts:
            entries.append({
                "datetime": parts[0].strip(),
                "date":     parts[0].strip()[:10],
                "name":     parts[1].strip() if len(parts) > 1 else ""
            })
    return entries

# ═══════════════════════════════════════════
# 신청 목록 관리
# ═══════════════════════════════════════════
def _get_requests():
    content, sha = _gh_read("cm_requests.json")
    if not content:
        return [], sha
    try:
        return json.loads(content), sha
    except Exception:
        return [], sha

def _save_request(name, contact):
    reqs, sha = _get_requests()
    req_id = _gen_code()
    reqs.append({
        "id": req_id, "name": name, "contact": contact,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending"
    })
    _gh_write("cm_requests.json", json.dumps(reqs, ensure_ascii=False, indent=2), sha, f"신청:{name}")
    return req_id

def _approve_request(req_id, code):
    reqs, sha = _get_requests()
    for r in reqs:
        if r["id"] == req_id:
            r["status"] = "approved"
            r["code"] = code
    _gh_write("cm_requests.json", json.dumps(reqs, ensure_ascii=False, indent=2), sha, f"승인:{req_id}")

# ═══════════════════════════════════════════
# Secrets 로드
# ═══════════════════════════════════════════
try:
    TG_TOKEN   = st.secrets["TG_TOKEN"]
    TG_CHAT_ID = st.secrets["TG_CHAT_ID"]
    ADMIN_PW   = st.secrets.get("ADMIN_PW", "")
except Exception:
    TG_TOKEN = TG_CHAT_ID = ADMIN_PW = ""

_MAX_ATTEMPTS = 5

# session_state 초기화
for _k, _v in [
    ("auth_ok", False), ("auth_attempts", 0), ("req_sent", False),
    ("device_token", ""), ("is_admin", False),
    ("reentry_code", ""), ("show_login", False)
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# 기기 토큰 query param 자동 확인
_dt_param = st.query_params.get("dt", "")
if _dt_param and not st.session_state.auth_ok:
    if _check_device_token(_dt_param):
        st.session_state.auth_ok = True
        st.session_state.device_token = _dt_param

# localStorage 토큰 자동 주입
try:
    import streamlit.components.v1 as _stcjs
    _stcjs.html("""
    <script>
    (function(){
        try {
            var dt = localStorage.getItem('cm_dt');
            if(dt && window.top.location.href.indexOf('dt=') === -1){
                var url = window.top.location.href.split('?')[0] + '?dt=' + dt;
                window.top.location.replace(url);
            }
        } catch(e) {}
    })();
    </script>
    """, height=0)
except Exception:
    pass

def _inject_save_token(token):
    try:
        import streamlit.components.v1 as _stc_dt
        _stc_dt.html(f"""
        <script>
        (function(){{
            try {{ localStorage.setItem('cm_dt', '{token}'); }} catch(e) {{}}
            try {{
                var url = window.top.location.href.split('?')[0] + '?dt={token}';
                window.top.history.replaceState(null, '', url);
            }} catch(e) {{}}
        }})();
        </script>
        """, height=0)
    except Exception:
        pass

# ════════════════════════════════════════════════════════════
# 인증 화면
# ════════════════════════════════════════════════════════════
if not st.session_state.auth_ok:

    st.markdown("""
    <div style='max-width:480px;margin:60px auto 0;padding:40px 36px 32px;border-radius:16px;
                box-shadow:0 8px 32px rgba(29,78,216,0.12);background:white;text-align:center;
                border:1px solid #dbeafe;'>
        <div style='font-size:48px;margin-bottom:8px;'>🏗️</div>
        <h2 style='color:#1d4ed8;margin:0 0 6px;font-size:22px;'>건설사업관리 인월수 산출</h2>
        <p style='color:#64748b;font-size:13px;margin:0 0 4px;'>Ver 1.1 &nbsp;|&nbsp; (주)아이팝엔지니어링</p>
        <p style='color:#94a3b8;font-size:12px;margin:0;'>승인된 사용자만 이용 가능합니다</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='max-width:480px;margin:20px auto 0;'>", unsafe_allow_html=True)

    # 관리자 바로 입장
    with st.expander("🔑 관리자 입장", expanded=False):
        admin_quick_pw = st.text_input("관리자 비밀번호", type="password", key="admin_quick_pw")
        if st.button("🚀 관리자로 입장", use_container_width=True):
            if admin_quick_pw == ADMIN_PW and ADMIN_PW:
                st.session_state.auth_ok = True
                st.session_state.is_admin = True
                _log_usage("관리자")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

    if st.session_state.show_login:
        tab_login, tab_request = st.tabs(["🔑 코드 입력", "📋 사용 신청"])
    else:
        tab_request, tab_login = st.tabs(["📋 사용 신청", "🔑 코드 입력"])

    # 탭1: 코드 입력
    with tab_login:
        if st.session_state.req_sent and not st.session_state.reentry_code:
            st.success("✅ 신청 완료! 관리자 승인 후 텔레그램으로 코드를 전달드립니다.")
            st.info("👇 코드를 받으시면 아래에 입력해주세요.")

        if st.session_state.reentry_code:
            st.success("✅ 승인 완료!")
            st.info(
                f"📌 **재입장 코드 (반드시 저장하세요!)**\n\n"
                f"🔐 `{st.session_state.reentry_code}`\n\n"
                f"다음 방문 시 이 코드로 바로 입장 가능합니다. (유효기간: **30일**)"
            )
            if st.button("✅ 앱 시작하기", use_container_width=True, type="primary"):
                _log_usage(st.session_state.device_token)
                _inject_save_token(st.session_state.device_token)
                st.session_state.auth_ok = True
                st.session_state.reentry_code = ""
                st.rerun()
            st.stop()

        remaining = _MAX_ATTEMPTS - st.session_state.auth_attempts
        if remaining <= 0:
            st.error("⛔ 입력 횟수 초과로 접근이 차단되었습니다. 관리자에게 문의하세요.")
            st.stop()

        code_input = st.text_input(
            "코드 입력", type="password",
            placeholder="승인 코드(8자리) 또는 재입장 코드",
            help=f"남은 시도: {remaining}회"
        )
        if st.button("✅ 입장", use_container_width=True, type="primary"):
            entered = code_input.strip().upper()
            dt_tokens, dt_sha, dt_clean = _get_device_tokens()
            if entered in dt_tokens:
                st.session_state.auth_ok = True
                st.session_state.device_token = entered
                _log_usage(dt_tokens.get(entered, {}).get("name", ""))
                _inject_save_token(entered)
                st.rerun()
            else:
                codes_dict, _ = _get_codes_dict()
                if entered in codes_dict:
                    user_name = codes_dict[entered]
                    _use_code(entered)
                    reentry = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
                    _add_device_token(reentry, user_name, days=30)
                    st.session_state.device_token = reentry
                    st.session_state.reentry_code = reentry
                    st.rerun()
                else:
                    st.session_state.auth_attempts += 1
                    left = _MAX_ATTEMPTS - st.session_state.auth_attempts
                    if left <= 0:
                        st.error("⛔ 입력 횟수 초과로 접근이 차단되었습니다.")
                    else:
                        st.error(f"❌ 코드가 올바르지 않습니다. (남은 시도: {left}회)")

    # 탭2: 사용 신청
    with tab_request:
        st.markdown("##### 사용 신청")
        st.caption("신청 후 관리자 승인 시 텔레그램으로 코드를 전달드립니다.")
        req_name    = st.text_input("이름 *", placeholder="홍길동")
        req_contact = st.text_input("연락처 *", placeholder="010-0000-0000")
        if st.button("📨 사용 신청하기", use_container_width=True, type="primary"):
            if not req_name or not req_contact:
                st.error("이름과 연락처는 필수입니다.")
            else:
                _save_request(req_name, req_contact)
                _tg_send(TG_TOKEN, TG_CHAT_ID,
                    f"📋 <b>건설사업관리 인월수 산출 — 사용 신청</b>\n\n"
                    f"👤 이름: {req_name}\n📞 연락처: {req_contact}\n\n"
                    f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app\n"
                    f"✅ 관리자 패널에서 승인 후 코드를 전달해주세요.")
                st.session_state.show_login = True
                st.session_state.req_sent = True
                st.rerun()

    # 관리자 패널 (인증화면 내)
    with st.expander("🔧 관리자 패널", expanded=False):
        admin_pw_input = st.text_input("관리자 비밀번호", type="password", key="admin_pw")
        if admin_pw_input == ADMIN_PW and ADMIN_PW:
            st.success("✅ 관리자 모드")

            # 대기 신청 목록
            st.markdown("---")
            st.markdown("**📥 대기 신청 목록**")
            if st.button("🔄 새로고침", key="refresh_reqs"):
                st.rerun()
            reqs_list, _ = _get_requests()
            pending = [r for r in reqs_list if r.get("status") == "pending"]
            if not pending:
                st.info("대기 중인 신청이 없습니다.")
            else:
                for r in pending:
                    c1, c2 = st.columns([4, 2])
                    c1.markdown(f"👤 **{r['name']}** | 📞 {r['contact']} | 🕐 {r.get('time','')}")
                    if c2.button("✅ 승인 & 발송", key=f"req_{r['id']}"):
                        new_code = _gen_code()
                        _add_code(new_code, r['name'])
                        _approve_request(r['id'], new_code)
                        _tg_send(TG_TOKEN, TG_CHAT_ID,
                            f"✅ <b>승인 완료</b>\n👤 {r['name']}\n🔐 <code>{new_code}</code>\n"
                            f"📞 {r['contact']}\n"
                            f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app\n"
                            f"⚠️ 수동으로 코드를 전달해주세요.")
                        st.success(f"코드 발급: **{new_code}** — 텔레그램으로 수동 전달 필요")
                        st.rerun()

            # 텔레그램 봇 직접 승인
            st.markdown("---")
            st.markdown("**📲 텔레그램 봇 신청자 (직접 승인)**")
            tg_users = _tg_get_updates(TG_TOKEN)
            if tg_users:
                for u in tg_users[-10:]:
                    display_name = f"{u['first_name']} {u['last_name']}".strip() or u['username'] or u['chat_id']
                    col_u, col_b = st.columns([3, 2])
                    col_u.write(f"👤 {display_name} (ID: {u['chat_id']})")
                    if col_b.button("✅ 승인", key=f"approve_{u['chat_id']}"):
                        new_code = _gen_code()
                        _add_code(new_code, display_name)
                        ok = _tg_send(TG_TOKEN, u['chat_id'],
                            f"🔑 <b>건설사업관리 인월수 산출 — 승인 코드</b>\n\n"
                            f"👤 {display_name}님\n🔐 코드: <code>{new_code}</code>\n\n"
                            f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app\n"
                            f"⚠️ 1회 사용 후 <b>30일간</b> 재인증 없이 사용 가능합니다.")
                        _tg_send(TG_TOKEN, TG_CHAT_ID,
                            f"✅ <b>승인</b>\n👤 {display_name}\n🔐 {new_code}\n"
                            f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app\n"
                            f"{'📤 발송 성공' if ok else '⚠️ 발송 실패'}")
                        if ok:
                            st.success(f"✅ {display_name} 텔레그램 발송 완료!")
                        else:
                            st.warning(f"⚠️ 발송 실패. 코드: **{new_code}**")
            else:
                st.info("텔레그램 봇에 메시지를 보낸 사용자가 없습니다.")

            # 수동 코드 발급
            st.markdown("---")
            st.markdown("**✍️ 수동 코드 발급**")
            manual_name = st.text_input("수신자 이름", key="manual_name")
            manual_chat = st.text_input("텔레그램 Chat ID (선택)", key="manual_chat")
            if st.button("🎲 코드 생성 & 발송", key="gen_manual"):
                new_code = _gen_code()
                _add_code(new_code, manual_name)
                msg = (f"🔑 <b>건설사업관리 인월수 산출 승인 코드</b>\n\n"
                       f"👤 {manual_name}님\n🔐 코드: <code>{new_code}</code>\n\n"
                       f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app\n"
                       f"⚠️ 1회 사용 후 30일간 재인증 없이 사용 가능합니다.")
                _tg_send(TG_TOKEN, TG_CHAT_ID,
                    f"🔑 수동 발급\n👤 {manual_name}\n🔐 <code>{new_code}</code>\n"
                    f"🔗 https://cm-calculator-ngd5xmshzk5vmypksklpnt.streamlit.app")
                if manual_chat:
                    ok = _tg_send(TG_TOKEN, manual_chat, msg)
                    if ok:
                        st.success(f"✅ 코드: **{new_code}** — {manual_name}님 텔레그램 발송 완료!")
                    else:
                        st.warning(f"⚠️ 발송 실패. 코드: **{new_code}** — 수동 전달 필요")
                else:
                    st.success(f"코드: **{new_code}** — 관리자 텔레그램으로 전달됐습니다.")

            # 사용 통계
            st.markdown("---")
            st.markdown("**📊 사용 통계**")
            if st.button("🔄 통계 새로고침", key="refresh_stats"):
                st.rerun()
            log_entries = _parse_log()
            if log_entries:
                today_str  = datetime.now().strftime("%Y-%m-%d")
                week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
                month_str  = datetime.now().strftime("%Y-%m")
                cnt_today = sum(1 for e in log_entries if e["date"] == today_str)
                cnt_week  = sum(1 for e in log_entries if e["date"] >= week_start)
                cnt_month = sum(1 for e in log_entries if e["date"].startswith(month_str))
                cnt_total = len(log_entries)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("오늘",     f"{cnt_today}회")
                c2.metric("이번 주",  f"{cnt_week}회")
                c3.metric("이번 달",  f"{cnt_month}회")
                c4.metric("누적 총계", f"{cnt_total}회")
                st.markdown("**최근 10회 접속**")
                for e in reversed(log_entries[-10:]):
                    st.text(f"{e['datetime']}  |  {e['name'] or '(이름없음)'}")
            else:
                st.info("아직 접속 기록이 없습니다.")

            # 유효 코드 목록
            st.markdown("---")
            st.markdown("**📋 현재 유효 승인 코드**")
            codes_now, _ = _get_codes_dict()
            if codes_now:
                for c, n in list(codes_now.items()):
                    col_c, col_del = st.columns([4, 1])
                    col_c.code(f"{c}  ←  {n or '(이름 없음)'}")
                    if col_del.button("🗑️", key=f"del_code_{c}"):
                        codes_now2, sha2 = _get_codes_dict()
                        if c in codes_now2:
                            del codes_now2[c]
                            body = "\n".join(f"{k}:{v}" for k, v in codes_now2.items()) + "\n"
                            _gh_write("cm_access_codes.txt", body, sha2, f"코드삭제:{c}")
                        st.rerun()
            else:
                st.info("현재 유효한 승인 코드가 없습니다.")

            # 재입장 코드 목록
            st.markdown("---")
            st.markdown("**📋 재입장 코드 목록 (30일 유효)**")
            dt_tokens2, dt_sha2, _ = _get_device_tokens()
            if dt_tokens2:
                for tok, info in list(dt_tokens2.items()):
                    col_t, col_td = st.columns([4, 1])
                    col_t.code(f"{tok}  ←  {info.get('name','(이름없음)')}  |  만료: {info.get('expiry','')}")
                    if col_td.button("🗑️", key=f"del_tok_{tok}"):
                        content2, sha3 = _gh_read("cm_device_tokens.txt")
                        new_lines2 = [l for l in content2.splitlines() if not l.startswith(tok)]
                        _gh_write("cm_device_tokens.txt", "\n".join(new_lines2) + "\n", sha3, f"토큰삭제:{tok[:8]}")
                        st.rerun()
                if st.button("🗑️ 전체 재입장 코드 초기화", key="clear_all_tokens"):
                    _gh_write("cm_device_tokens.txt", "", dt_sha2, "전체초기화")
                    st.rerun()
            else:
                st.info("현재 유효한 재입장 코드가 없습니다.")

        elif admin_pw_input:
            st.error("비밀번호가 틀렸습니다.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("""
    <p style='text-align:center;color:#cbd5e1;font-size:11px;margin-top:24px;'>
        Copyright © 2025 (주)아이팝엔지니어링 | All Rights Reserved.
    </p>
    """, unsafe_allow_html=True)
    st.stop()

# ════════════════════════════════════════════════════════════
# 메인 앱 — 인월수 산출 (HTML 유사 레이아웃)
# ════════════════════════════════════════════════════════════

# ── CSS 커스텀 ──
st.markdown("""
<style>
/* 상단 헤더 여백 줄이기 */
.block-container { padding-top: 1rem !important; }
/* 섹션 타이틀 */
.sec-title {
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: #1d4ed8;
    display: flex; align-items: center; gap: 6px; margin-bottom: 10px;
}
.sec-title::before {
    content: ''; display: inline-block;
    width: 3px; height: 12px; background: #1d4ed8; border-radius: 2px;
}
/* 결과 테이블 헤더 */
.res-header {
    background: #1d4ed8; color: white;
    padding: 6px 4px; font-size: 11px; font-weight: 600;
    text-align: center; border-radius: 4px 4px 0 0;
}
/* 그룹 카드 */
.field-group {
    background: #f8fafd; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 12px 10px 8px; margin-bottom: 8px;
}
.group-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
    text-transform: uppercase; color: #1d4ed8; margin-bottom: 6px;
}
/* 결과 카드 */
.sum-card {
    background: #fff; border: 1px solid #bfdbfe;
    border-radius: 8px; padding: 10px 12px;
    text-align: center; margin-bottom: 6px;
}
.sum-card.highlight { background: #dbeafe; border-color: #1d4ed8; }
.sum-label { font-size: 11px; color: #64748b; margin-bottom: 4px; }
.sum-value { font-size: 20px; font-weight: 700; color: #92400e; }
.sum-card.highlight .sum-value { color: #1d4ed8; }
/* 로그 창 */
.log-box {
    background: #ecfdf5; border: 1px solid #a7f3d0;
    border-left: 3px solid #10b981; border-radius: 6px;
    padding: 10px 14px; font-family: monospace; font-size: 12px;
    color: #065f46; white-space: pre-wrap; line-height: 1.8;
    max-height: 220px; overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ═══ 계산 DB ═══
DB = [
    ["공사착수",                    "식",      72.7,  False, False, False, False],
    ["시공성과확인 및 검측업무",     "공사일수",  2.9,  True,  True,  True,  True ],
    ["사용자재의 적정성 검토",       "공사개월", 10.0,  True,  True,  False, True ],
    ["품질시험 및 성과검토",         "공사개월", 12.6,  True,  False, False, True ],
    ["시공계획검토",                 "공사개월",  8.8,  True,  True,  True,  True ],
    ["기술검토 및 교육",             "공사개월", 10.1,  True,  False, False, True ],
    ["공정관리",                     "공사개월",  9.0,  True,  True,  False, True ],
    ["안전관리",                     "공사개월", 22.0,  False, True,  False, True ],
    ["환경관리",                     "공사개월",  5.3,  False, True,  False, True ],
    ["설계변경 관리",                "공사개월",  7.5,  False, False, True,  True ],
    ["기성검사",                     "회",       6.6,  False, False, False, False],
    ["준공검사",                     "식",       3.8,  False, False, False, False],
    ["계약자간 시공인터페이스 조정", "공사개월",  2.8,  True,  False, False, False],
    ["하도급적정성검토",             "공사년수", 23.0,  False, False, False, True ],
    ["시공단계의 예산검증 및 지원",  "회",      36.4,  False, False, False, True ],
    ["일반행정업무",                 "용역일수",  1.6,  False, False, False, True ],
]

AVG_T_TABLE = [
    [10,10],[30,14],[50,17],[70,24],[100,28],[150,30],
    [200,37],[300,38],[400,38],[500,39],[700,45],[1000,54]
]
M2_PER_PYEONG = 3.30579

def get_avg_T(cost):
    if cost <= 10:   return 10.0
    if cost >= 1000: return 54.0
    for i in range(len(AVG_T_TABLE)-1):
        c1,d1 = AVG_T_TABLE[i]; c2,d2 = AVG_T_TABLE[i+1]
        if c1 <= cost <= c2:
            return d1 + (cost-c1)*(d2-d1)/(c2-c1)
    return 38.0

def calc_difficulty(C, S, T):
    if C <= 0 or T <= 0: return 1.0
    C_unit = C/10; avg_T = get_avg_T(C)
    p_corr = (avg_T-T)/avg_T*0.1
    s_ratio = min(S/C,1.0) if C>0 else 0
    if C_unit <= 200:
        cost_f = 0.011*C_unit*(1-0.0025*C_unit)
        D = cost_f + p_corr + 0.5*s_ratio + 0.2
    else:
        D = 1.1 + p_corr + 0.5*s_ratio + 0.2 + (C_unit-200)/250
    return round(max(0.6, min(D, 2.0)), 3)

def default_q(task, unit, T):
    if any(k in task for k in ["시공계획","기술검토"]): return T
    if any(k in task for k in ["설계변경","시공인터페이스","예산검증"]): return 1.0
    if any(k in task for k in ["사용자재","품질시험","기성검사"]): return round(T/6,1)
    if unit == "공사개월": return T
    if unit in ["공사일수","용역일수"]: return T*22
    if unit == "공사년수": return round(T/12,2)
    if "준공" in task: return 1.0
    if unit == "회": return T
    return 1.0

# ══════════════════════════════════════════════
# 상단 타이틀바
# ══════════════════════════════════════════════
top_l, top_r = st.columns([3,1])
with top_l:
    st.markdown("### 🏗️ 건설사업관리 인월수 산출 &nbsp;<span style='font-size:13px;color:#94a3b8;font-weight:400;'>Ver 1.1 &nbsp;·&nbsp; 최종 수정일 2026-04-02</span>", unsafe_allow_html=True)
    st.caption("국토교통부 고시 제2023-580호 · 건설엔지니어링 대가 등에 관한 기준 &nbsp;|&nbsp; (주)아이팝엔지니어링")

# ══════════════════════════════════════════════
# 좌(입력) / 우(결과) 2컬럼 레이아웃
# ══════════════════════════════════════════════
left_col, right_col = st.columns([1, 1.6], gap="medium")

# ─────────────────── 좌측 입력 패널 ───────────────────
with left_col:

    # 색상 범례
    st.markdown("""
    <div style='display:flex;gap:14px;padding:6px 0 10px;font-size:11px;'>
        <span style='display:flex;align-items:center;gap:5px;'>
            <span style='width:10px;height:10px;background:#f1f5f9;border:1.5px solid #94a3b8;border-radius:3px;display:inline-block;'></span>
            <span style='color:#64748b;'>회색 = 자동 계산</span>
        </span>
        <span style='display:flex;align-items:center;gap:5px;'>
            <span style='width:10px;height:10px;background:#fffbeb;border:1.5px solid #f59e0b;border-radius:3px;display:inline-block;'></span>
            <span style='color:#92400e;'>노란색 = 직접 입력</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ① 프로젝트 정보
    st.markdown('<div class="sec-title">1 프로젝트 정보</div>', unsafe_allow_html=True)
    with st.container():
        proj_name = st.text_input("용역명", value="OOO 신축공사", label_visibility="collapsed",
                                   placeholder="용역명")
        proj_addr = st.text_input("대지위치", value="대전시", label_visibility="collapsed",
                                   placeholder="대지위치")

    st.markdown('<div class="group-label" style="margin-top:8px;">연면적 · 공사비</div>', unsafe_allow_html=True)
    c_m2, c_py = st.columns(2)
    with c_m2:
        area_m2 = st.number_input("연면적 (㎡)", min_value=0.0, value=9917.4, step=1.0)
    with c_py:
        area_py = st.number_input("연면적 (평)", min_value=0.0,
                                   value=round(9917.4/M2_PER_PYEONG,1), step=1.0)

    unit_price = st.number_input("평당단가 (만원)", min_value=0.0, value=800.0, step=10.0)
    cost_auto  = round(area_py * unit_price / 10000, 1)
    cost = st.number_input("총 공사비 (억원)", min_value=0.0, value=cost_auto, step=1.0)

    st.markdown('<div class="group-label" style="margin-top:8px;">골조</div>', unsafe_allow_html=True)
    struct_ratio = st.number_input("골조비중 (%)", min_value=0.0, max_value=100.0, value=30.0, step=1.0)
    struct_auto  = round(cost * struct_ratio / 100, 1)
    struct = st.number_input("골조공사비 (억원)", min_value=0.0, value=struct_auto, step=1.0)

    st.markdown('<div class="group-label" style="margin-top:8px;">기간 · 난이도</div>', unsafe_allow_html=True)
    dur = st.number_input("공사기간 (개월)", min_value=1.0, value=42.0, step=1.0)
    D_auto = calc_difficulty(cost, struct, dur)
    st.markdown(f"""
    <div style='background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;padding:6px 12px;
                font-family:monospace;font-size:13px;color:#64748b;margin-bottom:8px;'>
        적용 난이도 (D) &nbsp;&nbsp; <b style='color:#1d4ed8;font-size:16px;'>{D_auto:.3f}</b>
    </div>
    """, unsafe_allow_html=True)

    # ② 옵션
    st.markdown('<div class="sec-title" style="margin-top:12px;">2 옵션 선택</div>', unsafe_allow_html=True)
    comp = st.radio("공종", ["단순","보통","복잡"], index=1, horizontal=True, label_visibility="collapsed")
    chk_super   = st.checkbox("감독권한대행 등 건설사업관리 시행")
    chk_remodel = st.checkbox("리모델링 적용 (Kb × 1.1)")
    chk_bim     = st.checkbox("BIM 적용 (Kc × 1.1)")

    # ③ 수량 조정
    st.markdown('<div class="sec-title" style="margin-top:12px;">3 수량 미세 조정</div>', unsafe_allow_html=True)
    if st.button("🔄 자동값 초기화", key="reset_q"):
        for task, unit, *_ in DB:
            st.session_state[f"q_{task}"] = default_q(task, unit, dur)

    qty_vals = {}
    for task, unit, std, ha, hb, hc, hD in DB:
        dq = default_q(task, unit, dur)
        qa, qb, qc = st.columns([3, 2, 2])
        qa.caption(task)
        qb.caption(f"({unit})")
        qty_vals[task] = qc.number_input(
            f"q_{task}", value=dq, step=0.1,
            label_visibility="collapsed", key=f"q_{task}"
        )

    # 계산 버튼
    calc_btn = st.button("▶ 전체 계산 및 출력", type="primary", use_container_width=True)

# ─────────────────── 우측 결과 패널 ───────────────────
with right_col:

    Ka = 0.9 if comp=="단순" else (1.1 if comp=="복잡" else 1.0)
    Kb = 1.1 if chk_remodel else 1.0
    Kc = 1.1 if chk_bim     else 1.0
    D  = D_auto

    if calc_btn:
        st.session_state.calc_done = True
        _log_usage(st.session_state.get("device_token",""))

    # ④ 산식 로그
    st.markdown('<div class="sec-title">4 상세 산식 검증 (Log)</div>', unsafe_allow_html=True)
    if "calc_done" in st.session_state:
        avg_T   = get_avg_T(cost)
        p_corr  = (avg_T-dur)/avg_T*0.1
        s_ratio = min(struct/cost,1.0) if cost>0 else 0
        C_unit  = cost/10
        cost_f  = 0.011*C_unit*(1-0.0025*C_unit) if C_unit<=200 else 1.1+(C_unit-200)/250
        log_txt = (
            f"══════════════════════════════════════════\n"
            f"[STEP 1] 평균건설사업관리기간 (직선보간)\n"
            f"  → 평균기간 = {avg_T:.4f} 개월\n\n"
            f"[STEP 2] 기간보정계수\n"
            f"  = ({avg_T:.4f} - {dur}) / {avg_T:.4f} × 0.1\n"
            f"  = {p_corr:.5f}\n\n"
            f"[STEP 3] 공사난이도 (D)\n"
            f"  비용 = {cost_f:.4f} | 기간 = {p_corr:.4f}\n"
            f"  골조 = {0.5*s_ratio:.4f} | 상수 = 0.2000\n"
            f"  ─────────────────────────────────\n"
            f"  산출 D = {cost_f+p_corr+0.5*s_ratio+0.2:.4f}  적용 D = {D}\n"
            f"══════════════════════════════════════════"
        )
        st.markdown(f'<div class="log-box">{log_txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="log-box" style="color:#94a3b8;">계산 버튼을 누르면 상세 산식이 여기에 표시됩니다.</div>', unsafe_allow_html=True)

    # ⑤ 산출 내역서
    st.markdown('<div class="sec-title" style="margin-top:14px;">5 최종 산출 내역서</div>', unsafe_allow_html=True)

    # 테이블 헤더
    h0,h1,h2,h3,h4,h5,h6,h7 = st.columns([2.8,1,0.9,0.7,0.7,0.7,0.9,1.3])
    for col, txt in zip([h0,h1,h2,h3,h4,h5,h6,h7],
                        ["업무항목","수량","기준","a","b","c","난이도","산출(인일)"]):
        col.markdown(f"<div style='font-size:11px;font-weight:700;color:#fff;background:#1d4ed8;"
                     f"padding:5px 3px;text-align:center;border-radius:3px;'>{txt}</div>",
                     unsafe_allow_html=True)

    if "calc_done" in st.session_state:
        total_md = 0.0
        for task, unit, std, ha, hb, hc, hD in DB:
            Q  = qty_vals.get(task, 0)
            ka = Ka if ha else 1.0
            kb = Kb if hb else 1.0
            kc = Kc if hc else 1.0
            k_final = ka*kb*kc
            d_app = D if hD else 1.0
            if task=="안전관리" and d_app<1.0: d_app=1.0
            row_val = std*Q*k_final*d_app
            warn = ""
            if task=="안전관리" and k_final*d_app<1.0:
                row_val=std*Q; warn="⚠️"
            row_val = round(row_val,1)
            total_md += row_val

            c0,c1,c2,c3,c4,c5,c6,c7 = st.columns([2.8,1,0.9,0.7,0.7,0.7,0.9,1.3])
            c0.markdown(f"<span style='font-size:12px;'>{task}</span>", unsafe_allow_html=True)
            c1.markdown(f"<span style='font-size:12px;'>{Q:.1f}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='font-size:12px;'>{std}</span>", unsafe_allow_html=True)
            c3.markdown(f"<span style='font-size:12px;color:#475569;'>{f'{ka:.2f}' if ha else '—'}</span>", unsafe_allow_html=True)
            c4.markdown(f"<span style='font-size:12px;color:#475569;'>{f'{kb:.2f}' if hb else '—'}</span>", unsafe_allow_html=True)
            c5.markdown(f"<span style='font-size:12px;color:#475569;'>{f'{kc:.2f}' if hc else '—'}</span>", unsafe_allow_html=True)
            c6.markdown(f"<span style='font-size:12px;color:#475569;'>{f'{d_app:.3f}' if hD else '—'}</span>", unsafe_allow_html=True)
            c7.markdown(f"<span style='font-size:12px;font-weight:700;color:#1d4ed8;'>{row_val:,.1f} {warn}</span>", unsafe_allow_html=True)

        # 최종 결과 요약
        st.divider()
        base_mm  = round(total_md/22, 3)
        final_mm = base_mm if chk_super else round(base_mm*0.8, 3)
        tech_ratio = 0.10 if comp=="단순" else (0.15 if comp=="보통" else 0.20)
        tech_mm  = math.floor(final_mm*tech_ratio*1000)/1000
        res_mm   = round(final_mm-tech_mm, 3)

        st.markdown("**■ 최종 결과**")
        r1,r2,r3,r4 = st.columns(4)
        for col, label, val, hl in [
            (r1, "감독권한대행 기준", f"{base_mm:.3f}", False),
            (r2, "최종 투입인월수",   f"{final_mm:.3f}", True),
            (r3, "상주기술인",        f"{res_mm:.3f}", False),
            (r4, f"기술지원({int(tech_ratio*100)}%)", f"{tech_mm:.3f}", False),
        ]:
            col.markdown(
                f"<div class='sum-card {'highlight' if hl else ''}'>"
                f"<div class='sum-label'>{label}</div>"
                f"<div class='sum-value'>{val}</div>"
                f"<div style='font-size:11px;color:#64748b;'>인ㆍ월수</div>"
                f"</div>", unsafe_allow_html=True
            )

        if not chk_super:
            st.warning("※ 감독권한대행 미해당 — 시공단계 투입인원수에서 20% 감산 적용")

        # CSV 저장
        st.divider()
        rows = [
            ["건설사업관리 대가 산출 내역서"], ["(주)아이팝엔지니어링"],
            ["작성일", datetime.now().strftime("%Y-%m-%d")], [],
            ["용역명", proj_name, "대지위치", proj_addr],
            ["연면적(㎡)", f"{area_m2}㎡", "연면적(평)", f"{area_py}평", "평당단가", f"{unit_price}만원/평"],
            ["총공사비", f"{cost}억원", "골조공사비", f"{struct}억원", "골조비중", f"{struct_ratio}%"],
            ["공사기간", f"{dur}개월", "난이도(D)", D, "공종", comp], [],
            ["업무항목","단위","기준값","수량","a","b","c","난이도","산출(인일)"]
        ]
        for task, unit, std, ha, hb, hc, hD in DB:
            Q = qty_vals.get(task,0)
            ka=Ka if ha else 1.0; kb=Kb if hb else 1.0; kc=Kc if hc else 1.0
            d_app=D if hD else 1.0
            if task=="안전관리" and d_app<1.0: d_app=1.0
            rv=round(std*Q*ka*kb*kc*d_app,1)
            if task=="안전관리" and ka*kb*kc*d_app<1.0: rv=std*Q
            rows.append([task,unit,std,f"{Q:.1f}",
                         f"{ka:.2f}" if ha else "-", f"{kb:.2f}" if hb else "-",
                         f"{kc:.2f}" if hc else "-", f"{d_app:.3f}" if hD else "-", f"{rv:.1f}"])
        rows += [[],["[ 최종 결과 ]"],
                 ["감독권한대행 기준",f"{base_mm:.3f} 인ㆍ월수"],
                 ["최종 투입인월수",f"{final_mm:.3f} 인ㆍ월수"],
                 ["상주기술인",f"{res_mm:.3f} 인ㆍ월수"],
                 ["기술지원기술인",f"{tech_mm:.3f} 인ㆍ월수 ({int(tech_ratio*100)}%)"]]
        csv = "\n".join(",".join(f'"{str(c).replace(chr(34),chr(34)*2)}"' for c in r) for r in rows)
        c_dl1, c_dl2 = st.columns(2)
        c_dl1.download_button(
            "💾 CSV 저장",
            data="\ufeff"+csv,
            file_name=f"{datetime.now().strftime('%Y%m%d')}_{proj_name}_인월수산출.csv",
            mime="text/csv;charset=utf-8", use_container_width=True
        )
        c_dl2.button("🖨️ 인쇄", use_container_width=True,
                     help="브라우저 인쇄(Ctrl+P)를 이용해주세요")
    else:
        st.info("👈 좌측에서 정보 입력 후 **▶ 전체 계산 및 출력** 버튼을 눌러주세요.")


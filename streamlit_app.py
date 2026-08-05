# -*- coding: utf-8 -*-
"""
ネットワーク障害 切り分け探偵 -- 情報Ⅰ学習用Webアプリ
Streamlit 単一ファイルで完結。
"""

import random

import streamlit as st
import pandas as pd

# ============================================================
# 基本設定
# ============================================================
st.set_page_config(
    page_title="ネット障害 切り分け探偵",
    page_icon="🕵️",
    layout="wide",
)

PLACEHOLDER = "―― 選択してください ――"

ACTION_KEYS = ["physical", "ipconfig", "ping_gw", "nslookup", "ping_dest"]

ACTION_LABEL = {
    "physical": "🔌 LANケーブル・LED点灯確認（物理点検）",
    "ipconfig": "💻 ipconfig 実行（IP・デフォルトゲートウェイ確認）",
    "ping_gw": "🌐 デフォルトゲートウェイへの ping",
    "nslookup": "🔍 nslookup 実行（DNSの名前解決確認）",
    "ping_dest": "🎯 宛先Webサーバー（外部）への ping",
}

ACTION_SHORT = {
    "physical": "物理点検",
    "ipconfig": "ipconfig",
    "ping_gw": "GWへping",
    "nslookup": "nslookup",
    "ping_dest": "宛先へping",
}

ACTION_CMD = {
    "physical": "[目視確認] LANケーブルの接続 / 機器のLEDランプ点灯状況をチェック",
    "ipconfig": "C:\\Users\\student> ipconfig /all",
    "ping_gw": "C:\\Users\\student> ping 192.168.1.1",
    "nslookup": "C:\\Users\\student> nslookup www.school-portal.jp",
    "ping_dest": "C:\\Users\\student> ping www.school-portal.jp",
}

SCENARIOS = {
    "A": {
        "title": "ケースA：LANケーブル断線",
        "icon": "🔌💥",
        "cause": "自分のPCのLANケーブルが物理的に抜けている",
    },
    "B": {
        "title": "ケースB：DNSサーバー障害",
        "icon": "🌐📛",
        "cause": "プロバイダのDNSサーバーがダウンしている",
    },
    "C": {
        "title": "ケースC：ルーターのフリーズ",
        "icon": "🧊",
        "cause": "自宅のルーター（デフォルトゲートウェイ）がフリーズしている",
    },
}

# 各シナリオでの各アクションの実行結果 (状態, 詳細メッセージ)
SIM = {
    "A": {
        "physical": ("NG", "🔴 LEDランプが消灯しています。ケーブル未接続の可能性が高いです。"),
        "ipconfig": ("NG", "🔴 IPv4アドレス: 169.254.23.5 (APIPA) → DHCPサーバーに到達できていません。"),
        "ping_gw": ("NG", "🔴 Request timed out.（パケットロス 100%）"),
        "nslookup": ("NG", "🔴 *** 要求がタイムアウトしました。DNSサーバーに到達できません。"),
        "ping_dest": ("NG", "🔴 Request timed out.（パケットロス 100%）"),
    },
    "B": {
        "physical": ("OK", "🟢 LEDランプ点灯中。物理的な接続は正常です。"),
        "ipconfig": ("OK", "🟢 IPv4アドレス: 192.168.1.15 / GW: 192.168.1.1（正常に取得済み）"),
        "ping_gw": ("OK", "🟢 192.168.1.1 からの応答：時間 1ms（正常）"),
        "nslookup": ("NG", "🔴 DNS request timed out. サーバーから応答がありません。"),
        "ping_dest": ("NG", "🔴 ping要求ではホスト名 www.school-portal.jp が見つかりませんでした。"),
    },
    "C": {
        "physical": ("OK", "🟢 LEDランプ点灯中。物理的な接続は正常です。"),
        "ipconfig": ("OK", "🟢 IPv4アドレス: 192.168.1.15 / GW: 192.168.1.1（正常に取得済み）"),
        "ping_gw": ("NG", "🔴 Request timed out. デフォルトゲートウェイが応答しません。"),
        "nslookup": ("NG", "🔴 デフォルトゲートウェイに到達できず、DNS問い合わせも失敗しました。"),
        "ping_dest": ("NG", "🔴 宛先への経路がありません。（Destination host unreachable）"),
    },
}

IDEAL_ORDER = ["physical", "ipconfig", "ping_gw", "nslookup", "ping_dest"]


def build_plain_dot(order_labels, label_to_key):
    """Step1〜5の現在の選択状況を、シンプルなフローチャートのDOT文字列として描画する。"""
    lines = [
        "digraph G {",
        "rankdir=LR;",
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11];',
        'edge [color="#999999", penwidth=1.4];',
    ]
    for i, label in enumerate(order_labels, start=1):
        if not label or label == PLACEHOLDER:
            node_label = f"Step{i}\\n（未選択）"
            attrs = 'style="rounded,dashed", fillcolor="#f5f5f5", color="#bbbbbb", fontcolor="#999999"'
        else:
            key = label_to_key[label]
            node_label = f"Step{i}\\n{ACTION_SHORT[key]}"
            attrs = 'fillcolor="#dbe9fb", color="#3f6fb0", fontcolor="#1c3f66", penwidth=1.5'
        lines.append(f'n{i} [label="{node_label}", {attrs}];')
    for i in range(1, 5):
        lines.append(f"n{i} -> n{i + 1};")
    lines.append("}")
    return "\n".join(lines)


# ============================================================
# スタイル
# ============================================================
st.markdown(
    """
    <style>
    .terminal {
        background-color: #0e1117;
        color: #39ff88;
        font-family: "Consolas", "Menlo", monospace;
        padding: 14px 16px;
        border-radius: 8px;
        line-height: 1.7;
        font-size: 0.88rem;
        white-space: pre-wrap;
        border: 1px solid #333;
    }
    .terminal .cmd { color: #8ab4f8; }
    .terminal .ok { color: #39ff88; }
    .terminal .ng { color: #ff6b6b; }
    .terminal .diag {
        color: #ffd166;
        font-weight: bold;
    }
    .terminal .wasted { color: #777; }
    .score-badge {
        font-size: 2.6rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# サイドバー：導入・ストーリー
# ============================================================
with st.sidebar:
    st.markdown("## 🕵️ ネット障害 切り分け探偵")
    st.markdown(
        "ある日、あなたのパソコンが**インターネットにつながらなくなった**……。\n\n"
        "犯人（原因）は一体どこに？ 🔎\n\n"
        "**「手元」から「外」へ**、順番に証拠（コマンドの実行結果）を集めて、"
        "無駄なく真相にたどりつく名探偵になろう！"
    )
    st.markdown("---")
    st.markdown(
        "### 📏 探偵の心得（切り分けの鉄則）\n"
        "1. **物理優先**：まず手元（ケーブル・LED・IP設定）を疑う\n"
        "2. **内から外へ**：自宅ルーター → インターネットの順で疑う\n"
        "3. **名前解決の確認**：ドメイン名で通信する前にDNSを疑う\n"
        "4. **無駄を出さない**：原因が分かったら、それ以上の手順は不要"
    )
    st.markdown("---")
    st.caption("Step1〜Step5に、5つの点検アクションを重複なく1つずつ割り当てて、"
                "「アルゴリズムを検証する」ボタンを押してみよう。")

# ============================================================
# メインタイトル
# ============================================================
st.title("🕵️ ネット障害 切り分け探偵：点検アルゴリズム評価アプリ")
st.markdown(
    "「情報Ⅰ」ネットワーク分野の学習アプリです。あなたが組んだ点検の手順（アルゴリズム）が、"
    "3つの通信障害シナリオに対してどれだけ**論理的に無駄なく**原因を特定できるかを自動採点します。"
)
st.divider()

col_left, col_right = st.columns([1, 1.35], gap="large")

# ============================================================
# 左カラム：フロー設計
# ============================================================
with col_left:
    st.subheader("🧩 Step1〜Step5：点検フローを組み立てよう")
    st.caption("5つのアクションを、実行したい順番でStep1〜Step5に重複なく割り当ててください。"
                "選択肢の並び順はランダムです（順番自体はヒントになりません）。")

    if "shuffled_keys" not in st.session_state:
        shuffled_keys = ACTION_KEYS.copy()
        random.shuffle(shuffled_keys)
        st.session_state["shuffled_keys"] = shuffled_keys

    if st.button("🔀 選択肢の並び順をシャッフルする", use_container_width=True):
        shuffled_keys = ACTION_KEYS.copy()
        random.shuffle(shuffled_keys)
        st.session_state["shuffled_keys"] = shuffled_keys

    options = [PLACEHOLDER] + [ACTION_LABEL[k] for k in st.session_state["shuffled_keys"]]
    label_to_key = {v: k for k, v in ACTION_LABEL.items()}

    selections = []
    for i in range(1, 6):
        choice = st.selectbox(f"Step {i}", options, key=f"step_{i}")
        selections.append(choice)

    chosen_labels = [s for s in selections if s != PLACEHOLDER]
    has_all = len(chosen_labels) == 5
    has_duplicate = len(set(chosen_labels)) != len(chosen_labels)

    if has_duplicate:
        st.warning("⚠️ 同じアクションが複数のStepで選択されています。5つのアクションを重複なく選び直してください。")
    elif not has_all:
        st.info(f"あと {5 - len(chosen_labels)} 個のStepでアクションを選択してください。")

    st.markdown("##### 🗺️ あなたの点検フローチャート（リアルタイム表示）")
    st.graphviz_chart(build_plain_dot(selections, label_to_key), use_container_width=True)

    can_run = has_all and not has_duplicate
    run_clicked = st.button("🔬 アルゴリズムを検証する", type="primary", disabled=not can_run, use_container_width=True)

    if run_clicked and can_run:
        order = [label_to_key[selections[i]] for i in range(5)]
        st.session_state["order"] = order
        st.session_state["computed"] = True

    if "order" in st.session_state:
        st.markdown("##### 現在検証中のフロー")
        flow_str = "  ➔  ".join(ACTION_SHORT[k] for k in st.session_state["order"])
        st.code(flow_str, language=None)

# ============================================================
# 評価ロジック
# ============================================================

def get_positions(order):
    return {key: idx + 1 for idx, key in enumerate(order)}


def get_diag_pos(scenario, pos):
    if scenario == "A":
        return min(pos["physical"], pos["ipconfig"])
    if scenario == "B":
        return pos["nslookup"]
    if scenario == "C":
        return pos["ping_gw"]
    return 5


def build_case_result(scenario, order, pos):
    diag_pos = get_diag_pos(scenario, pos)
    wasted_keys = [k for k in order if pos[k] > diag_pos]
    warnings = []

    if scenario in ("A", "C"):
        if pos["ping_gw"] < min(pos["physical"], pos["ipconfig"]):
            warnings.append(
                "⚠️ 物理点検／ipconfigより先にゲートウェイへpingしています。ping失敗だけでは"
                "「ケーブル断線」なのか「ルーターのフリーズ」なのか区別がつかず、誤診断のリスクがあります。"
            )
    if scenario == "B":
        if pos["nslookup"] < pos["ping_gw"]:
            warnings.append(
                "⚠️ ゲートウェイへの疎通確認より先にnslookupを実行しています。障害がLAN内（ルーター等）にあるのか"
                "DNSサーバー側にあるのか、切り分けがやや甘くなります。"
            )

    return {
        "diag_pos": diag_pos,
        "wasted_keys": wasted_keys,
        "warnings": warnings,
    }


def compute_score(order):
    pos = get_positions(order)

    # ① 物理優先ルール：物理点検/ipconfig(のどちらか早い方)は、
    #    ゲートウェイping・nslookup・宛先pingのすべてより先か
    rule1 = min(pos["physical"], pos["ipconfig"]) < min(pos["ping_gw"], pos["nslookup"], pos["ping_dest"])
    # ② 階層的切り分け：ゲートウェイpingは、nslookup・宛先pingより先か（内から外へ）
    rule2 = pos["ping_gw"] < min(pos["nslookup"], pos["ping_dest"])
    # ③ 名前解決の前提確認：nslookupは宛先pingより先か
    rule3 = pos["nslookup"] < pos["ping_dest"]
    # ④ 徹底した手元確認：物理点検とipconfigの「両方」を終えてから外側の確認に進んでいるか
    rule4 = max(pos["physical"], pos["ipconfig"]) < min(pos["ping_gw"], pos["nslookup"], pos["ping_dest"])

    diag_positions = {s: get_diag_pos(s, pos) for s in SCENARIOS}

    total = int(rule1) * 25 + int(rule2) * 25 + int(rule3) * 25 + int(rule4) * 25

    return {
        "pos": pos,
        "rule1": rule1,
        "rule2": rule2,
        "rule3": rule3,
        "rule4": rule4,
        "diag_positions": diag_positions,
        "total": total,
    }


def rank_comment(score):
    if score >= 90:
        return "🕵️‍♂️ **名探偵ランク！** 手元から外へ、無駄のない見事な切り分けです。"
    if score >= 70:
        return "🔍 **一人前の技術者ランク。** 基本の型はできています。細部を詰めればパーフェクトです。"
    if score >= 50:
        return "🧭 **見習い探偵ランク。** 手順の順序を見直すと、もっと効率よく特定できます。"
    return "🌱 **探偵の卵ランク。** まずは「手元（物理点検）」から始める基本を意識してみましょう。"


def build_dot(scenario, order, diag_pos):
    lines = [
        "digraph G {",
        "rankdir=LR;",
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11];',
        'edge [color="#999999"];',
    ]
    for i, key in enumerate(order, start=1):
        status, _ = SIM[scenario][key]
        wasted = i > diag_pos
        is_diag = i == diag_pos

        if wasted:
            fill = "#e2e3e5"
            fontcolor = "#777777"
        elif status == "OK":
            fill = "#d4edda"
            fontcolor = "#1e5631"
        else:
            fill = "#f8d7da"
            fontcolor = "#7a1f1f"

        border = "#ffb400" if is_diag else "#666666"
        penwidth = 3 if is_diag else 1
        mark = "🎯" if is_diag else ("✅" if status == "OK" else "❌")
        extra = "\\n(確認不要)" if wasted else ""
        label = f"Step{i}\\n{ACTION_SHORT[key]}\\n{mark}{extra}"

        lines.append(
            f'n{i} [label="{label}", fillcolor="{fill}", fontcolor="{fontcolor}", '
            f'color="{border}", penwidth={penwidth}];'
        )

    for i in range(1, 5):
        lines.append(f"n{i} -> n{i+1};")
    lines.append("}")
    return "\n".join(lines)


def render_terminal(scenario, order, diag_pos):
    html_lines = []
    for i, key in enumerate(order, start=1):
        status, detail = SIM[scenario][key]
        wasted = i > diag_pos
        is_diag = i == diag_pos
        cls = "wasted" if wasted else ("ok" if status == "OK" else "ng")
        tag = " 🎯【ここで原因特定！】" if is_diag else (" (確認不要だった手順)" if wasted else "")
        html_lines.append(f'<span class="cmd">Step{i}$ {ACTION_CMD[key]}</span>')
        html_lines.append(f'<span class="{cls}">{detail}{tag}</span>')
        html_lines.append("")
    return "<div class='terminal'>" + "\n".join(html_lines) + "</div>"


# ============================================================
# 右カラム：検証結果
# ============================================================
with col_right:
    st.subheader("📊 検証結果・フィードバック")

    if not st.session_state.get("computed"):
        st.info("左側でStep1〜Step5にアクションを割り当て、「アルゴリズムを検証する」を押すと、"
                "ここに3つの障害シナリオでの検証結果が表示されます。")
    else:
        order = st.session_state["order"]
        result = compute_score(order)
        pos = result["pos"]

        score = result["total"]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"<div class='score-badge'>{score}<span style='font-size:1.2rem'>/100点</span></div>",
                        unsafe_allow_html=True)
            st.progress(score / 100)
        with c2:
            st.markdown(rank_comment(score))

        st.markdown("##### ✅ 採点基準チェックリスト")
        checklist = pd.DataFrame(
            [
                ["① 物理優先ルール（手元から外へ）", "OK 🟢" if result["rule1"] else "NG 🔴", "25点"],
                ["② 階層的切り分け（内から外へ）", "OK 🟢" if result["rule2"] else "NG 🔴", "25点"],
                ["③ 名前解決の前提確認", "OK 🟢" if result["rule3"] else "NG 🔴", "25点"],
                ["④ 徹底した手元確認（物理点検とipconfigの両方を先に）", "OK 🟢" if result["rule4"] else "NG 🔴", "25点"],
            ],
            columns=["評価項目", "判定", "配点"],
        )
        st.dataframe(checklist, hide_index=True, use_container_width=True)

        st.markdown("##### 📝 総合アドバイス")
        advice = []
        if not result["rule1"]:
            advice.append(
                "🔴 **物理優先ルール違反**：物理点検やipconfigより先に、ゲートウェイや宛先へのpingを実行しています。"
                "手元の接続を確認せずに外部を疑うのは非効率です。まず「自分のPC周り」から確認しましょう。"
            )
        else:
            advice.append("🟢 物理優先ルールOK：手元（物理層）から確認できています。")

        if not result["rule2"]:
            advice.append(
                "🔴 **階層的切り分け違反**：宛先（外部）へのpingを、ゲートウェイ（自宅ルーター）へのpingより先に行っています。"
                "近い場所から遠い場所へ、順番に疑うのが鉄則です。"
            )
        else:
            advice.append("🟢 階層的切り分けOK：内（ゲートウェイ）→外（宛先）の順で確認できています。")

        if not result["rule3"]:
            advice.append(
                "🔴 **名前解決の前提確認不足**：nslookupより先に宛先（ドメイン名）へのpingを行っています。"
                "ドメイン名で通信する前に、DNSで名前解決できるかを確認しましょう。"
            )
        else:
            advice.append("🟢 名前解決の確認OK：宛先への通信を試す前にnslookupを実施できています。")

        if not result["rule4"]:
            advice.append(
                "🟡 **手元確認が中途半端**：物理点検とipconfigの「どちらか一方」しか外側の確認より先に行っていません。"
                "両方をセットで先に済ませておくと、より確実で無駄のない切り分けになります。"
            )
        else:
            advice.append("🟢 手元確認は万全：物理点検・ipconfigの両方を終えてから外側の確認に進めています。")

        for a in advice:
            st.markdown(a)

        st.divider()
        st.markdown("##### 🔬 シナリオ別 詳細シミュレーション")
        tabs = st.tabs([f"{SCENARIOS[s]['icon']} {SCENARIOS[s]['title']}" for s in SCENARIOS])

        for tab, scenario in zip(tabs, SCENARIOS):
            with tab:
                case = build_case_result(scenario, order, pos)
                diag_pos = case["diag_pos"]
                wasted_keys = case["wasted_keys"]

                st.markdown(f"**🎯 特定成功**：Step{diag_pos} の時点で原因を特定できました。")
                st.caption(f"実際の原因：{SCENARIOS[scenario]['cause']}")

                for w in case["warnings"]:
                    st.warning(w)

                if scenario == "A" and wasted_keys:
                    wasted_labels = "、".join(ACTION_SHORT[k] for k in wasted_keys)
                    st.error(
                        f"💡 **冗長性の指摘**：Step{diag_pos}で物理的な断線と判明した時点で点検は完了すべきです。"
                        f"その後に実行した「{wasted_labels}」は、原因究明にはもう不要な手順（コスト高）でした。"
                    )
                elif wasted_keys:
                    wasted_labels = "、".join(ACTION_SHORT[k] for k in wasted_keys)
                    st.info(f"ℹ️ Step{diag_pos}で原因が判明した後に実行した「{wasted_labels}」は、"
                            "念のための確認以上の意味は薄い手順でした。")

                colA, colB = st.columns([1.1, 1])
                with colA:
                    st.markdown("**実行ログ（ターミナル風）**")
                    st.markdown(render_terminal(scenario, order, diag_pos), unsafe_allow_html=True)
                with colB:
                    st.markdown("**フロー図**")
                    st.graphviz_chart(build_dot(scenario, order, diag_pos), use_container_width=True)

# ============================================================
# 正解フローの例
# ============================================================
st.divider()
with st.expander("🏆 正解フローの例（プロが実践する最も効率的な手順）を見る"):
    st.markdown(
        "以下は、どんな障害にも無駄なく対応できる、教科書的に最も効率のよい点検順序の一例です。"
    )
    st.markdown("　➔　".join(f"**{i+1}. {ACTION_SHORT[k]}**" for i, k in enumerate(IDEAL_ORDER)))
    st.markdown(
        """
- **① 物理点検**：まず一番手元にある「ケーブル・LED」を見る。コストがほぼゼロで、原因の切り分けが最速で進む。
- **② ipconfig**：自分のPCに正しいIPアドレス・デフォルトゲートウェイが割り当てられているかを確認する。ここでAPIPAアドレス（169.254.x.x）ならDHCP/物理層の異常を疑う。
- **③ デフォルトゲートウェイへping**：自宅内（LAN内）の機器（ルーター）まで届いているかを確認する。ここで失敗すればルーターや自宅内LANの問題と分かる。
- **④ nslookup**：ドメイン名をIPアドレスに変換できるか（DNSが機能しているか）を確認する。ここで失敗すればDNSサーバー側の問題と分かる。
- **⑤ 宛先Webサーバーへping**：ここまで全て正常なら、最後に目的のサーバーまで実際に届くかを確認する。

このように「**手元 → 自宅内 → インターネットの外側**」という順序で、**一段階ずつ疑う範囲を広げていく**のが、
無駄のない切り分けの基本です。
        """
    )

st.divider()
st.caption("© 情報Ⅰ ネットワーク学習教材：ネット障害 切り分け探偵")
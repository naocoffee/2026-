# -*- coding: utf-8 -*-
"""
通信障害切り分けフローチャート・パズル
----------------------------------------
生徒が「点検ブロック」を YES/NO 分岐で組み合わせてオリジナルの
切り分けフローチャートを作成し、複数の障害シナリオでシミュレーションを
実行して、フローの正しさ・効率(無駄な点検の有無)・論理の順序を
自動評価するトレーニングアプリ。

このファイルと requirements.txt の2つだけで動作する。
"""

import streamlit as st

# =====================================================================
# 0. マスタデータ定義
# =====================================================================

# 点検ブロック(チェック項目)
# layer: 数値が小さいほど「下位層(物理層に近い)」の点検。
#        理想的な切り分けは layer の小さい順に進めるのが効率的、という
#        評価の基準に使う。
# category: 「local」はPCやルーター周りのローカルな点検、
#           「gateway」はデフォルトゲートウェイ到達性、
#           「dns」は名前解決、「destination」は宛先到達性。
CHECKS = {
    "lan_led":      {"label": "LANケーブルのLED(リンク状態)を確認する",      "layer": 1, "category": "local"},
    "router_power":  {"label": "ルーターの電源・起動状態を確認する",           "layer": 1, "category": "local"},
    "wifi_setting":  {"label": "PCのネットワーク/Wi-Fi設定を確認する",         "layer": 1, "category": "local"},
    "ping_gateway":  {"label": "デフォルトゲートウェイへ ping を打つ",         "layer": 2, "category": "gateway"},
    "nslookup":      {"label": "nslookup で名前解決を確認する",               "layer": 3, "category": "dns"},
    "ping_dest":     {"label": "宛先Webサーバーへ ping を打つ",               "layer": 4, "category": "destination"},
}

# 最終診断(リーフ)の選択肢
DIAGNOSES = {
    "d_cable":  "LANケーブル/物理配線の断線",
    "d_router": "ルーター本体の電源off・故障",
    "d_wifi":   "PCのネットワーク設定(Wi-Fi等)の不良",
    "d_dns":    "DNSサーバーの障害(名前解決不能)",
    "d_dest":   "宛先Webサーバー側の障害",
    "d_ok":     "問題なし(正常に通信できる)",
}

# テストケース(シナリオ)
# outcomes: 各点検を行った場合の結果。 True = 正常(YES) / False = 異常(NO)
# correct: 正しい最終診断
# ideal_steps: 「LEDから順に効率よく調べた場合」に必要な最小点検数の目安
SCENARIOS = [
    {
        "name": "ケース1: 自席のLANケーブル断線",
        "outcomes": {"lan_led": False, "router_power": True, "wifi_setting": True,
                     "ping_gateway": False, "nslookup": False, "ping_dest": False},
        "correct": "d_cable",
        "ideal_steps": 2,
    },
    {
        "name": "ケース2: ルーター本体の電源off/故障",
        "outcomes": {"lan_led": False, "router_power": False, "wifi_setting": False,
                     "ping_gateway": False, "nslookup": False, "ping_dest": False},
        "correct": "d_router",
        "ideal_steps": 2,
    },
    {
        "name": "ケース3: PCのWi-Fi設定不良",
        "outcomes": {"lan_led": True, "router_power": True, "wifi_setting": False,
                     "ping_gateway": False, "nslookup": False, "ping_dest": False},
        "correct": "d_wifi",
        "ideal_steps": 3,
    },
    {
        "name": "ケース4: DNSサーバー障害",
        "outcomes": {"lan_led": True, "router_power": True, "wifi_setting": True,
                     "ping_gateway": True, "nslookup": False, "ping_dest": False},
        "correct": "d_dns",
        "ideal_steps": 3,
    },
    {
        "name": "ケース5: 宛先Webサーバー側の障害",
        "outcomes": {"lan_led": True, "router_power": True, "wifi_setting": True,
                     "ping_gateway": True, "nslookup": True, "ping_dest": False},
        "correct": "d_dest",
        "ideal_steps": 4,
    },
    {
        "name": "ケース6: 正常なケース(問題なし)",
        "outcomes": {"lan_led": True, "router_power": True, "wifi_setting": True,
                     "ping_gateway": True, "nslookup": True, "ping_dest": True},
        "correct": "d_ok",
        "ideal_steps": 4,
    },
]

MAX_DEPTH = len(CHECKS)  # これ以上深くしたら強制的に「診断」で終わらせる

# =====================================================================
# 1. セッション状態(生徒が組み立てたフローの保存領域)
# =====================================================================

def init_state():
    if "nodes" not in st.session_state:
        st.session_state.nodes = {}
    if "pending" not in st.session_state:
        st.session_state.pending = [
            {"key": "root", "parent": None, "branch": "ROOT", "depth": 0}
        ]


def reset_tree():
    st.session_state.nodes = {}
    st.session_state.pending = [
        {"key": "root", "parent": None, "branch": "ROOT", "depth": 0}
    ]
    st.session_state.pop("results", None)


def get_ancestor_check_ids(parent_key):
    """指定ノードから根までの経路上で、すでに使われている check_id の一覧"""
    ids = []
    key = parent_key
    nodes = st.session_state.nodes
    while key is not None:
        node = nodes.get(key)
        if node is None:
            break
        if node["type"] == "check":
            ids.append(node["check_id"])
        key = node.get("parent")
    return ids


def create_check_node(slot, check_id):
    key = slot["key"]
    nodes = st.session_state.nodes
    yes_key = key + "_Y"
    no_key = key + "_N"
    nodes[key] = {
        "type": "check",
        "check_id": check_id,
        "parent": slot["parent"],
        "yes": yes_key,
        "no": no_key,
        "depth": slot["depth"],
    }
    st.session_state.pending.append(
        {"key": yes_key, "parent": key, "branch": "YES", "depth": slot["depth"] + 1}
    )
    st.session_state.pending.append(
        {"key": no_key, "parent": key, "branch": "NO", "depth": slot["depth"] + 1}
    )


def create_diagnosis_node(slot, diagnosis_id):
    key = slot["key"]
    nodes = st.session_state.nodes
    nodes[key] = {
        "type": "diagnosis",
        "diagnosis_id": diagnosis_id,
        "parent": slot["parent"],
        "yes": None,
        "no": None,
        "depth": slot["depth"],
    }


def resolve_slot(slot_key):
    st.session_state.pending = [s for s in st.session_state.pending if s["key"] != slot_key]


# =====================================================================
# 2. フローチャートのツリー表示(テキストによる可視化)
# =====================================================================

def tree_lines(key, depth=0, branch_label=None):
    nodes = st.session_state.nodes
    if key not in nodes:
        return ["    " * depth + f"- ({branch_label}) ▢ 未設定"]
    node = nodes[key]
    indent = "    " * depth
    tag = f"**[{branch_label}]** " if branch_label else ""
    lines = []
    if node["type"] == "check":
        lines.append(f"{indent}- {tag}🔍 {CHECKS[node['check_id']]['label']}")
        lines += tree_lines(node["yes"], depth + 1, "YES(正常)")
        lines += tree_lines(node["no"], depth + 1, "NO(異常)")
    else:
        lines.append(f"{indent}- {tag}🏁 診断: {DIAGNOSES[node['diagnosis_id']]}")
    return lines


# =====================================================================
# 3. シミュレーション(評価エンジン)
# =====================================================================

def simulate(outcomes):
    """完成したツリーを1つのシナリオ(outcomes)で走らせ、
    到達した診断と、通過した点検の履歴を返す"""
    nodes = st.session_state.nodes
    key = "root"
    path = []
    for _ in range(MAX_DEPTH + 2):  # 安全のための上限(通常は木構造なのでループしない)
        node = nodes.get(key)
        if node is None:
            return {"diagnosis": None, "path": path, "error": "未完成のフローです"}
        if node["type"] == "diagnosis":
            return {"diagnosis": node["diagnosis_id"], "path": path, "error": None}
        result = outcomes[node["check_id"]]
        path.append({"check_id": node["check_id"], "result": result})
        key = node["yes"] if result else node["no"]
    return {"diagnosis": None, "path": path, "error": "分岐が深すぎます"}


def evaluate_all():
    results = []
    for sc in SCENARIOS:
        sim = simulate(sc["outcomes"])
        correct = (sim["diagnosis"] == sc["correct"])
        steps = len(sim["path"])
        waste = max(0, steps - sc["ideal_steps"])
        # 順序の評価: 「正常(YES)」という結果が出た直後に、より下位層(物理層側)の
        # 点検へ戻っている場合のみ非効率と判定する。
        # 「異常(NO)」の直後に下位層(ローカル点検)へ戻るのは、原因を絞り込むための
        # 正しい動き(ゲートウェイpingがNG→Wi-Fi設定を確認、など)なので違反にしない。
        layers = [CHECKS[p["check_id"]]["layer"] for p in sim["path"]]
        order_violation = any(
            layers[i + 1] < layers[i] and sim["path"][i]["result"] is True
            for i in range(len(layers) - 1)
        )
        results.append({
            "scenario": sc["name"],
            "correct_label": DIAGNOSES[sc["correct"]],
            "your_label": DIAGNOSES.get(sim["diagnosis"], "(診断に到達できず)"),
            "is_correct": correct,
            "steps": steps,
            "ideal_steps": sc["ideal_steps"],
            "waste": waste,
            "order_violation": order_violation,
            "path": sim["path"],
            "error": sim["error"],
        })
    return results


# =====================================================================
# 4. Streamlit UI
# =====================================================================

st.set_page_config(page_title="障害切り分けフローチャート・パズル", page_icon="🧩", layout="wide")
init_state()

st.title("🧩 通信障害 切り分けフローチャート・パズル")
st.caption("YES/NOチャートを自分で組み立てて、原因の切り分けロジックを検証しよう")

with st.sidebar:
    st.header("📋 進行状況")
    n_nodes = len(st.session_state.nodes)
    n_pending = len(st.session_state.pending)
    st.metric("作成済みノード数", n_nodes)
    st.metric("未設定の分岐(残り)", n_pending)
    st.divider()
    if st.button("🔄 フローをリセットする", use_container_width=True):
        reset_tree()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["① 学習目標", "② フロー作成(パズル)", "③ シミュレーション評価"])

# ---------------------------------------------------------------
# TAB 1: 学習目標
# ---------------------------------------------------------------
with tab1:
    st.subheader("学習目標")
    st.markdown(
        """
このアプリでは、「ネットに繋がらない」という通信障害が起きたときに、
**どの順番でどこを調べれば、無駄なく・早く原因を特定できるか** を
自分自身でYES/NOの分岐(フローチャート)として組み立てます。

- 不具合を切り分けるための順序(アルゴリズム)を、自分の言葉ではなく
  **客観的な手順**として表現する
- 「これを調べたらYESならこっち、NOならこっち」という
  **無駄のない論理的な思考ステップ** を養う
- 自分が作ったフローが、実際の障害ケースに対して
  **正しく機能するか** をシミュレーションで検証する
        """
    )
    st.info("② のタブでフローチャートを作り、③ のタブで6つの障害ケースを流し込んで評価します。")

    with st.expander("💡 使える点検ブロック 一覧"):
        for cid, c in CHECKS.items():
            st.write(f"- **{c['label']}**")

    with st.expander("💡 ヒント: 効率的な切り分けの考え方(答えではありません)"):
        st.markdown(
            """
一般的なネットワーク切り分けは、**「機器に近い場所(物理層)」→「デフォルト
ゲートウェイ」→「名前解決(DNS)」→「宛先サーバー」** の順に、
範囲を絞りながら調べると無駄がありません。

例えば「LANケーブルのLEDがついていない(NO)」なら、次に確認すべきは
遠いサーバーではなく **ルーターの電源やWi-Fi設定など、身近な原因** です。
            """
        )

# ---------------------------------------------------------------
# TAB 2: フロー作成(パズル)
# ---------------------------------------------------------------
with tab2:
    st.subheader("フローチャートを組み立てる")
    st.caption("未設定の分岐が下に表示されます。「点検」か「診断(確定)」を選んで、1つずつ埋めていきましょう。")

    pending = list(st.session_state.pending)

    if not pending:
        st.success("✅ フローチャートが完成しています。③ のタブでシミュレーションを実行しましょう。")
    else:
        for slot in pending:
            key = slot["key"]
            branch = slot["branch"]
            depth = slot["depth"]

            if branch == "ROOT":
                header = "🟦 最初に行う点検を選んでください"
            else:
                parent_node = st.session_state.nodes.get(slot["parent"])
                parent_label = CHECKS[parent_node["check_id"]]["label"] if parent_node else "?"
                branch_jp = "YES(正常)" if branch == "YES" else "NO(異常)"
                header = f"🟦「{parent_label}」が **{branch_jp}** だった場合"

            with st.container(border=True):
                st.markdown(f"**{header}**")

                ancestor_ids = set(get_ancestor_check_ids(slot["parent"]))
                available_checks = {cid: c for cid, c in CHECKS.items() if cid not in ancestor_ids}
                force_diagnosis = (depth >= MAX_DEPTH) or (len(available_checks) == 0)

                if force_diagnosis:
                    st.caption("この段階では、これ以上の点検ブロックが使えないため「診断」を選んでください。")
                    action = "診断を確定する"
                else:
                    action = st.selectbox(
                        "この段階のアクション",
                        ["-- 選択してください --", "点検ブロックを配置する", "診断を確定する"],
                        key=f"action_{key}",
                    )

                if action == "点検ブロックを配置する":
                    options = ["-- 選択してください --"] + list(available_checks.keys())
                    chosen = st.selectbox(
                        "点検ブロックを選択",
                        options,
                        format_func=lambda x: CHECKS[x]["label"] if x in CHECKS else x,
                        key=f"check_{key}",
                    )
                    if st.button("この点検で確定する", key=f"btn_check_{key}"):
                        if chosen == "-- 選択してください --":
                            st.warning("点検ブロックを選択してください。")
                        else:
                            create_check_node(slot, chosen)
                            resolve_slot(key)
                            st.rerun()

                elif action == "診断を確定する":
                    options = ["-- 選択してください --"] + list(DIAGNOSES.keys())
                    chosen = st.selectbox(
                        "最終診断を選択(この枝はここで終了します)",
                        options,
                        format_func=lambda x: DIAGNOSES[x] if x in DIAGNOSES else x,
                        key=f"diag_{key}",
                    )
                    if st.button("この診断で確定する(リーフ)", key=f"btn_diag_{key}"):
                        if chosen == "-- 選択してください --":
                            st.warning("診断を選択してください。")
                        else:
                            create_diagnosis_node(slot, chosen)
                            resolve_slot(key)
                            st.rerun()

    st.divider()
    st.subheader("🌳 現在のフローチャート")
    if "root" in st.session_state.nodes:
        st.markdown("\n".join(tree_lines("root")))
    else:
        st.info("まだ何も作成されていません。上のフォームから最初の点検を選んでください。")

# ---------------------------------------------------------------
# TAB 3: シミュレーション評価
# ---------------------------------------------------------------
with tab3:
    st.subheader("シミュレーションによる評価")

    if st.session_state.pending:
        st.warning(
            f"フローチャートが未完成です(残り {len(st.session_state.pending)} 箇所)。"
            "② のタブで全ての分岐を埋めてから実行してください。"
        )
    else:
        st.caption("6つの障害シナリオを、あなたが作ったフローチャートに流し込んでテストします。")

        if st.button("▶ シミュレーションを実行する", type="primary"):
            st.session_state.results = evaluate_all()

        if "results" in st.session_state:
            results = st.session_state.results

            n_correct = sum(1 for r in results if r["is_correct"])
            total_waste = sum(r["waste"] for r in results)
            n_order_issue = sum(1 for r in results if r["order_violation"])

            c1, c2, c3 = st.columns(3)
            c1.metric("診断の正解率", f"{n_correct}/{len(results)}")
            c2.metric("合計の無駄な点検ステップ", f"{total_waste}")
            c3.metric("順序が非効率だったケース", f"{n_order_issue}/{len(results)}")

            st.divider()

            table_data = []
            for r in results:
                table_data.append({
                    "シナリオ": r["scenario"],
                    "正解の診断": r["correct_label"],
                    "あなたの診断": r["your_label"],
                    "判定": "✅ 正解" if r["is_correct"] else "❌ 不正解",
                    "使用ステップ数": r["steps"],
                    "理想ステップ数": r["ideal_steps"],
                    "順序": "⚠️ 非効率" if r["order_violation"] else "◯ 適切",
                })
            st.dataframe(table_data, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("📝 ケースごとの詳細フィードバック")

            for r in results:
                icon = "✅" if r["is_correct"] else "❌"
                with st.expander(f"{icon} {r['scenario']}"):
                    if r["error"]:
                        st.error(r["error"])
                        continue

                    st.markdown("**シミュレーションで通過した点検の履歴:**")
                    for i, p in enumerate(r["path"], start=1):
                        res_jp = "YES(正常)" if p["result"] else "NO(異常)"
                        st.write(f"{i}. {CHECKS[p['check_id']]['label']} → **{res_jp}**")

                    st.markdown(f"**到達した診断:** {r['your_label']}")
                    st.markdown(f"**正しい診断:** {r['correct_label']}")

                    advice = []
                    if not r["is_correct"]:
                        advice.append(
                            "❌ 診断を間違えています。このシナリオの点検結果(YES/NO)を見直し、"
                            "分岐の先が正しい原因に辿り着くように配置し直しましょう。"
                        )
                    else:
                        advice.append("✅ 正しい原因を検出できました。")

                    if r["waste"] > 0:
                        advice.append(
                            f"⚠️ 理想は{r['ideal_steps']}ステップですが、実際は{r['steps']}ステップ"
                            f"かかっています({r['waste']}ステップ分、無駄な点検の可能性があります)。"
                            "すでに結果がわかっている範囲を、もう一度別の角度から調べていないか確認しましょう。"
                        )

                    if r["order_violation"]:
                        advice.append(
                            "⚠️ 点検の順序が非効率です。機器に近い場所(物理層)→ゲートウェイ→"
                            "名前解決→宛先サーバー、の順に範囲を絞る方が、後戻りのない調べ方になります。"
                        )

                    for a in advice:
                        st.write(a)

            st.divider()
            st.subheader("💬 総合フィードバック")
            overall = []
            if n_correct == len(results):
                overall.append("🎉 全てのケースで正しい原因を特定できました。素晴らしい切り分けロジックです。")
            else:
                overall.append(f"6ケース中{n_correct}ケースで正しい診断に到達しました。誤答したケースの分岐を見直しましょう。")
            if total_waste == 0:
                overall.append("ステップ数も全ケースで理想的な最小手順に収まっており、無駄のないフローです。")
            elif total_waste <= 3:
                overall.append("いくつかのケースでやや無駄な点検が見られます。すでに得られた情報から不要と分かる点検を削れないか検討しましょう。")
            else:
                overall.append("無駄な点検が多く見られます。同じ情報を得られる点検を繰り返していないか、フロー全体を見直しましょう。")
            if n_order_issue > 0:
                overall.append("一部のケースで、点検の順序が非効率(後戻りが発生)でした。物理層に近い点検から順に絞り込む設計にすると改善します。")

            for o in overall:
                st.write("- " + o)
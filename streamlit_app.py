# Streamlitライブラリをインポート
import streamlit as st

# ページ設定（タブに表示されるタイトル、表示幅）
st.set_page_config(page_title="タイトル", layout="wide")

# タイトルを設定
st.title('Streamlitのサンプルアプリ')

# テキスト入力ボックスを作成し、ユーザーからの入力を受け取る
user_input = st.text_input('あなたの名前を入力してください')

# ボタンを作成し、クリックされたらメッセージを表示
if st.button('挨拶する'):
    if user_input:  # 名前が入力されているかチェック
        st.success(f'🌟 こんにちは、{user_input}さん! 🌟')  # メッセージをハイライト
    else:
        st.error('名前を入力してください。')  # エラーメッセージを表示

# スライダーを作成し、値を選択
number = st.slider('好きな数字（10進数）を選んでください', 0, 100)

# 補足メッセージ
st.caption("十字キー（左右）でも調整できます。")

# 選択した数字を表示
st.write(f'あなたが選んだ数字は「{number}」です。')

# 選択した数値を2進数に変換
binary_representation = bin(number)[2:]  # 'bin'関数で2進数に変換し、先頭の'0b'を取り除く
st.info(f'🔢 10進数の「{number}」を2進数で表現すると「{binary_representation}」になります。 🔢')  # 2進数の表示をハイライト

import streamlit as st
import random

st.title("乱数生成アプリ")

# タブで機能を分ける
tab1, tab2, tab3 = st.tabs(["整数", "小数", "リストから選択"])

with tab1:
    st.subheader("整数の乱数")
    col1, col2 = st.columns(2)
    with col1:
        min_val = st.number_input("最小値", value=1, key="int_min")
    with col2:
        max_val = st.number_input("最大値", value=100, key="int_max")

    if st.button("整数を生成"):
        result = random.randint(int(min_val), int(max_val))
        st.success(f"生成された整数: **{result}**")

with tab2:
    st.subheader("小数の乱数")
    col1, col2 = st.columns(2)
    with col1:
        f_min = st.number_input("最小値", value=0.0, key="float_min")
    with col2:
        f_max = st.number_input("最大値", value=1.0, key="float_max")

    if st.button("小数を生成"):
        result = random.uniform(f_min, f_max)
        st.success(f"生成された小数: **{result:.4f}**")

with tab3:
    st.subheader("リストからランダム選択")
    items_text = st.text_area("項目をカンマ区切りで入力", "赤,青,緑,黄")
    items = [x.strip() for x in items_text.split(",") if x.strip()]

    n = st.slider("選ぶ個数", 1, max(1, len(items)), 1)

    if st.button("選択する"):
        if len(items) >= n:
            result = random.sample(items, n)
            st.success(f"選ばれた項目: **{', '.join(result)}**")
        else:
            st.error("項目数が選ぶ個数より少ないです")

st.divider()
st.caption("Powered by Python `random` module")

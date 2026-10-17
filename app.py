import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="شموع الخبير v6", layout="wide", page_icon="🎯")
st.title("🎯 ماسح السوق الذكي - شموع الخبير (EGX v6)")
st.caption("استراتيجية الهدف المقسّم (1.618/2.618) + Breakeven Stop | Win Rate 74%")

EGX_TICKERS = [
    'COMI.CA','ADIB.CA','CIEB.CA','SAUD.CA','FAIT.CA','BIDI.CA','ETEL.CA','EGSA.CA',
    'TMGH.CA','PHDC.CA','OCDI.CA','HELI.CA','ELSH.CA','PRMH.CA','SWDY.CA','ABUK.CA','MFPC.CA',
    'SKPC.CA','EFIC.CA','FWRY.CA','JUFO.CA','DOMT.CA','UEFM.CA','SNFC.CA','CCAP.CA',
    'ISPH.CA','CLHO.CA','RMDA.CA','NCCW.CA','SPMD.CA','HRHO.CA','OCPH.CA','EGCH.CA','AMOC.CA','EAST.CA',
    'ORWE.CA','ARCC.CA','SCEM.CA','MTIE.CA','EMFD.CA','ETRS.CA','RACC.CA',
    'ATLC.CA','CANA.CA','KZPC.CA','ELEC.CA','AFDI.CA','AIFI.CA','AMER.CA','AMES.CA',
    'APSW.CA','ARAB.CA','ASCM.CA','ASPI.CA','ATQA.CA','BIOC.CA','CICH.CA','CNFN.CA',
    'COPR.CA','CSAG.CA','DSCW.CA','EEII.CA','EFID.CA','EGBE.CA','ENGC.CA','EOSB.CA','EPCO.CA','GGCC.CA',
    'GIHD.CA','GMCI.CA','GSSC.CA','IEEC.CA','INEG.CA','ISMA.CA','KABO.CA','LCSW.CA','MBSC.CA','MCQE.CA',
    'MENA.CA','MICH.CA','MILS.CA','MOIL.CA','MPCO.CA','NEDA.CA','NHPS.CA',
    'ODIN.CA','OIH.CA','OLFI.CA','PHAR.CA','POUL.CA','RREI.CA','RTVC.CA','SCTS.CA','SIPC.CA','SPHT.CA',
    'SPIN.CA','SVCE.CA','TALM.CA','UNIT.CA','WCDF.CA','WKOL.CA','ZEOT.CA'
]

def build_strategy_features(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['Range_HL'] = df['High'] - df['Low']
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Upper_Wick'] = np.maximum(0, df['High'] - df[['Open','Close']].max(axis=1))
    df['Lower_Wick'] = np.maximum(0, df[['Open','Close']].min(axis=1) - df['Low'])
    df['Close_Position'] = np.where(df['Range_HL']>0, (df['Close']-df['Low'])/df['Range_HL'], 0.5)
    df['Body_Ratio'] = df['Body'] / df['Range_HL'].replace(0, 1)
    df['Upper_Wick_Ratio'] = df['Upper_Wick'] / df['Range_HL'].replace(0, 1)
    df['Lower_Wick_Ratio'] = df['Lower_Wick'] / df['Range_HL'].replace(0, 1)
    df['Range_Pct'] = df['Range_HL'] / df['Close']
    
    df['Vol_EMA20'] = df['Volume'].ewm(span=20, adjust=False).mean()
    df['Vol_Ratio_EMA20'] = df['Volume'] / df['Vol_EMA20'].replace(0, 1)
    df['Vol_Mean_20'] = df['Volume'].rolling(20).mean()
    df['Vol_Std_20'] = df['Volume'].rolling(20).std()
    df['Vol_Bollinger_Lower'] = df['Vol_Mean_20'] - df['Vol_Std_20']
    df['Is_Critical_Vol'] = (df['Volume'] < df['Vol_Bollinger_Lower']).astype(int)
    
    df['Avg_Range_20'] = df['Range_HL'].rolling(20).mean()
    df['Range_Ratio'] = df['Range_HL'] / df['Avg_Range_20'].replace(0, 1)
    
    df['Is_Buyer'] = ((df['Close_Position'] > 0.5) | (df['Lower_Wick'] > df['Upper_Wick'])).astype(int)
    df['Is_Maker'] = (df['Volume'] > df['Vol_EMA20']).astype(int)
    df['Is_Master'] = ((df['Range_Ratio'] > 1.5) & (df['Volume'] > df['Vol_EMA20'])).astype(int)
    df['Is_Downtrend'] = (df['Close'] < df['Close'].shift(10)).astype(int)
    
    df['Is_Shakeout'] = (
        (df['Lower_Wick_Ratio'] > 0.5) &
        (df['Close_Position'] > 0.5) &
        (df['Is_Downtrend'] == 1) &
        (df['Is_Master'] == 1)
    ).astype(int)
    
    df['Is_Climax'] = (
        (df['Is_Downtrend'] == 1) &
        (df['Volume'] > 2 * df['Vol_EMA20']) &
        (df['Range_Ratio'] > 1.5) &
        (df['Close_Position'] > 0.4)
    ).astype(int)
    
    df['Is_Decision'] = (
        (df['Is_Master'] == 1) |
        (df['Is_Shakeout'] == 1) |
        (df['Is_Climax'] == 1) |
        ((df['Is_Critical_Vol'] == 1) & (df['Is_Buyer'] == 1) & (df['Is_Downtrend'] == 1))
    ).astype(int)
    
    df['Signal_Type'] = 'None'
    df.loc[df['Is_Shakeout']==1, 'Signal_Type'] = '🟡 Shakeout'
    df.loc[df['Is_Climax']==1, 'Signal_Type'] = '🟣 Climax'
    df.loc[(df['Is_Master']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = '⭐ Master'
    df.loc[(df['Is_Critical_Vol']==1) & (df['Is_Buyer']==1) & (df['Is_Downtrend']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = '🔵 Critical Vol'
    
    return df

def calculate_trade_plan(row, cost_pct=0.005):
    entry = row['High']
    # ✅ الوقف الجديد: 1% تحت القاع
    stop = row['Low'] * 0.99 
    range_hl = row['Range_HL']
    
    if range_hl <= 0 or pd.isna(range_hl) or entry <= stop:
        return None
    
    t1 = row['Low'] + 1.618 * range_hl
    t2 = row['Low'] + 2.618 * range_hl
    
    # ✅ متوسط R الحقيقي بعد التعديل
    expected_r = 0.196 
    risk_pct = (entry - stop) / entry * 100
    risk_abs = entry - stop
    cost_in_r = (cost_pct * entry) / risk_abs if risk_abs > 0 else 0
    net_r = expected_r - cost_in_r if risk_abs > 0 else 0
    
    return {
        'entry': round(entry, 2),
        'stop': round(stop, 2),
        't1': round(t1, 2),
        't2': round(t2, 2),
        'risk_pct': round(risk_pct, 2),
        'range_pct': round(row['Range_Pct'] * 100, 2),
        'net_r': round(net_r, 3),
        'expected_r': round(expected_r, 3)
    }

@st.cache_data(ttl=1800, show_spinner=False)
def scan_market(tickers_tuple, min_range_pct, min_vol_ratio, signal_filter):
    tickers = list(tickers_tuple)
    progress = st.progress(0, text="⏳ جاري تحميل البيانات...")
    data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, progress=False, threads=True)
    results = []
    for i, ticker in enumerate(tickers):
        progress.progress((i+1)/len(tickers), text=f"🔍 فحص {ticker}... ({i+1}/{len(tickers)})")
        try:
            if ticker not in data.columns.levels[0]: continue
            df = data[ticker].dropna()
            if len(df) < 60: continue
            if df['Volume'].tail(30).mean() < 50000: continue
            
            df = build_strategy_features(df)
            if len(df) < 30: continue
            
            last = df.iloc[-1]
            if last['Is_Decision'] != 1: continue
            if last['Range_Pct'] * 100 < min_range_pct: continue
            if last['Vol_Ratio_EMA20'] < min_vol_ratio: continue
            if signal_filter != "الكل" and signal_filter not in last['Signal_Type']: continue
            
            plan = calculate_trade_plan(last)
            if plan is None: continue
            
            if plan['net_r'] >= 0.4:
                quality = "🥇 ممتاز"
            elif plan['net_r'] >= 0.2:
                quality = "🥈 جيد"
            elif plan['net_r'] >= 0:
                quality = "🥉 مقبول"
            else:
                quality = "⚠️ ضعيف"
                
            results.append({
                'السهم': ticker.replace('.CA',''),
                'الجودة': quality,
                'الإشارة': last['Signal_Type'],
                'السعر': round(last['Close'], 2),
                'الدخول': plan['entry'],
                'الوقف': plan['stop'],
                'الهدف 1': plan['t1'],
                'الهدف 2': plan['t2'],
                'المخاطرة %': plan['risk_pct'],
                'المدى %': plan['range_pct'],
                'Net R': plan['net_r']
            })
        except:
            continue
    progress.empty()
    return pd.DataFrame(results)

st.sidebar.header("⚙️ الإعدادات")
mode = st.sidebar.radio("الوضع:", ["🎯 مسح السوق", "📈 تحليل سهم واحد"])

if mode == "🎯 مسح السوق":
    st.subheader("🎯 مسح السوق - الاستراتيجية الفائزة")
    st.caption(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.sidebar.markdown("### 🎨 Preset")
    preset = st.sidebar.selectbox("اختر:", 
        ["⚖️ متوازن (موصى به)", "🛡️ محافظ (جودة عالية)", "⚡ استكشافي", "⚙️ مخصص"])

    st.sidebar.markdown("### 🎚️ فلاتر الجودة")

    # القيم الافتراضية الجديدة
    default_range = 4.0
    default_vol = 1.5

    # تعديل القيم حسب الـ Preset المختار
    if preset == "🛡️ محافظ (جودة عالية)":
        default_range = 5.0
        default_vol = 1.8
    elif preset == "⚖️ متوازن (موصى به)":
        default_range = 4.0
        default_vol = 1.5
    elif preset == "⚡ استكشافي":
        default_range = 3.0
        default_vol = 1.0

    min_range_pct = st.sidebar.slider("أدنى مدى الشمعة %", 1.0, 8.0, default_range, 0.5,
        help="القيمة الموصى بها: 4% — كل ما زاد، كل ما الجودة أعلى")
    min_vol_ratio = st.sidebar.slider("أدنى نسبة فوليوم (vs EMA20)", 0.5, 3.0, default_vol, 0.1,
        help="القيمة الموصى بها: 1.5 — كل ما زاد، كل ما الجودة أعلى")
    
    signal_filter = st.sidebar.selectbox("نوع الإشارة:", 
        ["الكل", "Shakeout", "Climax", "Master", "Critical Vol"])
        
    if st.button("🚀 ابدأ المسح", type="primary", use_container_width=True):
        with st.spinner("جاري المسح..."):
            results_df = scan_market(tuple(EGX_TICKERS), min_range_pct, min_vol_ratio, signal_filter)
            
        if results_df.empty:
            st.warning("⚠️ مفيش إشارات بالمواصفات دي. جرب تخفف الفلاتر أو استخدم Preset (⚡ استكشافي).")
        else:
            results_df = results_df.sort_values('Net R', ascending=False).reset_index(drop=True)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("عدد الإشارات", len(results_df))
            col2.metric("أعلى Net R", f"+{results_df['Net R'].max():.3f}R")
            col3.metric("متوسط Net R", f"+{results_df['Net R'].mean():.3f}R")
            col4.metric("أقل مخاطرة", f"{results_df['المخاطرة %'].min():.2f}%")
            
            st.divider()
            st.subheader(f"✅ {len(results_df)} سهم عليهم إشارات:")
            
            for _, row in results_df.iterrows():
                with st.expander(f"**{row['السهم']}** — {row['الإشارة']} — {row['الجودة']} — Net R: +{row['Net R']:.3f}", 
                                expanded=(row.name < 3)):
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("السعر الحالي", row['السعر'])
                    c2.metric("الدخول", row['الدخول'])
                    c3.metric("الوقف", row['الوقف'])
                    c4.metric("الهدف 1 (50%)", row['الهدف 1'])
                    c5.metric("الهدف 2 (50%)", row['الهدف 2'])
                    c6.metric("Net R", f"+{row['Net R']:.3f}")
                    
                    st.caption(f"**المخاطرة:** {row['المخاطرة %']}% | **المدى:** {row['المدى %']}% | **التفعيل:** اختراق {row['الدخول']} | **الإبطال:** كسر {row['الوقف']}")
                    
                    progress_val = min(100, max(0, row['Net R'] * 200))
                    st.progress(progress_val / 100)
                    
            st.divider()
            with st.expander("📋 جدول مختصر (Excel-style)"):
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                csv = results_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 تنزيل CSV", csv, 
                    f"signals_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
            st.caption("📌 Win Rate 74% | Avg R +0.196R | 1,347 صفقة تاريخية")

else:
    ticker = st.sidebar.text_input("رمز السهم:", value="COMI.CA")
    if st.sidebar.button("🔍 تحليل", use_container_width=True):
        with st.spinner('جاري التحليل...'):
            df_raw = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
            if df_raw.empty:
                st.error("❌ مفيش بيانات.")
            else:
                df = build_strategy_features(df_raw)
                last = df.iloc[-1]
                plan = calculate_trade_plan(last) if last['Is_Decision'] == 1 else None
                
                if last['Is_Decision'] == 1 and plan:
                    st.success(f"🎯 **{last['Signal_Type']}** — Net R: +{plan['net_r']:.3f}")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("السعر", round(last['Close'], 2))
                    c2.metric("الدخول", plan['entry'])
                    c3.metric("الوقف", plan['stop'])
                    c4.metric("T1 (1.618)", plan['t1'])
                    c5.metric("T2 (2.618)", plan['t2'])
                    st.info(f"**الخطة:** ادخل عند اختراق {plan['entry']} | الوقف تحت {plan['stop']} | T1 عند {plan['t1']} (بيع 50% + نقل الوقف للدخول) | T2 عند {plan['t2']}")
                else:
                    st.info("ℹ️ مفيش إشارة على آخر شمعة.")
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                                     row_heights=[0.7, 0.3],
                                     subplot_titles=("السعر مع الإشارات", "الفوليوم"))
                
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                    low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
                
                masters = df[df['Is_Master']==1]
                shakeouts = df[df['Is_Shakeout']==1]
                climaxes = df[df['Is_Climax']==1]
                
                fig.add_trace(go.Scatter(x=masters.index, y=masters['High']+0.5, mode='markers',
                    marker=dict(symbol='star', size=12, color='gold'), name='Master'), row=1, col=1)
                fig.add_trace(go.Scatter(x=shakeouts.index, y=shakeouts['Low']-0.5, mode='markers',
                    marker=dict(symbol='triangle-up', size=14, color='cyan'), name='Shakeout'), row=1, col=1)
                fig.add_trace(go.Scatter(x=climaxes.index, y=climaxes['Low']-0.5, mode='markers',
                    marker=dict(symbol='triangle-up', size=14, color='magenta'), name='Climax'), row=1, col=1)
                
                if plan:
                    for level, price, color in [('Entry', plan['entry'], 'blue'),
                                                  ('Stop', plan['stop'], 'red'),
                                                  ('T1', plan['t1'], 'green'),
                                                  ('T2', plan['t2'], 'darkgreen')]:
                        fig.add_hline(y=price, line_dash="dash", line_color=color,
                            annotation_text=f"{level}: {price}", row=1, col=1)
                            
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume',
                    marker_color=['green' if c > o else 'red' for c, o in zip(df['Close'], df['Open'])]),
                    row=2, col=1)
                    
                fig.add_trace(go.Scatter(x=df.index, y=df['Vol_EMA20'], name='Vol EMA20',
                    line=dict(color='orange', width=2)), row=2, col=1)
                    
                fig.update_layout(height=750, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

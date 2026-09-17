# spc_acceptance_visual_v3.py
"""
验收控制线 + 传统SPC控制线 可视化计算器 (Web版)
修复：均值分布概率密度曲线只显示一半的问题
采用双Y轴方案，两条曲线均完整显示
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
import math
import pandas as pd

st.set_page_config(page_title="SPC vs 验收控制线", page_icon="📐", layout="wide")
st.title("📊 SPC 控制线 vs 验收控制线 (动态对比)")
st.markdown("作者：Mickey Min 版本v1.0 2026-09-11 电话15802128791")

# ================= 核心计算函数 =================
def calculate_acceptance_limits(usl, lsl, sigma_within, cpk_req, n_prime, z_pa):
    z_1p = 3 * cpk_req
    k_A = z_1p + z_pa / math.sqrt(n_prime)
    UCL_A = usl - k_A * sigma_within
    LCL_A = lsl + k_A * sigma_within
    center = (usl + lsl) / 2
    return {'UCL_A': UCL_A, 'LCL_A': LCL_A, 'k_A': k_A, 'z_1p': z_1p, 'center': center}

def calculate_spc_limits(process_mean, sigma_within, n_subgroup):
    sigma_xbar = sigma_within / np.sqrt(n_subgroup)
    ucl_spc = process_mean + 3 * sigma_xbar
    lcl_spc = process_mean - 3 * sigma_xbar
    return ucl_spc, lcl_spc, sigma_xbar

# ============================================
# 侧边栏参数
# ============================================
with st.sidebar:
    st.header("⚙️ 输入参数")
    st.subheader("📏 规格限")
    usl = st.number_input("上规格限 USL", value=50.1, step=0.01, format="%.4f")
    lsl = st.number_input("下规格限 LSL", value=49.9, step=0.01, format="%.4f")
    if usl <= lsl:
        st.error("⚠️ USL 必须大于 LSL")
    
    st.subheader("📊 过程参数")
    sigma_within = st.number_input("组内标准差 σ̂_within", value=0.012, min_value=0.0001, step=0.001, format="%.4f")
    process_mean = st.number_input("过程均值 X̄", value=50.0, step=0.01, format="%.4f")
    cpk_req = st.number_input("要求的最小 Cpk", value=1.33, min_value=0.67, max_value=2.0, step=0.01)
    
    st.subheader("🔢 抽样参数")
    n_prime = st.number_input("子组大小 n'", value=5, min_value=2, max_value=20, step=1)
    confidence = st.selectbox(
        "置信水平 P_A",
        options=["95.45% (z=2.00)", "99.00% (z=2.576)", "99.73% (z=3.00)"],
        index=0
    )
    z_pa = float(confidence.split("z=")[1].replace(")", ""))

# ============================================
# 主区域
# ============================================
if usl > lsl and sigma_within > 0:
    result = calculate_acceptance_limits(usl, lsl, sigma_within, cpk_req, n_prime, z_pa)
    ucl_spc, lcl_spc, sigma_xbar = calculate_spc_limits(process_mean, sigma_within, n_prime)
    
    ppk_upper = (usl - process_mean) / (3 * sigma_within)
    ppk_lower = (process_mean - lsl) / (3 * sigma_within)
    ppk = min(ppk_upper, ppk_lower)
    
    # ================= 概率密度数据 =================
    # 单值分布
    x_single = np.linspace(min(lsl, process_mean - 4*sigma_within), 
                           max(usl, process_mean + 4*sigma_within), 1000)
    y_single = norm.pdf(x_single, process_mean, sigma_within)
    
    # 均值分布 (完整曲线，从0开始)
    x_mean = np.linspace(process_mean - 5*sigma_xbar, process_mean + 5*sigma_xbar, 1000)
    y_mean = norm.pdf(x_mean, process_mean, sigma_xbar)
    
    # ================= 绘图 =================
    fig = go.Figure()
    
    # ---- 规格限 (红色实线) ----
    fig.add_trace(go.Scatter(
        x=[lsl, lsl], y=[0, 1.1], mode='lines',
        line=dict(color='red', width=3), name=f'LSL ({lsl:.3f})',
        yaxis='y1'
    ))
    fig.add_trace(go.Scatter(
        x=[usl, usl], y=[0, 1.1], mode='lines',
        line=dict(color='red', width=3), name=f'USL ({usl:.3f})',
        yaxis='y1'
    ))
    
    # ---- 验收控制线 (绿色实线) ----
    fig.add_trace(go.Scatter(
        x=[result['LCL_A'], result['LCL_A']], y=[0, 1.1], mode='lines',
        line=dict(color='green', width=3), name=f'LCL_A ({result["LCL_A"]:.3f})',
        yaxis='y1'
    ))
    fig.add_trace(go.Scatter(
        x=[result['UCL_A'], result['UCL_A']], y=[0, 1.1], mode='lines',
        line=dict(color='green', width=3), name=f'UCL_A ({result["UCL_A"]:.3f})',
        yaxis='y1'
    ))
    
    # ---- 传统 SPC 控制线 (蓝色虚线，基于均值分布) ----
    fig.add_trace(go.Scatter(
        x=[lcl_spc, lcl_spc], y=[0, 1.1], mode='lines',
        line=dict(color='blue', width=2, dash='dash'), name=f'LCL_SPC ({lcl_spc:.3f})',
        yaxis='y2'  # 用右轴，因为SPC线是基于均值分布的
    ))
    fig.add_trace(go.Scatter(
        x=[ucl_spc, ucl_spc], y=[0, 1.1], mode='lines',
        line=dict(color='blue', width=2, dash='dash'), name=f'UCL_SPC ({ucl_spc:.3f})',
        yaxis='y2'
    ))
    
    # ---- 单值分布曲线 (蓝色实线，左轴) ----
    fig.add_trace(go.Scatter(
        x=x_single, y=y_single / max(y_single),  # 归一化到1
        mode='lines', line=dict(color='blue', width=3),
        name='单值分布 N(μ, σ²)', yaxis='y1'
    ))
    
    # ---- 均值分布曲线 (蓝色虚线，右轴，完整曲线) ----
    fig.add_trace(go.Scatter(
        x=x_mean, y=y_mean / max(y_mean),  # 归一化到1
        mode='lines', line=dict(color='blue', width=2, dash='dash'),
        name='均值分布 N(μ, σ_x̄²)', yaxis='y2'
    ))
    
    # ---- Ppk 标注 ----
    fig.add_annotation(
        x=process_mean, y=1.05,
        text=f"Ppk = {ppk:.3f}",
        showarrow=False, font=dict(size=14, color="black"),
        xref='x', yref='y1'
    )
    
    # ---- 布局 ----
    fig.update_layout(
        title="两种控制线在概率密度图上的位置",
        xaxis=dict(title="测量值"),
        yaxis=dict(
            title="单值分布概率密度 (归一化)",
            range=[0, 1.15],
            showticklabels=False  # 隐藏刻度，因为已归一化
        ),
        yaxis2=dict(
            title="均值分布概率密度 (归一化)",
            range=[0, 1.15],
            overlaying='y',
            side='right',
            showticklabels=False
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # ================= 页面布局 =================
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 结果概览")
        st.metric("上验收限 UCL_A", f"{result['UCL_A']:.4f}",
                  delta=f"距 USL: {usl - result['UCL_A']:.4f}", delta_color="off")
        st.metric("下验收限 LCL_A", f"{result['LCL_A']:.4f}",
                  delta=f"距 LSL: {result['LCL_A'] - lsl:.4f}", delta_color="off")
        
        st.markdown("---")
        st.markdown(f"""
        **验收线参数:**
        - k_A = `{result['k_A']:.4f}`
        - z₁₋ₚ = `{result['z_1p']:.3f}`
        - z_PA/√n' = `{z_pa/math.sqrt(n_prime):.3f}`
        
        **SPC线参数:**
        - σ_x̄ = `{sigma_xbar:.4f}`
        - 中心: `{process_mean:.3f}`
        
        **过程能力:**
        - Ppk: `{ppk:.3f}`
        """)
        
        if ppk >= cpk_req:
            st.success(f"✅ Ppk ≥ {cpk_req} (满足要求)")
        elif ppk >= 1.0:
            st.warning(f"⚠️ Ppk < {cpk_req} (能力不足)")
        else:
            st.error("❌ Ppk < 1.0 (严重不足)")
        
        if lcl_spc < result['LCL_A'] or ucl_spc > result['UCL_A']:
            st.error("⚠️ SPC控制线超出验收线，过程'稳定'也可能产生不合格品！")
        else:
            st.info("✅ SPC控制线位于验收线内，过程受控")
    
    # ================= 计算过程 =================
    with st.expander("📝 查看计算过程", expanded=False):
        col_calc1, col_calc2 = st.columns(2)
        with col_calc1:
            st.markdown("**输入参数**")
            st.code(f"""
规格中心:      {result['center']:.4f}
规格宽度:      {usl - lsl:.4f}
Cpk 要求:      {cpk_req:.2f}
子组大小 n':   {n_prime}
组内标准差 σ̂:  {sigma_within:.4f}
置信水平:      {confidence}
            """)
        with col_calc2:
            st.markdown("**验收线计算步骤**")
            st.code(f"""
① z₁₋ₚ = 3 × Cpk = {result['z_1p']:.3f}
② z_PA = {z_pa:.3f}
③ k_A = z₁₋ₚ + z_PA/√n'
     = {result['z_1p']:.3f} + {z_pa:.3f}/{math.sqrt(n_prime):.3f}
     = {result['k_A']:.4f}
④ UCL_A = USL - k_A × σ̂ = {result['UCL_A']:.4f}
⑤ LCL_A = LSL + k_A × σ̂ = {result['LCL_A']:.4f}
            """)
    
    # ================= 敏感性分析 =================
    with st.expander("📊 参数敏感性分析", expanded=False):
        n_values = list(range(2, 13))
        batch_results = []
        for n in n_values:
            r = calculate_acceptance_limits(usl, lsl, sigma_within, cpk_req, n, z_pa)
            batch_results.append({
                "n'": n, "k_A": r['k_A'], "UCL_A": r['UCL_A'],
                "LCL_A": r['LCL_A'], "区间宽度": r['UCL_A'] - r['LCL_A']
            })
        df_batch = pd.DataFrame(batch_results)
        st.dataframe(df_batch.style.format({
            'k_A': '{:.4f}', 'UCL_A': '{:.4f}',
            'LCL_A': '{:.4f}', '区间宽度': '{:.4f}'
        }), use_container_width=True, hide_index=True)
        st.caption("💡 n' 越大，k_A 越小，控制限越靠近规格限")

else:
    if usl <= lsl:
        st.error("❌ 请确保 USL > LSL")
    if sigma_within <= 0:
        st.error("❌ 标准差必须大于 0")

st.markdown("---")
st.caption("""
**验收线公式 **:  
k_A = z₁₋ₚ + z_PA / √n'  
UCL_A = USL - k_A × σ̂_within  
LCL_A = LSL + k_A × σ̂_within  
其中: z₁₋ₚ = 3 × Cpk_req
""")
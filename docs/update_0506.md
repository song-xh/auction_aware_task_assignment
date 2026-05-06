~~~markdown
请帮我修改当前 RL-CAPA ablation reward curves 的 plotting 脚本，只调整绘图逻辑和视觉风格，不要重新训练模型，不要修改 reward 日志数据，不要修改 summary 计算逻辑，也不要额外改变 rl-capa-stage2 的 reward 偏移逻辑。当前 stage2 的 reward 修正如果已经存在，请保持不变。

目标：将当前图从普通 matplotlib 风格修改为更接近论文 reward curve 的风格，参考已有示例图：线条更细、更平滑，阴影更柔和，Times New Roman 字体，无标题，坐标轴和图例更适合论文排版。

具体修改要求如下：

1. 全局字体设置
在 plotting 脚本开头或绘图函数内部统一设置：

```python
plt.rcParams["font.family"] = ["Times New Roman"]
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.rm"] = "Times New Roman"
plt.rcParams["mathtext.it"] = "Times New Roman:italic"
plt.rcParams["mathtext.bf"] = "Times New Roman:bold"
~~~

同时保证坐标轴刻度、坐标轴标签、图例均使用 Times New Roman。

1. 标题
   删除图顶部标题：

- 不要再显示 `RL-CAPA Ablation Reward Curves`
- 如果代码里有 `ax.set_title(...)` 或 `plt.title(...)`，请删除或注释掉。

1. 横轴
   将横轴标签从 `Episode` 改为：

```python
ax.set_xlabel("Episodes", fontsize=18)
```

横轴范围必须严格从 0 到 2000，不要左右留白：

```python
ax.set_xlim(0, 2000)
ax.set_xticks([0, 500, 1000, 1500, 2000])
ax.margins(x=0)
```

确保保存后的图片中横轴从 0 开始，以 2000 结束，左右两边没有空白区域。

1. 纵轴
   将纵轴标签从 `Episode Reward` 或 `episodes reward` 改为：

```python
ax.set_ylabel("Total Reward", fontsize=18)
```

纵轴刻度不要显示 2200、2400、2600 这种原始值，而是显示 22、24、26、28、30、32，单位为 `10^2`。

推荐实现方式之一：绘图时将 reward 数值除以 100：

```python
plot_y = reward_values / 100.0
plot_lower = lower_bound / 100.0
plot_upper = upper_bound / 100.0
```

然后设置：

```python
ax.set_yticks([22, 24, 26, 28, 30, 32])
```

并在纵轴左上角标注单位：

```python
ax.text(
    0.0, 1.01, r"$\times 10^2$",
    transform=ax.transAxes,
    ha="left",
    va="bottom",
    fontsize=14
)
```

注意：

- 不要把 y 轴 label 改成 `Total Reward (×10^2)`，我希望 label 只显示 `Total Reward`。
- 单位 `×10^2` 单独显示在坐标轴左上角，效果类似参考图中的 `1e5` 标注。
- y 轴范围可以根据数据自动调整，但建议保证曲线完整显示，并使 tick 为 `[22, 24, 26, 28, 30, 32]`。例如：

```python
ax.set_ylim(20.5, 32.2)
```

如果实际曲线略高或略低，可以微调 ylim，但 tick 仍保持 22、24、26、28、30、32 的形式。

1. 颜色、线条和阴影风格
   请模仿参考图的论文风格：

- 线条不要太粗，建议 `linewidth=1.8` 或 `2.0`
- 阴影不要太深，建议 `alpha=0.16` 到 `0.22`
- 阴影应是平滑曲线周围的置信带/波动带，而不是过于突出的峰值效果
- 保留三条曲线：
  - `rl-capa`
  - `rl-capa-stage1`
  - `rl-capa-stage2`

建议颜色如下，可以根据 matplotlib 默认 tab 色系略作调整，但要保持论文图的柔和风格：

```python
colors = {
    "rl-capa": "#1f77b4",        # blue
    "rl-capa-stage1": "#ff7f0e", # orange
    "rl-capa-stage2": "#2ca02c", # green
}
```

绘制时建议：

```python
ax.plot(episodes, mean_curve, color=color, linewidth=1.8, label=label)
ax.fill_between(episodes, lower_curve, upper_curve, color=color, alpha=0.18, linewidth=0)
```

如果当前代码已经有平滑窗口和 std/sem 阴影，请只调整视觉参数，不要改变统计含义。若阴影过宽，可以使用标准误差 sem 或适度缩小显示带，但必须在代码注释中说明，例如：

```python
# The shaded area visualizes the smoothed variability band for readability.
```

1. 平滑逻辑
   保持当前 reward curve 的平滑逻辑。如果当前曲线仍然有过多尖峰，请检查是否使用了 rolling mean / moving average。建议使用统一平滑窗口，例如：

```python
smooth_window = 25
```

或沿用当前已有窗口。不要引入过强平滑，避免改变趋势。目标是得到类似参考图的平滑主曲线 + 柔和阴影，而不是尖锐波动曲线。

1. 图例
   图例风格模仿参考图：

- 使用 Times New Roman
- 放在图内，优先放在下方中间，避免遮挡主趋势：

```python
ax.legend(
    loc="lower center",
    ncol=3,
    frameon=False,
    fontsize=14
)
```

如果遮挡早期曲线，则可以改为 `loc="upper left"`，但优先尝试 `lower center`。
图例文本保持：

- `rl-capa`
- `rl-capa-stage1`
- `rl-capa-stage2`

1. 网格、边框和刻度
   整体风格要接近论文图：

- 使用浅灰色网格
- 坐标轴边框清晰但不要太粗
- 刻度字号适合论文图

建议：

```python
ax.grid(True, color="#b0b0b0", alpha=0.25, linewidth=0.8)
ax.tick_params(axis="both", which="major", labelsize=16, width=1.0, length=4)
for spine in ax.spines.values():
    spine.set_linewidth(1.0)
```

1. 图片尺寸和保存
   图片比例应适合论文单栏或双栏展示。建议使用：

```python
fig, ax = plt.subplots(figsize=(7.2, 4.2))
```

保存时同时输出 PNG 和 PDF：

```python
plt.tight_layout()
fig.savefig(output_png_path, dpi=300, bbox_inches="tight")
fig.savefig(output_pdf_path, bbox_inches="tight")
```

1. 检查点
   修改完成后请运行 plotting 脚本并确认：

- 图顶部没有标题
- 横轴标签是 `Episodes`
- 横轴刻度是 `0, 500, 1000, 1500, 2000`
- 横轴严格从 0 开始，到 2000 结束，左右没有空白
- 纵轴标签是 `Total Reward`
- 纵轴 tick 显示为 `22, 24, 26, 28, 30, 32`
- 左上角显示 `×10^2`
- 字体为 Times New Roman
- 曲线颜色、线宽、阴影透明度接近参考论文图
- 图例风格简洁，不遮挡主要曲线
- 不修改训练日志、reward 原始数据和 summary 计算逻辑

请最后输出：

1. 修改了哪些文件；
2. 关键 plotting 参数；
3. 生成的图片路径；
4. 简要说明是否通过上述检查点。

这是论文 rebuttal/修订实验图，只做 publication-quality plotting refinement，不做算法逻辑修改
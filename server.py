import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any

# 创建 FastAPI 实例
app = FastAPI(title="Eino Agent Simulation Service")


# ================== 数据模型定义 (对应 Go 结构体) ==================

# 对应 Go: MassingToolInput
class MassingToolInput(BaseModel):
    index: int = Field(default=0, description="体量模版编号")
    building_area: Optional[float] = Field(default=None, alias="building_area")

    # 修改这里：将 default=None 改为 default=5 (或其他合理的整数)
    floor_count: Optional[int] = Field(default=5, alias="floor_count")
    plot_ratio: Optional[float] = Field(default=2.0, alias="plot_ratio")


# 对应 Go: MassingToolOutput
class MassingToolOutput(BaseModel):
    geometry_data: str
    description: str
    status: str


# 对应 Go: SimulationInput
class SimulationInput(BaseModel):
    massing_data: str = Field(default="", alias="massing_data")
    context_data: str = Field(default="", alias="context_data")
    sim_type: str = Field(default="", alias="sim_type")


# 对应 Go: SimulationToolOutput
class SimulationToolOutput(BaseModel):
    is_success: bool = Field(alias="is_success")
    heatmap_image: str = Field(alias="heatmap_image")  # Base64 字符串
    metrics: Dict[str, float]
    summary: str


# ================== 业务逻辑接口 ==================

@app.get("/")
def health_check():
    return {"status": "running", "message": "Simulation Service is Ready on Windows"}


# 1. 体量生成接口
# Path: /api/massing/generate
@app.post("/api/massing/generate", response_model=MassingToolOutput)
async def generate_massing(input_data: MassingToolInput):
    print(f"[收到请求] 体量生成: Index={input_data.index}, Area={input_data.building_area}")

    # 【修复】给默认值，防止 None * 4 报错
    safe_floor_count = input_data.floor_count if input_data.floor_count is not None else 5
    safe_plot_ratio = input_data.plot_ratio if input_data.plot_ratio is not None else 2.5

    # 模拟返回数据
    mock_geometry = f"{{ 'type': 'Mesh', 'vertices': {safe_floor_count * 4} }}"

    return MassingToolOutput(
        geometry_data=mock_geometry,
        description=f"已生成方案，层数: {safe_floor_count}, 容积率: {safe_plot_ratio}",
        status="completed"
    )

# 通用的模拟处理函数 (模拟耗时操作和结果生成)
def run_simulation_logic(sim_type: str, massing: str) -> SimulationToolOutput:
    # 这是一个占位符 Base64 图片 (一个红点的 png)
    mock_base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

    if sim_type == "wind":
        return SimulationToolOutput(
            is_success=True,
            heatmap_image=mock_base64_image,
            metrics={"max_wind_speed": 5.4, "avg_wind_speed": 2.1},
            summary="风环境分析完成：场地内部通风良好，但在东北角存在局部静风区。"
        )
    elif sim_type == "sunlight":
        return SimulationToolOutput(
            is_success=True,
            heatmap_image=mock_base64_image,
            metrics={"sunlight_hours": 4.5, "shadow_ratio": 0.3},
            summary="日照分析完成：大部分区域满足大寒日2小时日照标准。"
        )
    elif sim_type == "thermal":
        return SimulationToolOutput(
            is_success=True,
            heatmap_image=mock_base64_image,
            metrics={"avg_utci": 26.5, "comfort_hours": 12.0},
            summary="热舒适分析完成：夏季室外热舒适度较低，建议增加遮阳。"
        )
    else:
        return SimulationToolOutput(
            is_success=False,
            heatmap_image="",
            metrics={},
            summary=f"未知的模拟类型: {sim_type}"
        )


# 2. 风环境模拟接口
@app.post("/api/sim/wind", response_model=SimulationToolOutput)
async def simulate_wind(input_data: SimulationInput):
    print(f"[收到请求] 风环境模拟: Length={len(input_data.massing_data)}")
    # 尽管 Go 发送了 sim_type，我们也可以强制视为 wind，或者做校验
    return run_simulation_logic("wind", input_data.massing_data)


# 3. 日照模拟接口
@app.post("/api/sim/sunlight", response_model=SimulationToolOutput)
async def simulate_sunlight(input_data: SimulationInput):
    print(f"[收到请求] 日照模拟")
    return run_simulation_logic("sunlight", input_data.massing_data)


# 4. 热舒适模拟接口
@app.post("/api/sim/thermal", response_model=SimulationToolOutput)
async def simulate_thermal(input_data: SimulationInput):
    print(f"[收到请求] 热舒适模拟")
    return run_simulation_logic("thermal", input_data.massing_data)


if __name__ == "__main__":
    # 重要：host="0.0.0.0" 允许局域网访问（Mac 才能访问到 Windows）
    # port=8000 对应 Go 代码中的端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import base64
import json
import utils

app = FastAPI()


# ====================
# 数据模型定义 (Pydantic)
# 对应 Go 端的 struct
# ====================

class MassingToolInput(BaseModel):
    # 对应 Go: Index int
    index: int = Field(0, alias="index")
    # 对应 Go: BuildingArea float64
    building_area: float = Field(..., alias="building_area")
    # 对应 Go: FloorCount int
    floor_count: int = Field(..., alias="floor_count")
    # 对应 Go: SizeX float64
    size_x: Optional[float] = Field(None, alias="size_x")
    # 对应 Go: SizeY float64
    size_y: Optional[float] = Field(None, alias="size_y")


class MassingToolOutput(BaseModel):
    geometry_data: str
    description: str
    status: str


class SimulationInput(BaseModel):
    # 对应 Go: MassingData string
    massing_data: str = Field(..., alias="massing_data")
    # 对应 Go: ContextData string
    context_data: str = Field(..., alias="context_data")
    # 对应 Go: SimType string
    sim_type: str = Field("sunlight", alias="sim_type")


class SimulationToolOutput(BaseModel):
    is_success: bool
    heatmap_image: str  # Base64 string
    metrics: Dict[str, float]
    summary: str


# ====================
# 辅助函数
# ====================

def encode_image_to_base64(image_path: str) -> str:
    """读取图片文件并转换为Base64字符串"""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return ""

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string


def get_gh_file_path(gh_name: str) -> str:
    """获取GH文件的绝对路径，确保和utils逻辑一致"""
    base_dir = os.path.dirname(os.path.realpath(__file__))
    return base_dir


# ====================
# 接口实现
# ====================

@app.post("/api/massing/generate", response_model=MassingToolOutput)
async def generate_massing(input_data: MassingToolInput):
    """
    体量生成接口
    对应 GH 文件: massing.gh
    """
    try:
        param_dict = {
            "massing_index": input_data.index,
            "floor_count": input_data.floor_count,
            "building_area": input_data.building_area,
            "size_x": 50.0,  # 示例默认值
            "size_y": 50.0  # 示例默认值
        }

        compute_result = utils.compute_with_input("massing.gh", param_dict)
        parsed_data = utils.parse_data(compute_result)

        geometry_list = parsed_data.get("massing", [])

        if not geometry_list:
            return MassingToolOutput(
                geometry_data="",
                description="生成失败：未收到几何数据返回",
                status="error"
            )

        geo_json_str = geometry_list[0] if isinstance(geometry_list[0], str) else json.dumps(geometry_list[0])

        return MassingToolOutput(
            geometry_data=geo_json_str,
            description=f"成功生成体量，方案索引: {input_data.index}",
            status="success"
        )

    except Exception as e:
        print(f"Massing generation error: {str(e)}")
        return MassingToolOutput(
            geometry_data="",
            description=f"服务端内部错误: {str(e)}",
            status="error"
        )


@app.post("/api/sim/sunlight", response_model=SimulationToolOutput)
async def simulate_sunlight(input_data: SimulationInput):
    """
    日照模拟接口
    对应 GH 文件: sunlight.gh
    """
    try:
        output_filename = "sunlight.png"
        output_path = os.path.join(get_gh_file_path(""), output_filename)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        param_dict = {
            "massing_data": input_data.massing_data,
            "context_data": input_data.context_data,
            "image_output_path": output_path
        }

        print(f"Starting sunlight simulation, output target: {output_path}")
        compute_result = utils.compute_with_input("sunlight.gh", param_dict)
        parsed_data = utils.parse_data(compute_result)

        img_base64 = encode_image_to_base64(output_path)

        if not img_base64:
            return SimulationToolOutput(
                is_success=False,
                heatmap_image="",
                metrics={},
                summary="模拟完成但未找到生成的分析图，请检查GH文件是否正确导出了图片。"
            )

        metrics = {}
        if "average_hours" in parsed_data:
            val = parsed_data["average_hours"][0]
            metrics["average_hours"] = float(val) if val is not None else 0.0

        if not metrics:
            metrics = {"sunlight_hours_avg": 0.0}

        return SimulationToolOutput(
            is_success=True,
            heatmap_image=img_base64,
            metrics=metrics,
            summary="日照模拟成功完成"
        )

    except Exception as e:
        print(f"Simulation error: {str(e)}")
        return SimulationToolOutput(
            is_success=False,
            heatmap_image="",
            metrics={},
            summary=f"模拟过程发生异常: {str(e)}"
        )

@app.post("/api/sim/wind", response_model=SimulationToolOutput)
async def simulate_wind(input_data: SimulationInput):
    """
    风环境模拟接口 (CFD / Wind Tunnel)
    对应 GH 文件: wind.gh
    """
    try:
        output_filename = "wind.png"
        output_path = os.path.join(get_gh_file_path(""), output_filename)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        param_dict = {
            "massing_data": input_data.massing_data,
            "context_data": input_data.context_data,
            "image_output_path": output_path,
            "sim_type": "wind"
        }

        print(f"[Wind] Starting simulation, target: {output_path}")

        compute_result = utils.compute_with_input("wind.gh", param_dict)
        parsed_data = utils.parse_data(compute_result)

        img_base64 = encode_image_to_base64(output_path)
        if not img_base64:
            return SimulationToolOutput(
                is_success=False,
                heatmap_image="",
                metrics={},
                summary="风环境模拟完成，但未生成分析图 (wind_analysis.png missing)。"
            )

        # wind.gh 输出: max_wind_speed, avg_wind_speed, comfort_ratio
        metrics = {}

        if "max_wind_speed" in parsed_data and parsed_data["max_wind_speed"]:
            metrics["max_wind_speed"] = float(parsed_data["max_wind_speed"][0])

        if "avg_wind_speed" in parsed_data and parsed_data["avg_wind_speed"]:
            metrics["avg_wind_speed"] = float(parsed_data["avg_wind_speed"][0])

        return SimulationToolOutput(
            is_success=True,
            heatmap_image=img_base64,
            metrics=metrics,
            summary="风环境模拟成功"
        )

    except Exception as e:
        print(f"[Wind] Error: {str(e)}")
        return SimulationToolOutput(
            is_success=False,
            heatmap_image="",
            metrics={},
            summary=f"风模拟服务内部错误: {str(e)}"
        )

@app.post("/api/sim/thermal", response_model=SimulationToolOutput)
async def simulate_thermal(input_data: SimulationInput):
    """
    热舒适度模拟接口 (UTCI / PET)
    对应 GH 文件: thermal.gh
    """
    try:
        output_filename = "thermal.png"
        output_path = os.path.join(get_gh_file_path(""), output_filename)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        param_dict = {
            "massing_data": input_data.massing_data,
            "context_data": input_data.context_data,
            "image_output_path": output_path
        }

        print(f"[Thermal] Starting simulation, target: {output_path}")

        compute_result = utils.compute_with_input("thermal.gh", param_dict)
        parsed_data = utils.parse_data(compute_result)

        img_base64 = encode_image_to_base64(output_path)
        if not img_base64:
            return SimulationToolOutput(
                is_success=False,
                heatmap_image="",
                metrics={},
                summary="热舒适度模拟完成，但未生成分析图 (thermal_analysis.png missing)。"
            )

        # thermal.gh 输出: avg_utci (通用热气候指数), max_utci
        metrics = {}

        if "avg_utci" in parsed_data and parsed_data["avg_utci"]:
            metrics["avg_utci"] = float(parsed_data["avg_utci"][0])

        if "comfortable_hours" in parsed_data and parsed_data["comfortable_hours"]:
            metrics["comfortable_hours"] = float(parsed_data["comfortable_hours"][0])

        return SimulationToolOutput(
            is_success=True,
            heatmap_image=img_base64,
            metrics=metrics,
            summary="热舒适度模拟成功"
        )

    except Exception as e:
        print(f"[Thermal] Error: {str(e)}")
        return SimulationToolOutput(
            is_success=False,
            heatmap_image="",
            metrics={},
            summary=f"热模拟服务内部错误: {str(e)}"
        )

# ====================
# 启动入口
# ====================
if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
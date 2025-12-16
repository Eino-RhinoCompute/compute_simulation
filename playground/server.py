from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()


# 1. 定义接收数据的模型 (对应 Go 发送的 JSON)
class Item(BaseModel):
    name: str
    number: int


# 2. 定义接口路由
@app.post("/api/calc")
async def calculate(item: Item):
    print(f"[Windows] 收到 Go 的数据: name={item.name}, number={item.number}")

    # --- 模拟业务逻辑 ---
    greeting = f"Hello, {item.name}! From Windows FastAPI."
    result_val = item.number * 10  # 简单计算
    # ------------------

    # 直接返回字典，FastAPI 会自动转为 JSON
    return {
        "msg": greeting,
        "value": result_val,
        "status": "ok"
    }


if __name__ == "__main__":
    # host="0.0.0.0" 意味着允许局域网内其他机器(你的Mac)访问
    print("FastAPI 服务正在启动，监听 0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
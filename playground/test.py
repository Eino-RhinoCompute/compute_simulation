import compute_rhino3d.Util
import compute_rhino3d.Grasshopper as gh
import rhino3dm
import json
import os
from typing import Any

"""
该python文件需要和所要调用的gh文件位于同一文件目录下
"""
compute_rhino3d.Util.url = "http://localhost:6500/"
compute_rhino3d.Util.apiKey = ""

def compute_without_input(gh_script_name: str) -> json:
    """
    不需要数据读入的gh文件,输入参数列表为空
    return: rhino compute计算的结果,为json格式文件
    """
    file_directory = os.path.dirname(os.path.realpath(__file__))
    GrasshopperScript_filepath = os.path.join(file_directory, '../grasshopper', gh_script_name)

    if not os.path.exists(GrasshopperScript_filepath):
        GrasshopperScript_filepath = os.path.join(file_directory, gh_script_name)

    variable_trees = []
    result = gh.EvaluateDefinition(GrasshopperScript_filepath, variable_trees)
    return result


def compute_with_input(gh_script_name: str,param_dict: dict[str,Any]) -> json:
    """
    需要数据读入的gh文件,需要手动将变量添加到变量树中
    param_dict:键为gh中对应使用Get 电池的名称,值为需要为该电池传入的内容
    return: rhino compute计算的结果,为json格式文件
    """
    file_directory = os.path.dirname(os.path.realpath(__file__))
    GrasshopperScript_filepath = os.path.join(file_directory, '../grasshopper', gh_script_name)

    if not os.path.exists(GrasshopperScript_filepath):
        GrasshopperScript_filepath = os.path.join(file_directory, gh_script_name)
    variable_trees = []
    for key, value in param_dict.items():
        variable_tree = gh.DataTree(key)
        if isinstance(value,list):
            variable_tree.Append([0],[*value])
        else:  
            variable_tree.Append([0],[value])   
        variable_trees.append(variable_tree)

    result = gh.EvaluateDefinition(GrasshopperScript_filepath, variable_trees)
    return result


def parse_data(compute_result: json):
    """
    从rhino compute计算得出的结果中解析出具体的几何体或数值信息
    """
    values = compute_result["values"]
    parsed_data = {}
    for i in range(len(values)):
        param_name = values[i]["ParamName"]
        parsed_data[param_name] = []
        for j in values[i]['InnerTree']:
            branch = values[i]["InnerTree"][j]
            for k in range(len(branch)):
                data = branch[k]['data']
                parsed_data[param_name].append(data)
    return parsed_data


if __name__ == "__main__":
    # region 数据输入测试
    # 简单数值测试
    param_dict = {
        "value": 1
    }
    output = compute_with_input("sunlight.gh", param_dict)
    print(parse_data(output))
    # endregion

    # region 数据输出测试
    # output = compute_without_input("数据输出.gh")
    # print(output['values'])
    # endregion

    #region 数据交互测试
    # """
    # 如直接使用parse_data函数得到结果,确保数据输出的gh文件中输出电池的名称
    # 与读取数据的gh文件中的Get 电池名称一一对应
    # 如果名称不一致,可以先打印出values的值,然后按照如下方式手动对应
    # """
    # output = compute_without_input("数据输出.gh")
    # param_dict = parse_data(output)
    # print(param_dict)

    #region 手动对应数据
    # values = output["values"]   
    # param_dict = {
    #     "rectangle" : values[1]["InnerTree"]['{0}'][0]['data'],
    #     "door" : values[1]["InnerTree"]['{0}'][0]['data'],
    #     "window" : values[2]["InnerTree"]['{0}'][0]['data'],
    #     "bayWindows" : [values[3]["InnerTree"]['{0}'][0]['data'],
    #                     values[3]["InnerTree"]['{0}'][1]['data']]
    # }
    #endregion

    # result = compute_with_input("数据交互.gh", param_dict)
    # print(result["values"])
    # #region 解码为rhino3dm格式，写入rhino文件
    # data_to_decode = result['values'][0]['InnerTree']['{0}'][0]['data']
    # mesh = rhino3dm.CommonObject.Decode(json.loads(data_to_decode))
    # model = rhino3dm.File3dm()
    # model.Objects.AddMesh(mesh)
    # filename = 'mesh.3dm'
    # model.Write(filename) 
    #endregion
    #endregion
# 千帆 Function Calling 演示：ERNIE + Streamlit

本项目演示如何用百度千帆 ChatCompletion API 的函数调用（Function Calling）能力，让 ERNIE 大模型根据用户的自然语言自动选择并调用 Python 函数，再基于函数返回结果生成回答。界面使用 Streamlit 聊天组件，可以自由提问，也可以点击示例问题。

## 特性

- **聊天界面**：支持多轮对话，每次函数调用的名称、参数和返回值都可以展开查看。
- **5 个示例函数**：
  - `calculate`：安全地计算数学表达式（基于 AST，只允许数字和运算符）；
  - `get_current_temperature`：通过免费的 [Open-Meteo](https://open-meteo.com/) 查询城市实时气温，无需额外密钥；
  - `delivery_inquiry` / `delivery_order`：模拟外卖查询（按价格筛选）和下单；
  - `extract_employee_info`：从一句话中抽取员工信息并录入，录入结果以表格展示。
- **按名称传参**：模型返回的参数按名字传给函数，参数顺序变化或缺少可选参数都不会出错；参数错误会返回给模型而不是让应用崩溃。
- **可选模型**：ERNIE-3.5-8K / ERNIE-4.0-8K / ERNIE-Speed-8K。

## 安装

需要 Python 3.9+。

```bash
git clone https://github.com/lenkazuma/QF_FunctionCalling.git
cd QF_FunctionCalling
pip install -r requirements.txt
```

## 配置千帆凭证

在 [百度智能云千帆控制台](https://console.bce.baidu.com/qianfan/) 获取凭证，任选一种方式：

- 环境变量（推荐）：

  ```bash
  # 安全认证 Access Key / Secret Key
  export QIANFAN_ACCESS_KEY=your-access-key
  export QIANFAN_SECRET_KEY=your-secret-key
  # 或应用 API Key / Secret Key
  export QIANFAN_AK=your-api-key
  export QIANFAN_SK=your-secret-key
  ```

- 运行后在页面侧边栏填写 AK / SK（只保存在当前会话中）。

## 运行

```bash
streamlit run QFfunction.py
```

浏览器打开 <http://localhost:8501>，输入问题或点击侧边栏的示例问题，例如：

- 114514+973580等于多少？
- 南京路街道附近50元以内的午餐有哪些推荐？
- 新入职员工李红在HR部门工作，她有研究生文凭。她的工号是918604。
- 深圳市今天气温如何？

## 项目结构

```
├── QFfunction.py   # Streamlit 聊天界面
├── agent.py        # 模型 ↔ 函数调用循环、千帆客户端封装
├── tools.py        # 函数实现、JSON Schema 定义与调度
└── tests/          # pytest 测试（不需要千帆凭证）
```

## 工作流程

1. 用户提问，连同函数的 JSON Schema 一起发送给 ERNIE；
2. 若模型返回 `function_call`，`tools.dispatch` 按名称执行对应函数；
3. 函数结果以 `role: function` 消息追加到对话中再次请求模型；
4. 模型返回最终文字回答（单轮最多连续调用 3 次函数，防止死循环）。

## 测试

```bash
pip install pytest
pytest -q
```

## 许可证

本项目遵循 MIT 许可证，详见 [LICENSE](LICENSE)。

# BehVault — 基于行为口令与国密SM4的智能保密文件库

> Behavioral Password + SM4 Encrypted File Vault

## 项目简介

BehVault 将击键动力学行为认证与国密SM4文件加密相结合，构建多因素智能保密文件库。用户登录不仅验证密码，还分析打字节奏特征（Hold Time、Flight Time等），输出0~100连续风险评分。认证通过后才能访问SM4加密的文件库。

### 六大创新点

1. **风险评分系统** — 输出连续风险值(0~100)，非二元通过/失败
2. **连续认证** — 登录后持续监测行为，异常时自动锁定文件库
3. **行为可视化** — Hold Time/Flight Time曲线，本人vs攻击者对比图
4. **自适应学习** — EMA + 滑动窗口更新行为模板，降低长期误拒率
5. **SM4保密文件库** — 自实现SM4-CBC，文件名+内容均加密
6. **攻击模拟评测** — 密码泄露/模仿/随机攻击，输出FAR/FRR/EER指标

## 技术栈

| 模块 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| GUI | Tkinter |
| 数据分析 | NumPy, Pandas |
| 机器学习 | scikit-learn (KNN) |
| 数据库 | SQLite3 |
| 可视化 | Matplotlib |
| 密码学 | 自实现SM4, gmssl (验证) |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

## 项目结构

```
BehVault/
├── main.py                 # 入口文件
├── requirements.txt        # Python依赖
├── src/
│   ├── database/           # SQLite数据库层
│   ├── auth/               # 击键捕获 + 特征提取
│   ├── crypto/             # SM4自实现 + 文件加解密
│   ├── ml/                 # KNN模型 + 风险评分 + 自适应学习
│   ├── vault/              # 加密文件库管理
│   ├── viz/                # Matplotlib可视化
│   ├── services/           # 业务逻辑服务层
│   └── gui/                # Tkinter图形界面
├── tests/                  # 单元测试
├── data/                   # 数据库文件
├── report/                 # 竞赛报告
└── screenshots/            # 截图
```

## 架构设计

```
GUI (Tkinter) → Service → Auth/ML/Crypto → Database (SQLite3)
```

GUI层严禁直接访问数据库、密码算法或ML模型。

## 运行测试

```bash
python tests/test_sm4.py
python tests/test_auth.py
python tests/test_ml.py
python tests/test_vault.py
```

## SM4验证

自实现SM4通过GB/T 32907-2016官方测试向量验证：
- `key = 0123456789abcdeffedcba9876543210`
- `plain = 0123456789abcdeffedcba9876543210`
- `cipher = 681edf34d206965e86b3e94f536e4246`

## 许可证

本项目为学术/竞赛用途。

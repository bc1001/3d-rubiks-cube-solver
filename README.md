### 📄 `README.md` 完整内容：

```markdown
# 🧩 3D Interactive Rubik's Cube Solver (3D 交互式魔方还原求解器)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)
![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)
![SQLite](https://img.shields.io/badge/SQLite-3.x-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个基于 **Flask + Three.js + Kociemba 算法** 的全栈 3D 交互式魔方还原求解系统。支持网页端 3D 自由旋转染色、随机打乱动画、一键解魔方、分步/自动播放还原动画，以及基于 IP 隔离的 2D 展开图历史记录管理。

---

## 🌟 核心功能特色

- 🎨 **3D 交互式自由染色**: 基于 WebGL 与 Three.js 搭建 3D 网页魔方，支持鼠标拖拽旋转视角与射线检测（Raycaster）精确点击贴纸染色。
- 🚀 **高效求解算法**: 后端集成经典的 **Kociemba 两步法算法（Two-Phase Algorithm）**，能在数毫秒内计算出最优还原方案（通常小于 20 步）。
- 🌪 **智能随机打乱 & 模式锁定**: 
  - 支持对完全还原的魔方进行 20 步流畅的高速随机打乱动画；
  - 内置**状态机模式控制**，打乱后自动锁定染色面板，防止非法修改，必须“重置”或“求解”。
- 📜 **IP 隔离历史记录与 2D 十字展开图 Preview**:
  - 后端采用 SQLite 数据库存储用户的打乱与求解历史；
  - 根据访问者 IP 严格隔离数据（仅查看/管理自己的记录）；
  - 前端基于 CSS Grid 实时渲染直观的 **2D T型魔方展开图（Cube Net）**，支持单条删除与一键清空。
- 🎬 **平滑 3D 旋转动画引擎**:
  - 自研 3D 挂载点（Pivot）旋转与 Cubic-Ease-Out 缓动动画；
  - 支持“上一步/下一步”分步探索、自动播放/暂停、动画重新播放；
  - 支持 **🐢 -> 🐇 速度滑动调节**。
- 🔀 **配色切换与安全校验**: 支持中心块左右配色（橙/红）一键对调，自动校验“已还原”状态避免无用计算。

---

## 🛠️ 技术栈

### 后端 (Backend)
- **Framework**: Python / Flask
- **Algorithm**: `kociemba` (魔方还原求解核心)
- **Database**: SQLite3 (原生嵌入式数据库)

### 前端 (Frontend)
- **3D Engine**: Three.js (r128) + OrbitControls
- **UI & Layout**: HTML5, CSS3 (Flexbox & CSS Grid), ES6+ JavaScript
- **Communication**: Fetch API (Async RESTful JSON)

---

## 📁 项目目录结构

```text
rubiks-cube-solver/
│
├── app.py                      # Flask 后端路由、数据库 CRUD 与 API 逻辑
├── rubiks_history.db           # SQLite 数据库文件 (首次运行自动生成)
│
├── templates/                  # HTML 模板目录
│   └── index.html              # 前端 DOM 结构与 UI 面板
│
└── static/                     # 静态资源目录
    ├── css/
    │   └── style.css           # 界面设计与 2D 展开图 CSS 样式
    └── js/
        └── main.js             # Three.js 3D 场景、动画引擎与交互逻辑
```

---

## 🚀 快速开始

### 1. 克隆本项目
```bash
git clone https://github.com/your-username/rubiks-cube-solver.git
cd rubiks-cube-solver
```

### 2. 安装依赖
请确保您的电脑已安装 Python 3.8+。在项目根目录下运行：
```bash
pip install Flask kociemba
```

### 3. 运行程序
```bash
python app.py
```

### 4. 浏览器访问
打开浏览器，访问：`http://127.0.0.1:5000` 即可开始使用！

---

## 💡 技术难点与亮点解析

1. **基于世界矩阵法向量 (Normal Matrix) 的 3D 状态提取**:
   在 3D 空间中，方块经过多次旋转后其本地坐标轴（Local Axes）会发生偏移。本项目摒弃了传统的本地索引读取，改用物理网格的世界法向量（World Normal Vectors）与全局轴向（Up, Down, Left, Right, Front, Back）进行比对，保证无论打乱经过多少次三维旋转，提取出的 54-色块字符串 100% 精确合法。

2. **浮点数漂移修复 (Floating Point Error Mitigation)**:
   在 Three.js 连续旋转中，多次三角函数计算会导致网格坐标出现形如 `0.9999994` 的微小误差。项目在每次旋转动画结束时，自动对比并四舍五入对齐 (`Math.round`) 坐标和旋转角，彻底解决多次旋转后魔方“变形分裂”的 BUG。

3. **动画快照防丢机制 (Snapshot Restoration)**:
   求解前会深度复制保存当前魔方所有方块的 3D 位置与三维旋转欧拉角（Euler Angles）。播放完还原动画后，点击“重新开始动画”可瞬间无缝归位至最原始的打乱状态。

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 协议开源，欢迎自由 fork、修改与提交 Pull Request！
```

---

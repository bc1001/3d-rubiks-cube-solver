import sqlite3
from flask import Flask, render_template_string, request, jsonify
import kociemba

app = Flask(__name__)
DB_FILE = 'rubiks_history.db'

# ==================== 数据库初始化 ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            cube_state TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>3D 动画交互魔方还原求解器</title>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    
    <style>
        body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #fff; overflow-x: hidden; }
        #container { width: 100vw; height: 48vh; position: relative; }
        #ui-panel { padding: 15px; background: #1e1e1e; box-shadow: 0 -2px 10px rgba(0,0,0,0.5); min-height: 47vh; }
        .palette { display: flex; justify-content: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
        .color-btn { width: 42px; height: 42px; border-radius: 50%; border: 3px solid #444; cursor: pointer; transition: transform 0.2s, border-color 0.2s; display: flex; align-items: center; justify-content: center; font-size: 18px; user-select: none; }
        .color-btn.active { transform: scale(1.18); border-color: #fff; box-shadow: 0 0 10px rgba(255,255,255,0.8); }
        .controls-row { display: flex; justify-content: center; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
        .btn { padding: 8px 16px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; background: #007bff; color: white; transition: background 0.2s; }
        .btn:hover { background: #0056b3; }
        .btn-swap { background: #17a2b8; } .btn-swap:hover { background: #138496; }
        .btn-reset { background: #6c757d; } .btn-reset:hover { background: #5a6268; }
        .btn-play { background: #28a745; } .btn-play:hover { background: #218838; }
        .btn-step { background: #ffc107; color: #111; } .btn-step:hover { background: #e0a800; }
        .btn-scramble { background: #dc3545; } .btn-scramble:hover { background: #c82333; }
        .btn-history { background: #8e44ad; } .btn-history:hover { background: #732d91; }
        .btn-danger-sm { background: #d9534f; padding: 3px 8px; font-size: 11px; border-radius: 4px; border:none; color:white; cursor:pointer; }
        .btn-danger-sm:hover { background: #c9302c; }
        
        #anim-bar { display: none; background: #2a2a2a; padding: 10px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #444; }
        #status-overlay { position: absolute; top: 15px; left: 15px; background: rgba(0,0,0,0.75); padding: 10px 15px; border-radius: 6px; font-size: 14px; z-index: 10; border: 1px solid #555; }
        #instructions { text-align: center; color: #aaa; margin-bottom: 10px; font-size: 13px; }
        
        /* 结果与历史记录通用面板 */
        .panel-box { max-width: 950px; margin: 0 auto 15px auto; padding: 15px; background: #252525; border-radius: 8px; display: none; }
        
        /* 还原步骤网格 */
        .steps-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; margin-top: 10px; max-height: 200px; overflow-y: auto; padding: 5px; }
        .step-card { background: #333; padding: 8px; border-radius: 5px; text-align: center; border: 2px solid transparent; cursor: pointer; transition: 0.2s; }
        .step-card.active { border-color: #007bff; background: #3d3d3d; }
        .step-card:hover { background: #444; }
        .step-code { font-size: 18px; font-weight: bold; color: #FFD700; }
        .step-desc { font-size: 11px; color: #ccc; margin-top: 2px; }

        /* 历史记录展开图网格 */
        .history-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 15px; margin-top: 10px; max-height: 280px; overflow-y: auto; padding: 5px; }
        .history-card { background: #2e2e2e; border: 1px solid #444; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; align-items: center; position: relative; transition: transform 0.2s; }
        .history-card:hover { transform: translateY(-2px); border-color: #8e44ad; }
        
        /* 2D 魔方展开图 (Cube Net) CSS Grid */
        .cube-net-container { display: grid; grid-template-columns: repeat(4, 32px); grid-template-rows: repeat(3, 32px); gap: 2px; background: #111; padding: 4px; border-radius: 4px; margin: 8px 0; }
        .face-grid { display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 1px; background: #222; width: 100%; height: 100%; }
        .sticker-mini { width: 100%; height: 100%; border-radius: 1px; }

        #toast { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(220,53,69,0.9); padding: 10px 20px; border-radius: 5px; display: none; z-index: 100; font-weight: bold; }
    </style>
</head>
<body>

    <div id="toast"></div>
    <div id="container">
        <div id="status-overlay">
            <b>模式：</b><span id="mode-text" style="color:#00CC44;">🎨 染色模式</span><br>
            <span id="step-info">当前状态：未锁定（点击贴纸可染色）</span>
        </div>
    </div>

    <div id="ui-panel">
        <div id="instructions">
            💡 提示：染色完成后点击求解；或者在<b>还原状态下点击打乱</b>。
        </div>

        <div class="palette" id="palette-container">
            <div class="color-btn" style="background: #333; border-color: #888;" onclick="selectColor('None', '#333333', this)" title="🔒 防误触锁定">🔒</div>
            <div class="color-btn active" style="background: #FFD700;" onclick="selectColor('Yellow', '#FFD700', this)" title="黄色"></div>
            <div class="color-btn" style="background: #FF8800;" onclick="selectColor('Orange', '#FF8800', this)" title="橙色"></div>
            <div class="color-btn" style="background: #00CC44;" onclick="selectColor('Green', '#00CC44', this)" title="绿色"></div>
            <div class="color-btn" style="background: #FFFFFF;" onclick="selectColor('White', '#FFFFFF', this)" title="白色"></div>
            <div class="color-btn" style="background: #FF3333;" onclick="selectColor('Red', '#FF3333', this)" title="红色"></div>
            <div class="color-btn" style="background: #3366FF;" onclick="selectColor('Blue', '#3366FF', this)" title="蓝色"></div>
        </div>

        <!-- 动画控制条 -->
        <div id="anim-bar">
            <div class="controls-row" style="margin-bottom:0;">
                <button class="btn btn-step" onclick="stepBackward()">◀ 上一步</button>
                <button class="btn btn-play" id="play-btn" onclick="toggleAutoPlay()">▶ 自动播放</button>
                <button class="btn btn-step" onclick="stepForward()">下一步 ▶</button>
                <button class="btn btn-reset" onclick="resetAnimation()">⏮ 重新开始动画</button>
                <span style="font-size:13px; margin-left:10px;">速度: 
                    🐢 <input type="range" id="speed-slider" min="100" max="800" value="400" style="vertical-align:middle; width:80px;"> 🐇
                </span>
            </div>
        </div>

        <div class="controls-row">
            <button class="btn btn-swap" id="swap-btn" onclick="swapLeftRightColors()">🔀 切换左右</button>
            <button class="btn btn-scramble" id="scramble-btn" onclick="startScramble()">🌪 随机打乱</button>
            <button class="btn btn-history" onclick="fetchHistory()">📜 历史记录</button>
            <button class="btn btn-reset" onclick="resetAll()">↺ 重置魔方</button>
            <button class="btn" id="solve-btn" onclick="solveCube()">🚀 计算还原步骤</button>
        </div>

        <!-- 历史记录面板 -->
        <div id="history-panel" class="panel-box">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h3 style="margin:0; color:#8e44ad;">📜 我的打乱历史记录 <span style="font-size:12px; color:#aaa;">(直观展开图预览)</span></h3>
                <button class="btn-danger-sm" onclick="clearAllHistory()">🧹 清空我的历史</button>
            </div>
            <div class="history-grid" id="history-container"></div>
        </div>

        <!-- 求解结果面板 -->
        <div id="result" class="panel-box">
            <h3 style="margin-top:0; color:#4CAF50;">🎉 还原方案已生成！</h3>
            <div><b>步骤总数：</b><span id="step-count"></span></div>
            <div class="steps-grid" id="steps-container"></div>
        </div>
    </div>

    <script>
        const COLOR_DATA = {
            'Yellow': { hex: 0xFFD700 }, 'Orange': { hex: 0xFF8800 }, 'Green':  { hex: 0x00CC44 },
            'White':  { hex: 0xFFFFFF }, 'Red':    { hex: 0xFF3333 }, 'Blue':   { hex: 0x3366FF }
        };

        let centerColorMap = { 'U': 'Yellow', 'R': 'Orange', 'F': 'Green', 'D': 'White', 'L': 'Red', 'B': 'Blue' };

        const MOVE_DESC = {
            'U': '顶顺', "U'": '顶逆', 'U2': '顶180°', 'D': '底顺', "D'": '底逆', 'D2': '底180°',
            'R': '右顺', "R'": '右逆', 'R2': '右180°', 'L': '左顺', "L'": '左逆', 'L2': '左180°',
            'F': '前顺', "F'": '前逆', 'F2': '前180°', 'B': '后顺', "B'": '后逆', 'B2': '后180°',
        };

        const SOLVED_STATE = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB";

        let currentSelectedColorName = 'Yellow';
        let currentSelectedHex = 0xFFD700;
        let currentMode = 'paint';

        let scene, camera, renderer, controls;
        let cubies = []; 
        let userInitialSnapshot = null;

        let solutionMoves = [];
        let currentStepIndex = 0;
        let isAnimating = false;
        let isAutoPlaying = false;
        let autoPlayTimer = null;
        let isManualState = true; 

        function setMode(mode) {
            currentMode = mode;
            const modeText = document.getElementById('mode-text');
            const stepInfo = document.getElementById('step-info');
            const colorBtns = document.querySelectorAll('.color-btn');
            
            if (mode === 'paint') {
                modeText.innerText = "🎨 染色模式"; modeText.style.color = "#00CC44";
                stepInfo.innerText = currentSelectedColorName === 'None' ? "当前状态：🔒 已锁定（旋转视角不染色）" : "当前状态：可染色（点击贴纸生效）";
                colorBtns.forEach(btn => btn.style.opacity = '1');
            } else if (mode === 'scrambling') {
                modeText.innerText = "🌪 打乱模式"; modeText.style.color = "#FF8800";
                stepInfo.innerText = "当前状态：系统正在执行随机打乱...";
                colorBtns.forEach(btn => btn.style.opacity = '0.3');
            } else if (mode === 'scrambled') {
                modeText.innerText = "🎲 待求解模式"; modeText.style.color = "#FF8800";
                stepInfo.innerText = "当前状态：已打乱，仅支持【求解】或【重置魔方】";
                colorBtns.forEach(btn => btn.style.opacity = '0.3');
            } else if (mode === 'solve') {
                modeText.innerText = "🎬 动画演示模式"; modeText.style.color = "#FFD700";
                colorBtns.forEach(btn => btn.style.opacity = '0.3');
            }
        }

        function selectColor(colorName, hexStr, el) {
            if (currentMode !== 'paint') { showToast("⚠️ 当前模式不可选色！请先点击“重置魔方”。"); return; }
            currentSelectedColorName = colorName;
            currentSelectedHex = parseInt(hexStr.replace('#', '0x'));
            document.querySelectorAll('.color-btn').forEach(btn => btn.classList.remove('active'));
            el.classList.add('active');
            setMode('paint');
        }

        function showToast(msg, isSuccess = false) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.background = isSuccess ? 'rgba(40,167,69,0.9)' : 'rgba(220,53,69,0.9)';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3500);
        }

        function swapLeftRightColors() {
            if (currentMode !== 'paint') { showToast("⚠️ 请先重置魔方再切换左右配色！"); return; }
            const temp = centerColorMap['R']; centerColorMap['R'] = centerColorMap['L']; centerColorMap['L'] = temp;
            resetAll();
            showToast("已切换左右中心块配色！", true);
        }

        function init3D() {
            const container = document.getElementById('container');
            scene = new THREE.Scene(); scene.background = new THREE.Color(0x121212);
            camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(5.5, 4.5, 7.5);
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.85); scene.add(ambientLight);
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.4); dirLight.position.set(10, 20, 15); scene.add(dirLight);

            build27Cubies();
            renderer.domElement.addEventListener('pointerdown', onStickerClick);

            window.addEventListener('resize', () => {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });
            animate();
            setMode('paint');
        }

        function build27Cubies() {
            const geom = new THREE.BoxGeometry(0.96, 0.96, 0.96);
            for (let x = -1; x <= 1; x++) {
                for (let y = -1; y <= 1; y++) {
                    for (let z = -1; z <= 1; z++) {
                        const mats = []; const colorNames = [];
                        mats.push(createFaceMat(x === 1, centerColorMap['R'], colorNames));
                        mats.push(createFaceMat(x === -1, centerColorMap['L'], colorNames));
                        mats.push(createFaceMat(y === 1, centerColorMap['U'], colorNames));
                        mats.push(createFaceMat(y === -1, centerColorMap['D'], colorNames));
                        mats.push(createFaceMat(z === 1, centerColorMap['F'], colorNames));
                        mats.push(createFaceMat(z === -1, centerColorMap['B'], colorNames));

                        const cubie = new THREE.Mesh(geom, mats);
                        cubie.position.set(x, y, z);
                        cubie.userData = { colorNames: colorNames, isCenter: (Math.abs(x) + Math.abs(y) + Math.abs(z) === 1) };
                        scene.add(cubie); cubies.push(cubie);
                    }
                }
            }
        }

        function createFaceMat(isOuter, colorName, colorNamesArr) {
            if (isOuter) {
                colorNamesArr.push(colorName);
                return new THREE.MeshBasicMaterial({ color: COLOR_DATA[colorName].hex });
            } else {
                colorNamesArr.push(null);
                return new THREE.MeshBasicMaterial({ color: 0x111111 });
            }
        }

        const raycaster = new THREE.Raycaster(); const mouse = new THREE.Vector2();

        function onStickerClick(event) {
            if (currentMode !== 'paint' || currentSelectedColorName === 'None') return;
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(cubies);

            if (intersects.length > 0) {
                const hit = intersects[0]; const cubie = hit.object;
                const faceIdx = Math.floor(hit.faceIndex / 2);

                if (cubie.userData.colorNames[faceIdx] !== null) {
                    if (cubie.userData.isCenter) { showToast("⚠️ 各面中心块颜色固定用于指示方位，无法修改！"); return; }
                    cubie.material[faceIdx].color.setHex(currentSelectedHex);
                    cubie.userData.colorNames[faceIdx] = currentSelectedColorName;
                    isManualState = true;
                }
            }
        }

        function saveSnapshot() {
            userInitialSnapshot = cubies.map(c => ({
                x: c.position.x, y: c.position.y, z: c.position.z,
                rx: c.rotation.x, ry: c.rotation.y, rz: c.rotation.z,
                colorNames: [...c.userData.colorNames]
            }));
        }

        function restoreSnapshot() {
            if (!userInitialSnapshot) return;
            cubies.forEach(c => scene.remove(c)); cubies = [];
            const geom = new THREE.BoxGeometry(0.96, 0.96, 0.96);
            userInitialSnapshot.forEach(item => {
                const mats = [];
                item.colorNames.forEach(cName => {
                    mats.push(new THREE.MeshBasicMaterial({ color: cName ? COLOR_DATA[cName].hex : 0x111111 }));
                });
                const cubie = new THREE.Mesh(geom, mats);
                cubie.position.set(item.x, item.y, item.z);
                cubie.rotation.set(item.rx, item.ry, item.rz);
                cubie.updateMatrixWorld(true);
                cubie.userData = { colorNames: [...item.colorNames], isCenter: (Math.abs(Math.round(item.x)) + Math.abs(Math.round(item.y)) + Math.abs(Math.round(item.z)) === 1) };
                scene.add(cubie); cubies.push(cubie);
            });
        }

        function extractCubeStateString() {
            const faceCenters = {
                'U': new THREE.Vector3(0, 1, 0), 'R': new THREE.Vector3(1, 0, 0),
                'F': new THREE.Vector3(0, 0, 1), 'D': new THREE.Vector3(0, -1, 0),
                'L': new THREE.Vector3(-1, 0, 0), 'B': new THREE.Vector3(0, 0, -1)
            };
            const colorToCode = {};
            for (let fCode in centerColorMap) colorToCode[centerColorMap[fCode]] = fCode;

            const localNormals = [
                new THREE.Vector3(1, 0, 0), new THREE.Vector3(-1, 0, 0),
                new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, -1, 0),
                new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, -1)
            ];

            const getCubieColorAtGlobalDir = (cx, cy, cz, globalDir) => {
                const c = cubies.find(c => Math.round(c.position.x) === cx && Math.round(c.position.y) === cy && Math.round(c.position.z) === cz);
                if (!c) return null;
                c.updateMatrixWorld(true);
                let normalMatrix = new THREE.Matrix3().getNormalMatrix(c.matrixWorld);
                for(let i=0; i<6; i++) {
                    let worldNormal = localNormals[i].clone().applyMatrix3(normalMatrix).normalize();
                    worldNormal.x = Math.round(worldNormal.x); worldNormal.y = Math.round(worldNormal.y); worldNormal.z = Math.round(worldNormal.z);
                    if (worldNormal.equals(globalDir)) return c.userData.colorNames[i];
                }
                return null;
            };

            let str = "";
            for (let z = -1; z <= 1; z++) for (let x = -1; x <= 1; x++) str += colorToCode[getCubieColorAtGlobalDir(x, 1, z, faceCenters['U'])];
            for (let y = 1; y >= -1; y--) for (let z = 1; z >= -1; z--) str += colorToCode[getCubieColorAtGlobalDir(1, y, z, faceCenters['R'])];
            for (let y = 1; y >= -1; y--) for (let x = -1; x <= 1; x++) str += colorToCode[getCubieColorAtGlobalDir(x, y, 1, faceCenters['F'])];
            for (let z = 1; z >= -1; z--) for (let x = -1; x <= 1; x++) str += colorToCode[getCubieColorAtGlobalDir(x, -1, z, faceCenters['D'])];
            for (let y = 1; y >= -1; y--) for (let z = -1; z <= 1; z++) str += colorToCode[getCubieColorAtGlobalDir(-1, y, z, faceCenters['L'])];
            for (let y = 1; y >= -1; y--) for (let x = 1; x >= -1; x--) str += colorToCode[getCubieColorAtGlobalDir(x, y, -1, faceCenters['B'])];
            return str;
        }

        function applyStateString(stateStr) {
            const codeToColor = {};
            for (let fCode in centerColorMap) codeToColor[fCode] = centerColorMap[fCode];
            const getCubieAt = (x, y, z) => cubies.find(c => Math.round(c.position.x)===x && Math.round(c.position.y)===y && Math.round(c.position.z)===z);
            
            let ptr = 0;
            const updateFace = (x, y, z, faceIdx) => {
                let cName = codeToColor[stateStr[ptr++]];
                let target = getCubieAt(x, y, z);
                target.userData.colorNames[faceIdx] = cName;
                target.material[faceIdx].color.setHex(COLOR_DATA[cName].hex);
            };

            for (let z = -1; z <= 1; z++) for (let x = -1; x <= 1; x++) updateFace(x, 1, z, 2);
            for (let y = 1; y >= -1; y--) for (let z = 1; z >= -1; z--) updateFace(1, y, z, 0);
            for (let y = 1; y >= -1; y--) for (let x = -1; x <= 1; x++) updateFace(x, y, 1, 4);
            for (let z = 1; z >= -1; z--) for (let x = -1; x <= 1; x++) updateFace(x, -1, z, 3);
            for (let y = 1; y >= -1; y--) for (let z = -1; z <= 1; z++) updateFace(-1, y, z, 1);
            for (let y = 1; y >= -1; y--) for (let x = 1; x >= -1; x--) updateFace(x, y, -1, 5);
        }

        function resetAll() {
            stopAutoPlay(); solutionMoves = []; currentStepIndex = 0; isAnimating = false; userInitialSnapshot = null; isManualState = true; 
            document.getElementById('anim-bar').style.display = 'none';
            document.getElementById('result').style.display = 'none';
            document.getElementById('history-panel').style.display = 'none';
            cubies.forEach(c => scene.remove(c)); cubies = [];
            build27Cubies(); setMode('paint');
        }

        // ==================== 3D 旋转动画引擎 ====================
        function animateLayerRotation(moveStr, isReverse, onComplete, customDuration=null) {
            if (isAnimating && customDuration === null) return;
            isAnimating = true;

            const face = moveStr[0]; let modifier = moveStr.slice(1);
            if (isReverse) { if (modifier === "'") modifier = ""; else if (modifier === "") modifier = "'"; }

            let axis = new THREE.Vector3(); let angle = -Math.PI / 2;
            if (modifier === "'") angle = Math.PI / 2; else if (modifier === "2") angle = -Math.PI;

            let filterFn;
            if (face === 'U') { axis.set(0, 1, 0); filterFn = c => Math.round(c.position.y) === 1; }
            else if (face === 'D') { axis.set(0, 1, 0); angle = -angle; filterFn = c => Math.round(c.position.y) === -1; }
            else if (face === 'R') { axis.set(1, 0, 0); filterFn = c => Math.round(c.position.x) === 1; }
            else if (face === 'L') { axis.set(1, 0, 0); angle = -angle; filterFn = c => Math.round(c.position.x) === -1; }
            else if (face === 'F') { axis.set(0, 0, 1); filterFn = c => Math.round(c.position.z) === 1; }
            else if (face === 'B') { axis.set(0, 0, 1); angle = -angle; filterFn = c => Math.round(c.position.z) === -1; }

            const rotatingCubies = cubies.filter(filterFn);
            const pivot = new THREE.Group(); scene.add(pivot); rotatingCubies.forEach(c => pivot.attach(c));

            // 【Bug 修复】：通过 (900 - sliderValue) 实现滑块向右越快，向左越慢！
            const sliderVal = parseInt(document.getElementById('speed-slider').value);
            const duration = customDuration !== null ? customDuration : (900 - sliderVal);
            
            const startTime = performance.now();

            function stepAnim(now) {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1.0);
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                
                pivot.rotation.set(0,0,0); pivot.rotateOnAxis(axis, angle * easeProgress);

                if (progress < 1.0) requestAnimationFrame(stepAnim);
                else {
                    pivot.rotation.set(0,0,0); pivot.rotateOnAxis(axis, angle); pivot.updateMatrixWorld(true);
                    rotatingCubies.forEach(c => {
                        scene.attach(c);
                        c.position.x = Math.round(c.position.x); c.position.y = Math.round(c.position.y); c.position.z = Math.round(c.position.z);
                    });
                    scene.remove(pivot); isAnimating = false;
                    if (onComplete) onComplete();
                }
            }
            requestAnimationFrame(stepAnim);
        }

        function stepForward() {
            if (isAnimating || currentStepIndex >= solutionMoves.length) return;
            animateLayerRotation(solutionMoves[currentStepIndex], false, () => { currentStepIndex++; updateUIState(); });
        }
        function stepBackward() {
            if (isAnimating || currentStepIndex <= 0) return;
            currentStepIndex--;
            animateLayerRotation(solutionMoves[currentStepIndex], true, () => { updateUIState(); });
        }
        function toggleAutoPlay() {
            if (isAutoPlaying) stopAutoPlay();
            else {
                if (currentStepIndex >= solutionMoves.length) resetAnimation();
                isAutoPlaying = true; document.getElementById('play-btn').innerText = "⏸ 暂停播放";
                autoPlayNextStep();
            }
        }
        function autoPlayNextStep() {
            if (!isAutoPlaying) return;
            if (currentStepIndex >= solutionMoves.length) {
                stopAutoPlay(); showToast("🎉 动画播放完毕！魔方已还原。", true); return;
            }
            animateLayerRotation(solutionMoves[currentStepIndex], false, () => {
                currentStepIndex++; updateUIState();
                if (isAutoPlaying) autoPlayTimer = setTimeout(autoPlayNextStep, 80);
            });
        }
        function stopAutoPlay() { isAutoPlaying = false; clearTimeout(autoPlayTimer); document.getElementById('play-btn').innerText = "▶ 自动播放"; }
        function resetAnimation() { stopAutoPlay(); isAnimating = false; currentStepIndex = 0; restoreSnapshot(); updateUIState(); }
        function updateUIState() {
            document.getElementById('step-info').innerText = `动画进度：第 ${currentStepIndex} / ${solutionMoves.length} 步`;
            document.querySelectorAll('#steps-container .step-card').forEach((card, idx) => {
                if (idx === currentStepIndex - 1) card.classList.add('active'); else card.classList.remove('active');
            });
        }

        // ==================== 随机打乱 ====================
        function startScramble() {
            if (isAnimating || solutionMoves.length > 0) return;
            if (currentMode !== 'paint') { showToast("⚠️ 请先点击【重置魔方】退出当前流程后再使用打乱！"); return; }
            
            const currentState = extractCubeStateString();
            if (currentState !== SOLVED_STATE) { showToast("⚠️ 打乱功能只能在魔方处于【完全还原】状态时使用！"); return; }

            setMode('scrambling');

            const faces = ['U', 'D', 'R', 'L', 'F', 'B']; const mods = ['', "'", '2'];
            let scrambleMoves = []; let lastFace = '';
            for(let i=0; i<20; i++) {
                let face; do { face = faces[Math.floor(Math.random() * faces.length)]; } while(face === lastFace);
                lastFace = face; scrambleMoves.push(face + mods[Math.floor(Math.random() * mods.length)]);
            }

            document.getElementById('history-panel').style.display = 'none';
            isManualState = false; 
            playScrambleSequence(scrambleMoves, 0);
        }

        function playScrambleSequence(moves, index) {
            if (index >= moves.length) {
                setMode('scrambled');
                showToast("✅ 打乱完成！您可以随时点击“计算还原步骤”。", true);
                return;
            }
            animateLayerRotation(moves[index], false, () => { playScrambleSequence(moves, index + 1); }, 75);
        }

        // ==================== 求解与历史记录 ====================
        async function solveCube() {
            if(isAnimating || currentMode === 'scrambling') return;
            const cubeString = extractCubeStateString();

            if (cubeString === SOLVED_STATE) { showToast("✅ 您的魔方目前已经处于还原状态，无需求解！", true); return; }

            saveSnapshot();

            try {
                const response = await fetch('/api/solve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ state: cubeString, is_manual: isManualState })
                });
                const data = await response.json();

                if (data.status === 'success') {
                    solutionMoves = data.moves; currentStepIndex = 0;
                    document.getElementById('history-panel').style.display = 'none';
                    setMode('solve');
                    document.getElementById('anim-bar').style.display = 'block';

                    displaySolution(data.solution, data.moves);
                    updateUIState();
                } else {
                    showToast("❌ 无法解开：请检查是否有错填颜色或非法状态。");
                }
            } catch (err) { showToast("❌ 网络请求错误。"); }
        }

        function renderNetHTML(stateStr) {
            const letterToHex = {};
            for (let fCode in centerColorMap) {
                letterToHex[fCode] = '#' + COLOR_DATA[centerColorMap[fCode]].hex.toString(16).padStart(6, '0');
            }

            const renderFaceHTML = (faceStr) => {
                let html = '<div class="face-grid">';
                for(let i=0; i<9; i++) {
                    let color = letterToHex[faceStr[i]] || '#333';
                    html += `<div class="sticker-mini" style="background:${color};"></div>`;
                }
                html += '</div>';
                return html;
            };

            const U = stateStr.slice(0, 9);
            const R = stateStr.slice(9, 18);
            const F = stateStr.slice(18, 27);
            const D = stateStr.slice(27, 36);
            const L = stateStr.slice(36, 45);
            const B = stateStr.slice(45, 54);

            return `
                <div class="cube-net-container">
                    <div></div>${renderFaceHTML(U)}<div></div><div></div>
                    ${renderFaceHTML(L)}${renderFaceHTML(F)}${renderFaceHTML(R)}${renderFaceHTML(B)}
                    <div></div>${renderFaceHTML(D)}<div></div><div></div>
                </div>
            `;
        }

        async function fetchHistory() {
            if (currentMode !== 'paint') { showToast("⚠️ 请先重置魔方后再查看并载入历史！"); return; }
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                const container = document.getElementById('history-container');
                container.innerHTML = '';
                
                if (data.history && data.history.length > 0) {
                    data.history.forEach((item) => {
                        const card = document.createElement('div');
                        card.className = 'history-card';
                        
                        const timeStr = item.created_at ? item.created_at.split(' ')[1] || item.created_at : '';

                        card.innerHTML = `
                            <div style="width:100%; display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:11px; color:#aaa;">时间: ${timeStr}</span>
                                <button class="btn-danger-sm" onclick="deleteHistoryItem(event, ${item.id})">🗑 删除</button>
                            </div>
                            ${renderNetHTML(item.state)}
                            <button class="btn" style="padding:4px 10px; font-size:12px; width:100%; margin-top:5px;" onclick="loadHistoryState('${item.state}')">载入该状态</button>
                        `;
                        container.appendChild(card);
                    });
                } else {
                    container.innerHTML = '<div style="color:#aaa; font-size:13px; grid-column: 1 / -1; text-align:center; padding:20px;">暂无属于您的历史记录。</div>';
                }
                document.getElementById('history-panel').style.display = 'block';
                document.getElementById('result').style.display = 'none';
            } catch (e) { showToast("❌ 获取历史记录失败。"); }
        }

        function loadHistoryState(stateStr) {
            resetAll();
            applyStateString(stateStr);
            isManualState = false;
            showToast("✅ 历史状态已载入，可直接计算还原！", true);
        }

        async function deleteHistoryItem(event, itemId) {
            event.stopPropagation();
            try {
                const res = await fetch('/api/history/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: itemId })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast("🗑 已成功删除该条记录！", true);
                    fetchHistory();
                }
            } catch(e) { showToast("❌ 删除失败。"); }
        }

        async function clearAllHistory() {
            if (!confirm("⚠️ 确定要清空您的所有历史打乱记录吗？")) return;
            try {
                const res = await fetch('/api/history/clear', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast("🧹 已清空您的所有历史记录！", true);
                    fetchHistory();
                }
            } catch(e) { showToast("❌ 清空失败。"); }
        }

        function displaySolution(solutionStr, moves) {
            document.getElementById('result').style.display = 'block';
            document.getElementById('step-count').innerText = moves.length + " 步";
            const container = document.getElementById('steps-container');
            container.innerHTML = '';
            moves.forEach((move, idx) => {
                const card = document.createElement('div');
                card.className = 'step-card';
                card.innerHTML = `<div style="font-size:10px; color:#aaa;">第 ${idx + 1} 步</div><div class="step-code">${move}</div><div class="step-desc">${MOVE_DESC[move] || ''}</div>`;
                container.appendChild(card);
            });
        }

        function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
        window.onload = init3D;
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ==================== 后端 API ====================

@app.route('/api/solve', methods=['POST'])
def solve_cube():
    data = request.json
    cube_state = data.get('state', '')
    is_manual = data.get('is_manual', True)
    
    user_ip = request.remote_addr

    if is_manual:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT cube_state FROM history WHERE ip = ? ORDER BY id DESC LIMIT 1", (user_ip,))
        last_row = cursor.fetchone()
        
        if not last_row or last_row[0] != cube_state:
            cursor.execute("INSERT INTO history (ip, cube_state) VALUES (?, ?)", (user_ip, cube_state))
            conn.commit()
        conn.close()

    try:
        solution = kociemba.solve(cube_state)
        moves = solution.split()
        return jsonify({'status': 'success', 'solution': solution, 'moves': moves})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/history', methods=['GET'])
def get_history():
    user_ip = request.remote_addr
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cube_state, created_at FROM history WHERE ip = ? ORDER BY id DESC LIMIT 15", (user_ip,))
    rows = cursor.fetchall()
    conn.close()

    history_list = [{'id': r[0], 'state': r[1], 'created_at': r[2]} for r in rows]
    return jsonify({'status': 'success', 'history': history_list})

@app.route('/api/history/delete', methods=['POST'])
def delete_history_item():
    data = request.json
    item_id = data.get('id')
    user_ip = request.remote_addr

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ? AND ip = ?", (item_id, user_ip))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    user_ip = request.remote_addr

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE ip = ?", (user_ip,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    print("--------------------------------------------------")
    print("🚀 3D 动画魔方求解器 (已修正速度控制逻辑) 启动成功！")
    print("👉 请在浏览器访问: http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', debug=True, port=5000)
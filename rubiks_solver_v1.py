from flask import Flask, render_template_string, request, jsonify
import kociemba

app = Flask(__name__)

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
        #container { width: 100vw; height: 55vh; position: relative; }
        #ui-panel { padding: 15px; background: #1e1e1e; box-shadow: 0 -2px 10px rgba(0,0,0,0.5); min-height: 40vh; }
        .palette { display: flex; justify-content: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
        .color-btn { width: 42px; height: 42px; border-radius: 50%; border: 3px solid #444; cursor: pointer; transition: transform 0.2s, border-color 0.2s; display: flex; align-items: center; justify-content: center; font-size: 18px; user-select: none; }
        .color-btn.active { transform: scale(1.18); border-color: #fff; box-shadow: 0 0 10px rgba(255,255,255,0.8); }
        .controls-row { display: flex; justify-content: center; gap: 12px; align-items: center; margin-bottom: 15px; flex-wrap: wrap; }
        .btn { padding: 8px 18px; font-size: 14px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; background: #007bff; color: white; transition: background 0.2s; }
        .btn:hover { background: #0056b3; }
        .btn-swap { background: #17a2b8; }
        .btn-swap:hover { background: #138496; }
        .btn-reset { background: #6c757d; }
        .btn-reset:hover { background: #5a6268; }
        .btn-play { background: #28a745; }
        .btn-play:hover { background: #218838; }
        .btn-step { background: #ffc107; color: #111; }
        .btn-step:hover { background: #e0a800; }
        
        #anim-bar { display: none; background: #2a2a2a; padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #444; }
        #status-overlay { position: absolute; top: 15px; left: 15px; background: rgba(0,0,0,0.75); padding: 10px 15px; border-radius: 6px; font-size: 14px; z-index: 10; border: 1px solid #555; }
        
        #instructions { text-align: center; color: #aaa; margin-bottom: 10px; font-size: 13px; }
        #result { max-width: 900px; margin: 0 auto; padding: 15px; background: #252525; border-radius: 8px; display: none; }
        .steps-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; margin-top: 10px; max-height: 200px; overflow-y: auto; padding: 5px; }
        .step-card { background: #333; padding: 8px; border-radius: 5px; text-align: center; border: 2px solid transparent; cursor: pointer; }
        .step-card.active { border-color: #007bff; background: #3d3d3d; }
        .step-code { font-size: 18px; font-weight: bold; color: #FFD700; }
        .step-desc { font-size: 11px; color: #ccc; margin-top: 2px; }
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
            💡 选择 <b>🔒 锁定位</b> 可自由拖拽旋转视角不染色 | 算解后可<b>播放 3D 旋转动画</b>
        </div>

        <!-- 调色板 (第一项为防误触锁定位) -->
        <div class="palette">
            <div class="color-btn" style="background: #333; border-color: #888;" onclick="selectColor('None', '#333333', this)" title="🔒 防误触锁定 (仅旋转视角，不染色)">🔒</div>
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
                    <input type="range" id="speed-slider" min="150" max="800" value="400" style="vertical-align:middle; width:80px;">
                </span>
            </div>
        </div>

        <div class="controls-row">
            <button class="btn btn-swap" id="swap-btn" onclick="swapLeftRightColors()">🔀 切换左右配色 (橙/红对调)</button>
            <button class="btn btn-reset" onclick="resetAll()">↺ 重置魔方</button>
            <button class="btn" id="solve-btn" onclick="solveCube()">🚀 计算还原步骤</button>
        </div>

        <div id="result">
            <h3 style="margin-top:0; color:#4CAF50;">🎉 还原方案已生成！</h3>
            <div><b>步骤总数：</b><span id="step-count"></span></div>
            <div class="steps-grid" id="steps-container"></div>
        </div>
    </div>

    <script>
        const COLOR_DATA = {
            'Yellow': { hex: 0xFFD700 },
            'Orange': { hex: 0xFF8800 },
            'Green':  { hex: 0x00CC44 },
            'White':  { hex: 0xFFFFFF },
            'Red':    { hex: 0xFF3333 },
            'Blue':   { hex: 0x3366FF }
        };

        // 默认配色已调整为：右侧为橙色 (R: Orange)，左侧为红色 (L: Red)
        let centerColorMap = {
            'U': 'Yellow', 
            'R': 'Orange', 
            'F': 'Green',
            'D': 'White',  
            'L': 'Red',    
            'B': 'Blue'
        };

        const MOVE_DESC = {
            'U': '顶层 顺时针', "U'": '顶层 逆时针', 'U2': '顶层 旋转180°',
            'D': '底层 顺时针', "D'": '底层 逆时针', 'D2': '底层 旋转180°',
            'R': '右层 顺时针', "R'": '右层 逆时针', 'R2': '右层 旋转180°',
            'L': '左层 顺时针', "L'": '左层 逆时针', 'L2': '左层 旋转180°',
            'F': '前层 顺时针', "F'": '前层 逆时针', 'F2': '前层 旋转180°',
            'B': '后层 顺时针', "B'": '后层 逆时针', 'B2': '后层 旋转180°',
        };

        let currentSelectedColorName = 'Yellow';
        let currentSelectedHex = 0xFFD700;

        let scene, camera, renderer, controls;
        let cubies = []; 
        let userInitialSnapshot = null; // 用户打乱染色的初始状态快照

        let solutionMoves = [];
        let currentStepIndex = 0;
        let isAnimating = false;
        let isAutoPlaying = false;
        let autoPlayTimer = null;

        function selectColor(colorName, hexStr, el) {
            currentSelectedColorName = colorName;
            currentSelectedHex = parseInt(hexStr.replace('#', '0x'));
            document.querySelectorAll('.color-btn').forEach(btn => btn.classList.remove('active'));
            el.classList.add('active');

            if (colorName === 'None') {
                document.getElementById('step-info').innerText = "当前状态：🔒 已锁定（旋转视角不染色）";
            } else {
                document.getElementById('step-info').innerText = "当前状态：可染色（点击贴纸生效）";
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3500);
        }

        function swapLeftRightColors() {
            if (isAnimating || solutionMoves.length > 0) resetAll();
            const temp = centerColorMap['R'];
            centerColorMap['R'] = centerColorMap['L'];
            centerColorMap['L'] = temp;

            resetAll();
            showToast("已切换左右中心块配色！");
        }

        function init3D() {
            const container = document.getElementById('container');
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x121212);

            camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(5.5, 4.5, 7.5);

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);

            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
            scene.add(ambientLight);
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.4);
            dirLight.position.set(10, 20, 15);
            scene.add(dirLight);

            build27Cubies();

            renderer.domElement.addEventListener('pointerdown', onStickerClick);

            window.addEventListener('resize', () => {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });

            animate();
        }

        function build27Cubies() {
            const geom = new THREE.BoxGeometry(0.96, 0.96, 0.96);

            for (let x = -1; x <= 1; x++) {
                for (let y = -1; y <= 1; y++) {
                    for (let z = -1; z <= 1; z++) {
                        const mats = [];
                        const colorNames = [];

                        mats.push(createFaceMat(x === 1, centerColorMap['R'], colorNames));
                        mats.push(createFaceMat(x === -1, centerColorMap['L'], colorNames));
                        mats.push(createFaceMat(y === 1, centerColorMap['U'], colorNames));
                        mats.push(createFaceMat(y === -1, centerColorMap['D'], colorNames));
                        mats.push(createFaceMat(z === 1, centerColorMap['F'], colorNames));
                        mats.push(createFaceMat(z === -1, centerColorMap['B'], colorNames));

                        const cubie = new THREE.Mesh(geom, mats);
                        cubie.position.set(x, y, z);
                        
                        cubie.userData = {
                            colorNames: colorNames,
                            isCenter: (Math.abs(x) + Math.abs(y) + Math.abs(z) === 1)
                        };

                        scene.add(cubie);
                        cubies.push(cubie);
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

        // 点击染色逻辑
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        function onStickerClick(event) {
            // 处于演示模式或处于“🔒 锁定位”时不进行染色
            if (solutionMoves.length > 0 || isAnimating || currentSelectedColorName === 'None') return;

            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(cubies);

            if (intersects.length > 0) {
                const hit = intersects[0];
                const cubie = hit.object;
                const faceIdx = Math.floor(hit.faceIndex / 2);

                if (cubie.userData.colorNames[faceIdx] !== null) {
                    if (cubie.userData.isCenter) {
                        showToast("⚠️ 各面中心块颜色固定用于指示方位，无法修改！");
                        return;
                    }
                    
                    cubie.material[faceIdx].color.setHex(currentSelectedHex);
                    cubie.userData.colorNames[faceIdx] = currentSelectedColorName;
                }
            }
        }

        // 保存用户染好的打乱快照，供重头看动画时恢复
        function saveSnapshot() {
            userInitialSnapshot = cubies.map(c => {
                return {
                    x: Math.round(c.position.x),
                    y: Math.round(c.position.y),
                    z: Math.round(c.position.z),
                    colorNames: [...c.userData.colorNames]
                };
            });
        }

        // 恢复用户打乱时的状态
        function restoreSnapshot() {
            if (!userInitialSnapshot) return;

            cubies.forEach(c => scene.remove(c));
            cubies = [];

            const geom = new THREE.BoxGeometry(0.96, 0.96, 0.96);

            userInitialSnapshot.forEach(item => {
                const mats = [];
                item.colorNames.forEach(cName => {
                    if (cName !== null) {
                        mats.push(new THREE.MeshBasicMaterial({ color: COLOR_DATA[cName].hex }));
                    } else {
                        mats.push(new THREE.MeshBasicMaterial({ color: 0x111111 }));
                    }
                });

                const cubie = new THREE.Mesh(geom, mats);
                cubie.position.set(item.x, item.y, item.z);
                cubie.userData = {
                    colorNames: [...item.colorNames],
                    isCenter: (Math.abs(item.x) + Math.abs(item.y) + Math.abs(item.z) === 1)
                };

                scene.add(cubie);
                cubies.push(cubie);
            });
        }

        function extractCubeStateString() {
            const colorToCode = {};
            for (let fCode in centerColorMap) {
                colorToCode[centerColorMap[fCode]] = fCode;
            }

            const getCubieAt = (x, y, z) => cubies.find(c => 
                Math.round(c.position.x) === x && 
                Math.round(c.position.y) === y && 
                Math.round(c.position.z) === z
            );

            let str = "";
            for (let z = -1; z <= 1; z++)
                for (let x = -1; x <= 1; x++)
                    str += colorToCode[getCubieAt(x, 1, z).userData.colorNames[2]];

            for (let y = 1; y >= -1; y--)
                for (let z = 1; z >= -1; z--)
                    str += colorToCode[getCubieAt(1, y, z).userData.colorNames[0]];

            for (let y = 1; y >= -1; y--)
                for (let x = -1; x <= 1; x++)
                    str += colorToCode[getCubieAt(x, y, 1).userData.colorNames[4]];

            for (let z = 1; z >= -1; z--)
                for (let x = -1; x <= 1; x++)
                    str += colorToCode[getCubieAt(x, -1, z).userData.colorNames[3]];

            for (let y = 1; y >= -1; y--)
                for (let z = -1; z <= 1; z++)
                    str += colorToCode[getCubieAt(-1, y, z).userData.colorNames[1]];

            for (let y = 1; y >= -1; y--)
                for (let x = 1; x >= -1; x--)
                    str += colorToCode[getCubieAt(x, y, -1).userData.colorNames[5]];

            return str;
        }

        function resetAll() {
            stopAutoPlay();
            solutionMoves = [];
            currentStepIndex = 0;
            isAnimating = false;
            userInitialSnapshot = null;

            document.getElementById('anim-bar').style.display = 'none';
            document.getElementById('result').style.display = 'none';
            document.getElementById('mode-text').innerText = "🎨 染色模式";
            document.getElementById('mode-text').style.color = "#00CC44";
            document.getElementById('step-info').innerText = "当前状态：可染色（点击贴纸生效）";

            cubies.forEach(c => scene.remove(c));
            cubies = [];
            build27Cubies();
        }

        // ==================== 3D 旋转动画引擎 ====================
        function animateLayerRotation(moveStr, isReverse, onComplete) {
            if (isAnimating) return;
            isAnimating = true;

            const face = moveStr[0];
            let modifier = moveStr.slice(1);
            
            if (isReverse) {
                if (modifier === "'") modifier = "";
                else if (modifier === "") modifier = "'";
            }

            let axis = new THREE.Vector3();
            let angle = -Math.PI / 2;

            if (modifier === "'") angle = Math.PI / 2;
            else if (modifier === "2") angle = -Math.PI;

            let filterFn;
            if (face === 'U') { axis.set(0, 1, 0); filterFn = c => Math.round(c.position.y) === 1; }
            else if (face === 'D') { axis.set(0, 1, 0); angle = -angle; filterFn = c => Math.round(c.position.y) === -1; }
            else if (face === 'R') { axis.set(1, 0, 0); filterFn = c => Math.round(c.position.x) === 1; }
            else if (face === 'L') { axis.set(1, 0, 0); angle = -angle; filterFn = c => Math.round(c.position.x) === -1; }
            else if (face === 'F') { axis.set(0, 0, 1); filterFn = c => Math.round(c.position.z) === 1; }
            else if (face === 'B') { axis.set(0, 0, 1); angle = -angle; filterFn = c => Math.round(c.position.z) === -1; }

            const rotatingCubies = cubies.filter(filterFn);

            const pivot = new THREE.Group();
            scene.add(pivot);
            rotatingCubies.forEach(c => pivot.attach(c));

            const duration = parseInt(document.getElementById('speed-slider').value);
            const startTime = performance.now();

            function stepAnim(now) {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1.0);
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                
                pivot.rotation.set(0,0,0);
                pivot.rotateOnAxis(axis, angle * easeProgress);

                if (progress < 1.0) {
                    requestAnimationFrame(stepAnim);
                } else {
                    pivot.rotation.set(0,0,0);
                    pivot.rotateOnAxis(axis, angle);
                    pivot.updateMatrixWorld(true);

                    rotatingCubies.forEach(c => {
                        scene.attach(c);
                        c.position.x = Math.round(c.position.x);
                        c.position.y = Math.round(c.position.y);
                        c.position.z = Math.round(c.position.z);
                    });

                    scene.remove(pivot);
                    isAnimating = false;
                    if (onComplete) onComplete();
                }
            }

            requestAnimationFrame(stepAnim);
        }

        function stepForward() {
            if (isAnimating || currentStepIndex >= solutionMoves.length) return;
            const move = solutionMoves[currentStepIndex];
            
            animateLayerRotation(move, false, () => {
                currentStepIndex++;
                updateUIState();
            });
        }

        function stepBackward() {
            if (isAnimating || currentStepIndex <= 0) return;
            currentStepIndex--;
            const move = solutionMoves[currentStepIndex];
            
            animateLayerRotation(move, true, () => {
                updateUIState();
            });
        }

        function toggleAutoPlay() {
            if (isAutoPlaying) {
                stopAutoPlay();
            } else {
                if (currentStepIndex >= solutionMoves.length) resetAnimation();
                isAutoPlaying = true;
                document.getElementById('play-btn').innerText = "⏸ 暂停播放";
                autoPlayNextStep();
            }
        }

        function autoPlayNextStep() {
            if (!isAutoPlaying) return;
            if (currentStepIndex >= solutionMoves.length) {
                stopAutoPlay();
                showToast("🎉 动画播放完毕！魔方已还原。");
                return;
            }

            const move = solutionMoves[currentStepIndex];
            animateLayerRotation(move, false, () => {
                currentStepIndex++;
                updateUIState();
                if (isAutoPlaying) {
                    autoPlayTimer = setTimeout(autoPlayNextStep, 80);
                }
            });
        }

        function stopAutoPlay() {
            isAutoPlaying = false;
            clearTimeout(autoPlayTimer);
            document.getElementById('play-btn').innerText = "▶ 自动播放";
        }

        // 【解决 Bug 1】：恢复打乱快照，重新开始动画
        function resetAnimation() {
            stopAutoPlay();
            isAnimating = false;
            currentStepIndex = 0;
            restoreSnapshot(); // 瞬间还原回最初打乱染色的状态
            updateUIState();
        }

        function updateUIState() {
            document.getElementById('step-info').innerText = `动画进度：第 ${currentStepIndex} / ${solutionMoves.length} 步`;
            
            document.querySelectorAll('.step-card').forEach((card, idx) => {
                if (idx === currentStepIndex - 1) card.classList.add('active');
                else card.classList.remove('active');
            });
        }

        async function solveCube() {
            // 保存用户此时的打乱状态快照
            saveSnapshot();

            const cubeString = extractCubeStateString();

            try {
                const response = await fetch('/api/solve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ state: cubeString })
                });
                const data = await response.json();

                if (data.status === 'success') {
                    solutionMoves = data.moves;
                    currentStepIndex = 0;

                    document.getElementById('mode-text').innerText = "🎬 动画演示模式";
                    document.getElementById('mode-text').style.color = "#FFD700";
                    document.getElementById('anim-bar').style.display = 'block';

                    displaySolution(data.solution, data.moves);
                    updateUIState();
                } else {
                    showToast("❌ 无法解开：请检查是否有错填颜色。");
                }
            } catch (err) {
                showToast("❌ 网络请求错误。");
            }
        }

        function displaySolution(solutionStr, moves) {
            document.getElementById('result').style.display = 'block';
            document.getElementById('step-count').innerText = moves.length + " 步";

            const container = document.getElementById('steps-container');
            container.innerHTML = '';

            moves.forEach((move, idx) => {
                const card = document.createElement('div');
                card.className = 'step-card';
                card.id = `step-card-${idx}`;
                card.innerHTML = `
                    <div style="font-size:10px; color:#aaa;">第 ${idx + 1} 步</div>
                    <div class="step-code">${move}</div>
                    <div class="step-desc">${MOVE_DESC[move] || ''}</div>
                `;
                container.appendChild(card);
            });
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        window.onload = init3D;
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/solve', methods=['POST'])
def solve_cube():
    data = request.json
    cube_state = data.get('state', '')
    
    try:
        solution = kociemba.solve(cube_state)
        moves = solution.split()
        return jsonify({'status': 'success', 'solution': solution, 'moves': moves})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    print("--------------------------------------------------")
    print("🚀 3D 动画演示魔方求解器更新成功！")
    print("👉 请在浏览器访问: http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', debug=True, port=5000)
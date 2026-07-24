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

// 3D 旋转动画引擎
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

// 随机打乱
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

// 求解与历史记录
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
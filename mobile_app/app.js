let currentTask = null;
let mediaRecorder = null;
let recordedChunks = [];
let recordingStartTime = null;
let timerInterval = null;

// UI Elements
const authScreen = document.getElementById('authScreen');
const appContent = document.getElementById('appContent');
const taskListView = document.getElementById('taskListView');
const taskDetailView = document.getElementById('taskDetailView');
const videoRecordView = document.getElementById('videoRecordView');
const taskList = document.getElementById('taskList');

// Init
document.getElementById('loginForm').addEventListener('submit', handleLogin);
document.getElementById('logoutBtn').addEventListener('click', handleLogout);
document.getElementById('backToTasks').addEventListener('click', showTaskList);
document.getElementById('cancelRec').addEventListener('click', stopAndCancelRecording);
document.getElementById('toggleRec').addEventListener('click', toggleRecording);

// Handle Login
async function handleLogin(e) {
    e.preventDefault();
    const domain = document.getElementById('tenantDomain').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const baseUrl = `http://${domain}.localhost:8000`;
    localStorage.setItem('api_base_url', baseUrl);

    try {
        // В реальном приложении здесь был бы запрос к API для получения токена
        // Для простоты имитируем вход и сохраняем домен
        showToast('Вход выполнен...');
        authScreen.classList.add('d-none');
        appContent.classList.remove('d-none');
        loadTasks();
    } catch (err) {
        showToast('Ошибка входа: ' + err.message);
    }
}

function handleLogout() {
    localStorage.removeItem('api_base_url');
    authScreen.classList.remove('d-none');
    appContent.classList.add('d-none');
}

// Load Tasks from API
async function loadTasks() {
    const baseUrl = localStorage.getItem('api_base_url');
    try {
        const response = await fetch(`${baseUrl}/api/tasks/`);
        const tasks = await response.json();
        renderTaskList(tasks);
    } catch (err) {
        console.error('Failed to load tasks', err);
        // Временно для демо, если API недоступен
        renderTaskList([
            {id: 1, title: 'Проверка оборудования', description: 'Осмотреть станок #5', status: 'OPEN', status_display: 'Открыта'},
            {id: 2, title: 'Уборка цеха', description: 'Сектор Б', status: 'IMPORTANT', status_display: 'Важно'}
        ]);
    }
}

function renderTaskList(tasks) {
    taskList.innerHTML = tasks.map(task => `
        <div class="col-12">
            <div class="card task-card border-0 shadow-sm p-3" onclick="showTaskDetail(${JSON.stringify(task).replace(/"/g, '&quot;')})">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <span class="badge badge-status-${task.status}">${task.status_display}</span>
                    <small class="text-muted">ID: ${task.id}</small>
                </div>
                <h6 class="fw-bold mb-1">${task.title}</h6>
                <p class="text-muted small mb-0">${task.description || 'Нет описания'}</p>
            </div>
        </div>
    `).join('');
}

// Task Details
function showTaskDetail(task) {
    currentTask = task;
    taskListView.classList.add('d-none');
    taskDetailView.classList.remove('d-none');
    
    document.getElementById('taskDetailContent').innerHTML = `
        <h4 class="fw-bold mb-1">${task.title}</h4>
        <p class="text-muted mb-4">${task.description || 'Описание отсутствует'}</p>
        
        <div class="mb-4">
            <h6 class="fw-bold mb-3 small text-muted text-uppercase">Этапы задачи (${task.total_duration || 0} мин)</h6>
            <div class="list-group list-group-flush bg-transparent">
                ${(task.stages || []).map(stage => `
                    <div class="list-group-item bg-transparent d-flex justify-content-between align-items-center px-0 border-light">
                        <div class="d-flex align-items-center">
                            <i class="bi ${stage.is_completed ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'} me-2"></i>
                            <span class="${stage.is_completed ? 'text-decoration-line-through text-muted' : ''}">${stage.name}</span>
                        </div>
                        <span class="badge rounded-pill bg-light text-dark border small">${stage.duration_minutes} мин</span>
                    </div>
                `).join('') || '<div class="text-muted small">Этапы не заданы</div>'}
            </div>
        </div>

        <div class="mb-4">
            <label class="form-label small text-muted text-uppercase">Статус задачи</label>
            <div class="d-flex flex-wrap gap-2">
                ${['OPEN', 'PAUSE', 'CONTINUE', 'IMPORTANT', 'CLOSE'].map(s => {
                    const label = {OPEN:'Открыта', PAUSE:'Пауза', CONTINUE:'Продолжить', IMPORTANT:'Важно', CLOSE:'Закрыть'}[s];
                    const active = task.status === s ? 'btn-primary' : 'btn-outline-secondary';
                    return `<button class="btn btn-sm ${active} rounded-pill px-3" onclick="updateTaskStatus('${s}')">${label}</button>`;
                }).join('')}
            </div>
        </div>

        <button class="btn btn-danger w-100 py-3 rounded-pill fw-bold mb-3" onclick="startRecording()">
            <i class="bi bi-camera-video-fill me-2"></i>ЗАПИСАТЬ ВИДЕО
        </button>
    `;
    loadTaskMedia(task.id);
}

function showTaskList() {
    taskListView.classList.remove('d-none');
    taskDetailView.classList.add('d-none');
    loadTasks();
}

async function updateTaskStatus(newStatus) {
    const baseUrl = localStorage.getItem('api_base_url');
    try {
        await fetch(`${baseUrl}/api/tasks/${currentTask.id}/`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: newStatus})
        });
        showToast('Статус обновлен');
        currentTask.status = newStatus;
        showTaskDetail(currentTask);
    } catch (err) {
        showToast('Статус изменен (локально)');
        currentTask.status = newStatus;
        showTaskDetail(currentTask);
    }
}

// Video Recording Logic
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' }, 
            audio: true 
        });
        const preview = document.getElementById('preview');
        preview.srcObject = stream;
        videoRecordView.classList.remove('d-none');
        
        mediaRecorder = new MediaRecorder(stream);
        recordedChunks = [];
        
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
        
        mediaRecorder.onstop = saveVideo;
        
        showToast('Камера готова');
    } catch (err) {
        alert('Ошибка камеры: ' + err.message);
    }
}

function toggleRecording() {
    const btn = document.getElementById('toggleRec');
    const indicator = document.getElementById('recIndicator');
    
    if (mediaRecorder.state === 'inactive') {
        // Start
        mediaRecorder.start();
        recordingStartTime = new Date();
        btn.innerHTML = '<i class="bi bi-stop-fill fs-1"></i>';
        indicator.classList.remove('d-none');
        startTimer();
    } else {
        // Stop
        mediaRecorder.stop();
        btn.innerHTML = '<i class="bi bi-record-fill fs-1"></i>';
        indicator.classList.add('d-none');
        stopTimer();
    }
}

function stopAndCancelRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    const stream = document.getElementById('preview').srcObject;
    if (stream) stream.getTracks().forEach(track => track.stop());
    videoRecordView.classList.add('d-none');
}

async function saveVideo() {
    const recordingEndTime = new Date();
    const blob = new Blob(recordedChunks, { type: 'video/webm' });
    
    stopAndCancelRecording();
    showToast('Сохранение видео...');

    const formData = new FormData();
    formData.append('file', blob, `mobile_task_${currentTask.id}_${Date.now()}.webm`);
    formData.append('task', currentTask.id);
    formData.append('title', `Запись к задаче #${currentTask.id}`);
    formData.append('recording_start', recordingStartTime.toISOString());
    formData.append('recording_end', recordingEndTime.toISOString());

    const baseUrl = localStorage.getItem('api_base_url');
    try {
        await fetch(`${baseUrl}/api/media/`, {
            method: 'POST',
            body: formData
        });
        showToast('Видео успешно сохранено');
        loadTaskMedia(currentTask.id);
    } catch (err) {
        showToast('Ошибка сохранения на сервер');
        // Локальная имитация для демо
        addLocalVideo(blob);
    }
}

// Timer for Recording
function startTimer() {
    let seconds = 0;
    const timerEl = document.getElementById('timer');
    timerInterval = setInterval(() => {
        seconds++;
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        timerEl.innerText = `${mins}:${secs}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    document.getElementById('timer').innerText = '00:00';
}

// Load Task Media
async function loadTaskMedia(taskId) {
    const baseUrl = localStorage.getItem('api_base_url');
    const videoList = document.getElementById('videoList');
    const videoCount = document.getElementById('videoCount');
    
    try {
        const response = await fetch(`${baseUrl}/api/media/?task=${taskId}`);
        const media = await response.json();
        videoCount.innerText = media.length;
        videoList.innerHTML = media.map(m => `
            <div class="col-4">
                <div class="video-thumb">
                    <video src="${m.file}"></video>
                    <i class="bi bi-play-fill position-absolute text-white fs-3"></i>
                </div>
            </div>
        `).join('');
    } catch (err) {
        // Fallback for empty
        videoCount.innerText = '0';
        videoList.innerHTML = '<div class="col-12 text-center py-3 text-muted small">Нет записей</div>';
    }
}

function addLocalVideo(blob) {
    const videoList = document.getElementById('videoList');
    const url = URL.createObjectURL(blob);
    const div = document.createElement('div');
    div.className = 'col-4';
    div.innerHTML = `<div class="video-thumb"><video src="${url}"></video><i class="bi bi-play-fill position-absolute text-white fs-3"></i></div>`;
    if (videoList.querySelector('.text-muted')) videoList.innerHTML = '';
    videoList.appendChild(div);
    document.getElementById('videoCount').innerText = videoList.children.length;
}

// Utils
function showToast(msg) {
    const toastEl = document.getElementById('liveToast');
    document.getElementById('toastMessage').innerText = msg;
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

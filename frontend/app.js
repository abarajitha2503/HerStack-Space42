const API = "http://localhost:8000";

let candidateId = null;
let sessionId = null;
let startTime = null;
let timerInterval = null;

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    document.getElementById(sectionId).classList.remove('hidden');
}

function addMessage(role, text) {
    const chatBox = document.getElementById('chatBox');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
    document.getElementById('typingIndicator').classList.remove('hidden');
}

function hideTyping() {
    document.getElementById('typingIndicator').classList.add('hidden');
}

function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        document.getElementById('timer').textContent = `⏱️ ${mins}:${secs.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
}

function updateScore(score) {
    const percent = Math.round(score * 100);
   // document.getElementById('score').textContent = `💯 ${percent}%`;
}

async function postJSON(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
    });
    return await res.json();
}

// Start Button
document.getElementById('btnStart').onclick = async () => {
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const target_role = document.getElementById('role').value;
    const fileInput = document.getElementById('cvFile');

    if (!name || !email) {
        document.getElementById('regHint').textContent = "Please enter your name and email";
        return;
    }

    if (!fileInput.files.length) {
        document.getElementById('regHint').textContent = "Please upload your CV";
        return;
    }

    document.getElementById('regHint').textContent = "Setting up your interview...";

    // Register
    const regData = await postJSON(`${API}/api/candidate/register`, {name, email, target_role});
    candidateId = regData.candidate_id;

    // Upload CV
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    const uploadRes = await fetch(`${API}/api/candidate/${candidateId}/upload_cv`, {
        method: "POST",
        body: fd
    });
    const uploadData = await uploadRes.json();

    if (!uploadData.ok) {
        document.getElementById('regHint').textContent = "Error uploading CV: " + uploadData.error;
        return;
    }

    // Start Interview
    const startData = await postJSON(`${API}/api/interview/start`, {candidate_id: candidateId});
    
    if (!startData.ok) {
        document.getElementById('regHint').textContent = "Error: " + startData.error;
        return;
    }

    sessionId = startData.session_id;

    // Switch to chat
    showSection('chat-section');
    startTimer();
    
    // Show first message
    showTyping();
    setTimeout(() => {
        hideTyping();
        addMessage('assistant', startData.question);
    }, 1000);
};

// Send Message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message || !sessionId) return;

    // Show user message
    addMessage('user', message);
    input.value = '';

    // Show typing
    showTyping();

    try {
        // Send to API
        const data = await postJSON(`${API}/api/interview/answer`, {
            session_id: sessionId,
            answer: message
        });

        hideTyping();

        if (!data.ok) {
            addMessage('assistant', 'Sorry, there was an error. Please try again.');
            console.error('API error:', data);
            return;
        }

        // Update score
        updateScore(data.last_accuracy || 0.5);

        // Check if ended
        if (data.ended) {
            stopTimer();
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;

            addMessage('assistant', data.message || data.stop_reason || 'Interview complete!');

            // Show completion screen
            setTimeout(() => {
                showSection('completion-section');
                
                const isQualified = data.stop_reason && data.stop_reason.toLowerCase().includes('qualified');
                document.getElementById('completionTitle').textContent = 
                    isQualified ? 'Congratulations! 🎉' : 'Interview Complete';
                document.getElementById('completionMessage').textContent = 
                    data.message || data.stop_reason || 'Thank you for your time!';
                document.getElementById('finalScore').textContent = 
                    Math.round((data.avg_accuracy || 0.5) * 100) + '%';
                document.getElementById('finalTime').textContent = `${mins}m ${secs}s`;
            }, 2000);
            return;
        }

        // Show next message
        addMessage('assistant', data.next_question || 'Please continue...');
        
    } catch (error) {
        hideTyping();
        console.error('Network error:', error);
        addMessage('assistant', 'Network error. Please check your connection and try again.');
    }
}
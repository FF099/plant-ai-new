    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');

    function getCSRFToken() {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
    }

    function appendMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
        messageDiv.innerText = text;
        chatBox.appendChild(messageDiv);

        chatBox.scrollTop = chatBox.scrollHeight;
    }

    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const message = userInput.value.trim();
        if (!message) return;

        appendMessage('user', message);
        userInput.value = '';

        // 🔥 loading message (เก็บไว้ลบทีหลัง)
        const loadingMessage = document.createElement('div');
        loadingMessage.classList.add('message', 'bot-message');
        loadingMessage.innerText = 'กำลังคิด...';
        chatBox.appendChild(loadingMessage);
        chatBox.scrollTop = chatBox.scrollHeight;

        fetch('/chat/api/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCSRFToken()
            },
            body: new URLSearchParams({
                'message': message
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.reply || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            loadingMessage.remove(); // ✅ ลบ loading
            appendMessage('bot', data.reply);
        })
        .catch(error => {
            loadingMessage.remove(); // ✅ ลบ loading
            appendMessage('bot', error.message);
            console.error('Error:', error);
        });
    });
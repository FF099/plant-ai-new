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
    messageDiv.classList.add(
        sender === 'user' ? 'user-message' : 'bot-message'
    );

    messageDiv.innerText = text;
    chatBox.appendChild(messageDiv);

    chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener('submit', function (e) {
    e.preventDefault();

    const message = userInput.value.trim();

    if (!message) return;

    // =====================================================
    // ยังไม่แสดงข้อความของ User ตรงนี้
    // เพราะต้องรอ Backend ตรวจสอบก่อนว่า
    // พิมพ์สลับภาษาหรือไม่ เช่น Fdlo -> โกสน
    // =====================================================

    userInput.value = '';

    // =====================================================
    // Loading message
    // =====================================================

    const loadingMessage = document.createElement('div');
    loadingMessage.classList.add('message', 'bot-message');
    loadingMessage.innerText = 'กำลังคิด...';

    chatBox.appendChild(loadingMessage);
    chatBox.scrollTop = chatBox.scrollHeight;

    // =====================================================
    // ส่งข้อความไป Django
    // =====================================================

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

    // =====================================================
    // รับข้อมูลจาก Django
    // =====================================================

    .then(response => {

        if (!response.ok) {

            return response.json().then(err => {
                throw new Error(
                    err.reply || 'Server error'
                );
            });

        }

        return response.json();
    })

    // =====================================================
    // แสดงผล
    // =====================================================

    .then(data => {

        // ลบ "กำลังคิด..."
        loadingMessage.remove();

        // =================================================
        // แสดงข้อความของ User
        //
        // ถ้า Backend แก้ Fdlo -> โกสน
        // จะใช้ "โกสน"
        //
        // ถ้าไม่มี normalized_message
        // จะ fallback กลับไปใช้ message เดิม
        // =================================================

        appendMessage(
            'user',
            data.normalized_message || message
        );

        // =================================================
        // แสดงคำตอบจาก AI
        // =================================================

        appendMessage(
            'bot',
            data.reply
        );
    })

    // =====================================================
    // กรณีเกิด Error
    // =====================================================

    .catch(error => {

        loadingMessage.remove();

        // ถ้าเกิด Error ก็ยังแสดงข้อความที่ผู้ใช้พิมพ์
        appendMessage(
            'user',
            message
        );

        appendMessage(
            'bot',
            error.message
        );

        console.error('Error:', error);
    });
});
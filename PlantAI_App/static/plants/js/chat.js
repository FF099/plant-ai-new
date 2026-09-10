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

    // คืนค่า element กลับไป เผื่อต้องแก้ข้อความทีหลัง
    // (เช่น กรณี backend normalize คำผิดให้)
    return messageDiv;
}

chatForm.addEventListener('submit', function (e) {
    e.preventDefault();

    const message = userInput.value.trim();

    if (!message) return;

    // =====================================================
    // แสดงข้อความของ User ทันที (Optimistic UI)
    //
    // เดิม: รอ Backend ตอบก่อนถึงจะแสดง ทำให้รู้สึกหน่วง
    // ใหม่: แสดงทันทีด้วยข้อความดิบที่พิมพ์
    //       แล้วถ้า Backend แก้คำผิดให้ (เช่น Fdlo -> โกสน)
    //       ค่อยไปแก้ข้อความใน element เดิมทีหลัง
    // =====================================================

    const userMessageEl = appendMessage('user', message);

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
        // ถ้า Backend แก้คำผิดให้ (normalized_message)
        // และต่างจากที่พิมพ์ไว้ตอนแรก
        // ให้คงข้อความเดิมที่พิมพ์ไว้ (เช่น "Fdlo")
        // แล้วแปะข้อความเล็กๆ บอกคำที่ถูกต้องต่อท้าย
        // =================================================

        if (
            data.normalized_message &&
            data.normalized_message !== message
        ) {
            const hintDiv = document.createElement('div');
            hintDiv.classList.add('normalized-hint');
            hintDiv.innerText = `คำที่คุณต้องการคือ "${data.normalized_message}"`;
            userMessageEl.appendChild(hintDiv);
        }

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

        // ข้อความ user แสดงไปแล้วตั้งแต่ต้น ไม่ต้อง append ซ้ำ

        appendMessage(
            'bot',
            error.message
        );

        console.error('Error:', error);
    });
});
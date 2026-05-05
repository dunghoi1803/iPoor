/* iPOOR Chatbot Logic with Markdown Support */
(function() {
    // Conversation state
    let conversationId = null;
    
    // Markdown + Sanitizer from local vendor
    const markedLib = window.marked;
    const DOMPurify = window.DOMPurify;
    
    const parseMarkdown = (text) => {
        let html = text || '';
        
        // Escape HTML first for security
        html = html.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Parse markdown
        if (typeof markedLib?.parse === 'function') {
            try {
                html = markedLib.parse(html, { breaks: true, gfm: true });
            } catch (e) {
                // Fallback to simple parser
                html = simpleParse(html);
            }
        } else {
            html = simpleParse(html);
        }
        
        // Sanitize with DOMPurify if available, otherwise basic whitelist
        if (typeof DOMPurify?.sanitize === 'function') {
            html = DOMPurify.sanitize(html, { ALLOWED_TAGS: ['p','br','strong','em','code','ul','ol','li','h1','h2','h3','h4','blockquote','table','thead','tbody','tr','th','td','a','span'] });
        } else {
            // Basic whitelist if no DOMPurify
            const allowedTags = ['p','br','strong','em','code','ul','ol','li','h1','h2','h3','h4','blockquote','table','thead','tbody','tr','th','td','a','span'];
            const allowedPattern = new RegExp('<' + '(?!/?(' + allowedTags.join('|') + ')\\b)[^>]*>', 'gi');
            html = html.replace(allowedPattern, '&lt;');
        }
        
        return html;
    };
    
    const simpleParse = (text) => {
        // Simple fallback markdown parser
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/^(\d+)\.\s+(.*?)$/gm, '<li>$2</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
    };
    
    const escapeHtml = (text) => {
        // Escape for user messages (no markdown)
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    };
    
    const chatbotHTML = `
        <div id="ipoor-chatbot-container">
            <div class="chat-bubble" id="chat-bubble">
                <svg viewBox="0 0 24 24"><path d="M12,2A10,10,0,0,0,2,12c0,3.42,1.72,6.44,4.33,8.23l-0.7,3.06a1,1,0,0,0,1.21,1.18l3.65-0.92A9.92,9.92,0,0,0,12,24a10,10,0,0,0,0-20ZM12,22a7.92,7.92,0,0,1-3.6-0.85,1,1,0,0,0-0.86-0.08L5,21.69l0.42-1.84a1,1,0,0,0-0.45-1.07A7.95,7.95,0,0,1,4,12,8,8,0,0,1,12,4a8,8,0,0,1,0,16ZM8,11a1,1,0,1,0,1,1A1,1,0,0,0,8,11Zm8,0a1,1,0,1,0,1,1A1,1,0,0,0,16,11Zm-4,6a3,3,0,0,0,2.6-1.5,1,1,0,1,0-1.73-1,1,1,0,0,1-1.74,0,1,1,0,1,0-1.73,1A3,3,0,0,0,12,17Z"/></svg>
                <div class="chat-badge">1</div>
            </div>
            <div class="chat-window" id="chat-window">
                <div class="chat-header">
                    <div class="chat-header-info">
                        <div class="chat-avatar">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M12,2A10,10,0,0,0,2,12c0,3.42,1.72,6.44,4.33,8.23l-0.7,3.06a1,1,0,0,0,1.21,1.18l3.65-0.92A9.92,9.92,0,0,0,12,24a10,10,0,0,0,0-20Z"/></svg>
                        </div>
                        <div>
                            <div class="chat-title">iPOOR Assistant</div>
                            <div class="chat-status">Trực tuyến</div>
                        </div>
                    </div>
                    <div class="chat-close" id="chat-close">
                        <svg width="20" height="20" fill="white" viewBox="0 0 24 24"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/></svg>
                    </div>
                </div>
                <div class="chat-body" id="chat-body">
                    <div class="chat-message message-bot">
                        Xin chào! Tôi là trợ lý ảo iPOOR. Tôi có thể giúp gì cho bạn hôm nay?
                        <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                    </div>
                </div>
                <div id="typing-indicator" class="typing" style="margin-left: 20px;">iPOOR đang trả lời...</div>
                <div class="chat-footer">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Nhập câu hỏi tại đây...">
                    <button class="chat-send" id="chat-send">
                        <svg width="20" height="20" fill="white" viewBox="0 0 24 24"><path d="M2,21L23,12L2,3V10L17,12L2,14V21Z"/></svg>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Append HTML
    const div = document.createElement('div');
    div.innerHTML = chatbotHTML;
    document.body.appendChild(div);

    // Elements
    const bubble = document.getElementById('chat-bubble');
    const windowEl = document.getElementById('chat-window');
    const closeBtn = document.getElementById('chat-close');
    const sendBtn = document.getElementById('chat-send');
    const inputEl = document.getElementById('chat-input');
    const bodyEl = document.getElementById('chat-body');
    const typingIndicator = document.getElementById('typing-indicator');

    // Toggle
    bubble.addEventListener('click', () => {
        windowEl.classList.toggle('active');
        document.querySelector('.chat-badge').style.display = 'none';
    });

    closeBtn.addEventListener('click', () => {
        windowEl.classList.remove('active');
    });

    // Send
    async function sendMessage() {
        const text = inputEl.value.trim();
        if (!text) return;

        // User message - escape plain (no markdown)
        addMessage(escapeHtml(text), 'user');
        inputEl.value = '';

        typingIndicator.style.display = 'block';
        bodyEl.scrollTop = bodyEl.scrollHeight;

        try {
            const token = localStorage.getItem('ipoor_access_token') || sessionStorage.getItem('ipoor_access_token');
            const apiUrl = window.IPOOR_API_BASE || 'http://localhost:8000';

            const response = await fetch(`${apiUrl}/chatbot/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: JSON.stringify({ 
                    message: text,
                    conversation_id: conversationId
                })
            });

            const data = await response.json();
            typingIndicator.style.display = 'none';
            
            // Save conversation_id for next message
            if (data.conversation_id) {
                conversationId = data.conversation_id;
            }
            
            // Bot message - parse markdown
            addMessage(data.reply || 'Xin lỗi, tôi không thể trả lời câu hỏi này lúc này.', 'bot');
            
        } catch (error) {
            console.error('Chatbot error:', error);
            typingIndicator.style.display = 'none';
            addMessage('Đã có lỗi xảy ra khi kết nối với máy chủ. Vui lòng thử lại sau.', 'bot');
        }
    }

    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message message-${sender}`;
        
        // Parse markdown for bot, escape for user
        const content = sender === 'bot' ? parseMarkdown(text) : escapeHtml(text);
        
        msgDiv.innerHTML = `
            <div class="message-content">${content}</div>
            <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
        `;
        bodyEl.appendChild(msgDiv);
        bodyEl.scrollTop = bodyEl.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

})();
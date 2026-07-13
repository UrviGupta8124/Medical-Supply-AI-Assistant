document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const sendButton = document.getElementById('send-button');
  const chatMessagesContainer = document.getElementById('chat-messages');
  const navItems = document.querySelectorAll('.h-nav-item');

  let messages = [];
  let isLoading = false;

  chatInput.focus();

  // Navigation Button Logic
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      if (isLoading) return;

      // Update active state
      navItems.forEach(nav => nav.classList.remove('active'));
      item.classList.add('active');

      const btnText = item.textContent.trim();
      
      let query = "";
      if (btnText === 'Medical Protocols') query = "Provide a comprehensive overview of all Defense Medical Protocols, including TCCC, Trauma, Emergency, Environmental, CBRN, MEDEVAC, and Mental Health.";
      else if (btnText === 'Drug & Treatment') query = "Show me the available inventory for drugs and treatments.";
      else if (btnText === 'Clinical Guidelines') query = "Provide a summary of the Defense clinical guidelines for general medical and emergency care.";
      else if (btnText === 'First Aid & Triage') query = "What is the Defense First Aid and Triage protocol for massive hemorrhage?";
      else if (btnText === 'Field Manual') query = "Summarize the Defense MARCH PAWS field manual algorithm.";

      if (query) {
        chatInput.value = query;
        sendButton.disabled = false;
        // Trigger form submission
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // Quick Access Button Logic
  const quickBtns = document.querySelectorAll('.quick-btn');
  quickBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (isLoading) return;
      
      const btnText = btn.querySelector('span').textContent.trim();
      let query = "";
      if (btnText === 'Trauma Care') query = "What are the specific Defense Trauma Management Protocols for injuries like gunshot wounds, blast injuries, and burns?";
      else if (btnText === 'CPR Guidelines') query = "What are the Defense Emergency Medical Protocols for Cardiac Emergencies like CPR?";
      else if (btnText === 'Battlefield Medicine') query = "Explain the Defense TCCC MARCH Algorithm.";
      else if (btnText === 'Evacuation Protocols') query = "What are the Defense Medical Evacuation (MEDEVAC) procedures and 9-Line request?";

      if (query) {
        chatInput.value = query;
        sendButton.disabled = false;
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // Input Validation
  chatInput.addEventListener('input', () => {
    sendButton.disabled = !chatInput.value.trim() || isLoading;
  });

  // Helper to scroll to bottom
  function scrollToBottom() {
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  // Helper to get time
  function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    minutes = minutes < 10 ? '0' + minutes : minutes;
    return hours + ':' + minutes + ' ' + ampm;
  }

  // Create Message Element
  function createMessageElement(id, role, content) {
    const wrapper = document.createElement('div');
    wrapper.id = id;
    wrapper.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // For bot, parse markdown. For user, text.
    if (role === 'bot') {
      contentDiv.innerHTML = marked.parse(content);
    } else {
      contentDiv.textContent = content;
    }

    // Add timestamp
    const timeSpan = document.createElement('div');
    timeSpan.style.fontSize = '0.7rem';
    timeSpan.style.marginTop = '8px';
    timeSpan.style.textAlign = 'right';
    timeSpan.style.opacity = '0.7';
    timeSpan.textContent = getCurrentTime() + (role === 'user' ? ' ✓✓' : '');
    
    contentDiv.appendChild(timeSpan);
    wrapper.appendChild(contentDiv);
    
    return wrapper;
  }

  // Handle Form Submission
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || isLoading) return;

    // Add user message
    const userMsg = { role: 'user', content: text };
    const userMsgId = 'msg-' + Date.now();
    messages.push(userMsg);
    
    chatMessagesContainer.appendChild(createMessageElement(userMsgId, 'user', text));
    chatInput.value = '';
    sendButton.disabled = true;
    isLoading = true;
    scrollToBottom();

    // Prepare for bot response
    const botMsgId = 'msg-' + (Date.now() + 1);
    const botWrapper = createMessageElement(botMsgId, 'bot', '...');
    chatMessagesContainer.appendChild(botWrapper);
    const botContentDiv = botWrapper.querySelector('.message-content');

    let botFullContent = '';

    try {
      const response = await fetch('http://localhost:5001/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messages }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      botContentDiv.innerHTML = ''; // clear '...'

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        botFullContent += chunk;
        
        // Update HTML with parsed markdown
        botContentDiv.innerHTML = marked.parse(botFullContent);
        
        // Add timestamp back
        const timeSpan = document.createElement('div');
        timeSpan.style.fontSize = '0.7rem';
        timeSpan.style.marginTop = '8px';
        timeSpan.style.textAlign = 'right';
        timeSpan.style.opacity = '0.7';
        timeSpan.textContent = getCurrentTime();
        botContentDiv.appendChild(timeSpan);
        
        scrollToBottom();
      }

      messages.push({ role: 'bot', content: botFullContent });

    } catch (error) {
      console.error('Error fetching from backend:', error);
      botContentDiv.innerHTML = '<span style="color:red;">Error connecting to Defense Intranet.</span>';
    } finally {
      isLoading = false;
      sendButton.disabled = !chatInput.value.trim();
      chatInput.focus();
    }
  });
});

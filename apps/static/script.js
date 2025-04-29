document.addEventListener("DOMContentLoaded", () => {
    const csrfTokenElement = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenElement ? csrfTokenElement.getAttribute('content') : '';

    // 채팅 관련 요소
    const chatForm = document.getElementById('chat-form');
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');

    // 오디오 관련 요소
    const audioInput = document.getElementById('audio-input');
    const uploadAudioBtn = document.getElementById('upload-audio-btn');

    // 녹음 관련 요소
    const recordBtn = document.getElementById('record-btn');
    const stopBtn = document.getElementById('stop-btn');
    const recordingStatus = document.getElementById('recording-status');
    const audioPlayback = document.getElementById('audio-playback');
    let mediaRecorder;
    let audioChunks = [];

    // 페이지 로드 시 세션 초기화
    resetSession();

    // === 채팅 폼 제출 ===
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();

        if (message === "") return;

        appendMessage("user", message);
        userInput.value = "";
        userInput.disabled = true;

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken, // CSRF 토큰
                },
                body: JSON.stringify({ 
                    message: message,
                }), 
            });

            if (!response.ok) {
                const errorData = await response.text();
                console.error("Failed to send message:", errorData);
                appendMessage("assistant", "죄송합니다. 메시지 전송에 실패했습니다.");
                return;
            }

            const data = await response.json();
            console.log("Received chat response:", data);

            if (data.response) {
                appendMessage("assistant", data.response, data.tts_url, data.message_id);
            } else {
                appendMessage("assistant", "죄송합니다. 응답이 없습니다.");
                console.error("No response in data:", data);
            }
        } catch (error) {
            appendMessage("assistant", "죄송합니다. 서버에 문제가 발생했습니다.");
            console.error("Error:", error);
        } finally {
            userInput.disabled = false;
            userInput.focus();
        }
    });

    // === 녹음 시작 버튼 ===
    recordBtn.addEventListener("click", () => {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    mediaRecorder = new MediaRecorder(stream);
                    mediaRecorder.start();
                    console.log("MediaRecorder started");
                    recordingStatus.textContent = "녹음 중...";
                    recordBtn.disabled = true;
                    stopBtn.disabled = false;
                    audioChunks = [];

                    const recordingTimeout = setTimeout(() => {
                        if (mediaRecorder && mediaRecorder.state !== "inactive") {
                            mediaRecorder.stop();
                        }
                    }, 20000); // 최대 20초 녹음

                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                        console.log("Data available:", event.data);
                    };

                    mediaRecorder.onstop = () => {
                        clearTimeout(recordingTimeout);
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        sendAudio(audioBlob);
                        recordingStatus.textContent = "녹음 중지됨";
                        recordBtn.disabled = false;
                        stopBtn.disabled = true;

                        // 오디오 재생 (로컬 확인용)
                        const audioURL = URL.createObjectURL(audioBlob);
                        audioPlayback.src = audioURL;
                        audioPlayback.style.display = 'block';
                        console.log("Recording stopped and audio playback ready");
                    };
                })
                .catch(err => {
                    console.error("오디오 접근 권한이 거부되었습니다:", err);
                    alert("오디오 접근 권한을 허용해 주세요.");
                });
        } else {
            alert("이 브라우저는 오디오 녹음을 지원하지 않습니다.");
        }
    });

    // === 녹음 중지 버튼 ===
    stopBtn.addEventListener("click", () => {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }
    });

    // === 음성 업로드 버튼 ===
    uploadAudioBtn.addEventListener("click", async () => {
        const file = audioInput.files[0];
        if (!file) {
            alert("업로드할 음성 파일을 선택해주세요.");
            return;
        }

        // 업로드 전, 로컬에서 재생 확인
        const audioURL = URL.createObjectURL(file);
        audioPlayback.src = audioURL;
        audioPlayback.style.display = 'block';

        const formData = new FormData();
        formData.append('audio', file);

        appendMessage("user", "음성 메시지를 업로드 중입니다...");

        try {
            const response = await fetch('/upload_audio', {
                method: 'POST',
                body: formData,
                
                credentials: 'same-origin',
            });

            if (!response.ok) {
                const errorData = await response.text();
                console.error("Failed to upload audio:", errorData);
                appendMessage("assistant", "죄송합니다. 음성 업로드에 실패했습니다.");
                return;
            }

            const data = await response.json();
            console.log("Received upload_audio response:", data);

            if (data.transcript) {
                // 업로드 완료 후, 음성인식 결과를 user 메시지로 표시
                appendMessage("user", data.transcript);
                // 텍스트를 /chat 에 다시 전송
                await sendMessage(data.transcript);
            } else {
                appendMessage("assistant", "죄송합니다. 음성 인식에 실패했습니다.");
                console.error("Invalid response data:", data);
            }
        } catch (error) {
            appendMessage("assistant", "죄송합니다. 음성 업로드 중 오류가 발생했습니다.");
            console.error("Error:", error);
        }
    });

    // === 오디오를 서버로 전송하는 함수 ===
    async function sendAudio(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        try {
            const response = await fetch('/upload_audio', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
            });

            if (!response.ok) {
                const errorData = await response.text();
                console.error("Failed to upload audio:", errorData);
                appendMessage("assistant", "죄송합니다. 음성 업로드에 실패했습니다.");
                return;
            }

            const data = await response.json();
            console.log("Received upload_audio response:", data);

            if (data.transcript) {
                appendMessage("user", data.transcript);
                await sendMessage(data.transcript);
            } else {
                appendMessage("assistant", "죄송합니다. 음성 인식에 실패했습니다.");
                console.error("Invalid response data:", data);
            }
        } catch (error) {
            appendMessage("assistant", "죄송합니다. 음성 업로드 중 오류가 발생했습니다.");
            console.error("Error:", error);
        }
    }

    // === 텍스트 메시지를 서버로 전송 ===
    async function sendMessage(message) {
        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    
                },
                body: JSON.stringify({ 
                    message: message,
                }), 
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("Failed to send message:", errorData);
                appendMessage("assistant", "죄송합니다. 메시지 전송에 실패했습니다.");
                return;
            }

            const data = await response.json();
            console.log("Received chat response:", data);

            if (data.response) {
                appendMessage("assistant", data.response, data.tts_url, data.message_id);
            } else {
                appendMessage("assistant", "죄송합니다. 응답이 없습니다.");
                console.error("No response in data:", data);
            }
        } catch (error) {
            appendMessage("assistant", "죄송합니다. 서버에 문제가 발생했습니다.");
            console.error("Error:", error);
        }
    }

    // === 메시지를 채팅 박스에 추가 ===
    function appendMessage(sender, message, ttsUrl = "", messageId = null) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message", sender);
        
        if (sender === "assistant" && messageId) {
            messageElement.dataset.messageId = messageId;
            console.log(`Message ID set: ${messageId}`);
        }
    
        let displayText = "";
  if (sender === "assistant") {
    // bot -> "아리 봇" 표시
    displayText = `아리 봇: ${message}`;
  } else if (sender === "user") {
    // user -> prefix 없이 메시지 내용만
    displayText = message;
  } else {
    // 그 외 sender가 있다면 fallback
    displayText = `${sender}: ${message}`;
  }
        const messageText = document.createElement("p");
        messageText.innerText = displayText;
        messageElement.appendChild(messageText);
    
        // TTS 자동 재생
        if (ttsUrl) {
            const audioElement = document.createElement("audio");
            audioElement.src = ttsUrl;
            audioElement.autoplay = true;
            audioElement.controls = true; // 사용자가 오디오 제어 가능
            messageElement.appendChild(audioElement);
    
            // 자동 재생 시작 시 로그
            audioElement.addEventListener('play', () => {
                console.log("TTS 자동 재생 시작:", ttsUrl);
            });
    
            // 자동 재생 실패 시, 사용자에게 알림
            audioElement.addEventListener('error', (e) => {
                console.error("TTS 자동 재생 오류:", e);
                alert("음성 재생 중 오류가 발생했습니다.");
            });
        }
        
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // === 세션 초기화 ===
    function resetSession() {
        fetch("/reset", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                //"X-CSRFToken": csrfToken, // /reset 엔드포인트가 CSRF를 필요로 하는지 확인
            },
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => { throw new Error(text) });
            }
            return response.json();
        })
        .then(data => {
            console.log("Session reset:", data);
            // 채팅 창 초기화
            chatBox.innerHTML = "";
            
            // 추천 메시지 가져오기
            const recommendation = data.recommendation || "새로운 대화를 시작하세요.";
            appendMessage("assistant", recommendation, data.tts_url, data.message_id);
        })
        .catch(error => {
            console.error("Error resetting session:", error);
            appendMessage("assistant", "세션 초기화에 실패했습니다.", "", null);
        });
    }
});

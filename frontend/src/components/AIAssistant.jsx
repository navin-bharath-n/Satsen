import { useEffect, useRef, useState } from "react";
import axios from "axios";
import "./AIAssistant.css";

const API = "http://127.0.0.1:8000";

function AIAssistant({ events, userLocation }) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [hasGreeted, setHasGreeted] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [inputText, setInputText] = useState("");
  const [chatHistory, setChatHistory] = useState([
    { sender: "SATSEN JARVIS AI", text: "Hello Boss! I am SATSEN JARVIS AI. Tap the microphone or type below to ask about active fires or escape routes." }
  ]);

  const initialGreeting = "Hello Boss! I am SATSEN JARVIS AI. Tap the microphone or type below to ask about active fires or escape routes.";

  const recognitionRef = useRef(null);
  const listeningRef = useRef(listening);
  const eventsRef = useRef(events);

  useEffect(() => {
    listeningRef.current = listening;
  }, [listening]);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  const processQuery = async (queryText) => {
    if (!queryText.trim()) return;

    // Add user message to UI
    setChatHistory(prev => [...prev, { sender: "Commander (You)", text: queryText }]);
    setInputText("");

    try {
      const res = await axios.post(`${API}/openai-disaster-chat`, {
        message: queryText,
        events: eventsRef.current,
        user_lat: userLocation?.lat,
        user_lon: userLocation?.lon
      });

      const reply = res.data.reply;
      setChatHistory(prev => [...prev, { sender: "AI Core", text: reply }]);
      speak(reply);
    } catch (err) {
      console.error(err);
      setChatHistory(prev => [...prev, { sender: "AI Core", text: "Error connecting to the AI core." }]);
    }
  };

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setChatHistory(prev => [...prev, { sender: "AI Core", text: "Speech recognition is not supported in this browser." }]);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let currentTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }

      setTranscript(currentTranscript);

      if (event.results[0].isFinal) {
        processQuery(currentTranscript);
        setListening(false);
      }
      if (currentTranscript) {
        setTranscript(currentTranscript);
      } else {
        setTranscript("");
      }
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognition.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'audio-capture') {
        setListening(false);
        setChatHistory(prev => [...prev, { sender: "AI Core", text: "Microphone access is blocked or no microphone was detected. Please check your browser permissions." }]);
        setIsOpen(true);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      window.speechSynthesis.cancel();
    };
  }, []);

  const handleTextSubmit = (e) => {
    e.preventDefault();
    processQuery(inputText);
  };

  const speak = (text) => {
    window.speechSynthesis.cancel(); // Cancel any ongoing speech

    const msg = new SpeechSynthesisUtterance(text);

    // Attempt to find a female voice
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v =>
      v.name.toLowerCase().includes("female") ||
      v.name.toLowerCase().includes("girl") ||
      v.name.toLowerCase().includes("zira") || // Microsoft Zira (common Windows female voice)
      v.name.toLowerCase().includes("samantha") // macOS common female voice
    );

    if (femaleVoice) {
      msg.voice = femaleVoice;
    }

    msg.rate = 1.0;
    msg.pitch = 1.2; // Slightly higher pitch for a more female/friendly tone
    msg.volume = 1;

    msg.onstart = () => setSpeaking(true);
    msg.onend = () => setSpeaking(false);
    msg.onerror = () => setSpeaking(false);

    window.speechSynthesis.speak(msg);
  };

  // Ensure voices are loaded (especially for some browsers where it's async)
  useEffect(() => {
    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.getVoices();
    };
  }, []);

  const toggleListen = () => {
    if (!recognitionRef.current) return;

    if (listening) {
      recognitionRef.current.stop();
      setListening(false);
    } else {
      setTranscript("Listening...");
      setListening(true);
      window.speechSynthesis.cancel();
      setSpeaking(false);
      recognitionRef.current.start();
    }

    if (!isOpen) setIsOpen(true);
  };

  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  };

  return (
    <div className={`ai-assistant-container ${isOpen ? 'open' : ''}`}>
      {/* Expanding Panel */}
      <div className="ai-panel">
        <div className="ai-panel-header">
          <h3>🎙️ SATSEN JARVIS AI</h3>
          <button className="close-btn" onClick={() => setIsOpen(false)}>×</button>
        </div>

        <div className="ai-chat-area">
          {chatHistory.map((chat, idx) => (
            <div key={idx} className={`chat-bubble ${chat.sender === "SATSEN JARVIS AI" ? "ai-bubble" : "user-bubble"}`}>
              <span className="sender">{chat.sender}</span>
              <p>{chat.text}</p>
            </div>
          ))}

          {transcript && (
            <div className={`chat-bubble user-bubble pulsing-text`}>
              <span className="sender">Commander (You)</span>
              <p>{transcript}</p>
            </div>
          )}
        </div>

        <form className="ai-input-area" onSubmit={handleTextSubmit}>
          <input
            type="text"
            placeholder="Type your command..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button type="submit" className="send-btn">🚀</button>
        </form>

        {speaking && (
          <button className="stop-speech-btn" onClick={stopSpeaking}>
            🛑 Stop Audio
          </button>
        )}
      </div>

      {/* Main Floating Button */}
      <div
        className={`ai-voice-button ${listening ? "listening" : ""} ${speaking ? "speaking" : ""}`}
        onClick={() => {
          if (!isOpen && !listening) {
            setIsOpen(true);
            if (!hasGreeted) {
              setHasGreeted(true);
              speak(initialGreeting);
            }
            // Add a small delay so the panel opens before the mic prompts for permission/starts
            setTimeout(() => {
              if (!listening) toggleListen();
            }, 500);
          } else {
            toggleListen();
          }
        }}
        title="Voice Assistant"
      >
        <div className="mic-icon">{listening ? "🔴" : speaking ? "🔊" : "🎤"}</div>
        <div className="waves"></div>
      </div>
    </div>
  );
}

export default AIAssistant;

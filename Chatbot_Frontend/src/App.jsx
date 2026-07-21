import { useState, useRef, useEffect } from "react";
import "./App.css";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello, I am your AI virtual Invigilator & support assistant. How can I help you today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();

    if (!input.trim() || isLoading) return;
    const userMessage = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
      { role: "assistant", content: "" },
    ]);

    const historyPayload = messages
      .filter((msg) => msg.content && msg.content.trim() !== "")
      .map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, history: historyPayload }),
      });

      if (!response.ok) throw new Error("Failed to connect to backend.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let streamResponse = "";
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataContent = trimmed.slice(6).trim();

            if (dataContent === "[Done]") {
              break;
            }

            try {
              const parsed = JSON.parse(dataContent);

              if (parsed.error) {
                streamResponse = `Error: ${parsed.error}`;
              }
              if (parsed.token) {
                streamResponse += parsed.token;
              }

              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: streamResponse,
                };
                return updated;
              });
            } catch (err) {}
          }
        }
      }
    } catch (error) {
      console.error("Streaming error: ", error);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content:
            "Error connecting to server. Make sure your FastAPI backend is running on port 8000.",
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h2>M-20 Exam Assistant And Exam Invigilator</h2>
        <span className="status-badge">Live</span>
      </header>
      <div className="messages-box">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-bubble ${msg.role}`}>
            <div className="sender-tag">
              {msg.role === "user" ? "You" : "AI assistant "}
            </div>
            <div className="message-text">
              {msg.content ||
                (isLoading && idx === messages.length - 1 ? "Typing..." : "")}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form onSubmit={sendMessage} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about exam rules or support..."
          disabled={isLoading}
        />

        <button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}

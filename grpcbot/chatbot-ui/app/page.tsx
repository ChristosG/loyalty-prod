// app/page.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import Navbar from "../components/Navbar";
import ChatWindow from "../components/ChatWindow";
import InputArea from "../components/InputArea";
import SettingsPanel from "../components/SettingsPanel";
import { FaArrowDown, FaThumbsUp, FaThumbsDown } from "react-icons/fa";

type ChatMessage = {
  role: "user" | "bot";
  content: string;
};

function mergeToken(current: string, token: string): string {
  let maxOverlap = 0;
  const len = Math.min(current.length, token.length);
  for (let i = 1; i <= len; i++) {
    if (current.slice(-i) === token.slice(0, i)) {
      maxOverlap = i;
    }
  }
  return current + token.slice(maxOverlap);
}

// RecommendationClient Component with new "userSubmitted" prop
const RecommendationClient: React.FC<{
  setInputArea: React.Dispatch<React.SetStateAction<boolean>>;
  isInputActive: boolean;
  userSubmitted: boolean;
}> = ({ setInputArea, isInputActive, userSubmitted }) => {
  const [showOptions, setShowOptions] = useState(false);
  const [optionsDisliked, setOptionsDisliked] = useState(false);
  const [showMessage, setShowMessage] = useState(true);

  useEffect(() => {
    // Hide message if the input is active or if the user has already submitted an input
    if (isInputActive || userSubmitted) {
      setShowMessage(false);
    } else if (optionsDisliked && !userSubmitted) {
      setShowMessage(true);
    }
  }, [isInputActive, optionsDisliked, userSubmitted]);

  const handleDislikeInitial = () => {
    setShowOptions(true);
    setShowMessage(false); // Hide the message when options are displayed
  };

  const handleDislikeOptions = () => {
    setOptionsDisliked(true);
    setInputArea(true);
    setShowOptions(false); // Hide options when disliked
    setShowMessage(true); // Show the message container initially
  };

  const handleLikeOption = () => {
    setShowOptions(false); // Hide options when any option is liked
    setShowMessage(false);
  };

  return (
    <div className="my-6 flex justify-center">
      <div className="w-full max-w-md">
        {/* Initial recommendation */}
        {!showOptions && !optionsDisliked && (
          <div className="p-6 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4 text-center">
              Recommendation for you:
            </p>
            <p className="text-gray-700 dark:text-gray-300 mb-4 text-center">
              Based on your history we recommend you a Dinner at Burger King (2000 pts)
            </p>
            <div className="flex justify-center space-x-4">
              <button
                className="group flex items-center justify-center px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-green-400 transition-colors duration-200 shadow-sm hover:shadow-md"
                aria-label="Like"
                onClick={() => {}}
              >
                <FaThumbsUp className="mr-2" />
                <span className="hidden group-hover:inline">Reedem</span> 
              </button>
              <button
                className="group flex items-center justify-center px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-red-400 transition-colors duration-200 shadow-sm hover:shadow-md"
                onClick={handleDislikeInitial}
                aria-label="Dislike"
              >
                <FaThumbsDown className="mr-2" />
                <span className="hidden group-hover:inline">Show more</span> 
              </button>
            </div>
          </div>
        )}

        {/* Alternative options */}
        {showOptions && !optionsDisliked && (
          <div className="p-6 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4 text-center">
              Alternative Suggestions:
            </p>
            <p className="text-gray-700 dark:text-gray-300 mb-4 text-center">
              Choose from these related options:
            </p>
            <div className="grid grid-cols-2 gap-4 mb-4">
              {["McDonlads", "KFC", "Domino's Pizza", "Wolt"].map((option, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-gray-200 dark:bg-gray-700 rounded-md hover:shadow-inner transition-shadow duration-200"
                >
                  <span className="text-gray-800 dark:text-gray-200 font-medium">{option}</span>
                  <button
                    className="group flex items-center justify-center p-2 bg-green-500 hover:bg-green-600 text-white rounded-full focus:outline-none focus:ring-2 focus:ring-green-400 transition-colors duration-200 shadow-sm hover:shadow-md"
                    aria-label={`Like ${option}`}
                    onClick={handleLikeOption}
                  >
                    <FaThumbsUp />
                  </button>
                </div>
              ))}
            </div>
            <button
              className="w-full px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-red-400 transition-colors duration-200 shadow-sm hover:shadow-md"
              onClick={handleDislikeOptions}
              aria-label="Dislike all options"
            >
              <FaThumbsDown className="mr-2" /> Chat with Assistant for more
            </button>
          </div>
        )}

        {/* Message container */}
        {optionsDisliked && showMessage && (
          <div className="p-6 bg-yellow-100 dark:bg-yellow-800 rounded-lg shadow-md text-center">
            <p className="text-gray-800 dark:text-yellow-200 font-semibold">
              Didn't find what you were looking for?
            </p>
            <p className="text-gray-700 dark:text-yellow-300 mt-2">
              Tell us more about what interests you, and we'll find the best options for you!
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default function ChatPage() {
  const [maxTokens, setMaxTokens] = useState<number>(512);
  const [temperature, setTemperature] = useState<number>(0.0);
  const [topK, setTopK] = useState<number>(1);
  const [topP, setTopP] = useState<number>(0.95);
  const [repetitionPenalty, setRepetitionPenalty] = useState<number>(1.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState<number>(0.0);
  const [presencePenalty, setPresencePenalty] = useState<number>(0.0);

  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [prompt, setPrompt] = useState("");
  const [conversations, setConversations] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [showInputArea, setShowInputArea] = useState(false);
  const [isInputActive, setIsInputActive] = useState(false);

  // New state to track if the user has submitted at least one message
  const [hasUserSubmitted, setHasUserSubmitted] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const pendingBotMessageRef = useRef<string>("");
  const updateScheduledRef = useRef<boolean>(false);
  const userInterruptedScroll = useRef<boolean>(false);

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const profiles = [
    {
      name: "LessHelu",
      maxTokens: 1024,
      temperature: 0.1,
      topK: 40,
      topP: 0.9,
      repetitionPenalty: 1.1,
      frequencyPenalty: 0.05,
      presencePenalty: 0.05,
    },
    {
      name: "Default",
      maxTokens: 1024,
      temperature: 0.0,
      topK: 40,
      topP: 0.95,
      repetitionPenalty: 1.0,
      frequencyPenalty: 0.0,
      presencePenalty: 0.0,
    },
    // {
    //   name: "Creative",
    //   maxTokens: 1024,
    //   temperature: 0.55,
    //   topK: 50,
    //   topP: 0.8,
    //   repetitionPenalty: 1.1,
    //   frequencyPenalty: 0.1,
    //   presencePenalty: 0.05,
    // },
  ];

  const [selectedProfileIndex, setSelectedProfileIndex] = useState(0);

  const switchToProfile = (index: number) => {
    const p = profiles[index];
    setMaxTokens(p.maxTokens);
    setTemperature(p.temperature);
    setTopK(p.topK);
    setTopP(p.topP);
    setRepetitionPenalty(p.repetitionPenalty);
    setFrequencyPenalty(p.frequencyPenalty);
    setPresencePenalty(p.presencePenalty);
    setSelectedProfileIndex(index);
  };

  useEffect(() => {
    switchToProfile(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const isNearBottom = () => {
      if (!chatContainerRef.current) return true;
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      return scrollHeight - scrollTop <= clientHeight + 100;
    };

    const checkAutoScroll = () => {
      if (!chatContainerRef.current) return;

      if (userInterruptedScroll.current) {
        if (!isNearBottom()) {
          return;
        }
        setAutoScroll(true);
        userInterruptedScroll.current = false;
      }

      if (autoScroll) {
        chatContainerRef.current.scrollTo({ top: chatContainerRef.current.scrollHeight, behavior: "smooth" });
      }
    };

    if (pendingBotMessageRef.current && chatContainerRef.current) {
      checkAutoScroll();
    }
  }, [conversations, autoScroll]);

  const toggleSettings = () => {
    setShowSettings((prev) => !prev);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setConversations((prev) => [
      ...prev,
      { role: "user", content: prompt },
      { role: "bot", content: "" },
    ]);
    pendingBotMessageRef.current = "";
    userInterruptedScroll.current = false;
    setAutoScroll(true);
    setIsInputActive(false);

    // Mark that the user has submitted at least one message
    setHasUserSubmitted(true);

    const payload = {
      prompt,
      max_tokens: maxTokens,
      temperature,
      top_k: topK,
      top_p: topP,
      repetition_penalty: repetitionPenalty,
      frequency_penalty: frequencyPenalty,
      presence_penalty: presencePenalty,
    };

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    let wsPort = "";

    if (window.location.hostname === "localhost") {
      wsPort = ":7000";
    }

    const ws = new WebSocket(`${wsProtocol}://${window.location.hostname}${wsPort}/ws`);

    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      ws.send(JSON.stringify(payload));
    };

    ws.onmessage = (event) => {
      const token = event.data;
      pendingBotMessageRef.current = mergeToken(pendingBotMessageRef.current, token);

      if (!updateScheduledRef.current) {
        updateScheduledRef.current = true;
        setTimeout(() => {
          setConversations((prev) => {
            const updated = [...prev];
            const lastIndex = updated.length - 1;
            if (updated[lastIndex].role === "bot") {
              updated[lastIndex].content = pendingBotMessageRef.current;
            }
            return updated;
          });
          updateScheduledRef.current = false;
        }, 20);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error: ", error);
      setIsConnected(false);
    };

    setPrompt("");
  };

  const handleScroll = () => {
    if (!chatContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop <= clientHeight + 5;

    if (!isAtBottom) {
      setAutoScroll(false);
      userInterruptedScroll.current = true;
    }
  };

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({ top: chatContainerRef.current.scrollHeight, behavior: "smooth" });
      setAutoScroll(true);
      userInterruptedScroll.current = false;
    }
  };

  return (
    <div className={`min-h-screen flex flex-col ${theme === "dark" ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-900"}`}>
      <Navbar
        theme={theme}
        toggleTheme={toggleTheme}
        toggleSettings={toggleSettings}
        profiles={profiles}
        selectedProfileIndex={selectedProfileIndex}
        onSelectProfile={switchToProfile}
      />

      {showSettings && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-50 z-40 flex items-start justify-center">
          <SettingsPanel
            maxTokens={maxTokens}
            setMaxTokens={setMaxTokens}
            temperature={temperature}
            setTemperature={setTemperature}
            topK={topK}
            setTopK={setTopK}
            topP={topP}
            setTopP={setTopP}
            repetitionPenalty={repetitionPenalty}
            setRepetitionPenalty={setRepetitionPenalty}
            frequencyPenalty={frequencyPenalty}
            setFrequencyPenalty={setFrequencyPenalty}
            presencePenalty={presencePenalty}
            setPresencePenalty={setPresencePenalty}
            closePanel={() => setShowSettings(false)}
          />
        </div>
      )}

      <div className="flex-1 overflow-hidden mt-16">
        <ChatWindow
          conversations={conversations}
          containerRef={chatContainerRef}
          theme={theme}
          onScroll={() => {}}
        />
      </div>

      <div className="sticky bottom-0">
        <RecommendationClient
          setInputArea={setShowInputArea}
          isInputActive={isInputActive}
          userSubmitted={hasUserSubmitted} // Pass the flag to control the message container
        />
        {showInputArea && (
          <InputArea
            prompt={prompt}
            setPrompt={setPrompt}
            handleSubmit={handleSubmit}
            isConnected={isConnected}
            setIsInputActive={setIsInputActive}
          />
        )}
      </div>
    </div>
  );
}

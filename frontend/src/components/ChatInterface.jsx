import React, { useState, useRef, useEffect } from 'react';
import api from '../services/api';
import { Send, Bot, User as UserIcon, AlertCircle, Mic, MicOff, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

const ChatInterface = () => {
    // Get unique storage key based on user email AND role
    const getStorageKey = () => {
        try {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                const user = JSON.parse(userStr);
                // Use email (unique per user) + role for truly separate histories
                const email = user.email || 'unknown';
                const role = user.role || 'student';
                return `chat_history_${email}_${role}`;
            }
        } catch (e) { }
        return 'chat_history_guest';
    };

    const [storageKey, setStorageKey] = useState(getStorageKey());

    const defaultMessage = [
        { role: 'assistant', content: 'Bonjour ! Je suis l\'assistant FacPark. Je peux répondre à vos questions sur le règlement ou vous aider à gérer votre compte. Comment puis-je vous aider ?' }
    ];

    // Load messages from localStorage (user-specific) or use default
    const [messages, setMessages] = useState(() => {
        const key = getStorageKey();
        const saved = localStorage.getItem(key);
        return saved ? JSON.parse(saved) : defaultMessage;
    });

    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Detect user change (login/logout) and reload correct history
    useEffect(() => {
        // Check on mount
        const checkUserChange = () => {
            const newKey = getStorageKey();
            if (newKey !== storageKey) {
                // User changed! Load new history
                console.log(`Chat: User changed, switching from ${storageKey} to ${newKey}`);
                setStorageKey(newKey);
                const saved = localStorage.getItem(newKey);
                setMessages(saved ? JSON.parse(saved) : defaultMessage);
            }
        };

        // Initial check
        checkUserChange();

        // Listen for storage changes (works across tabs)
        const handleStorageChange = (e) => {
            if (e.key === 'user') {
                checkUserChange();
            }
        };
        window.addEventListener('storage', handleStorageChange);

        // Periodic check for same-tab navigation (fallback)
        const interval = setInterval(checkUserChange, 1000);

        return () => {
            window.removeEventListener('storage', handleStorageChange);
            clearInterval(interval);
        };
    }, [storageKey]);

    // Speech Recognition hook
    const {
        transcript,
        listening,
        resetTranscript,
        browserSupportsSpeechRecognition
    } = useSpeechRecognition();

    // Sync input with transcript when listening
    useEffect(() => {
        if (listening) {
            setInput(transcript);
        }
    }, [transcript, listening]);

    // Save history whenever messages change (user-specific key)
    useEffect(() => {
        localStorage.setItem(storageKey, JSON.stringify(messages));
        scrollToBottom();
    }, [messages, storageKey]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const clearHistory = () => {
        setMessages(defaultMessage);
        localStorage.setItem(storageKey, JSON.stringify(defaultMessage));
    };

    const toggleListening = () => {
        if (listening) {
            SpeechRecognition.stopListening();
        } else {
            resetTranscript();
            SpeechRecognition.startListening({ continuous: true, language: 'fr-FR' });
        }
    };

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        // Stop listening if active
        if (listening) {
            SpeechRecognition.stopListening();
        }

        const userMsg = input;
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setInput('');
        resetTranscript();
        setIsLoading(true);

        try {
            const { data } = await api.post('/chat/message', { message: userMsg });

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.response,
                citations: data.citations,
                rag_used: data.rag_used,
                blocked: data.blocked
            }]);
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "Désolé, je rencontre des difficultés techniques actuellement.",
                error: true
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!browserSupportsSpeechRecognition) {
        console.warn("Browser does not support speech recognition.");
    }

    return (
        <div className="flex flex-col h-[600px] card p-0 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400">
                        <Bot size={18} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100">Assistant FacPark</h3>
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                            En ligne • Gemini/RAG
                        </p>
                    </div>
                </div>

                {/* Clear History Button */}
                <button
                    onClick={clearHistory}
                    title="Effacer l'historique"
                    className="p-2 text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                >
                    <Trash2 size={18} />
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin bg-slate-50/50 dark:bg-slate-950/50">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                        {/* Avatar */}
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user'
                            ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600'
                            : 'bg-primary-100 dark:bg-primary-900/30 text-primary-600'
                            }`}>
                            {msg.role === 'user' ? <UserIcon size={16} /> : <Bot size={16} />}
                        </div>

                        {/* Bubble */}
                        <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user'
                            ? 'bg-primary-600 text-white'
                            : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-sm'
                            }`}>

                            {/* Content */}
                            <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'text-white' : 'dark:prose-invert'}`}>
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>

                            {/* Citations */}
                            {msg.citations && msg.citations.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-slate-200/20 dark:border-slate-700/50">
                                    <p className="text-xs font-semibold mb-1 opacity-70">Sources vérifiées :</p>
                                    <div className="space-y-1">
                                        {msg.citations.map((cit, cIdx) => (
                                            <div key={cIdx} className="text-xs bg-slate-100/50 dark:bg-slate-900/30 p-1.5 rounded border border-slate-200/20 dark:border-slate-700/30">
                                                <span className="font-mono text-primary-500 font-bold">{cit.article}:</span> {cit.excerpt}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Blocked Warning */}
                            {msg.blocked && (
                                <div className="mt-2 flex items-center gap-2 text-red-400 text-xs">
                                    <AlertCircle size={12} />
                                    <span>Requête bloquée par sécurité</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center shrink-0">
                            <Bot size={16} />
                        </div>
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm flex gap-1 items-center h-10">
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                            <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={sendMessage} className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
                <div className="relative flex items-end gap-2">
                    <textarea
                        className="w-full pl-4 pr-12 py-3 bg-slate-100 dark:bg-slate-950 border border-transparent focus:border-primary-500 rounded-xl outline-none transition-all resize-none min-h-[48px] max-h-[150px]"
                        placeholder={listening ? "En écoute... (Parlez maintenant)" : "Posez une question sur le parking... (Shift+Entrée pour ligne)"}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                if (input.trim() && !isLoading) {
                                    sendMessage(e);
                                }
                            }
                        }}
                        disabled={isLoading} // Removed listening disable to allow editing
                        style={{
                            height: 'auto',
                            minHeight: '48px',
                            maxHeight: '150px',
                            overflowY: input.split('\n').length > 3 ? 'auto' : 'hidden'
                        }}
                        onInput={(e) => {
                            e.target.style.height = 'auto';
                            e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
                        }}
                    />

                    {/* Microphone Button */}
                    {browserSupportsSpeechRecognition && (
                        <button
                            type="button"
                            onClick={toggleListening}
                            className={`p-3 rounded-xl transition-colors shrink-0 ${listening
                                ? 'bg-red-500 text-white animate-pulse'
                                : 'bg-slate-200 text-slate-600 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-400'
                                }`}
                            title={listening ? "Arrêter l'écoute" : "Activer la saisie vocale"}
                        >
                            {listening ? <MicOff size={18} /> : <Mic size={18} />}
                        </button>
                    )}

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="p-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:bg-slate-400 transition-colors shrink-0"
                    >
                        <Send size={18} />
                    </button>
                </div>
                <p className="text-xs text-slate-500 mt-1 text-center">
                    Entrée pour envoyer • Shift+Entrée pour nouvelle ligne
                </p>
            </form>
        </div>
    );
};


export default ChatInterface;

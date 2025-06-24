import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, User, CornerDownLeft, Loader2, Github, Settings, Calendar, BarChart2, MessageCircle, X, Sun, Moon, Laptop, AlertTriangle } from 'lucide-react';

// --- 常量定义 ---
// 请确保这里的 URL 是你部署成功的后端服务的公开地址
const API_BASE_URL = 'https://ai-analyst-backend-210188681814.us-central1.run.app';

// --- Theme Management ---
type Theme = "light" | "dark" | "system";

const useTheme = () => {
    const [theme, setTheme] = useState<Theme>(() => {
        if (typeof window !== 'undefined') {
            return (localStorage.getItem("theme") as Theme) || "system";
        }
        return "system";
    });

    useEffect(() => {
        const root = window.document.documentElement;
        const isDark =
            theme === "dark" ||
            (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
        
        root.classList.remove(isDark ? "light" : "dark");
        root.classList.add(isDark ? "dark" : "light");
        
        if (typeof window !== 'undefined') {
            localStorage.setItem("theme", theme);
        }

    }, [theme]);

    return [theme, setTheme] as const;
};


// --- TypeScript Type Definitions ---
interface AnalysisResult {
  id: number;
  repo_name: string;
  repo_url: string;
  analysis_timestamp: string;
  one_liner_summary: string;
  tech_stack: string[];
  key_features: string[];
  community_focus: string[];
}

interface AppConfig {
  trending_language: string;
  schedule_interval_minutes: string; 
}

interface Message {
  id: number;
  sender: 'user' | 'bot';
  text: string;
}

// --- Helper Components ---
// (StatusIndicator, ProjectCard, ChatModal, ThemeToggle components remain the same, so they are omitted for brevity)

interface StatusIndicatorProps {
  lastUpdated: string;
  nextUpdate: string;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ lastUpdated, nextUpdate }) => (
  <div className="flex items-center space-x-4 text-sm text-slate-500 dark:text-gray-400">
    <div className="flex items-center space-x-2">
      <Calendar className="w-4 h-4" />
      <span>上次更新: {lastUpdated}</span>
    </div>
    <div className="flex items-center space-x-2">
      <Loader2 className="w-4 h-4 animate-spin" />
      <span>下次更新: {nextUpdate}</span>
    </div>
  </div>
);

interface ProjectCardProps {
    project: AnalysisResult;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project }) => (
    <div className="bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-700 rounded-xl shadow-lg hover:shadow-cyan-500/10 dark:hover:shadow-cyan-500/20 hover:border-cyan-500/50 transition-all duration-300 ease-in-out p-6 flex flex-col">
        <div className="flex-grow">
            <div className="flex items-center justify-between">
                <a href={project.repo_url} target="_blank" rel="noopener noreferrer" className="flex items-center space-x-3 group">
                    <Github className="w-6 h-6 text-slate-500 dark:text-gray-400 group-hover:text-slate-900 dark:group-hover:text-white transition-colors" />
                    <h3 className="text-xl font-bold text-slate-800 dark:text-gray-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors">{project.repo_name}</h3>
                </a>
            </div>
            <p className="text-slate-600 dark:text-gray-300 italic mt-3">"{project.one_liner_summary}"</p>
            
            <div className="space-y-3 pt-4">
                <div>
                    <h4 className="font-semibold text-slate-500 dark:text-gray-400 text-sm mb-2">技术栈</h4>
                    <div className="flex flex-wrap gap-2">
                        {project.tech_stack.map((tech, index) => (
                            <span key={index} className="px-3 py-1 text-xs font-mono bg-slate-100 dark:bg-gray-700 text-cyan-700 dark:text-cyan-300 rounded-full">{tech}</span>
                        ))}
                    </div>
                </div>
                 <div>
                    <h4 className="font-semibold text-slate-500 dark:text-gray-400 text-sm mb-2 mt-3">核心亮点</h4>
                    <ul className="list-none space-y-1">
                        {project.key_features.map((feature, index) => (
                            <li key={index} className="text-slate-700 dark:text-gray-300 text-sm flex items-start"><span className="mr-2 mt-1">✨</span>{feature}</li>
                        ))}
                    </ul>
                </div>
                <div>
                    <h4 className="font-semibold text-slate-500 dark:text-gray-400 text-sm mb-2 mt-3">社区关注点</h4>
                     <ul className="list-none space-y-1">
                        {project.community_focus.map((focus, index) => (
                             <li key={index} className="text-slate-700 dark:text-gray-300 text-sm flex items-start"><span className="mr-2 mt-1">🗣️</span>{focus}</li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
        <p className="text-xs text-slate-400 dark:text-gray-500 pt-4 mt-4 border-t border-slate-200 dark:border-gray-700/50">分析于: {new Date(project.analysis_timestamp).toLocaleString('zh-CN')}</p>
    </div>
);

interface ChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    messages: Message[];
    input: string;
    isTyping: boolean;
    handleInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleSendMessage: (e: React.FormEvent<HTMLFormElement>) => void;
}

const ChatModal: React.FC<ChatModalProps> = ({ isOpen, onClose, messages, input, isTyping, handleInputChange, handleSendMessage }) => {
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (isOpen) {
            setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
        }
    }, [messages, isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-40 flex items-end justify-end p-4 sm:p-6">
            <div className="fixed inset-0 bg-black/50 transition-opacity" onClick={onClose}></div>
            <div className="relative z-50 bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-700 rounded-xl shadow-2xl w-full max-w-lg h-[85vh] sm:h-[90vh] flex flex-col transition-transform transform-gpu animate-slide-in">
                <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-gray-700">
                    <h2 className="text-lg font-semibold text-slate-800 dark:text-white">对话式任务配置</h2>
                    <button onClick={onClose} className="p-1 rounded-full text-slate-500 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-gray-700 hover:text-slate-900 dark:hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <div className="flex-grow p-4 space-y-4 overflow-y-auto">
                    {messages.map((msg) => (
                         <div key={msg.id} className={`flex items-end gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.sender === 'bot' && <div className="w-8 h-8 rounded-full bg-cyan-500 flex items-center justify-center flex-shrink-0"><Bot className="w-5 h-5 text-white" /></div>}
                            <div
                               className={`max-w-xs md:max-w-md px-4 py-2 rounded-2xl text-white ${msg.sender === 'user' ? 'bg-blue-600 rounded-br-none' : 'bg-slate-600 dark:bg-gray-700 rounded-bl-none'}`}
                               dangerouslySetInnerHTML={{ __html: msg.text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-cyan-300">$1</strong>') }}
                            ></div>
                            {msg.sender === 'user' && <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0"><User className="w-5 h-5 text-white" /></div>}
                        </div>
                    ))}
                    {isTyping && (
                        <div className="flex items-end gap-2 justify-start">
                            <div className="w-8 h-8 rounded-full bg-cyan-500 flex items-center justify-center flex-shrink-0"><Bot className="w-5 h-5 text-white" /></div>
                            <div className="px-4 py-3 bg-slate-200 dark:bg-gray-700 rounded-2xl rounded-bl-none">
                                <div className="flex items-center justify-center space-x-1">
                                    <span className="w-1.5 h-1.5 bg-slate-400 dark:bg-gray-400 rounded-full animate-bounce delay-0"></span>
                                    <span className="w-1.5 h-1.5 bg-slate-400 dark:bg-gray-400 rounded-full animate-bounce delay-150"></span>
                                    <span className="w-1.5 h-1.5 bg-slate-400 dark:bg-gray-400 rounded-full animate-bounce delay-300"></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>
                <div className="p-4 border-t border-slate-200 dark:border-gray-700">
                    <form onSubmit={handleSendMessage} className="flex items-center space-x-2">
                        <input
                            type="text"
                            value={input}
                            onChange={handleInputChange}
                            placeholder="和 AI 对话来调整任务..."
                            className="w-full bg-slate-100 dark:bg-gray-700 border border-slate-300 dark:border-gray-600 rounded-lg py-2 px-4 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 transition"
                            disabled={isTyping}
                        />
                        <button
                            type="submit"
                            className="bg-cyan-500 hover:bg-cyan-600 disabled:bg-slate-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg p-2 transition-colors"
                            disabled={isTyping || !input.trim()}
                        >
                            <CornerDownLeft className="w-5 h-5" />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

interface ThemeToggleProps {
    theme: Theme;
    setTheme: (theme: Theme) => void;
}
const ThemeToggle: React.FC<ThemeToggleProps> = ({ theme, setTheme }) => {
    const [isOpen, setIsOpen] = useState(false);
    const options: { value: Theme; label: string; icon: React.ElementType }[] = [
        { value: 'light', label: '浅色', icon: Sun },
        { value: 'dark', label: '深色', icon: Moon },
        { value: 'system', label: '系统', icon: Laptop },
    ];

    return (
        <div className="relative">
            <button onClick={() => setIsOpen(!isOpen)} className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-gray-700 transition-colors">
                <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute top-2 h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                <span className="sr-only">切换主题</span>
            </button>
            {isOpen && (
                <div className="absolute right-0 mt-2 w-32 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-slate-200 dark:border-gray-700 z-50">
                    {options.map((option) => (
                        <button
                            key={option.value}
                            onClick={() => {
                                setTheme(option.value);
                                setIsOpen(false);
                            }}
                            className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left ${
                                theme === option.value ? 'bg-slate-100 dark:bg-gray-900' : 'hover:bg-slate-100 dark:hover:bg-gray-700'
                            }`}
                        >
                            <option.icon className="h-4 w-4" />
                            {option.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};


// --- Main App Component ---
const App: React.FC = () => {
  const [theme, setTheme] = useTheme();
  
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  
  const refreshTimerId = useRef<NodeJS.Timeout | null>(null);

  // Use useCallback with an empty dependency array to create a stable fetchData function
  const fetchData = useCallback(async (isInitialLoad = false) => {
      if (isInitialLoad) {
          setIsLoading(true);
      }
      console.log("Fetching data...");
      try {
        const [configRes, resultsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/config`),
          fetch(`${API_BASE_URL}/api/results`)
        ]);
        if (!configRes.ok || !resultsRes.ok) {
          throw new Error('网络响应错误，请检查后端服务是否开启。');
        }
        const configData = await configRes.json();
        const resultsData = await resultsRes.json();
        
        console.log("Data fetched successfully:", { configData, resultsData });

        setConfig(configData);
        setResults(resultsData);
        setError(null);
      } catch (err: any) {
        setError(err.message || '获取数据失败，请稍后重试。');
      } finally {
        if (isInitialLoad) {
            setIsLoading(false);
        }
      }
    }, []); // Empty array means this function is created once and never changes.
  
  useEffect(() => {
    fetchData(true); // Initial data load

    setMessages([
      { id: 1, sender: 'bot', text: '你好！我是你的 GitHub 热点分析助手。' },
      { id: 2, sender: 'bot', text: '你可以跟我聊天来调整任务设置。' }
    ]);
  }, [fetchData]); // Dependency on stable fetchData function, so this runs only once.
  
  // This effect handles the automatic refresh timer
  useEffect(() => {
    if (refreshTimerId.current) {
        clearTimeout(refreshTimerId.current);
    }

    if (results.length > 0 && config) {
        const intervalMinutes = parseInt(config.schedule_interval_minutes, 10);
        if (isNaN(intervalMinutes) || intervalMinutes < 1) return;

        const lastUpdateDate = parseUTCDate(results[0].analysis_timestamp);
        if(!lastUpdateDate) return;

        const nextUpdateDate = new Date(lastUpdateDate.getTime() + intervalMinutes * 60 * 1000);
        
        let timeUntilNextUpdate = nextUpdateDate.getTime() - Date.now();
        
        // If the next update time has passed, poll every 30 seconds for new data
        if (timeUntilNextUpdate < 0) {
            console.log("Next update time has passed. Scheduling a check in 30 seconds.");
            timeUntilNextUpdate = 30000;
        }

        console.log(`Scheduling next data refresh in ${Math.round(timeUntilNextUpdate / 1000)} seconds.`);
        
        refreshTimerId.current = setTimeout(() => {
            fetchData();
        }, timeUntilNextUpdate);
    }
    
    return () => {
        if (refreshTimerId.current) {
            clearTimeout(refreshTimerId.current);
        }
    };
  }, [results, config, fetchData]);

  const handleSendMessage = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage: Message = { id: Date.now(), sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsTyping(true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: currentInput }),
        });

        if (!response.ok) {
            throw new Error("与机器人通信失败");
        }

        const data = await response.json();
        const botMessage: Message = { id: Date.now() + 1, sender: 'bot', text: data.reply };
        
        // After a successful config change, fetch data immediately to reflect changes
        // and restart the refresh timer with the new configuration.
        await fetchData();

        setMessages(prev => [...prev, botMessage]);

    } catch (chatError: any) {
        const errorMessage: Message = { id: Date.now() + 1, sender: 'bot', text: `出错了: ${chatError.message}` };
        setMessages(prev => [...prev, errorMessage]);
    } finally {
        setIsTyping(false);
    }
  };

  // NEW: Robustly parse date strings as UTC
  const parseUTCDate = (dateString: string | undefined): Date | null => {
    if (!dateString) return null;

    // Best case: ISO 8601 format like "2023-10-27T08:30:00.123Z"
    if (dateString.includes('T') && dateString.endsWith('Z')) {
        return new Date(dateString);
    }
    
    // Handle Python's default format "YYYY-MM-DD HH:MM:SS.ffffff"
    // By replacing the space with 'T' and adding 'Z', we tell the constructor it's UTC.
    if (dateString.includes(' ')) {
        return new Date(dateString.replace(' ', 'T') + 'Z');
    }

    // Fallback for other potential formats, though less reliable
    try {
        const d = new Date(dateString);
        if(isNaN(d.getTime())) return null;
        return d;
    } catch(e) {
        return null;
    }
  }

  const getTimeAgo = (date: string): string => {
    const timestamp = parseUTCDate(date)?.getTime();
    if (timestamp === undefined || isNaN(timestamp)) return '未知时间';
    
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 5) return '刚刚';
    if (seconds < 60) return `${seconds} 秒前`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} 分钟前`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} 小时前`;
    const days = Math.floor(hours / 24);
    return `${days} 天前`;
  }

  const getNextUpdateTime = (): string => {
      if (!results || results.length === 0 || !config || !config.schedule_interval_minutes) {
          return 'N/A';
      }
      
      const intervalMinutes = parseInt(config.schedule_interval_minutes, 10);
      if (isNaN(intervalMinutes) || intervalMinutes < 1) {
          return 'N/A';
      }
      
      const lastUpdate = parseUTCDate(results[0].analysis_timestamp);
      if(!lastUpdate) return 'N/A';

      lastUpdate.setMinutes(lastUpdate.getMinutes() + intervalMinutes);
      return lastUpdate.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit'});
  }
  
  const formatInterval = (minutesStr: string | undefined): string => {
      if (minutesStr === undefined || minutesStr === null || minutesStr === '') {
          return '未知';
      }
      const minutes = parseInt(minutesStr, 10);
      if (isNaN(minutes) || minutes < 1) {
          return '未知';
      }
      if (minutes < 60) {
          return `${minutes} 分钟`;
      }
      const hours = minutes / 60;
      if (Number.isInteger(hours)) {
          return `${hours} 小时`;
      }
      return `${parseFloat(hours.toFixed(1))} 小时`;
  };


  // --- Rendering logic ---
  if (isLoading && results.length === 0) { // Only show full-page loader on initial load
    return (
        <div className="bg-white dark:bg-gray-900 min-h-screen flex items-center justify-center">
            <Loader2 className="w-12 h-12 animate-spin text-cyan-500" />
        </div>
    );
  }

  if (error) {
      return (
          <div className="bg-white dark:bg-gray-900 min-h-screen flex flex-col items-center justify-center text-center px-4">
              <AlertTriangle className="w-16 h-16 text-red-500 mb-4" />
              <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">出错了！</h2>
              <p className="text-slate-600 dark:text-gray-400">{error}</p>
              <button onClick={() => window.location.reload()} className="mt-6 px-4 py-2 bg-cyan-500 text-white rounded-md hover:bg-cyan-600">刷新页面</button>
          </div>
      );
  }

  return (
    <div className="bg-slate-50 dark:bg-gray-900 text-slate-800 dark:text-white min-h-screen font-sans transition-colors duration-300">
      <header className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg border-b border-slate-200 dark:border-gray-700/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <BarChart2 className="w-8 h-8 text-cyan-500" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">GitHub 热点趋势分析助手</h1>
          </div>
          <div className="flex items-center gap-4">
            {results.length > 0 && config &&
              <StatusIndicator 
                lastUpdated={getTimeAgo(results[0].analysis_timestamp)}
                nextUpdate={getNextUpdateTime()}
              />
            }
            <ThemeToggle theme={theme} setTheme={setTheme} />
          </div>
        </div>
      </header>

      <main className="container mx-auto p-4 sm:p-6 lg:p-8">
          {config && <div className="flex items-center space-x-3 mb-6">
             <Settings className="w-6 h-6 text-slate-500 dark:text-gray-400"/>
             <h2 className="text-xl font-semibold">当前分析配置: 追踪 <span className="text-cyan-600 dark:text-cyan-400 font-bold">{config.trending_language}</span> 项目，每 <span className="text-cyan-600 dark:text-cyan-400 font-bold">{formatInterval(config.schedule_interval_minutes)}</span> 更新</h2>
          </div>}
           <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {results.length > 0 ? results.map((project) => (
              <ProjectCard key={project.id} project={project} />
            )) : 
            <div className="col-span-full text-center py-12">
                <p className="text-slate-500 dark:text-gray-400">暂无分析结果，后台任务可能正在执行中...</p>
                <p className="text-sm text-slate-400 dark:text-gray-500 mt-2">请等待下一次自动刷新或手动触发后台任务。</p>
            </div>
            }
          </div>
      </main>
      
      <button 
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-8 right-8 z-20 w-16 h-16 bg-cyan-500 rounded-full flex items-center justify-center shadow-lg hover:bg-cyan-600 hover:scale-110 hover:shadow-cyan-500/50 transform transition-all duration-300 ease-in-out"
        aria-label="打开聊天"
      >
          <MessageCircle className="w-8 h-8 text-white"/>
      </button>

      <ChatModal 
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        messages={messages}
        input={input}
        isTyping={isTyping}
        handleInputChange={(e) => setInput(e.target.value)}
        handleSendMessage={handleSendMessage}
      />
    </div>
  );
}

export default App;

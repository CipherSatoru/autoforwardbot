import React, { useState, useEffect } from 'react';
import { 
  init, 
  miniApp, 
  useLaunchParams, 
  mainButton,
  backButton
} from '@telegram-apps/sdk-react';
import { 
  Repeat, 
  Settings, 
  Zap, 
  Waves, 
  Trash2, 
  Plus, 
  ShieldCheck,
  Languages,
  ArrowRightLeft,
  PieChart
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Initialize Telegram SDK
init();

const App = () => {
  const lp = useLaunchParams();
  const [tasks, setTasks] = useState([
    { id: 1, source: 'News Channel', dest: 'My Personal Group', status: 'active', messages: 128 },
    { id: 2, source: 'Crypto Alpha', dest: 'Trading Hub', status: 'paused', messages: 45 }
  ]);

  useEffect(() => {
    miniApp.ready();
    mainButton.setParams({
        text: 'CREATE NEW TASK',
        isVisible: true,
        backgroundColor: '#2481cc',
        textColor: '#ffffff'
    });
    
    // Main button click handler
    const offClick = mainButton.onClick(() => {
        alert("Redirecting to task creation...");
    });

    return () => {
        offClick();
        mainButton.hide();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#f1f1f1] dark:bg-[#1c1c1c] text-[#000] dark:text-[#fff] font-sans pb-24">
      {/* Header Profile Section */}
      <header className="p-6 bg-white dark:bg-[#242424] rounded-b-3xl shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center text-white text-xl font-bold">
              {lp.initData?.user?.firstName?.[0] || 'U'}
            </div>
            <div>
              <h1 className="text-xl font-bold">Platinum Dashboard</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Welcome, {lp.initData?.user?.firstName || 'User'}</p>
            </div>
          </div>
          <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-xl">
             <ShieldCheck className="text-blue-500" />
          </div>
        </div>
        
        {/* Global Stats Summary */}
        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="bg-[#f8f9fa] dark:bg-[#2c2c2c] p-4 rounded-2xl">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total Forwarded</p>
            <h2 className="text-2xl font-bold mt-1">2,482</h2>
          </div>
          <div className="bg-[#f8f9fa] dark:bg-[#2c2c2c] p-4 rounded-2xl">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Active Tasks</p>
            <h2 className="text-2xl font-bold mt-1 text-green-500">{tasks.length}</h2>
          </div>
        </div>
      </header>

      {/* Active Tasks Section */}
      <main className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-lg uppercase tracking-tight text-gray-400">My Active Tasks</h3>
          <button className="text-blue-500 font-medium flex items-center gap-1">View All <ArrowRightLeft size={16}/></button>
        </div>

        <div className="space-y-4">
          <AnimatePresence>
            {tasks.map((task) => (
              <motion.div 
                key={task.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-white dark:bg-[#242424] p-5 rounded-3xl shadow-sm relative overflow-hidden group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-bold text-blue-500 uppercase">Task #{task.id}</span>
                    <h4 className="font-bold text-lg">{task.source}</h4>
                    <div className="flex items-center gap-2 text-gray-400">
                      <Zap size={14} className="text-yellow-500" />
                      <span className="text-sm">Forwarding to: {task.dest}</span>
                    </div>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${task.status === 'active' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'}`}>
                    {task.status}
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-gray-100 dark:border-gray-800 pt-4">
                  <div className="flex gap-4">
                    <button className="p-2 bg-gray-50 dark:bg-[#333] rounded-xl text-gray-500 hover:text-blue-500 transition-colors">
                      <Settings size={20} />
                    </button>
                    <button className="p-2 bg-gray-50 dark:bg-[#333] rounded-xl text-gray-500 hover:text-red-500 transition-colors">
                      <Trash2 size={20} />
                    </button>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-gray-400 uppercase font-bold">Sync Count</p>
                    <p className="font-bold text-xl">{task.messages}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Premium Tools Grid */}
        <h3 className="font-bold text-lg uppercase tracking-tight text-gray-400 mt-10 mb-4">Pro Tools</h3>
        <div className="grid grid-cols-2 gap-4">
          <ToolCard icon={<Waves className="text-blue-400" />} title="Watermark" desc="Auto-brand media" />
          <ToolCard icon={<Languages className="text-purple-400" />} title="Translate" desc="100+ languages" />
          <ToolCard icon={<Zap className="text-yellow-400" />} title="AI Rewrite" desc="Auto-summarize" />
          <ToolCard icon={<PieChart className="text-green-400" />} title="Analytics" desc="Insight logs" />
        </div>
      </main>

      {/* Floating Add Button for Mobile Feel */}
      <button className="fixed bottom-8 right-8 w-16 h-16 bg-blue-500 rounded-full shadow-2xl flex items-center justify-center text-white elevation-10 active:scale-95 transition-transform">
        <Plus size={32} />
      </button>
    </div>
  );
};

const ToolCard = ({ icon, title, desc }) => (
  <div className="bg-white dark:bg-[#242424] p-5 rounded-3xl shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-transparent active:border-blue-500">
    <div className="w-10 h-10 bg-gray-50 dark:bg-[#333] rounded-2xl flex items-center justify-center mb-3">
      {icon}
    </div>
    <h4 className="font-bold text-sm">{title}</h4>
    <p className="text-[10px] text-gray-400 mt-1 leading-tight">{desc}</p>
  </div>
);

export default App;
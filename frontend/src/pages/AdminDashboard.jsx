import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import PlateChecker from '../components/PlateChecker';
import api from '../services/api';
import ChatInterface from '../components/ChatInterface';
import { Users, Car, CheckCircle, BarChart3, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const StatCard = ({ icon: Icon, label, value, color = "blue" }) => {
    const colors = {
        blue: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
        green: "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400",
        red: "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400",
        purple: "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400",
    };

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${colors[color]}`}>
                    <Icon size={24} />
                </div>
                <span className={`text-2xl font-bold text-slate-900 dark:text-white`}>{value}</span>
            </div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        </div>
    );
};

const AdminDashboard = () => {
    const [stats, setStats] = useState(null);
    const [accessHistory, setAccessHistory] = useState([]);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const { data } = await api.post('/chat/tool', { tool_name: 'get_admin_stats' });
                if (data.success) {
                    setStats(data.data);
                }

                // Fetch recent access logs for chart (mocking chart data structure for now or using real if available)
                const logsRes = await api.get('/admin/access-events?limit=7');
                // Simple transform for chart
                // Ideally backend provides aggregated stats, but we'll adapt
            } catch (error) {
                console.error("Admin stats error", error);
            }
        };
        fetchStats();
    }, []);

    // Mock chart data for visuals
    const chartData = [
        { name: 'Lun', acces: 45 },
        { name: 'Mar', acces: 52 },
        { name: 'Mer', acces: 38 },
        { name: 'Jeu', acces: 65 },
        { name: 'Ven', acces: 48 },
        { name: 'Sam', acces: 25 },
    ];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-slate-950 pb-12 pt-20">
            <Navbar title="Administration" />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-slide-up">
                    <StatCard
                        icon={Users}
                        label="Étudiants Actifs"
                        value={stats ? stats.total_students : "-"}
                        color="blue"
                    />
                    <StatCard
                        icon={Car}
                        label="Véhicules Total"
                        value={stats ? stats.total_vehicles : "-"}
                        color="purple"
                    />
                    <StatCard
                        icon={CheckCircle}
                        label="Places Libres"
                        value={stats ? stats.available_slots : "-"}
                        color="green"
                    />
                    <StatCard
                        icon={AlertTriangle}
                        label="Suspensions"
                        value={stats ? stats.active_suspensions : "-"}
                        color="red"
                    />
                </div>

                {/* Main Content */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* Vision Testing Column */}
                    <div className="space-y-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Contrôle d'Accès (Simulation)</h2>
                        <PlateChecker />
                    </div>

                    {/* Analytics Column */}
                    <div className="space-y-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Activité Récente</h2>

                        <div className="card h-[300px] flex flex-col">
                            <h3 className="text-sm font-medium text-slate-500 mb-4 flex items-center gap-2">
                                <BarChart3 size={16} />
                                Flux hebdomadaire
                            </h3>
                            <div className="flex-1 w-full min-h-0">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
                                            cursor={{ fill: 'transparent' }}
                                        />
                                        <Bar dataKey="acces" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={30} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="card h-[500px] flex flex-col">
                            <h3 className="text-sm font-medium text-slate-500 mb-4 flex items-center gap-2">
                                Assistant Administrateur
                            </h3>
                            <div className="flex-1 w-full min-h-0 relative">
                                <ChatInterface />
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
};

export default AdminDashboard;

import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import ChatInterface from '../components/ChatInterface';
import api from '../services/api';
import { Car, Calendar, MapPin, Clock } from 'lucide-react';

const InfoCard = ({ icon: Icon, label, value, subtext, color = "blue" }) => {
    const colors = {
        blue: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
        green: "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400",
        purple: "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400",
        orange: "bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400",
        red: "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400",
    };

    return (
        <div className="card flex items-start gap-4">
            <div className={`p-3 rounded-xl ${colors[color]}`}>
                <Icon size={24} />
            </div>
            <div>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
                <p className="text-xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
                {subtext && <p className="text-xs text-slate-400 mt-1">{subtext}</p>}
            </div>
        </div>
    );
};

const StudentDashboard = () => {
    const [subscription, setSubscription] = useState(null);
    const [slot, setSlot] = useState(null);
    const [vehicles, setVehicles] = useState([]);
    const [suspension, setSuspension] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [subRes, slotRes, vehRes, suspRes] = await Promise.all([
                    api.post('/chat/tool', { tool_name: 'get_my_subscription' }),
                    api.post('/chat/tool', { tool_name: 'get_my_slot' }),
                    api.post('/chat/tool', { tool_name: 'get_my_vehicles' }),
                    api.post('/chat/tool', { tool_name: 'get_my_suspension_status' })
                ]);

                if (subRes.data.success) setSubscription(subRes.data.data);
                if (slotRes.data.success) setSlot(slotRes.data.data);
                if (vehRes.data.success) setVehicles(vehRes.data.data || []);
                if (suspRes.data.success) setSuspension(suspRes.data.data);
            } catch (error) {
                // Silently handle errors for dashboard widgets to prevent intrusive toasts on 404s (e.g., no subscription)
                console.warn("Dashboard incomplete data:", error);
            }
        };
        fetchData();
    }, []);

    // Determine access status
    const getAccessStatus = () => {
        if (suspension?.is_suspended) {
            return { value: "Suspendu", subtext: `Jusqu'au ${new Date(suspension.end_date).toLocaleDateString()}`, color: "red" };
        }
        if (subscription) {
            return { value: "Actif", subtext: "Horaires: 7h-22h", color: "green" };
        }
        return { value: "Inactif", subtext: "Aucun abonnement", color: "orange" };
    };

    const accessStatus = getAccessStatus();

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-slate-950 pb-12 pt-20">
            <Navbar title="Espace Étudiant" />

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">

                {/* Info Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-slide-up">
                    <InfoCard
                        icon={Calendar}
                        label="Abonnement"
                        value={subscription ? subscription.type : "Aucun"}
                        subtext={subscription ? `Expire le ${new Date(subscription.end_date).toLocaleDateString()}` : "Contactez l'admin"}
                        color="blue"
                    />
                    <InfoCard
                        icon={MapPin}
                        label="Place Attribuée"
                        value={slot ? slot.slot_code : "En attente"}
                        subtext={slot ? `Zone ${slot.zone}` : "Aucune place"}
                        color="purple"
                    />
                    <InfoCard
                        icon={Car}
                        label="Véhicules"
                        value={`${vehicles.length} / 3`}
                        subtext={vehicles.length > 0 ? vehicles[0].plate : "Aucun véhicule"}
                        color="green"
                    />
                    <InfoCard
                        icon={Clock}
                        label="Statut Accès"
                        value={accessStatus.value}
                        subtext={accessStatus.subtext}
                        color={accessStatus.color}
                    />
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Chatbot Column */}
                    <div className="lg:col-span-2 space-y-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Assistant Virtuel</h2>
                        <ChatInterface />
                    </div>

                    {/* Side Info Column */}
                    <div className="space-y-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Mes Véhicules</h2>
                        <div className="card space-y-4">
                            {vehicles.length === 0 ? (
                                <p className="text-slate-500 text-sm text-center py-4">Aucun véhicule enregistré</p>
                            ) : (
                                vehicles.map((v) => (
                                    <div key={v.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-slate-500">
                                                <Car size={20} />
                                            </div>
                                            <div>
                                                <p className="font-bold text-slate-900 dark:text-white">{v.plate}</p>
                                                <p className="text-xs text-slate-500">{v.make} {v.model}</p>
                                            </div>
                                        </div>
                                        <span className="px-2 py-1 text-xs font-medium rounded bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                            {v.plate_type}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="card bg-gradient-to-br from-indigo-600 to-purple-700 text-white border-none">
                            <h3 className="font-bold mb-2">Besoin d'aide ?</h3>
                            <p className="text-sm text-indigo-100 mb-4">
                                Posez vos questions à l'assistant concernant le règlement intérieur, les places de parking ou les procédures d'abonnement.
                            </p>
                            <div className="bg-white/10 rounded-lg p-3 text-sm backdrop-blur-sm border border-white/10">
                                <p className="font-mono text-xs opacity-70 mb-1">Essayez :</p>
                                "Combien de véhicules puis-je avoir ?"
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
};

export default StudentDashboard;

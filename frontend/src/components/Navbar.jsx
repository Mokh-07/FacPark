import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';

const Navbar = ({ title }) => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    {/* Logo / Title */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-primary-500/20">
                            P
                        </div>
                        <span className="font-bold text-xl bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent hidden sm:block">
                            FacPark
                        </span>
                        {title && (
                            <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                                {title}
                            </span>
                        )}
                    </div>

                    {/* User Profile */}
                    <div className="flex items-center gap-4">
                        <div className="text-right hidden md:block">
                            <p className="text-sm font-medium text-slate-900 dark:text-slate-200">
                                {user?.full_name}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                {user?.email}
                            </p>
                        </div>

                        <button
                            onClick={handleLogout}
                            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-red-500 transition-colors"
                            title="Déconnexion"
                        >
                            <LogOut size={20} />
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

        const user = await login(email, password);

        if (user) {
            if (user.role === 'ADMIN') {
                navigate('/admin');
            } else {
                navigate('/student');
            }
        }
        setIsLoading(false);
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-[url('https://images.unsplash.com/photo-1494976388531-d1058494cdd8?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center">
            {/* Overlay */}
            <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"></div>

            <div className="relative w-full max-w-md bg-white/10 dark:bg-slate-900/60 backdrop-blur-xl border border-white/20 dark:border-slate-700 p-8 rounded-2xl shadow-2xl animate-fade-in">

                <div className="text-center mb-8">
                    <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-primary-500/30 mb-4">
                        P
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">FacPark</h1>
                    <p className="text-slate-300">Connexion au portail universitaire</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
                        <input
                            type="email"
                            required
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-white placeholder-slate-500 transition-all"
                            placeholder="etudiant@fac.tn"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">Mot de passe</label>
                        <input
                            type="password"
                            required
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-white placeholder-slate-500 transition-all"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full py-3.5 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-primary-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    >
                        {isLoading ? (
                            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        ) : (
                            "Se connecter"
                        )}
                    </button>
                </form>

                <div className="mt-8 text-center">
                    <p className="text-xs text-slate-400">
                        Comptes démo : <br />
                        <span className="text-slate-300">admin@fac.tn</span> (admin123)<br />
                        <span className="text-slate-300">ahmed.benali@etudiant.fac.tn</span> (student123)
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;

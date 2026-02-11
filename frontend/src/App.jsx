import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

// Pages (Lazy loading for better perf)
import Login from './pages/Login';
import StudentDashboard from './pages/StudentDashboard';
import AdminDashboard from './pages/AdminDashboard';

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    {/* Public Routes */}
                    <Route path="/login" element={<Login />} />

                    {/* Default Redirect */}
                    <Route path="/" element={<Navigate to="/login" replace />} />

                    {/* Student Routes */}
                    <Route element={<ProtectedRoute allowedRoles={['STUDENT']} />}>
                        <Route path="/student" element={<StudentDashboard />} />
                    </Route>

                    {/* Admin Routes */}
                    <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                        <Route path="/admin" element={<AdminDashboard />} />
                    </Route>

                    {/* Catch all */}
                    <Route path="*" element={<Navigate to="/login" />} />
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;

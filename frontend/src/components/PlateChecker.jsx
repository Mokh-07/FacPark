import React, { useState, useRef } from 'react';
import api from '../services/api';
import { Camera, CheckCircle, XCircle, Search, Upload, RefreshCw } from 'lucide-react';
import { toast } from 'react-hot-toast';

const PlateChecker = () => {
    const [selectedImage, setSelectedImage] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);
    const [result, setResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSelectedImage(file);
            setPreviewUrl(URL.createObjectURL(file));
            setResult(null);
        }
    };

    const checkPlate = async () => {
        if (!selectedImage) return;

        setIsLoading(true);
        const formData = new FormData();
        formData.append('file', selectedImage);

        try {
            // Use the detect-and-check endpoint (simulating gate)
            const { data } = await api.post('/vision/detect-and-check', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setResult(data);
            if (data.success) {
                if (data.access.decision === 'ALLOW') toast.success(`Accès autorisé : ${data.access.message}`);
                else toast.error(`Accès refusé : ${data.access.message}`);
            } else {
                toast.error("Aucune plaque détectée");
            }
        } catch (error) {
            toast.error("Erreur lors de l'analyse");
            console.error(error);
        } finally {
            setIsLoading(false);
        }
    };

    const reset = () => {
        setSelectedImage(null);
        setPreviewUrl(null);
        setResult(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <div className="card space-y-6">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Camera className="text-primary-500" />
                    Test Vision & Accès
                </h3>
                {result && (
                    <button onClick={reset} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                        <RefreshCw size={18} />
                    </button>
                )}
            </div>

            {/* Upload Area */}
            <div className={`relative w-full aspect-video rounded-xl border-2 border-dashed flex flex-col items-center justify-center transition-all ${previewUrl ? 'border-primary-500/50 bg-slate-950' : 'border-slate-300 dark:border-slate-700 hover:border-primary-400 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                }`}>
                {previewUrl ? (
                    <>
                        <img src={previewUrl} alt="Preview" className="h-full w-full object-contain rounded-lg" />
                        {/* Overlay Result */}
                        {result && result.success && (
                            <div className="absolute inset-x-0 bottom-0 p-4 bg-black/70 backdrop-blur-sm rounded-b-lg border-t border-white/10 flex items-center justify-between">
                                <div>
                                    <p className="text-white font-mono text-xl font-bold tracking-wider">
                                        {result.detection.plate}
                                    </p>
                                    <p className="text-xs text-slate-400">
                                        Conf: {(result.detection.confidence * 100).toFixed(1)}%
                                    </p>
                                </div>
                                <div className={`px-4 py-2 rounded-lg font-bold flex items-center gap-2 ${result.access.decision === 'ALLOW' ? 'bg-green-500/20 text-green-400 border border-green-500/50' : 'bg-red-500/20 text-red-400 border border-red-500/50'
                                    }`}>
                                    {result.access.decision === 'ALLOW' ? <CheckCircle size={20} /> : <XCircle size={20} />}
                                    {result.access.decision}
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-center p-6 cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                        <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-400">
                            <Upload size={24} />
                        </div>
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            Cliquez pour uploader une image
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                            JPG, PNG (Max 5MB)
                        </p>
                    </div>
                )}
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept="image/*"
                    onChange={handleFileChange}
                />
            </div>

            {/* Action Button */}
            {selectedImage && !result && (
                <button
                    onClick={checkPlate}
                    disabled={isLoading}
                    className="w-full btn-primary flex items-center justify-center gap-2 py-3"
                >
                    {isLoading ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            Analyse en cours...
                        </>
                    ) : (
                        <>
                            <Search size={18} />
                            Vérifier l'accès
                        </>
                    )}
                </button>
            )}

            {/* Detailed Result Message */}
            {result && (
                <div className={`p-4 rounded-lg border text-sm ${result.access.decision === 'ALLOW'
                        ? 'bg-green-50/50 dark:bg-green-900/10 border-green-200 dark:border-green-900 text-green-800 dark:text-green-200'
                        : 'bg-red-50/50 dark:bg-red-900/10 border-red-200 dark:border-red-900 text-red-800 dark:text-red-200'
                    }`}>
                    <span className="font-bold">{result.access.ref_code}:</span> {result.access.message}
                </div>
            )}
        </div>
    );
};

export default PlateChecker;

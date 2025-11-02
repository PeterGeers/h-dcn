
import React, { useState, useEffect, useMemo } from 'react';
import { Icon } from './Icon';
import { getImageDimensions } from '../utils/imageUtils';

interface ControlPanelProps {
  onRemoveBackground: () => void;
  onImproveClarity: () => void;
  onResize: (width: number, height: number) => void;
  onResizeByPercentage: (percentage: number) => void;
  onEnterCropMode: () => void;
  onReset: () => void;
  onUploadNew: () => void;
  processedImage: string | null;
  isLoading: boolean;
}

type ResizeMode = 'pixels' | 'percent';

const ControlButton: React.FC<{ onClick: () => void; disabled: boolean; children: React.ReactNode; iconName: string; }> = ({ onClick, disabled, children, iconName }) => (
    <button
        onClick={onClick}
        disabled={disabled}
        className="w-full flex items-center justify-center space-x-2 bg-indigo-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-indigo-500 disabled:bg-slate-600 disabled:cursor-not-allowed transition-colors duration-200"
    >
        <Icon name={iconName} className="w-5 h-5" />
        <span>{children}</span>
    </button>
);

const ModeButton: React.FC<{ onClick: () => void; active: boolean; children: React.ReactNode }> = ({ onClick, active, children }) => (
    <button
        onClick={onClick}
        className={`w-full text-sm font-medium py-1 px-3 rounded-md transition-colors ${active ? 'bg-indigo-600 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-300'}`}
    >
        {children}
    </button>
);


export const ControlPanel: React.FC<ControlPanelProps> = ({
  onRemoveBackground,
  onImproveClarity,
  onResize,
  onResizeByPercentage,
  onEnterCropMode,
  onReset,
  onUploadNew,
  processedImage,
  isLoading,
}) => {
    const [width, setWidth] = useState(0);
    const [height, setHeight] = useState(0);
    const [resizeMode, setResizeMode] = useState<ResizeMode>('pixels');
    const [percentage, setPercentage] = useState(100);

    const originalDimensions = useMemo(() => ({ width, height }), [width, height]);

    useEffect(() => {
        if (processedImage) {
            getImageDimensions(processedImage).then(({ width, height }) => {
                setWidth(width);
                setHeight(height);
            }).catch(console.error);
        }
    }, [processedImage]);

    const handleApplyResize = () => {
        if (isLoading) return;
        if (resizeMode === 'pixels') {
            if (width > 0 && height > 0) {
                onResize(width, height);
            }
        } else {
             if (percentage > 0) {
                onResizeByPercentage(percentage);
            }
        }
    };
    
    const percentWidth = Math.round(originalDimensions.width * (percentage / 100));
    const percentHeight = Math.round(originalDimensions.height * (percentage / 100));

    return (
        <div className="bg-slate-800/50 p-6 rounded-lg space-y-8 h-full">
            <div>
                <h2 className="text-xl font-bold mb-4">AI Tools</h2>
                <div className="space-y-3">
                    <ControlButton onClick={onRemoveBackground} disabled={isLoading} iconName="cut">Remove Background</ControlButton>
                    <ControlButton onClick={onImproveClarity} disabled={isLoading} iconName="sparkles">Improve Clarity</ControlButton>
                </div>
            </div>

            <div>
                <h2 className="text-xl font-bold mb-4">Transform</h2>
                <div className="space-y-4">
                    <div>
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="font-semibold">Resize</h3>
                            <div className="flex space-x-1 bg-slate-800 p-0.5 rounded-lg">
                                <ModeButton onClick={() => setResizeMode('pixels')} active={resizeMode === 'pixels'}>Pixels</ModeButton>
                                <ModeButton onClick={() => setResizeMode('percent')} active={resizeMode === 'percent'}>Percent</ModeButton>
                            </div>
                        </div>

                        {resizeMode === 'pixels' && (
                            <div className="flex items-center space-x-2">
                                <input type="number" value={width} onChange={(e) => setWidth(parseInt(e.target.value, 10) || 0)} className="w-full bg-slate-700 p-2 rounded-md text-center" disabled={isLoading} />
                                <span className="text-slate-400">x</span>
                                <input type="number" value={height} onChange={(e) => setHeight(parseInt(e.target.value, 10) || 0)} className="w-full bg-slate-700 p-2 rounded-md text-center" disabled={isLoading} />
                            </div>
                        )}

                        {resizeMode === 'percent' && (
                            <div className="space-y-2">
                                <div className="flex items-center space-x-2">
                                    <input type="range" min="1" max="200" value={percentage} onChange={(e) => setPercentage(parseInt(e.target.value, 10))} className="w-full h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer" disabled={isLoading} />
                                    <input type="number" value={percentage} onChange={(e) => setPercentage(parseInt(e.target.value, 10) || 0)} className="w-24 bg-slate-700 p-2 rounded-md text-center" disabled={isLoading} />
                                    <span className="text-slate-400">%</span>
                                </div>
                                <p className="text-center text-sm text-slate-400">Output: {percentWidth} x {percentHeight} px</p>
                            </div>
                        )}

                         <button onClick={handleApplyResize} disabled={isLoading} className="mt-2 w-full text-sm bg-slate-600/50 hover:bg-slate-600 text-slate-200 font-medium py-1 px-3 rounded-md transition-colors">Apply Resize</button>
                    </div>
                     <div>
                        <h3 className="font-semibold mb-2">Crop</h3>
                        <div className="grid grid-cols-1 gap-2">
                           <button onClick={onEnterCropMode} disabled={isLoading} className="bg-slate-600/50 hover:bg-slate-600 text-slate-200 font-semibold py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2">
                               <Icon name="crop" className="w-5 h-5" />
                               <span>Interactive Crop</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div>
                <h2 className="text-xl font-bold mb-4">Actions</h2>
                <div className="space-y-3">
                     <a
                        href={processedImage ?? '#'}
                        download="enhanced-image.png"
                        className={`w-full flex items-center justify-center space-x-2 bg-emerald-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-emerald-500 transition-colors duration-200 ${!processedImage || isLoading ? 'opacity-50 pointer-events-none' : ''}`}
                    >
                        <Icon name="download" className="w-5 h-5" />
                        <span>Download</span>
                    </a>
                    <button
                        onClick={onReset}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center space-x-2 bg-slate-600/50 text-slate-300 font-semibold py-2 px-4 rounded-lg hover:bg-slate-600 disabled:opacity-50 transition-colors duration-200"
                    >
                        <Icon name="reset" className="w-5 h-5" />
                        <span>Reset</span>
                    </button>
                    <button
                        onClick={onUploadNew}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center space-x-2 border border-slate-600 text-slate-300 font-semibold py-2 px-4 rounded-lg hover:bg-slate-700 hover:border-slate-500 disabled:opacity-50 transition-colors duration-200"
                    >
                        <Icon name="upload" className="w-5 h-5" />
                        <span>New Image</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

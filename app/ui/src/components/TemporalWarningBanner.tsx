import React, { useState } from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';

interface TemporalWarningBannerProps {
  isEstimated: boolean;
  fairnessApplied: boolean;
}

const DISMISS_KEY = "ep_temporal_warning_dismissed";

const TemporalWarningBanner: React.FC<TemporalWarningBannerProps> = ({ isEstimated, fairnessApplied }) => {
  const [dismissed, setDismissed] = useState<boolean>(() => {
    return sessionStorage.getItem(DISMISS_KEY) === "true";
  });

  const handleDismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "true");
    setDismissed(true);
  };

  if ((!isEstimated && !fairnessApplied) || dismissed) return null;

  return (
    <div className="space-y-2 mb-6 relative group">
      <button
        onClick={handleDismiss}
        aria-label="Dismiss warning"
        className="absolute top-2 right-2 p-1 rounded hover:bg-white/10 transition-colors text-slate-400 z-10 opacity-0 group-hover:opacity-100"
      >
        <X className="w-4 h-4" />
      </button>

      {isEstimated && (
        <div className="flex items-start gap-4 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-500">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-500">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-amber-500 text-sm">Velocity Data Initialising</h3>
            <p className="text-xs text-amber-200/70 mt-1 leading-relaxed">
              Temporal features for this field are currently being estimated using baseline demand. 
              The confidence interval is widened to account for this uncertainty. 
              Full accuracy will be available after 12 hours of additional market observation.
            </p>
          </div>
        </div>
      )}

      {fairnessApplied && (
        <div className="flex items-start gap-4 p-4 rounded-xl border border-indigo-500/30 bg-indigo-500/10 backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-700">
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
            <Info className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-indigo-400 text-sm">Fairness Calibration Active</h3>
            <p className="text-xs text-indigo-200/70 mt-1 leading-relaxed">
              Per-group threshold calibration is active (FPR/TPR diffs ≤ 0.10). 
              Decision boundaries have been adjusted to ensure compliance with demographic parity standards.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default TemporalWarningBanner;

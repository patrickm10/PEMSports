import React, { useEffect, useRef } from 'react';
import type { Ranking } from '../models/Ranking';
import { X, TrendingUp, Activity } from 'lucide-react';

interface PlayerDetailProps {
  player: Ranking | null;
  onClose: () => void;
}

export const PlayerDetail: React.FC<PlayerDetailProps> = ({ player, onClose }) => {
  const overlayRef = useRef<HTMLDivElement>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!player) return null;

  return (
    <div 
      className="modal-overlay" 
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="modal-title"
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="modal-content glass-panel" role="document">
        <button className="btn-close" onClick={onClose} aria-label="Close detail panel">
          <X size={24} />
        </button>
        
        <div className="detail-header">
          <h2 id="modal-title" className="detail-name">{player.player_name}</h2>
          <div className="detail-badges">
            <span className="badge rank">Rank #{player.rank || '—'}</span>
            <span className="badge position">{player.position.toUpperCase()}</span>
            <span className="badge team">{player.team.split('_').pop()?.toUpperCase()}</span>
          </div>
        </div>
        
        <div className="detail-metrics">
          <div className="metric-card">
            <div className="metric-icon"><TrendingUp size={20} /></div>
            <div className="metric-data">
              <span className="metric-label">Total FPTS (PPR)</span>
              <span className="metric-value">{player.fpts_ppr.toFixed(1)}</span>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-icon"><Activity size={20} /></div>
            <div className="metric-data">
              <span className="metric-label">Avg FPTS / Game</span>
              <span className="metric-value">{player.fpts_ppr_per_game.toFixed(1)}</span>
            </div>
          </div>
        </div>

        <div className="detail-body">
          <h3>Advanced Analytics Insights</h3>
          <p className="placeholder-text">
            In future revisions, integrating with `td_predictor.py` and ML pipelines 
            will expose deep feature metrics here securely based on his deterministic UUID: 
            <br/><br/>
            <code>{player.player_id}</code>
          </p>
        </div>
      </div>
    </div>
  );
};

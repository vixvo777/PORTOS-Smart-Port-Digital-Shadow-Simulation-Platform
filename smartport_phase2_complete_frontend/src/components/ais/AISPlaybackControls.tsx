import type {HistoricalTrack} from '../../hooks/useHistoricalAIS';
type Props={timeSeconds:number;startSeconds:number;endSeconds:number;playing:boolean;speed:number;loading:boolean;error?:string;trackCount:number;pointCount:number;onTime:(n:number)=>void;onPlaying:(v:boolean)=>void;onSpeed:(v:number)=>void};
export default function AISPlaybackControls(p:Props){
 const fmt=(s:number)=>new Date(s*1000).toISOString().replace('T',' ').slice(0,19)+' · source-time mapping';
 return <div className="ais-playback panel">
  <div className="play-controls">
   <button className="play" onClick={()=>p.onPlaying(!p.playing)} disabled={p.loading}>{p.playing?'Pause':'Play'} AIS</button>
   <button className="square" onClick={()=>{p.onPlaying(false);p.onTime(p.startSeconds)}}>Reset</button>
   <select value={p.speed} onChange={e=>p.onSpeed(Number(e.target.value))}><option value={1}>1×</option><option value={10}>10×</option><option value={60}>60×</option><option value={300}>300×</option></select>
   <span className="clock-readout">{fmt(p.timeSeconds)}</span>
  </div>
  <input aria-label="Historical AIS timeline" type="range" min={p.startSeconds} max={p.endSeconds} step={1} value={Math.min(p.endSeconds,p.timeSeconds)} onChange={e=>{p.onPlaying(false);p.onTime(Number(e.target.value))}}/>
  <div className="scrub-labels"><span>{p.trackCount} vessels · {p.pointCount.toLocaleString()} observations</span><span>{p.loading?'Loading AIS…':p.error||'Historical AIS sample · 15–16 June 2019'}</span></div>
 </div>;
}

import { useEffect, useMemo, useState } from 'react';
import { aisApi, type AISPosition, type AISTrackSummary } from '../services/aisApi';

export type HistoricalTrack = { mmsi:string; vesselName:string; vesselType:string; segments:AISPosition[][]; summaries:AISTrackSummary[] };
export function useHistoricalAIS(start:string,end:string,enabled=true) {
  const [tracks,setTracks] = useState<HistoricalTrack[]>([]);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState('');
  const [coverage,setCoverage] = useState<any>(null);
  useEffect(() => {
    if (!enabled) return;
    let cancelled=false;
    setLoading(true); setError('');
    (async()=>{
      try {
        const [meta,index] = await Promise.all([aisApi.coverage(),aisApi.tracks(start,end,80,10)]);
        if(cancelled)return;
        setCoverage(meta);
        const summaries=index.items;
        const unique=[...new Set(summaries.map(x=>x.mmsi))];
        const responses:(Awaited<ReturnType<typeof aisApi.track>>|null)[]=[];
        for(let i=0;i<unique.length;i+=8){
          const batch=await Promise.all(unique.slice(i,i+8).map(m=>aisApi.track(m,start,end).catch(()=>null)));
          responses.push(...batch);
        }
        if(cancelled)return;
        const next:HistoricalTrack[]=[];
        responses.forEach((r,i)=>{
          if(!r?.items?.length)return;
          const grouped=new Map<number,AISPosition[]>();
          for(const p of r.items){const a=grouped.get(p.track_segment)||[];a.push(p);grouped.set(p.track_segment,a);}
          const segments=[...grouped.values()].map(a=>a.sort((x,y)=>Date.parse(x.timestamp.replace(' ','T')+'Z')-Date.parse(y.timestamp.replace(' ','T')+'Z')));
          const s=summaries.filter(x=>x.mmsi===unique[i]);
          next.push({mmsi:unique[i],vesselName:r.items[0].vessel_name||s[0]?.vessel_name||unique[i],vesselType:r.items[0].vessel_type||s[0]?.vessel_type||'Unknown',segments,summaries:s});
        });
        setTracks(next);
      }catch(e){if(!cancelled)setError(e instanceof Error?e.message:'Could not load historical AIS');}
      finally{if(!cancelled)setLoading(false);}
    })();
    return()=>{cancelled=true;};
  },[start,end,enabled]);
  const pointCount=useMemo(()=>tracks.reduce((n,t)=>n+t.segments.reduce((m,s)=>m+s.length,0),0),[tracks]);
  return {tracks,loading,error,coverage,pointCount};
}

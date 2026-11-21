import type { AISPosition } from '../services/aisApi';
const epoch=(s:string)=>Date.parse(s.replace(' ','T')+'Z');
const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
const radians=(d:number)=>d*Math.PI/180;
const degrees=(r:number)=>r*180/Math.PI;

// Interpolate only inside a single continuous track segment. The caller must never
// concatenate segments or interpolate across a segment boundary.
export function interpolateSegment(points:AISPosition[],timeMs:number) {
  if(!points.length)return null;
  if(timeMs<=epoch(points[0].timestamp))return {...points[0],interpolated:false};
  if(timeMs>=epoch(points[points.length-1].timestamp))return {...points[points.length-1],interpolated:false};
  let lo=0,hi=points.length-1;
  while(lo+1<hi){const mid=(lo+hi)>>1;if(epoch(points[mid].timestamp)<=timeMs)lo=mid;else hi=mid;}
  const a=points[lo],b=points[hi],ta=epoch(a.timestamp),tb=epoch(b.timestamp);
  const gap=(tb-ta)/1000;
  if(gap<=0||gap>300||a.track_segment!==b.track_segment)return null;
  const f=clamp((timeMs-ta)/(tb-ta),0,1);
  return {...a,longitude:a.longitude+(b.longitude-a.longitude)*f,latitude:a.latitude+(b.latitude-a.latitude)*f,
    sog:a.sog==null||b.sog==null?a.sog:a.sog+(b.sog-a.sog)*f,
    cog:a.cog==null||b.cog==null?a.cog:degrees(radians(a.cog)+Math.atan2(Math.sin(radians(b.cog-a.cog))*f,Math.cos(radians(b.cog-a.cog))*f)),
    timestamp:new Date(timeMs).toISOString().replace('T',' ').slice(0,19),interpolated:true};
}
export function positionAt(segments:AISPosition[][],timeMs:number) {
  for(const segment of segments){if(!segment.length)continue;const first=epoch(segment[0].timestamp),last=epoch(segment[segment.length-1].timestamp);if(timeMs>=first&&timeMs<=last)return interpolateSegment(segment,timeMs);}
  return null;
}
export function segmentPolyline(points:AISPosition[]) {
  return points.map(p=>[p.longitude,p.latitude] as [number,number]);
}

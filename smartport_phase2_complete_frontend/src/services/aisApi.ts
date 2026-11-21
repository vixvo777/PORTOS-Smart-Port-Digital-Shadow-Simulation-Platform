import { API } from '../lib';

export type AISPosition = {
  timestamp: string; longitude: number; latitude: number;
  sog: number | null; cog: number | null; heading: number | null;
  navigation_status: number | null; track_segment: number; gap_seconds: number | null;
  vessel_name?: string | null; vessel_type?: string | null;
};
export type AISTrackSummary = {
  mmsi: string; track_segment: number; point_count: number;
  start_time: string; end_time: string; vessel_name?: string | null;
  vessel_type?: string | null;
};
export type AISTrack = { mmsi: string; count: number; items: AISPosition[] };

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`);
  if (!response.ok) throw new Error(`AIS API ${response.status}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}
const enc = encodeURIComponent;
export const aisApi = {
  coverage: () => get<{available:boolean;records:number;vessels:number;start_time:string;end_time:string;historical:boolean}>('/api/v1/ais/coverage'),
  tracks: (start:string,end:string,limit=200,minPoints=10) =>
    get<{start:string;end:string;items:AISTrackSummary[]}>(`/api/v1/ais/tracks?start=${enc(start)}&end=${enc(end)}&limit=${limit}&min_points=${minPoints}`),
  track: (mmsi:string,start:string,end:string) =>
    get<AISTrack>(`/api/v1/ais/track/${enc(mmsi)}?start=${enc(start)}&end=${enc(end)}`)
};

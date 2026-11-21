import {useEffect,useMemo} from 'react';
import * as C from 'cesium';
import type {HistoricalTrack} from '../../hooks/useHistoricalAIS';
import {positionAt} from '../../utils/aisPlayback';

type Props={viewer:C.Viewer|null;tracks:HistoricalTrack[];timeSeconds:number;visible?:boolean;onSelect?:(mmsi:string)=>void};
export default function AISVesselLayer({viewer,tracks,timeSeconds,visible=true,onSelect}:Props){
 const flattened=useMemo(()=>tracks.flatMap(t=>t.segments.map((s,i)=>({mmsi:t.mmsi,name:t.vesselName,segment:s,index:i}))),[tracks]);
 useEffect(()=>{
  if(!viewer)return;
  const entities:C.Entity[]=[];
  flattened.forEach(t=>{
   if(t.segment.length<2)return;
   const coords=t.segment.flatMap(p=>[p.longitude,p.latitude]);
   const line=viewer.entities.add({polyline:{positions:C.Cartesian3.fromDegreesArray(coords),width:2,material:new C.ColorMaterialProperty(C.Color.fromCssColorString('#42d4e8').withAlpha(.58)),clampToGround:true},properties:{ais:true,mmsi:t.mmsi}});
   entities.push(line);
  });
  return()=>entities.forEach(e=>viewer.entities.remove(e));
 },[viewer,flattened]);
 useEffect(()=>{
  if(!viewer)return;
  const existing=viewer.entities.values.filter(e=>e.properties?.aisVessel?.getValue?.());
  existing.forEach(e=>viewer.entities.remove(e));
  if(!visible)return;
  const ms=timeSeconds*1000;
  tracks.forEach(t=>{
   const p=positionAt(t.segments,ms);if(!p)return;
   const heading=(p.heading!=null&&p.heading>=0&&p.heading<360)?p.heading:(p.cog??0);
   const entity=viewer.entities.add({position:C.Cartesian3.fromDegrees(p.longitude,p.latitude,8),
    point:{pixelSize:9,color:new C.ConstantProperty(C.Color.fromCssColorString('#45d5e8')),outlineColor:new C.ConstantProperty(C.Color.WHITE),outlineWidth:1},
    label:{text:t.vesselName||t.mmsi,font:'10px sans-serif',fillColor:new C.ConstantProperty(C.Color.WHITE),outlineColor:new C.ConstantProperty(C.Color.BLACK),outlineWidth:2,style:C.LabelStyle.FILL_AND_OUTLINE,pixelOffset:new C.Cartesian2(0,-16),distanceDisplayCondition:new C.DistanceDisplayCondition(0,50000)},
    properties:{aisVessel:true,mmsi:t.mmsi,heading,sog:p.sog,interpolated:p.interpolated}});
   if(onSelect)entity.description=`MMSI ${t.mmsi}`;
  });
 },[viewer,tracks,timeSeconds,visible,onSelect]);
 return null;
}

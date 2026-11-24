import {test,expect} from '@playwright/test';
import {readFileSync,existsSync} from 'node:fs';
import {resolve,relative,isAbsolute,sep} from 'node:path';
import {createHash} from 'node:crypto';

type Clip={id:string;path:string;sha256:string;duration_seconds:number;channels:number;sample_rate:number;frames:number};
const privateRoot=resolve('../.publication-private');
function privatePath(file:string){
 const path=resolve(file);const rel=relative(privateRoot,path);
 if(!rel||rel==='..'||rel.startsWith('..'+sep)||isAbsolute(rel))throw new Error('Audio evidence must stay inside the private test area.');
 return path;
}
const evidence=process.env.ROADMAP_AUDIO_MANIFEST_FILE;
const clips:Clip[]=evidence&&existsSync(privatePath(evidence))?JSON.parse(readFileSync(privatePath(evidence),'utf8')).items:[];
if(!clips.length){
 test('roadmap audio requires private real-synthesis evidence',()=>{
  test.skip(true,'Set ROADMAP_AUDIO_MANIFEST_FILE after the private worker synthesis sweep.');
 });
}else{
 if(clips.length!==68||new Set(clips.map(c=>c.id)).size!==68)throw new Error('Expected exactly68 unique real roadmap clips.');
 for(const clip of clips){
  test(`${clip.id}: decode and normal/accelerated playback`,async({page})=>{
   const data=readFileSync(privatePath(clip.path));
   expect(createHash('sha256').update(data).digest('hex')).toBe(clip.sha256);
   // Browser requests are intercepted locally; no listener or app service runs.
   await page.route('http://127.0.0.1:3998/**',async route=>{
    if(new URL(route.request().url()).pathname==='/clip.wav'){
     await route.fulfill({contentType:'audio/wav',body:data});return;
    }
    await route.fulfill({contentType:'text/html',body:'<!doctype html><title>Synthetic audio validation</title><button id="play">Play synthetic clip</button><audio id="audio" preload="auto" src="/clip.wav"></audio><script>document.getElementById("play").onclick=()=>document.getElementById("audio").play();</script>'});
   });
   await page.goto('http://127.0.0.1:3998/');
   const decoded=await page.evaluate(async()=>{
    const context=new AudioContext();
    try{
     const response=await fetch('/clip.wav');const buffer=await context.decodeAudioData(await response.arrayBuffer());
     return {channels:buffer.numberOfChannels,duration:buffer.duration,nonSilent:buffer.getChannelData(0).some(v=>Math.abs(v)>0.00001)};
    }finally{await context.close();}
   });
   expect(decoded.channels).toBe(clip.channels);expect(decoded.nonSilent).toBe(true);
   expect(Math.abs(decoded.duration-clip.duration_seconds)).toBeLessThan(0.03);
   const audio=page.locator('audio');
   await expect.poll(()=>audio.evaluate((el:HTMLAudioElement)=>el.readyState)).toBeGreaterThanOrEqual(2);
   await audio.evaluate((el:HTMLAudioElement)=>{el.playbackRate=1;});
   await page.getByRole('button',{name:'Play synthetic clip'}).click();
   await expect.poll(()=>audio.evaluate((el:HTMLAudioElement)=>el.currentTime)).toBeGreaterThan(0);
   await audio.evaluate((el:HTMLAudioElement)=>{el.playbackRate=16;});
   await expect.poll(()=>audio.evaluate((el:HTMLAudioElement)=>el.ended),{timeout:30000}).toBe(true);
   expect(await audio.evaluate((el:HTMLAudioElement)=>el.error?.code??null)).toBeNull();
   expect(await audio.evaluate((el:HTMLAudioElement)=>el.currentTime)).toBeCloseTo(clip.duration_seconds,1);
  });
 }
}

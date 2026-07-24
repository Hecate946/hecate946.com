import type { SeasonDefinition } from './types';

type AutumnPalette = {
  light: string;
  middle: string;
  dark: string;
  vein: string;
  outline: string;
};

const palettes: readonly AutumnPalette[] = [
  // Golden yellow
  { light: '#f4c84a', middle: '#d99a25', dark: '#9a591d', vein: 'rgba(105, 62, 20, 0.76)', outline: 'rgba(91, 52, 18, 0.56)' },
  { light: '#edb936', middle: '#ca7f20', dark: '#86451d', vein: 'rgba(92, 50, 18, 0.78)', outline: 'rgba(76, 40, 17, 0.58)' },
  // Warm orange
  { light: '#e99135', middle: '#c55b26', dark: '#7c2d22', vein: 'rgba(98, 35, 24, 0.74)', outline: 'rgba(74, 24, 25, 0.56)' },
  { light: '#de742d', middle: '#ad4828', dark: '#6f2724', vein: 'rgba(88, 31, 25, 0.76)', outline: 'rgba(70, 23, 24, 0.56)' },
  // Scarlet and deep red
  { light: '#df5840', middle: '#b52f2f', dark: '#6d1f2b', vein: 'rgba(82, 24, 31, 0.8)', outline: 'rgba(66, 18, 27, 0.6)' },
  { light: '#c93d36', middle: '#98262f', dark: '#571d2a', vein: 'rgba(70, 22, 30, 0.82)', outline: 'rgba(54, 17, 25, 0.62)' },
] as const;

function fillShape(context: CanvasRenderingContext2D, trace: () => void, palette: AutumnPalette, variant: number) {
  context.save();
  context.shadowColor = 'rgba(54, 17, 18, 0.28)';
  context.shadowBlur = 7;
  context.shadowOffsetY = 4;
  trace();
  const gradient = context.createLinearGradient(-55, -60, 52, 67);
  gradient.addColorStop(0, palette.light);
  gradient.addColorStop(0.5, palette.middle);
  gradient.addColorStop(1, palette.dark);
  context.fillStyle = gradient;
  context.fill();
  context.shadowColor = 'transparent';
  trace();
  context.clip();
  const glow = context.createRadialGradient(-25, -31, 0, -18, -22, 72);
  glow.addColorStop(0, 'rgba(255, 183, 82, 0.22)');
  glow.addColorStop(0.55, 'rgba(234, 105, 44, 0.04)');
  glow.addColorStop(1, 'rgba(255,255,255,0)');
  context.fillStyle = glow;
  context.fillRect(-90, -90, 180, 180);
  for (let i = 0; i < 5; i += 1) {
    const a = variant * 1.41 + i * 2.23;
    const r = 12 + ((variant * 13 + i * 19) % 31);
    context.fillStyle = i % 2 ? 'rgba(246,151,61,0.055)' : 'rgba(73,23,25,0.065)';
    context.beginPath();
    context.ellipse(Math.cos(a) * r, Math.sin(a) * r * 0.7, 1.8, 1.1, a, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
  trace();
  context.strokeStyle = palette.outline;
  context.lineWidth = 1.5;
  context.stroke();
}

function strokeStem(context: CanvasRenderingContext2D, palette: AutumnPalette, fromX: number, fromY: number, toX: number, toY: number, width = 4) {
  context.strokeStyle = palette.vein;
  context.lineCap = 'round';
  context.lineWidth = width;
  context.beginPath();
  context.moveTo(fromX, fromY);
  context.quadraticCurveTo((fromX + toX) / 2 - 2, (fromY + toY) / 2, toX, toY);
  context.stroke();
}

function drawRoundedLobed(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  const trace = () => {
    context.beginPath();
    context.moveTo(-8, 47);
    context.bezierCurveTo(-35, 50, -51, 36, -45, 17);
    context.bezierCurveTo(-63, 7, -59, -14, -41, -18);
    context.bezierCurveTo(-52, -39, -33, -55, -16, -42);
    context.bezierCurveTo(-8, -67, 15, -65, 18, -39);
    context.bezierCurveTo(39, -53, 57, -35, 45, -16);
    context.bezierCurveTo(66, -8, 62, 14, 43, 20);
    context.bezierCurveTo(53, 39, 26, 54, -8, 47);
    context.closePath();
  };
  fillShape(context, trace, palette, variant);
  strokeStem(context, palette, -18, 69, 30, -38, 3.8);
  context.lineWidth = 1.7;
  for (const [x, y, ex, ey] of [[-2,31,-35,14],[6,17,-35,-10],[15,1,-20,-30],[3,28,32,27],[12,12,43,4],[22,-5,42,-21]] as const) {
    context.beginPath(); context.moveTo(x,y); context.quadraticCurveTo((x+ex)/2,y-2,ex,ey); context.stroke();
  }
}

function drawBerrySprig(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  context.save();
  context.rotate(((variant % 5) - 2) * 0.03);
  context.strokeStyle = palette.vein;
  context.lineCap = 'round';
  context.lineWidth = 3.2;
  context.beginPath();
  context.moveTo(-48, 68); context.quadraticCurveTo(-10, 24, 7, -60);
  context.moveTo(-10, 28); context.quadraticCurveTo(18, 13, 49, -15);
  context.moveTo(2, -17); context.quadraticCurveTo(25, -32, 49, -34);
  context.stroke();
  const leafData = [[-22,36,-0.85,27],[-13,17,0.95,28],[-5,-3,-0.9,27],[2,-24,0.84,26],[17,18,-0.75,29],[33,2,0.82,27]] as const;
  for (let i=0;i<leafData.length;i+=1) {
    const [x,y,a,l] = leafData[i]!;
    const trace = () => { context.save(); context.translate(x,y); context.rotate(a); context.beginPath(); context.moveTo(0,0); context.bezierCurveTo(l*.35,-l*.22,l*.32,-l*.78,0,-l); context.bezierCurveTo(-l*.32,-l*.78,-l*.35,-l*.22,0,0); context.closePath(); context.restore(); };
    fillShape(context, trace, palette, variant+i);
  }
  const berries = [[21,-45,10],[41,-45,9],[48,-27,9],[29,-27,8],[10,-61,8]] as const;
  for (const [x,y,r] of berries) {
    context.fillStyle = palette.middle; context.beginPath(); context.arc(x,y,r,0,Math.PI*2); context.fill();
    context.strokeStyle = palette.outline; context.lineWidth = 1.2; context.stroke();
  }
  context.restore();
}

function drawOvalLeaf(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  const trace = () => { context.beginPath(); context.moveTo(-8,48); context.bezierCurveTo(-43,37,-51,1,-38,-29); context.bezierCurveTo(-24,-61,12,-65,40,-43); context.bezierCurveTo(60,-26,58,10,39,33); context.bezierCurveTo(22,53,5,57,-8,48); context.closePath(); };
  fillShape(context, trace, palette, variant);
  strokeStem(context,palette,-17,67,35,-40,3.7);
  context.lineWidth=1.65;
  for (const [sx,sy,ex,ey] of [[-4,27,-30,12],[3,15,-28,-2],[11,3,-22,-18],[20,-11,-10,-34],[2,24,30,25],[10,11,39,8],[18,-3,43,-13],[26,-17,43,-29]] as const) { context.beginPath(); context.moveTo(sx,sy); context.quadraticCurveTo((sx+ex)/2,sy-2,ex,ey); context.stroke(); }
}

function drawOakLeaf(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  const trace = () => { context.beginPath(); context.moveTo(0,52); context.bezierCurveTo(-13,46,-25,42,-25,31); context.bezierCurveTo(-48,37,-60,23,-45,9); context.bezierCurveTo(-65,1,-58,-19,-39,-20); context.bezierCurveTo(-52,-39,-34,-52,-18,-40); context.bezierCurveTo(-17,-62,0,-71,8,-49); context.bezierCurveTo(25,-61,41,-46,32,-29); context.bezierCurveTo(55,-35,61,-14,43,-4); context.bezierCurveTo(62,7,52,26,31,25); context.bezierCurveTo(38,43,18,54,0,52); context.closePath(); };
  fillShape(context,trace,palette,variant);
  strokeStem(context,palette,-7,72,7,-52,4);
  context.lineWidth=1.7;
  for (const [y,ex,ey] of [[32,-31,25],[17,-44,8],[2,-42,-15],[-14,-29,-36],[31,31,25],[16,44,7],[1,42,-14],[-15,29,-35]] as const) { context.beginPath(); context.moveTo(1,y); context.quadraticCurveTo(ex*.45,y-4,ex,ey); context.stroke(); }
}

function drawMapleLeaf(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  const trace = () => { const o=((variant%3)-1)*1.5; context.beginPath(); context.moveTo(0,48); context.lineTo(-15,40); context.lineTo(-30,55); context.lineTo(-28,32); context.lineTo(-53,36); context.lineTo(-43,17); context.lineTo(-67,5+o); context.lineTo(-45,-6); context.lineTo(-57,-28); context.lineTo(-31,-22); context.lineTo(-35,-49); context.lineTo(-14,-34); context.lineTo(0,-67); context.lineTo(14,-34); context.lineTo(36,-49); context.lineTo(31,-22); context.lineTo(58,-28); context.lineTo(45,-6); context.lineTo(67,5-o); context.lineTo(43,17); context.lineTo(53,36); context.lineTo(28,32); context.lineTo(30,55); context.lineTo(15,40); context.closePath(); };
  fillShape(context,trace,palette,variant);
  strokeStem(context,palette,-6,74,0,-57,4.2);
  context.lineWidth=1.75;
  for (const [sx,sy,cx,cy,ex,ey] of [[0,4,-14,-10,-50,-27],[0,13,-19,18,-51,32],[0,-5,13,-13,50,-27],[0,13,18,18,51,32],[0,-10,-8,-28,-14,-44],[0,-10,8,-28,14,-44]] as const) { context.beginPath(); context.moveTo(sx,sy); context.quadraticCurveTo(cx,cy,ex,ey); context.stroke(); }
}

function drawSlimLobed(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  const trace = () => { context.beginPath(); context.moveTo(-5,51); context.bezierCurveTo(-22,43,-34,35,-28,23); context.bezierCurveTo(-46,22,-50,7,-34,1); context.bezierCurveTo(-48,-9,-39,-23,-25,-20); context.bezierCurveTo(-34,-38,-17,-49,-8,-34); context.bezierCurveTo(-4,-58,9,-67,15,-42); context.bezierCurveTo(30,-55,43,-42,34,-27); context.bezierCurveTo(52,-27,55,-10,39,-3); context.bezierCurveTo(53,8,43,23,28,19); context.bezierCurveTo(37,36,17,49,-5,51); context.closePath(); };
  fillShape(context,trace,palette,variant);
  strokeStem(context,palette,-13,72,12,-43,3.8);
  context.lineWidth=1.55;
  for (const [y,ex,ey] of [[31,-27,24],[17,-35,7],[2,-32,-11],[-14,-22,-29],[30,26,23],[15,37,6],[0,33,-12],[-15,24,-30]] as const) { context.beginPath(); context.moveTo(1,y); context.quadraticCurveTo(ex*.48,y-3,ex,ey); context.stroke(); }
}

function traceLeaflet(context: CanvasRenderingContext2D, x: number, y: number, angle: number, length: number) {
  const w=length*.34; context.save(); context.translate(x,y); context.rotate(angle); context.beginPath(); context.moveTo(0,0); context.bezierCurveTo(w,-length*.18,w,-length*.7,0,-length); context.bezierCurveTo(-w,-length*.7,-w,-length*.18,0,0); context.closePath(); context.restore();
}

function drawCompoundLeaf(context: CanvasRenderingContext2D, palette: AutumnPalette, variant: number) {
  context.strokeStyle=palette.vein; context.lineCap='round'; context.lineWidth=4; context.beginPath(); context.moveTo(-15,70); context.quadraticCurveTo(-1,22,4,-60); context.stroke();
  const pairs=[[42,27,.87],[23,30,.82],[3,32,.77],[-18,30,.7],[-38,25,.61]] as const;
  for(let i=0;i<pairs.length;i+=1){const [y,l,s]=pairs[i]!; const x=((y+60)/130)*-11+3; const la=-Math.PI/2-s,ra=-Math.PI/2+s; fillShape(context,()=>traceLeaflet(context,x,y,la,l),palette,variant+i); fillShape(context,()=>traceLeaflet(context,x+1,y-2,ra,l),palette,variant+i+1);}
  fillShape(context,()=>traceLeaflet(context,4,-55,0,27),palette,variant+9);
}

export function drawAutumnLeaf(context: CanvasRenderingContext2D, variant: number) {
  const palette=palettes[variant%palettes.length]!;
  context.save();
  context.rotate(((variant%7)-3)*0.018);
  switch(variant%7){
    case 0: drawRoundedLobed(context,palette,variant); break;
    case 1: drawBerrySprig(context,palette,variant); break;
    case 2: drawOvalLeaf(context,palette,variant); break;
    case 3: drawOakLeaf(context,palette,variant); break;
    case 4: drawMapleLeaf(context,palette,variant); break;
    case 5: drawSlimLobed(context,palette,variant); break;
    default: drawCompoundLeaf(context,palette,variant);
  }
  context.restore();
}

export const autumnShower: SeasonDefinition = {
  variantCount: 28,
  particleCount: { compact: 64, desktop: 108 },
  size: { minimum: 30, maximum: 40 },
  scale: 0.78,
  speed: { minimum: 105, maximum: 175 },
  drift: { minimum: -24, maximum: 24 },
  sway: { minimum: 22, maximum: 68 },
  swayRate: { minimum: 0.68, maximum: 1.35 },
  spin: { minimum: -1.3, maximum: 1.3 },
  flutterRate: { minimum: 1.8, maximum: 4.1 },
  opacity: { minimum: 0.86, maximum: 1 },
  flutter: true,
  drawSprite: drawAutumnLeaf,
};

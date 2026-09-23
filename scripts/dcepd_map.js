/* Applicant geography only. No individual coordinates or remote map services. */
(()=>{
const boundaryNode=document.getElementById('map-boundaries'),dataNode=document.getElementById('dashboard-data');
if(!boundaryNode||!dataNode)return;
const geo=JSON.parse(boundaryNode.textContent),data=JSON.parse(dataNode.textContent);
const counts=new Map(data.geography.map(r=>[r.location,r.applications]));
const ns='http://www.w3.org/2000/svg';
const ZANZIBAR=new Set(['Kaskazini Pemba','Kaskazini Unguja','Kusini Pemba','Kusini Unguja','Mjini Magharibi']);
const palette=['#440154','#482878','#3e4989','#31688e','#26828e','#1f9e89','#35b779','#6ece58','#b5de2b','#fde725'];

function colourAt(t){
 const p=t*(palette.length-1),a=Math.floor(p),b=Math.min(a+1,palette.length-1),weight=p-a;
 const channel=(hex,start)=>parseInt(hex.slice(start,start+2),16);
 return '#'+[1,3,5].map(start=>Math.round(channel(palette[a],start)*(1-weight)+channel(palette[b],start)*weight).toString(16).padStart(2,'0')).join('');
}
function binsFor(values){
 const maximum=Math.max(...values,5),minimum=Math.min(...values,5);
 const edges=[0,1,5];
 for(let power=1;edges.at(-1)<=maximum;power*=10){
  for(const factor of [10,25,50]){const edge=factor*power;if(edge>edges.at(-1))edges.push(edge)}
 }
 const active=edges.filter((edge,i)=>edge<=maximum||(i>0&&edges[i-1]<=maximum)).filter(edge=>edge>=(minimum>=5?5:0));
 return active.slice(0,-1).map((lower,i)=>({
  label:lower===active[i+1]-1?lower.toLocaleString():lower.toLocaleString()+'–'+(active[i+1]-1).toLocaleString(),
  max:active[i+1]-1,
  color:colourAt(i/Math.max(active.length-2,1))
 }));
}
function allPoints(geometry){
 const out=[];
 const walk=node=>{
  if(Array.isArray(node)&&typeof node[0]==='number'&&typeof node[1]==='number'){out.push(node);return}
  if(Array.isArray(node))node.forEach(walk);
 };
 walk(geometry.coordinates);
 return out;
}
function fitProject(features,width,height,pad=30){
 const pts=features.flatMap(f=>allPoints(f.geometry));
 const lons=pts.map(p=>p[0]),lats=pts.map(p=>p[1]);
 const minLon=Math.min(...lons),maxLon=Math.max(...lons),minLat=Math.min(...lats),maxLat=Math.max(...lats);
 const usableW=width-pad*2,usableH=height-pad*2;
 const sx=usableW/Math.max(maxLon-minLon,0.0001),sy=usableH/Math.max(maxLat-minLat,0.0001),scale=Math.min(sx,sy);
 const drawW=(maxLon-minLon)*scale,drawH=(maxLat-minLat)*scale;
 const ox=(width-drawW)/2,oy=(height-drawH)/2;
 return ([lon,lat])=>[ox+(lon-minLon)*scale,oy+(maxLat-lat)*scale];
}
function featurePath(f,project){
 const polys=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;
 return polys.flatMap(poly=>poly.map(ring=>ring.map((pt,i)=>{const [x,y]=project(pt);return (i?'L':'M')+x.toFixed(2)+','+y.toFixed(2)}).join('')+'Z')).join('');
}
function renderMap({hostId,legendId,selectionId,coverageId,features,width,height,titleText,ariaLabel,project,note}){
 const host=document.getElementById(hostId),legend=document.getElementById(legendId),selection=document.getElementById(selectionId),coverage=document.getElementById(coverageId);
 if(!host||!legend||!selection||!coverage)return;
 const values=features.map(f=>counts.get(f.properties.name)).filter(n=>Number.isInteger(n)&&n>=0);
 const bins=binsFor(values);
 const svg=document.createElementNS(ns,'svg');
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('role','group');svg.setAttribute('aria-label',ariaLabel);
 const title=document.createElementNS(ns,'title');title.textContent=titleText;svg.append(title);
 let mapped=0,regions=0;
 for(const f of features){
  const name=f.properties.name,n=counts.get(name),known=Number.isInteger(n),path=document.createElementNS(ns,'path');
  const label=name+': '+(known?n.toLocaleString()+' application records':'no separately published regional count (not zero)');
  path.setAttribute('d',featurePath(f,project));path.setAttribute('fill',known?(bins.find(b=>n<=b.max)||bins.at(-1)).color:'#e2e5e5');
  path.setAttribute('fill-rule','evenodd');path.setAttribute('stroke','#557778');path.setAttribute('stroke-width','.8');path.setAttribute('tabindex','0');path.setAttribute('role','img');path.setAttribute('aria-label',label);
  const tip=document.createElementNS(ns,'title');tip.textContent=label;path.append(tip);
  const select=()=>{selection.textContent=label};path.addEventListener('click',select);path.addEventListener('focus',select);path.addEventListener('mouseenter',select);svg.append(path);
  if(known){mapped+=n;regions++}
 }
 host.replaceChildren(svg);legend.replaceChildren();
 for(const b of [...bins,{label:'No separately published count',color:'#e2e5e5'}]){
  const span=document.createElement('span'),swatch=document.createElement('i');swatch.className='swatch';swatch.style.background=b.color;span.append(swatch,document.createTextNode(b.label));legend.append(span)
 }
 coverage.textContent=`${mapped.toLocaleString()} applications mapped to ${regions} of ${features.length} regions with published counts. ${note}`;
}

const mainland=geo.features.filter(f=>!ZANZIBAR.has(f.properties.name));
const zanzibar=geo.features.filter(f=>ZANZIBAR.has(f.properties.name));

// Preserve the established mainland display projection.
const mainlandProject=([lon,lat])=>[35+(lon-29.5)*67.5*Math.cos(6.4*Math.PI/180),40+(-.9-lat)*67.5];
renderMap({
 hostId:'tz-map',legendId:'map-legend',selectionId:'map-selection',coverageId:'map-coverage',
 features:mainland,width:820,height:820,titleText:'Applicant residence by mainland Tanzania region',
 ariaLabel:'Mainland Tanzania regions coloured by published application count',project:mainlandProject,
 note:'Grey means no separately published count, not zero. Small cells withheld from the public output also remain grey.'
});

renderMap({
 hostId:'zanzibar-map',legendId:'zanzibar-legend',selectionId:'zanzibar-selection',coverageId:'zanzibar-coverage',
 features:zanzibar,width:560,height:620,titleText:'Applicant residence by Zanzibar region',
 ariaLabel:'Zanzibar regions coloured by published application count',project:fitProject(zanzibar,560,620,42),
 note:'This panel uses its own colour scale because Zanzibar counts are much smaller than mainland counts; colours must not be compared directly between the two maps.'
});

const names=new Set(geo.features.map(f=>f.properties.name));
const off=data.geography.filter(r=>!names.has(r.location)).map(r=>r.location);
const offNode=document.getElementById('map-unassigned');
if(offNode)offNode.textContent=`Not assigned to regional polygons: ${off.join(', ')||'none'}.`;
})();

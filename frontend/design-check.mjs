import {chromium} from '@playwright/test';
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.addInitScript(()=>localStorage.setItem('token','preview'));
const food={id:1,name:'Görög joghurt',kcal:100,protein:10,carbs:5,fat:4,source:'manual',confidence:'precise'};
let entries=[];
await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;let result={};
 if(path==='/api/profile')result={profile:{sex:'male',birth_date:'1990-01-01',height_cm:180,weight_kg:85,activity:'light',weekly_loss_kg:.5,target_weight_kg:78},calculation:{daily_target:2100,bmr:1800,maintenance:2600}};
 else if(path==='/api/foods')result=[food];
 else if(path.startsWith('/api/day/'))result={entries,totals:{kcal:entries.length*100,protein:entries.length*10,carbs:entries.length*5,fat:entries.length*4}};
 else if(path==='/api/entries'){entries=[{id:1,food,grams:100,meal:'breakfast',nutrients:{kcal:100,protein:10,carbs:5,fat:4}}];result={id:1}}
 else if(path.startsWith('/api/entries/'))entries=[];
 await route.fulfill({json:result});});
await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:5173');await page.getByText('2 100',{exact:false}).first().waitFor().catch(()=>{});
for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:900});await page.waitForTimeout(200);if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Overflow '+width)}
await page.setViewportSize({width:390,height:844});
await page.getByRole('button',{name:'Étel hozzáadása',exact:true}).click();await page.getByRole('button',{name:/Görög joghurt/}).click();await page.getByRole('button',{name:'+ Hozzáadás a naplóhoz',exact:true}).click();await page.getByRole('button',{name:'Görög joghurt törlése'}).waitFor();
await page.waitForTimeout(800);await page.screenshot({path:'design-mobile.png',fullPage:true});
await page.getByRole('button',{name:'Görög joghurt törlése'}).click();await page.getByRole('button',{name:'Profil megnyitása'}).click();await page.getByRole('heading',{name:'Profil és cél',exact:true}).waitFor();
await page.getByRole('button',{name:'×',exact:true}).click();await page.getByRole('button',{name:'Trendek',exact:false}).click();await page.getByRole('heading',{name:'A számok mögött'}).waitFor();
await page.setViewportSize({width:1440,height:1000});await page.waitForTimeout(800);await page.screenshot({path:'design-desktop.png',fullPage:true});
await browser.close();if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: 320/390/768/1440 px, add/delete, profile, trends, no runtime errors.');

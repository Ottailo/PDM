import {test,expect} from '@playwright/test';
import {randomUUID} from 'node:crypto';
import {mkdir} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {pmOwner,pmInvite,pmWrite} from './pm-helpers';

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
async function screenshot(page:import('@playwright/test').Page,name:string) {
  const target=resolve(ROOT,'tests/screenshots/personas');
  await mkdir(target,{recursive:true});
  await page.screenshot({path:resolve(target,name+'.png'),fullPage:true});
}

test('PM plan produces real assigned work, mobile access actions and read-only persona denial',async({browser,baseURL})=>{
  test.setTimeout(180000);

  const stamp=randomUUID().slice(0,10);
  const origin=baseURL||'http://localhost:5174';
  const ownerContext=await browser.newContext({baseURL:origin});
  const techContext=await browser.newContext({baseURL:origin,viewport:{width:375,height:812}});
  const viewerContext=await browser.newContext({baseURL:origin});
  const storesContext=await browser.newContext({baseURL:origin});
  const plannerContext=await browser.newContext({baseURL:origin});
  try {
    await pmOwner(ownerContext,'owner',stamp);
    const tech=await pmInvite(ownerContext.request,techContext,`pm-tech-${stamp}@example.test`,'technician');
    await pmInvite(ownerContext.request,viewerContext,`pm-view-${stamp}@example.test`,'viewer');
    await pmInvite(ownerContext.request,storesContext,`pm-stores-${stamp}@example.test`,'stores');
    await pmInvite(ownerContext.request,plannerContext,`pm-planner-${stamp}@example.test`,'planner');
    const machine=await pmWrite(ownerContext.request,'/assets',{code:'TEST-PM-'+stamp,name:'Test-only scheduled pump'},'POST',201);
    const due=new Date(Date.now()+3600000);
    const startLocal=new Intl.DateTimeFormat('sv-SE',{timeZone:'Africa/Lagos',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(due).replace(' ','T');
    const body={asset_id:machine.asset.id,title:'Test-only PM '+stamp,description:'Synthetic software plan, no physical equipment',priority:'medium',assignee_id:tech.identity.membership.id,checklist:[{text:'Record test-only PM evidence'}],timezone:'Africa/Lagos',start_local:startLocal,interval_unit:'day',interval_count:1,reminder_hours:24};
    const page=await ownerContext.newPage();
    page.setDefaultTimeout(15000);
    await page.goto('/app/maintenance/plans');
    await page.getByRole('button',{name:'Create preventive plan',exact:true}).click();
    await page.getByRole('dialog').getByRole('combobox',{name:/^Machine/}).selectOption(String(machine.asset.id));
    await page.getByRole('dialog').getByRole('textbox',{name:/^Plan title/}).fill(body.title);
    await page.getByLabel('Work instructions',{exact:true}).fill(body.description);
    await page.getByRole('dialog').getByRole('combobox',{name:/^Assigned person/}).selectOption(String(tech.identity.membership.id));
    await page.getByRole('dialog').getByLabel(/^First due date and time/).fill(startLocal);
    await page.getByRole('dialog').getByLabel(/^Time zone \(IANA\)/).fill('Africa/Lagos');
    await page.getByLabel('Step 1',{exact:true}).fill('Record test-only PM evidence');
    await expect(page.getByRole('button',{name:'Create plan',exact:true})).toBeDisabled();
    await page.getByRole('button',{name:'Preview dates',exact:true}).click();
    await expect(page.getByRole('region',{name:'Server calendar preview'})).toBeVisible();
    const saveResponse=page.waitForResponse(response=>response.url().endsWith('/api/v1/maintenance-plans')&&response.request().method()==='POST');
    await page.getByRole('button',{name:'Create plan',exact:true}).click();
    const saved=await saveResponse;
    expect(saved.status()).toBe(201);
    const created=await saved.json();
    for (const context of [viewerContext,storesContext,techContext]) await pmWrite(context.request,'/maintenance-plans',body,'POST',403);
    await page.goto('/app/maintenance/plans');
    await expect(page.getByText(body.title,{exact:true}).first()).toBeVisible();
    await page.goto('/app/maintenance/plans/'+created.plan.id);
    await expect(page.getByRole('heading',{name:body.title,exact:true}).first()).toBeVisible();
    await expect.poll(async()=>{
      const r=await ownerContext.request.get('/api/v1/maintenance-plans/'+created.plan.id);
      return (await r.json()).occurrences.length;
    },{timeout:45000}).toBe(1);
    const detail=await (await ownerContext.request.get('/api/v1/maintenance-plans/'+created.plan.id)).json();
    const jobId=detail.occurrences[0].work_order_id;
    await expect.poll(async()=>{
      const d=await (await ownerContext.request.get('/api/v1/maintenance-plans/'+created.plan.id)).json();
      return d.reminders.some((r:{stage:string,state:string})=>r.stage==='due'&&r.state==='accepted');
    },{timeout:45000}).toBe(true);
    await page.reload();
    await expect(page.getByText('SMTP accepted',{exact:true}).first()).toBeVisible();
    await screenshot(page,'pm-owner-plan-and-real-reminder');
    const technicianPage=await techContext.newPage();
    await technicianPage.goto('/app/maintenance/'+jobId);
    await expect(technicianPage.getByRole('button',{name:'Start work',exact:true})).toBeVisible();
    await technicianPage.getByRole('button',{name:'Start work',exact:true}).click();
    await technicianPage.getByRole('dialog').getByRole('button',{name:'Start work',exact:true}).click();
    await technicianPage.getByRole('button',{name:'Submit for review',exact:true}).click();
    await technicianPage.getByRole('dialog').getByLabel('Record test-only PM evidence').check();
    await technicianPage.getByLabel('Completion notes').fill('Synthetic PM evidence, not factory work');
    await technicianPage.getByLabel('Time spent (minutes)').fill('12');
    await technicianPage.getByRole('dialog').getByRole('button',{name:'Submit for review',exact:true}).click();
    await expect(technicianPage.getByRole('dialog')).toHaveCount(0);
    await expect(technicianPage.getByText('Awaiting review',{exact:true}).first()).toBeVisible();
    await expect(technicianPage.getByRole('button',{name:'Approve completion',exact:true})).toHaveCount(0);
    await screenshot(technicianPage,'pm-technician-mobile-submitted');
    const plannerPage=await plannerContext.newPage();
    await plannerPage.goto('/app/maintenance/'+jobId);
    await plannerPage.getByRole('button',{name:'Approve completion',exact:true}).click();
    await plannerPage.getByRole('dialog').getByRole('button',{name:'Approve completion',exact:true}).click();
    await expect(plannerPage.getByRole('button',{name:'Reopen job',exact:true})).toBeVisible();
    await screenshot(plannerPage,'pm-planner-reviewed-history');
    for (const [context,label] of [[viewerContext,'viewer'],[storesContext,'stores']] as const) {
      const reader=await context.newPage();
      await reader.goto('/app/maintenance/plans/'+created.plan.id);
      await expect(reader.getByRole('heading',{name:body.title,exact:true}).first()).toBeVisible();
      await screenshot(reader,'pm-'+label+'-read-only-plan');
    }
    await page.setViewportSize({width:375,height:812});
    await page.goto('/app/team');
    const remove=page.getByRole('button',{name:'Remove Test PM technician',exact:true});
    await expect(remove).toBeVisible();
    const dimensions=await remove.boundingBox();
    expect(dimensions).not.toBeNull();
    expect(dimensions!.height).toBeGreaterThanOrEqual(44);
    expect(dimensions!.x).toBeGreaterThanOrEqual(0);
    expect(dimensions!.x+dimensions!.width).toBeLessThanOrEqual(375);
    await screenshot(page,'pm-owner-mobile-visible-team-actions');
    for (const width of [320,390]) {
      await page.setViewportSize({width,height:844});
      const bounds=await remove.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    }
    await page.getByRole('button',{name:'Remove Test PM technician',exact:true}).click();
    await expect(page.getByRole('dialog').getByLabel(/^Confirm your password/)).toBeVisible();
    await page.getByRole('dialog').getByRole('button',{name:'Close dialog',exact:true}).click();
  } finally {
    await Promise.all([ownerContext,techContext,viewerContext,storesContext,plannerContext].map(c=>c.close()));
  }
});

import type { APIRequestContext, BrowserContext } from '@playwright/test';
import { expect } from '@playwright/test';
import { createHmac, randomUUID } from 'node:crypto';
import { waitForMailLink } from './mailpit';

export async function pmWrite(request: APIRequestContext,path: string,data: unknown={},method='POST',expected=200,key=randomUUID()) {
  const csrf=await request.get('/api/v1/csrf');
  expect(csrf.status()).toBe(200);
  const response=await request.fetch('/api/v1'+path,{method,data,headers:{'X-CSRF-Token':(await csrf.json()).csrf_token,'Idempotency-Key':key}});
  expect(response.status(), `${method} ${path}: ${await response.text()}`).toBe(expected);
  return response.json();
}

function totp(secret: string) {
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits=[...secret].map(c=>alphabet.indexOf(c).toString(2).padStart(5,'0')).join('');
  const key=Buffer.from((bits.match(/.{8}/g)||[]).map(b=>parseInt(b,2)));
  const counter=Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));
  const hash=createHmac('sha1',key).update(counter).digest();
  return ((hash.readUInt32BE(hash[hash.length-1]&15)&0x7fffffff)%1000000).toString().padStart(6,'0');
}

export async function pmOwner(context: BrowserContext,label: string,stamp: string) {
  const email=`pm-browser-${label}-${stamp}@example.test`;
  const password=`Pm-only!${stamp}-${label}-42`;
  const created=await pmWrite(context.request,'/auth/signup',{email,password,name:`Test PM ${label}`,company_name:`Test PM ${label} ${stamp}`},'POST',201);
  const link=new URL(await waitForMailLink(context.request,email,'/verify-email'));
  await pmWrite(context.request,'/auth/verify-email',{token:link.searchParams.get('token')});
  await pmWrite(context.request,'/auth/login',{email,password});
  const setup=await pmWrite(context.request,'/auth/mfa/setup',{password});
  const enrolled=await pmWrite(context.request,'/auth/mfa/confirm',{code:totp(setup.secret)});
  return {email,password,company:created.company,recovery:enrolled.recovery_codes as string[]};
}

export async function pmInvite(owner: APIRequestContext,person: BrowserContext,email: string,role: string) {
  const password=`Pm-person-only!${randomUUID()}42`;
  await pmWrite(owner,'/invitations',{email,role},'POST',201);
  const link=new URL(await waitForMailLink(owner,email,'/invite'));
  await pmWrite(person.request,'/invitations/accept',{token:link.searchParams.get('token'),name:`Test PM ${role}`,password});
  await pmWrite(person.request,'/auth/login',{email,password});
  const identity=await (await person.request.get('/api/v1/auth/me')).json();
  return {email,password,identity};
}

# BriefWorks Authentication Implementation Plan

## Purpose

BriefWorks is a private educational production studio, not a public SaaS product. Authentication should be designed around controlled access, manual approval, and defense in depth.

The first version of the application should support secure login without public account creation. Users should not be able to create accounts through the frontend. Account creation and approval should be handled through Supabase and, later, Cloudflare Access policies.

## Final Authentication Model

```text
Cloudflare Access         = outer private access gate, added before public deployment
Supabase Auth             = application identity provider
Google OAuth              = only login method
FastAPI authorization     = backend permission enforcement
Supabase RLS              = database-level protection
Private Supabase Storage  = protected source and generated files
```

BriefWorks should begin as:

```text
Private app
Approved Google account only
No public registration
No username/password signup
No create-account page
```

Future expansion should allow:

```text
Trusted user whitelisting
Approved device access
Role-based access
Project-level permissions
Cloudflare device posture checks
```

---

## Security Principles

1. **No public signup flow**
   - Do not build `/signup`, `/register`, or `/create-account`.
   - Users should not self-register through the frontend.

2. **Google OAuth only**
   - The login page should offer one primary action: `Continue with Google`.
   - Avoid username/password authentication for the first version.

3. **Manual user approval**
   - Approved users should be created or invited through Supabase.
   - The app should also maintain an `approved_users` table for internal authorization.

4. **Backend enforcement**
   - React can hide UI elements, but FastAPI must enforce all sensitive permissions.

5. **Database enforcement**
   - Supabase Row Level Security should protect project-owned and user-owned data.

6. **Private files by default**
   - Uploaded documents, generated artifacts, and exports should be stored in private Supabase Storage buckets.

7. **Cloudflare Access before public deployment**
   - Local development can proceed without Cloudflare Access.
   - No public BriefWorks deployment should exist without an outer access gate.

---

## Recommended Build Phases

| Phase | Goal | Required for Local V1? | Required Before Public Deployment? |
|---|---|---:|---:|
| 1 | Supabase Google OAuth login | Yes | Yes |
| 2 | No signup page | Yes | Yes |
| 3 | React protected routes | Yes | Yes |
| 4 | FastAPI JWT verification | Yes | Yes |
| 5 | Approved users table | Yes | Yes |
| 6 | Supabase RLS | Yes | Yes |
| 7 | Private storage buckets | Yes | Yes |
| 8 | Cloudflare Access | No | Yes |
| 9 | Device posture checks | No | Later |

---

## Repository Assumptions

This plan assumes the current repository shape:

```text
app/                 React/Vite frontend
services/api/        Future FastAPI backend
supabase/            Future Supabase migrations and local config
```

Earlier drafts may refer to `apps/web`. For this repository, use `app` unless the project is later converted into a monorepo.

The initial implementation should replace the default Vite starter screen with the authenticated BriefWorks shell. Do not preserve Vite sample UI, sample logos, or counter state as part of the auth work.

---

# Phase 1: Supabase Auth Setup

## Goal

Enable secure Google login while preventing open public account creation.

## Supabase Settings

In the Supabase dashboard:

```text
Authentication → Providers → Google → Enable
Authentication → URL Configuration → Add redirect URLs
Authentication → General Configuration → Disable open signups
```

Important setting:

```text
Allow new users to sign up: Disabled
```

This means users should not be able to create new accounts simply by reaching the login page.

## Google OAuth Setup

In Google Cloud Console:

1. Create an OAuth client.
2. Choose web application.
3. Add authorized redirect URIs.
4. Copy the Google Client ID.
5. Copy the Google Client Secret.
6. Paste both into the Supabase Google provider settings.

Recommended redirect URLs:

```text
http://localhost:5173/auth/callback
https://briefworks.yourdomain.com/auth/callback
```

Supabase callback URL pattern:

```text
https://<your-supabase-project-ref>.supabase.co/auth/v1/callback
```

Use the exact callback URL shown in the Supabase Google provider configuration when setting up Google Cloud OAuth.

---

# Phase 2: Frontend Route Design

## Required Routes

The React/Vite app should include:

```text
/login
/auth/callback
/app
/app/projects
/app/projects/:projectId
/app/sources
/app/intellex
/app/mathesys
/app/qngen
```

## Routes Not to Build

Do not build:

```text
/signup
/register
/create-account
/forgot-username
/public-onboarding
```

## Recommended Login Page Copy

```text
BriefWorks

Private educational production studio.
Access is restricted to approved accounts.

[Continue with Google]
```

Recommended button text:

```text
Continue with Google
```

Optional supporting text:

```text
Only approved Google accounts may access BriefWorks.
```

## Login UI Design Requirements

Follow `.cursor/rules/style.md` for the authentication UI. The login screen should feel like a controlled-entry view for a private production system, not a consumer signup page.

Use this visual direction:

```text
Canvas: white or off-white
Shell/accent panel: navy
Primary action: scarlet filled button
Secondary accents: limited gold
Typography: display face for headings, Arial/Helvetica for body
Layout: left-aligned, structured, generous spacing
```

The login page should include:

```text
BriefWorks wordmark or text heading
Private access notice
Continue with Google primary action
Short approved-account helper text
Error message area
No signup links
No password reset links
No public onboarding links
```

Recommended login labels:

```text
Access Restricted
Private educational production studio
Continue with Google
Only approved Google accounts may access BriefWorks.
```

Avoid:

```text
Join now
Create your account
Start for free
Welcome aboard
Unlock your learning journey
```

---

# Phase 3: React/Vite + TypeScript Implementation

## Install Dependencies

From the Vite React app directory:

```bash
npm install @supabase/supabase-js react-router-dom
```

Recommended optional dependencies:

```bash
npm install @tanstack/react-query zustand
```

Use TanStack Query for API data fetching and Zustand only if the app needs lightweight client-side state beyond auth/session state.

---

## Environment Variables

Create a frontend environment file:

```bash
app/.env.local
```

Add:

```bash
VITE_SUPABASE_URL="https://your-project-ref.supabase.co"
VITE_SUPABASE_PUBLISHABLE_KEY="your-public-publishable-key"
VITE_API_BASE_URL="http://localhost:8000"
```

For production:

```bash
VITE_SUPABASE_URL="https://your-project-ref.supabase.co"
VITE_SUPABASE_PUBLISHABLE_KEY="your-public-publishable-key"
VITE_API_BASE_URL="https://api.briefworks.yourdomain.com"
```

Important:

```text
Only use VITE_ variables for values that are safe to expose in the browser.
Never place the Supabase service role key in the Vite frontend.
Never place OpenAI API keys in the Vite frontend.
Use a Supabase publishable key for frontend code. Legacy anon keys are public, but new projects should prefer publishable keys.
```

---

## Supabase Client

Create:

```text
app/src/lib/supabaseClient.ts
```

```ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string;

if (!supabaseUrl || !supabasePublishableKey) {
  throw new Error('Missing Supabase environment variables.');
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
```

---

## Auth Service

Create:

```text
app/src/features/auth/authService.ts
```

```ts
import { supabase } from '../../lib/supabaseClient';

export async function signInWithGoogle(): Promise<void> {
  const redirectTo = `${window.location.origin}/auth/callback`;

  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
    },
  });

  if (error) {
    throw error;
  }
}

export async function signOut(): Promise<void> {
  const { error } = await supabase.auth.signOut();

  if (error) {
    throw error;
  }
}

export async function getAccessToken(): Promise<string | null> {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    throw error;
  }

  return data.session?.access_token ?? null;
}
```

---

## Auth Provider

Create:

```text
app/src/features/auth/AuthProvider.tsx
```

```tsx
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '../../lib/supabaseClient';

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    supabase.auth.getSession().then(({ data, error }) => {
      if (!isMounted) return;

      if (error) {
        console.error('Failed to load Supabase session:', error);
      }

      setSession(data.session ?? null);
      setIsLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setIsLoading(false);
    });

    return () => {
      isMounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    return {
      session,
      user: session?.user ?? null,
      isLoading,
      isAuthenticated: Boolean(session),
    };
  }, [session, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider.');
  }

  return context;
}
```

---

## Protected Route Component

Create:

```text
app/src/features/auth/ProtectedRoute.tsx
```

```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
```

---

## Login Page

Create:

```text
app/src/pages/LoginPage.tsx
```

```tsx
import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { signInWithGoogle } from '../features/auth/authService';
import { useAuth } from '../features/auth/AuthProvider';
import './LoginPage.css';

export function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  async function handleGoogleLogin() {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      await signInWithGoogle();
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to start Google login. Try again.');
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <p className="auth-eyebrow">Access Restricted</p>
        <h1 id="auth-title">BriefWorks</h1>
        <p className="auth-copy">
          Private educational production studio. Access is restricted to approved accounts.
        </p>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isSubmitting}
          className="auth-primary-button"
        >
          {isSubmitting ? 'Redirecting...' : 'Continue with Google'}
        </button>

        <p className="auth-helper">Only approved Google accounts may access BriefWorks.</p>

        {errorMessage ? (
          <p className="auth-error" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </section>
    </main>
  );
}
```

This page intentionally does not include signup, email/password login, username creation, or password reset flows.

Create:

```text
app/src/pages/LoginPage.css
```

```css
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 48px 24px;
  background:
    linear-gradient(90deg, var(--color-navy, #001E2E) 0 36%, transparent 36%),
    var(--bg-app, #FFFFFF);
}

.auth-card {
  width: min(100%, 480px);
  padding: 40px;
  background: var(--bg-panel, #F7F7F5);
  border: 1px solid var(--border-subtle, #D8D8D6);
  border-top: 6px solid var(--color-scarlet, #940000);
  box-shadow: var(--shadow-panel, 0 8px 24px rgba(0, 0, 0, 0.08));
}

.auth-eyebrow {
  margin: 0 0 12px;
  color: var(--color-gold, #84754E);
  font-family: var(--font-display, "Arial Narrow", Arial, sans-serif);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.auth-card h1 {
  margin: 0;
  color: var(--color-scarlet, #940000);
  font-family: var(--font-display, "Arial Narrow", Arial, sans-serif);
  font-size: clamp(40px, 8vw, 64px);
  line-height: 0.95;
}

.auth-copy,
.auth-helper,
.auth-error {
  font-family: var(--font-body, Arial, Helvetica, sans-serif);
}

.auth-copy {
  margin: 24px 0 0;
  color: var(--text-primary, #000000);
  font-size: 18px;
  line-height: 1.5;
}

.auth-primary-button {
  width: 100%;
  margin-top: 32px;
  padding: 12px 28px;
  color: var(--color-white, #FFFFFF);
  background: var(--color-scarlet, #940000);
  border: 2px solid var(--color-scarlet, #940000);
  font-family: var(--font-display, "Arial Narrow", Arial, sans-serif);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.auth-primary-button:hover {
  background: var(--color-dark-scarlet, #660000);
  border-color: var(--color-dark-scarlet, #660000);
}

.auth-primary-button:focus-visible {
  outline: 3px solid var(--color-gold, #84754E);
  outline-offset: 3px;
}

.auth-primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.auth-helper {
  margin: 16px 0 0;
  color: var(--text-secondary, #4F5051);
  font-size: 14px;
}

.auth-error {
  margin: 20px 0 0;
  padding: 12px 14px;
  color: var(--color-dark-scarlet, #660000);
  background: #FFFFFF;
  border-left: 4px solid var(--color-scarlet, #940000);
  font-size: 14px;
}
```

---

## Auth Callback Page

Create:

```text
app/src/pages/AuthCallbackPage.tsx
```

```tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';

export function AuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    async function handleCallback() {
      const code = new URLSearchParams(window.location.search).get('code');
      const authResult = code
        ? await supabase.auth.exchangeCodeForSession(code)
        : await supabase.auth.getSession();

      if (authResult.error) {
        console.error('Authentication callback failed:', authResult.error);
        navigate('/login', { replace: true });
        return;
      }

      navigate('/app', { replace: true });
    }

    void handleCallback();
  }, [navigate]);

  return <div>Completing secure login...</div>;
}
```

---

## App Routes

Create or update:

```text
app/src/App.tsx
```

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './features/auth/AuthProvider';
import { ProtectedRoute } from './features/auth/ProtectedRoute';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { LoginPage } from './pages/LoginPage';

function AppHomePage() {
  return <div>BriefWorks App</div>;
}

function ProjectsPage() {
  return <div>Projects</div>;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/app" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<AppHomePage />} />
            <Route path="/app/projects" element={<ProjectsPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

---

## Authenticated API Client

Create:

```text
app/src/lib/apiClient.ts
```

```ts
import { getAccessToken } from '../features/auth/authService';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL as string;

if (!apiBaseUrl) {
  throw new Error('Missing VITE_API_BASE_URL.');
}

interface ApiRequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const { requiresAuth = true, headers, ...fetchOptions } = options;
  const requestHeaders = new Headers(headers);

  requestHeaders.set('Content-Type', 'application/json');

  if (requiresAuth) {
    const token = await getAccessToken();

    if (!token) {
      throw new Error('Missing access token.');
    }

    requestHeaders.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...fetchOptions,
    headers: requestHeaders,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with status ${response.status}.`);
  }

  return response.json() as Promise<TResponse>;
}
```

Example usage:

```ts
interface CurrentUserResponse {
  id: string;
  email: string;
  role: string;
}

export async function getCurrentUser(): Promise<CurrentUserResponse> {
  return apiRequest<CurrentUserResponse>('/me');
}
```

## Frontend Approval Handshake

A Supabase session only proves that Google login succeeded. It does not prove that the user is approved for BriefWorks.

After login and on protected app load:

```text
React detects Supabase session.
React calls FastAPI `/me` with the Supabase access token.
FastAPI verifies JWT and checks `approved_users`.
If `/me` returns 200, render the app.
If `/me` returns 401, send the user to `/login`.
If `/me` returns 403, sign out and show an access-restricted message.
```

The protected route should eventually gate on both values:

```text
Has Supabase session
Has approved BriefWorks user from `/me`
```

Recommended 403 copy:

```text
This Google account is not approved for BriefWorks access.
```

---

# Phase 4: FastAPI Auth Enforcement

## Backend Environment Variables

Create:

```text
services/api/.env
```

Add:

```bash
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_JWT_SECRET="your-supabase-jwt-secret"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
APP_ENV="local"
```

Important:

```text
SUPABASE_SERVICE_ROLE_KEY must only exist server-side.
Never expose it to React/Vite.
Do not log access tokens, refresh tokens, service keys, or OAuth provider secrets.
```

---

## JWT Verification Dependency

Recommended backend files:

```text
services/api/app/dependencies/auth.py
services/api/app/models/auth.py
```

Install backend dependencies:

```bash
pip install pyjwt cryptography pydantic
```

Example dependency:

```python
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

SUPABASE_JWT_SECRET = "load-from-env"

@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    role: str | None = None


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header.",
        )

    return token


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = extract_bearer_token(authorization)

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    return CurrentUser(id=user_id, email=email)
```

Note: use environment loading in real code instead of hardcoding `SUPABASE_JWT_SECRET`.

JWT validation requirements:

```text
Validate token signature.
Validate expiration.
Validate audience.
Validate issuer for the configured Supabase project.
Reject missing subject or email claims.
Treat frontend route protection as convenience only.
```

If the Supabase project uses asymmetric signing keys, prefer verifying against the Supabase JWKS endpoint instead of a shared JWT secret. If the project uses the default shared JWT secret, keep `SUPABASE_JWT_SECRET` only in backend environment storage.

---

## Approved User Check

Conceptual dependency:

```python
from fastapi import Depends, HTTPException, status


def require_approved_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    approved_user = lookup_approved_user_by_email(user.email)

    if not approved_user or not approved_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not approved for BriefWorks access.",
        )

    return CurrentUser(
        id=user.id,
        email=user.email,
        role=approved_user.role,
    )
```

Every protected route should depend on `require_approved_user`, not just `get_current_user`.

The approval check should use one of these sources:

```text
Preferred for V1: FastAPI queries `approved_users` with the server-only Supabase service role key.
Later option: Store stable role claims in Supabase `app_metadata`.
Avoid: `user_metadata`, because users can modify it.
```

On access denial, return `403` rather than redirecting or silently creating a user. The frontend may show a restrained message: `This Google account is not approved for BriefWorks access.`

---

## Example Protected Route

```python
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/me")
def get_me(user: CurrentUser = Depends(require_approved_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
    }
```

Example generation route:

```python
@router.post("/mathesys/generate")
def generate_lesson(
    request: GenerateLessonRequest,
    user: CurrentUser = Depends(require_approved_user),
):
    verify_project_access(user.id, request.project_id)
    job_id = enqueue_generation_job(user.id, request.project_id, request)

    return {
        "status": "queued",
        "job_id": job_id,
    }
```

---

# Phase 5: Supabase Database Design

## Recommended Auth Tables

```sql
create extension if not exists citext;

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email citext unique not null,
  display_name text,
  last_seen_at timestamptz,
  created_at timestamptz not null default now()
);

create table approved_users (
  id uuid primary key default gen_random_uuid(),
  email citext unique not null,
  role text not null default 'owner',
  is_active boolean not null default true,
  notes text,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint approved_users_role_check
    check (role in ('owner', 'admin', 'editor', 'viewer'))
);
```

Initial row:

```sql
insert into approved_users (email, role, is_active)
values ('your-email@gmail.com', 'owner', true);
```

Recommended indexes:

```sql
create index approved_users_active_email_idx
on approved_users (email)
where is_active = true;
```

`approved_users` should be treated as internal authorization data. The React app should not list or manage it directly in V1.

## User-Owned Tables

All user-owned or project-owned tables should include ownership fields.

Example:

```sql
create table projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  status text not null default 'active',
  created_at timestamptz not null default now()
);
```

Example source table:

```sql
create table sources (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  storage_path text,
  source_type text,
  created_at timestamptz not null default now()
);
```

Recommended ownership indexes:

```sql
create index projects_owner_id_idx on projects (owner_id);
create index sources_owner_id_idx on sources (owner_id);
create index sources_project_id_idx on sources (project_id);
```

---

# Phase 6: Supabase Row Level Security

Enable RLS:

```sql
alter table profiles enable row level security;
alter table approved_users enable row level security;
alter table projects enable row level security;
alter table sources enable row level security;
```

Keep `approved_users` locked down for client roles in V1:

```sql
revoke all on table approved_users from anon;
revoke all on table approved_users from authenticated;
```

The FastAPI backend can query `approved_users` with the server-only service role key. If BriefWorks later needs an admin UI, add narrow admin-only policies at that time.

Profile policies:

```sql
create policy "Users can read their own profile"
on profiles
for select
to authenticated
using ((select auth.uid()) is not null and id = (select auth.uid()));

create policy "Users can insert their own profile"
on profiles
for insert
to authenticated
with check ((select auth.uid()) is not null and id = (select auth.uid()));

create policy "Users can update their own profile"
on profiles
for update
to authenticated
using ((select auth.uid()) is not null and id = (select auth.uid()))
with check ((select auth.uid()) is not null and id = (select auth.uid()));
```

Project policies:

```sql
create policy "Users can read their own projects"
on projects
for select
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can insert their own projects"
on projects
for insert
to authenticated
with check ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can update their own projects"
on projects
for update
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()))
with check ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can delete their own projects"
on projects
for delete
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()));
```

Source policies:

```sql
create policy "Users can read their own sources"
on sources
for select
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can insert their own sources"
on sources
for insert
to authenticated
with check ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can update their own sources"
on sources
for update
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()))
with check ((select auth.uid()) is not null and owner_id = (select auth.uid()));

create policy "Users can delete their own sources"
on sources
for delete
to authenticated
using ((select auth.uid()) is not null and owner_id = (select auth.uid()));
```

Important:

```text
Use RLS even if BriefWorks begins as a one-user application.
It prevents weak assumptions from becoming security debt later.
Always include `to authenticated` in policies intended for logged-in users.
Remember that UPDATE requires a matching SELECT policy.
Do not authorize from user-editable `user_metadata`.
```

---

# Phase 7: Private Supabase Storage

## Recommended Buckets

```text
source-files
artifact-outputs
exports
thumbnails
```

All should be private.

Do not store private BriefWorks data in public buckets.

Protected file types include:

```text
PDFs
DOCX files
TXT/MD source notes
Images
Audio
Video
Generated HTML artifacts
Generated SVGs
Generated exports
Question banks
```

## File Access Flow

```text
Frontend requests file
    ↓
FastAPI checks authenticated user
    ↓
FastAPI verifies project/file ownership
    ↓
FastAPI creates signed URL or streams file
    ↓
Frontend displays or downloads file
```

Storage paths should include user or project scope:

```text
users/{user_id}/projects/{project_id}/sources/{source_id}/original.pdf
users/{user_id}/projects/{project_id}/artifacts/{artifact_id}/index.html
users/{user_id}/projects/{project_id}/exports/{export_id}.zip
```

## Storage RLS Policies

Private buckets are not enough by themselves. Supabase Storage uses policies on `storage.objects`, so each bucket needs explicit access rules.

V1 can keep the browser upload path simple:

```text
Frontend requests an upload target from FastAPI.
FastAPI verifies project access.
FastAPI uploads with the service role key or returns a short-lived signed upload URL.
Frontend never receives the service role key.
```

If the frontend uploads directly to Storage with the user's session, use policies scoped to the first path segment:

```sql
create policy "Users can read their own source files"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'source-files'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy "Users can upload their own source files"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'source-files'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy "Users can update their own source files"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'source-files'
  and (storage.foldername(name))[1] = (select auth.uid())::text
)
with check (
  bucket_id = 'source-files'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

create policy "Users can delete their own source files"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'source-files'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);
```

For direct upload paths, use this path shape instead of the earlier display-oriented path:

```text
{user_id}/projects/{project_id}/sources/{source_id}/original.pdf
```

Storage upsert requires `insert`, `select`, and `update` permissions. Avoid upsert for V1 unless replacement behavior is required.

---

# Phase 8: Cloudflare Access Before Public Deployment

Cloudflare Access is not required for local development, but it should be required before any public deployment.

Protect:

```text
briefworks.yourdomain.com
api.briefworks.yourdomain.com
```

Initial policy:

```text
Allow: your Google email
Deny: everyone else
```

Future policy:

```text
Allow specific approved emails
Allow approved identity provider groups
Require MFA
Require approved devices
Require device posture checks
```

Recommended deployment rule:

```text
No public BriefWorks URL without Cloudflare Access or equivalent private access control.
```

---

# Phase 9: Future Device-Based Access

Device-based access should be added later, not in v1.

Future Cloudflare Access posture options may include:

```text
Only approved devices
Cloudflare One Client required
Minimum OS version
Disk encryption required
Active security client required
Certificate-based device identity
```

Use device posture checks when BriefWorks contains enough valuable data or trusted users that device-level security is worth the added operational complexity.

---

# File and Directory Placement

Recommended frontend placement:

```text
app/src/
  App.tsx
  lib/
    supabaseClient.ts
    apiClient.ts
  features/
    auth/
      AuthProvider.tsx
      ProtectedRoute.tsx
      authService.ts
  pages/
    LoginPage.tsx
    AuthCallbackPage.tsx
```

Recommended backend placement:

```text
services/api/app/
  main.py
  routes/
    auth.py
    projects.py
    sources.py
    mathesys.py
    qngen.py
  dependencies/
    auth.py
  models/
    auth.py
  config.py
```

Recommended Supabase placement:

```text
supabase/
  migrations/
    0001_auth_profiles_and_approved_users.sql
    0002_projects_and_sources.sql
    0003_rls_policies.sql
```

---

# Authentication Flow Summary

```text
User opens /app
    ↓
React checks Supabase session
    ↓
No session found
    ↓
Redirect to /login
    ↓
User clicks Continue with Google
    ↓
Supabase starts Google OAuth
    ↓
Google authenticates user
    ↓
Supabase redirects to /auth/callback
    ↓
React stores session
    ↓
React calls FastAPI /me with Bearer token
    ↓
FastAPI verifies JWT
    ↓
FastAPI checks approved_users
    ↓
User enters BriefWorks
```

---

# Public Deployment Security Flow

```text
User opens briefworks.yourdomain.com
    ↓
Cloudflare Access checks identity/device policy
    ↓
If approved, request reaches React app
    ↓
React requires Supabase session
    ↓
User logs in with Google
    ↓
FastAPI verifies Supabase JWT on API requests
    ↓
Supabase RLS enforces database ownership
    ↓
Private Storage policies protect files
```

---

# V1 Implementation Checklist

## Supabase

- [ ] Create Supabase project.
- [ ] Enable Google OAuth provider.
- [ ] Configure Google OAuth credentials.
- [ ] Add localhost redirect URL.
- [ ] Add the real production redirect URL before deployment.
- [ ] Disable open signups.
- [ ] Create `profiles` table.
- [ ] Create `approved_users` table.
- [ ] Add your Google email to `approved_users`.
- [ ] Create initial `projects` table.
- [ ] Enable RLS.
- [ ] Add owner-based RLS policies.
- [ ] Create private storage buckets.
- [ ] Add Storage policies or route all Storage access through FastAPI.

## React/Vite + TypeScript

- [ ] Install `@supabase/supabase-js`.
- [ ] Install `react-router-dom`.
- [ ] Add `VITE_SUPABASE_URL`.
- [ ] Add `VITE_SUPABASE_PUBLISHABLE_KEY`.
- [ ] Add `VITE_API_BASE_URL`.
- [ ] Replace the default Vite starter UI.
- [ ] Add BriefWorks theme tokens from `.cursor/rules/style.md`.
- [ ] Create Supabase client.
- [ ] Create auth service.
- [ ] Create auth provider.
- [ ] Create protected route wrapper.
- [ ] Create `/login` page.
- [ ] Create `/auth/callback` page.
- [ ] Protect `/app` routes.
- [ ] Confirm protected routes require `/me` approval, not only a Supabase session.
- [ ] Add logout.
- [ ] Add authenticated API client.

## FastAPI

- [ ] Add Supabase JWT verification.
- [ ] Add `get_current_user` dependency.
- [ ] Add `require_approved_user` dependency.
- [ ] Add `/me` route.
- [ ] Protect `/projects` routes.
- [ ] Protect source upload routes.
- [ ] Protect generation job routes.
- [ ] Return `403` for authenticated but unapproved users.
- [ ] Ensure service keys remain server-side only.

## Before Public Deployment

- [ ] Configure Cloudflare Access.
- [ ] Protect frontend domain.
- [ ] Protect API domain.
- [ ] Allow only your Google email.
- [ ] Confirm no public signup page exists.
- [ ] Confirm Supabase open signups are disabled.
- [ ] Confirm RLS is enabled.
- [ ] Confirm buckets are private.
- [ ] Confirm no service keys are exposed to Vite.

---

# Final Recommendation

For BriefWorks v1, use:

```text
Supabase Auth
Google OAuth only
Login page only
No signup page
Manual user approval
FastAPI JWT verification
Approved users table
Supabase RLS
Private storage buckets
Cloudflare Access before public deployment
```

The final mental model is:

```text
Cloudflare Access = private front gate
Google OAuth      = secure identity login
Supabase Auth     = app session authority
FastAPI           = backend permission checkpoint
Supabase RLS      = database guardrail
Private Storage   = protected file vault
BriefWorks        = private educational production studio
```

This design keeps the first version simple while avoiding weak security assumptions that would become expensive to fix later.

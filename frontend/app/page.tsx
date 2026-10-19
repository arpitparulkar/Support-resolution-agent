'use client';

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react';

const API_URL = 'http://127.0.0.1:8000';
const SUGGESTIONS = [
  { title: 'Track my order', detail: 'Check the latest status of your order.', icon: 'box', prompt: 'Can you help me track my order?' },
  { title: 'Request a refund', detail: 'Get assistance with refund eligibility.', icon: 'refresh', prompt: 'I would like help understanding my refund options.' },
  { title: 'Delivery support', detail: 'Resolve delivery delays and shipping issues.', icon: 'truck', prompt: 'My delivery is delayed. Can you look into it?' },
  { title: 'Talk to support', detail: 'Get help with a more complex issue.', icon: 'headset', prompt: 'I need help with a support issue.' },
];

type Section = 'dashboard' | 'assistant' | 'conversations' | 'tickets';
type Message = { id?: number; role: string; content: string; created_at?: string };
type Conversation = { id: number; title: string; updated_at: string };
type Ticket = { id: number; ticket_id: string; issue: string; priority: string; status: string; order_id?: string | null; created_at: string };
type Account = { token: string; email: string; name: string };

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  const paths: Record<string, React.ReactNode> = {
    sparkle: <><path {...common} d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/><path {...common} d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z"/></>,
    grid: <><rect {...common} x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect {...common} x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect {...common} x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect {...common} x="13.5" y="13.5" width="7" height="7" rx="1.5"/></>,
    message: <><path {...common} d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.4-3.3A7.5 7.5 0 1 1 20 11.5Z"/><path {...common} d="M8 11h8M8 14h5"/></>,
    clock: <><circle {...common} cx="12" cy="12" r="8.5"/><path {...common} d="M12 7v5l3.5 2"/></>,
    ticket: <><path {...common} d="M4 7.5A2.5 2.5 0 0 0 4 12.5v4A1.5 1.5 0 0 0 5.5 18h13a1.5 1.5 0 0 0 1.5-1.5v-4a2.5 2.5 0 0 0 0-5v-1A1.5 1.5 0 0 0 18.5 5h-13A1.5 1.5 0 0 0 4 6.5v1Z"/><path {...common} d="M9 5v13" strokeDasharray="2 2"/></>,
    plus: <><path {...common} d="M12 5v14M5 12h14"/></>,
    arrow: <><path {...common} d="M5 12h14M13 6l6 6-6 6"/></>,
    send: <><path {...common} d="m21 3-7.2 18-3.5-7.3L3 10.2 21 3Z"/><path {...common} d="M10.3 13.7 21 3"/></>,
    menu: <><path {...common} d="M4 6h16M4 12h16M4 18h16"/></>,
    chevron: <path {...common} d="m9 18 6-6-6-6"/>,
    sun: <><circle {...common} cx="12" cy="12" r="4"/><path {...common} d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></>,
    moon: <path {...common} d="M20.5 14.2A8.7 8.7 0 0 1 9.8 3.5 8.8 8.8 0 1 0 20.5 14.2Z"/>,
    logout: <><path {...common} d="M10 17l5-5-5-5M15 12H3"/><path {...common} d="M12 3h6.5A1.5 1.5 0 0 1 20 4.5v15a1.5 1.5 0 0 1-1.5 1.5H12"/></>,
    box: <><path {...common} d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path {...common} d="m4.5 7.7 7.5 4.4 7.5-4.4M12 12v9"/></>,
    refresh: <><path {...common} d="M20 7v5h-5M4 17v-5h5"/><path {...common} d="M5.6 9A7 7 0 0 1 18 6l2 1m-16 10 2 1a7 7 0 0 0 12.4-3"/></>,
    truck: <><path {...common} d="M3 6h11v11H3zM14 10h4l3 3v4h-7z"/><circle {...common} cx="7.5" cy="18" r="1.5"/><circle {...common} cx="17.5" cy="18" r="1.5"/></>,
    headset: <><path {...common} d="M4 13v-2a8 8 0 0 1 16 0v2"/><path {...common} d="M4 13h3v6H6a2 2 0 0 1-2-2v-4Zm16 0h-3v6h1a2 2 0 0 0 2-2v-4ZM17 20c-1 1-2.5 1-4 1"/></>,
    check: <path {...common} d="m5 12 4 4L19 6"/>,
    close: <><path {...common} d="m6 6 12 12M18 6 6 18"/></>,
    lock: <><rect {...common} x="4" y="10" width="16" height="11" rx="2"/><path {...common} d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
    eye: <><path {...common} d="M2.5 12s3.2-6 9.5-6 9.5 6 9.5 6-3.2 6-9.5 6-9.5-6-9.5-6Z"/><circle {...common} cx="12" cy="12" r="2.5"/></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24">{paths[name] ?? paths.sparkle}</svg>;
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date);
}

function responseError(data: unknown, fallback: string) {
  if (data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string') return data.detail;
  return fallback;
}

export default function Page() {
  const [account, setAccount] = useState<Account | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState('');
  const [theme, setTheme] = useState<'dark' | 'light'>('light');
  const [section, setSection] = useState<Section>('dashboard');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState('');
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketLoading, setTicketLoading] = useState(false);
  const [ticketError, setTicketError] = useState('');
  const [conversationLoading, setConversationLoading] = useState(false);
  const [conversationError, setConversationError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [serviceAvailable, setServiceAvailable] = useState<boolean | null>(null);
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const messageEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = window.localStorage.getItem('resolveai_token');
    const storedEmail = window.localStorage.getItem('resolveai_email') ?? '';
    const storedName = window.localStorage.getItem('resolveai_name') ?? '';
    const savedTheme = window.localStorage.getItem('resolveai_theme');
    if (token) setAccount({ token, email: storedEmail, name: storedName });
    if (savedTheme === 'light' || savedTheme === 'dark') setTheme(savedTheme);
    setAuthReady(true);
  }, []);

  useEffect(() => {
    window.localStorage.setItem('resolveai_theme', theme);
  }, [theme]);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((response) => setServiceAvailable(response.ok))
      .catch(() => setServiceAvailable(false));
  }, []);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  useEffect(() => {
    if (!account || (section !== 'dashboard' && section !== 'conversations')) return;
    let cancelled = false;
    setConversationLoading(true);
    setConversationError('');
    fetch(`${API_URL}/conversations`, { headers: { Authorization: `Bearer ${account.token}` } })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(responseError(data, 'Could not load conversations.'));
        if (!cancelled) setConversations(Array.isArray(data) ? data : []);
      })
      .catch((error: unknown) => {
        if (!cancelled) setConversationError(error instanceof Error ? error.message : 'Could not load conversations.');
      })
      .finally(() => { if (!cancelled) setConversationLoading(false); });
    return () => { cancelled = true; };
  }, [account, section]);

  useEffect(() => {
    if (!account || section !== 'tickets') return;
    let cancelled = false;
    setTicketLoading(true);
    setTicketError('');
    fetch(`${API_URL}/tickets`, { headers: { Authorization: `Bearer ${account.token}` } })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(responseError(data, 'Could not load tickets.'));
        if (!cancelled) setTickets(Array.isArray(data) ? data : []);
      })
      .catch((error: unknown) => {
        if (!cancelled) setTicketError(error instanceof Error ? error.message : 'Could not load tickets.');
      })
      .finally(() => { if (!cancelled) setTicketLoading(false); });
    return () => { cancelled = true; };
  }, [account, section]);

  const selectSection = (next: Section) => {
    setSection(next);
    setMobileOpen(false);
    setChatError('');
  };

  const startNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setDraft('');
    setChatError('');
  };

  const beginNewChat = () => {
    startNewChat();
    selectSection('assistant');
  };

  const openConversation = async (conversationId: number) => {
    if (!account) return;
    setSection('assistant');
    setMobileOpen(false);
    setConversationLoading(true);
    setConversationError('');
    setChatError('');
    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
        headers: { Authorization: `Bearer ${account.token}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(responseError(data, 'Could not open this conversation.'));
      setActiveConversationId(data.id);
      setMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch (error) {
      setConversationError(error instanceof Error ? error.message : 'Could not open this conversation.');
    } finally {
      setConversationLoading(false);
    }
  };

  const sendMessage = async () => {
    const message = draft.trim();
    if (!message || !account || isSending) return;
    setDraft('');
    setChatError('');
    setMessages((current) => [...current, { role: 'user', content: message }]);
    setIsSending(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${account.token}` },
        body: JSON.stringify({ message, ...(activeConversationId !== null ? { conversation_id: activeConversationId } : {}) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(responseError(data, 'Your message could not be sent. Please try again.'));
      setActiveConversationId(data.conversation_id);
      setMessages((current) => [...current, { role: 'assistant', content: data.reply }]);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'Your message could not be sent. Please try again.');
    } finally {
      setIsSending(false);
    }
  };

  const handleAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError('');
    setAuthBusy(true);
    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const payload = authMode === 'login' ? { email, password } : { email, full_name: fullName, password };
    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(responseError(data, 'We could not sign you in. Please check your details.'));
      const nextAccount = { token: data.access_token, email, name: authMode === 'register' ? fullName : '' };
      window.localStorage.setItem('resolveai_token', nextAccount.token);
      window.localStorage.setItem('resolveai_email', nextAccount.email);
      window.localStorage.setItem('resolveai_name', nextAccount.name);
      setAccount(nextAccount);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Unable to reach the support service.');
    } finally {
      setAuthBusy(false);
    }
  };

  const logout = () => {
    window.localStorage.removeItem('resolveai_token');
    window.localStorage.removeItem('resolveai_email');
    window.localStorage.removeItem('resolveai_name');
    setAccount(null);
    setConversations([]);
    setMessages([]);
    setActiveConversationId(null);
    setSection('dashboard');
  };

  const onComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  if (!authReady) return <main className="boot-screen"><span className="brand-mark"><Icon name="sparkle" size={22} /></span></main>;

  if (!account) {
    return (
      <main className={`auth-screen theme-${theme}`}>
        <div className="auth-topbar">
          <a className="brand-lockup" href="#" aria-label="ResolveAI home"><span className="brand-mark"><Icon name="sparkle" size={20} /></span><span>Resolve<span className="brand-accent">AI</span></span></a>
          <button className="icon-button theme-switch" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
        </div>
        <div className="auth-layout">
          <section className="auth-story">
            <div className="eyebrow"><span className="online-dot" /> INTELLIGENT CUSTOMER CARE</div>
            <h1>Support that thinks.<br /><span>Resolution that works.</span></h1>
            <p>An intelligent support platform that understands customer issues, coordinates specialized agents, and helps deliver reliable resolutions.</p>
            <div className="hero-actions"><a className="primary-button" href="#auth-title">Launch assistant <Icon name="arrow" size={17} /></a><a className="secondary-link" href="#how-it-works">Explore how it works <span aria-hidden="true">↗</span></a></div>
            <p className="hand-note">powered by intelligent agents <span aria-hidden="true">↗</span></p>
            <svg className="workflow-sketch" viewBox="0 0 620 210" role="img" aria-label="Illustration of a customer request moving through an AI agent and support tools to a resolution">
              <path className="sketch-line" d="M119 105 C158 73 185 73 218 104 S274 137 311 103 S373 72 407 104 S465 137 503 103" />
              <path className="sketch-arrow" d="m493 92 13 11-13 11" />
              <circle className="sketch-halo" cx="93" cy="105" r="47" />
              <circle className="sketch-node" cx="93" cy="105" r="28" />
              <path className="sketch-person" d="M85 103a8 8 0 1 1 16 0m-21 18c2-9 8-13 13-13s11 4 13 13" />
              <rect className="sketch-agent" x="231" y="75" width="60" height="60" rx="15" />
              <path className="sketch-agent-face" d="M247 101h2m23 0h2m-22 14c5 4 10 4 15 0" />
              <circle className="sketch-star" cx="278" cy="67" r="5" />
              <path className="sketch-tool" d="M350 84h43v42h-43zM359 96h25m-25 9h18m-18 9h21" />
              <circle className="sketch-node" cx="531" cy="105" r="28" />
              <path className="sketch-check" d="m518 105 9 9 17-19" />
              <text x="93" y="176" textAnchor="middle">CUSTOMER REQUEST</text>
              <text x="261" y="176" textAnchor="middle">AI AGENT</text>
              <text x="371" y="176" textAnchor="middle">TOOLS</text>
              <text x="531" y="176" textAnchor="middle">RESOLUTION</text>
            </svg>
            <div className="story-footer"><span>One conversation.</span><span className="footer-separator">/</span><span>Thoughtful answers.</span></div>
          </section>
          <section className="auth-panel" aria-labelledby="auth-title">
            <div className="auth-heading"><p className="eyebrow">YOUR SUPPORT SPACE</p><h2 id="auth-title">{authMode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p>{authMode === 'login' ? 'Sign in to continue your conversations.' : 'A few details and we’ll get you started.'}</p></div>
            <form className="auth-form" onSubmit={handleAuth}>
              {authMode === 'register' && <label>Full name<input required minLength={2} autoComplete="name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your name" /></label>}
              <label>Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
              <label>Password<div className="password-field"><input required minLength={6} type={showPassword ? 'text' : 'password'} autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 6 characters" /><button className="password-toggle" type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}><Icon name="eye" size={17} /></button></div></label>
              {authError && <div className="inline-error" role="alert">{authError}</div>}
              <button className="primary-button auth-submit" type="submit" disabled={authBusy}>{authBusy ? <span className="spinner" /> : <>{authMode === 'login' ? 'Sign in' : 'Create account'} <Icon name="arrow" size={17} /></>}</button>
            </form>
            <p className="auth-switch">{authMode === 'login' ? 'New to ResolveAI?' : 'Already have an account?'} <button onClick={() => { setAuthError(''); setAuthMode(authMode === 'login' ? 'register' : 'login'); }}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
            <div className="auth-security"><Icon name="lock" size={15} /> Your account is protected with secure sign-in</div>
          </section>
        </div>
        <section className="editorial-features graph-paper" id="how-it-works" aria-labelledby="features-title">
          <div className="features-intro"><p className="eyebrow">HOW RESOLVEAI WORKS</p><h2 id="features-title">A little more thought<br />behind every answer.</h2><p>Specialized support workflows help turn a customer question into a clear next step.</p></div>
          <div className="feature-list">
            <article><span className="feature-index">01</span><div><h3>Specialized agents</h3><p>Orders, refunds, and escalation workflows handle the support tasks they are designed for.</p></div><span className="feature-mark feature-loop" aria-hidden="true">↗</span></article>
            <article><span className="feature-index">02</span><div><h3>Context-aware help</h3><p>Conversation history and connected knowledge help keep answers relevant to the request.</p></div><span className="feature-mark feature-bracket" aria-hidden="true">{ }</span></article>
            <article><span className="feature-index">03</span><div><h3>Human follow-up</h3><p>Requests that need additional attention can be routed into the existing support ticket workflow.</p></div><span className="feature-mark feature-star" aria-hidden="true">✳</span></article>
          </div>
        </section>
        <div className="auth-bottom"><span>ResolveAI Support</span><span>Here when you need us.</span></div>
      </main>
    );
  }

  const navItems: { id: Section; label: string; icon: string }[] = [
    { id: 'dashboard', label: 'Overview', icon: 'grid' },
    { id: 'assistant', label: 'AI assistant', icon: 'sparkle' },
    { id: 'conversations', label: 'Conversations', icon: 'clock' },
    { id: 'tickets', label: 'Support tickets', icon: 'ticket' },
  ];
  const sectionTitle = section === 'dashboard' ? 'Overview' : section === 'assistant' ? 'AI assistant' : section === 'conversations' ? 'Conversations' : 'Support tickets';

  return (
    <main className={`app-shell theme-${theme}`}>
      {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-top">
          <a className="brand-lockup" href="#" aria-label="ResolveAI"><span className="brand-mark"><Icon name="sparkle" size={19} /></span>{!collapsed && <span>Resolve<span className="brand-accent">AI</span></span>}</a>
          <button className="icon-button collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}><Icon name="chevron" size={16} /></button>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><Icon name="close" /></button>
        </div>
        {!collapsed && <div className="workspace-label">INTELLIGENT SUPPORT</div>}
        <button className="new-conversation" onClick={beginNewChat} title="Start a new conversation"><Icon name="plus" size={17} />{!collapsed && <span>New conversation</span>}</button>
        <nav className="primary-nav" aria-label="Main navigation">
          {!collapsed && <span className="nav-caption">WORKSPACE</span>}
          {navItems.map((item) => <button key={item.id} className={`nav-item ${section === item.id ? 'active' : ''}`} onClick={() => selectSection(item.id)} title={collapsed ? item.label : undefined} aria-current={section === item.id ? 'page' : undefined}><Icon name={item.icon} size={18} /><span>{item.label}</span></button>)}
        </nav>
        {!collapsed && <div className="sidebar-capabilities"><span className="nav-caption">SUPPORT SPECIALTIES</span><div className="capability-line"><span className="capability-dot orders" />Orders</div><div className="capability-line"><span className="capability-dot refunds" />Refunds</div><div className="capability-line"><span className="capability-dot escalation" />Escalation</div></div>}
        <div className="sidebar-spacer" />
        <div className="account-block">
          <div className="user-avatar">{(account.name || account.email || 'U').slice(0, 1).toUpperCase()}</div>
          {!collapsed && <div className="account-copy"><strong>{account.name || account.email.split('@')[0] || 'Your account'}</strong><span>{account.email}</span></div>}
          <button className="icon-button logout-button" onClick={logout} aria-label="Sign out" title="Sign out"><Icon name="logout" size={17} /></button>
        </div>
        <button className="theme-row" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title="Toggle color theme"><Icon name={theme === 'dark' ? 'sun' : 'moon'} size={17} />{!collapsed && <><span>{theme === 'dark' ? 'Light appearance' : 'Dark appearance'}</span><span className={`theme-track ${theme}`}><i /></span></>}</button>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Icon name="menu" /></button>
          <div className="breadcrumb"><span>ResolveAI</span><Icon name="chevron" size={14} /><strong>{sectionTitle}</strong></div>
          <div className="topbar-right"><span className="service-status"><i className={serviceAvailable === false ? 'offline' : ''} />{serviceAvailable === null ? 'Checking service' : serviceAvailable ? 'Support online' : 'Service unavailable'}</span><span className="topbar-divider" /><span className="topbar-avatar">{(account.name || account.email || 'U').slice(0, 1).toUpperCase()}</span></div>
        </header>

        {section === 'dashboard' && <section className="content-area dashboard-view">
          <div className="page-heading"><div><p className="eyebrow">YOUR SUPPORT SPACE</p><h1>Support that thinks.<br />Resolution that works.</h1><p>Welcome back{account.name ? `, ${account.name.split(' ')[0]}` : ''}. Manage your support conversations from one place.</p></div><button className="primary-button" onClick={beginNewChat}>Launch assistant <Icon name="arrow" size={17} /></button></div>
          <div className="welcome-banner"><div className="banner-copy"><span className="banner-kicker"><Icon name="sparkle" size={15} /> HERE TO HELP</span><h2>Need assistance?</h2><p>Get help with orders, refunds, and delivery issues using your intelligent support assistant.</p><button className="banner-link" onClick={beginNewChat}>Ask ResolveAI <Icon name="arrow" size={16} /></button></div><div className="banner-art" aria-hidden="true"><div className="art-ring ring-one" /><div className="art-ring ring-two" /><div className="art-core"><Icon name="sparkle" size={28} /></div><span className="art-orbit orbit-a"><Icon name="box" size={17} /></span><span className="art-orbit orbit-b"><Icon name="message" size={17} /></span></div></div>
          <div className="section-heading"><div><h2>What can we help with?</h2><p>Choose a starting point for your support request.</p></div></div>
          <div className="suggestion-grid">{SUGGESTIONS.map((item) => <button className="suggestion-card" key={item.title} onClick={() => { beginNewChat(); setDraft(item.prompt); }}><span className="suggestion-icon"><Icon name={item.icon} size={19} /></span><span className="suggestion-title">{item.title}</span><span className="suggestion-detail">{item.detail}</span><span className="card-arrow"><Icon name="arrow" size={16} /></span></button>)}</div>
          <div className="section-heading recent-heading"><div><h2>Recent conversations</h2><p>Your latest support threads.</p></div><button className="text-button" onClick={() => selectSection('conversations')}>View all <Icon name="arrow" size={15} /></button></div>
          {conversationLoading ? <div className="conversation-list skeleton-list"><div /><div /><div /></div> : conversationError ? <div className="notice error-notice" role="alert">{conversationError}</div> : conversations.length ? <div className="conversation-list">{conversations.slice(0, 4).map((conversation) => <button className="conversation-row" key={conversation.id} onClick={() => void openConversation(conversation.id)}><span className="conversation-icon"><Icon name="message" size={17} /></span><span className="conversation-copy"><strong>{conversation.title || 'Support conversation'}</strong><span>Conversation · {formatDate(conversation.updated_at)}</span></span><Icon name="chevron" size={17} /></button>)}</div> : <div className="quiet-empty">No conversations yet. Start one whenever you need a hand.</div>}
          <div className="agent-note"><span className="agent-note-icon"><Icon name="sparkle" size={17} /></span><div><strong>Specialized support, one place</strong><p>ResolveAI can help with order questions, refund requests, and issues that need human follow-up.</p></div><span className="agent-pills"><i>Orders</i><i>Refunds</i><i>Escalation</i></span></div>
        </section>}

        {section === 'assistant' && <section className="chat-view">
          <div className="chat-heading"><div className="assistant-avatar"><Icon name="sparkle" size={19} /></div><div className="chat-title"><h1>{activeConversationId ? conversations.find((item) => item.id === activeConversationId)?.title || 'Support conversation' : 'AI Support Assistant'}</h1><p>Powered by intelligent multi-agent workflows</p></div><span className="ready-indicator"><i className={serviceAvailable === false ? 'offline' : ''} />{serviceAvailable === null ? 'Checking' : serviceAvailable ? 'Ready' : 'Offline'}</span><button className="new-chat-icon" onClick={startNewChat} title="New conversation" aria-label="New conversation"><Icon name="plus" /></button></div>
          <div className="chat-scroll" role="log" aria-live="polite" aria-label="Conversation messages">
            {conversationLoading && <div className="chat-loading"><span className="spinner" /> Loading conversation</div>}
            {!messages.length && !conversationLoading ? <div className="chat-welcome"><div className="welcome-sparkle"><Icon name="sparkle" size={24} /></div><p className="eyebrow">RESOLVEAI SUPPORT</p><h2>What&apos;s on your mind today?</h2><p className="welcome-description">Ask a question, describe an issue, or let the AI agents help you find a resolution.</p><div className="chat-doodle" aria-hidden="true"><svg viewBox="0 0 120 55"><path d="M5 36c32-20 63-24 100-7m-14-14 17 14-19 4" /></svg><span>start with a question</span></div><div className="chat-suggestions">{SUGGESTIONS.map((item) => <button key={item.title} onClick={() => setDraft(item.prompt)}><span><Icon name={item.icon} size={17} /></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><Icon name="arrow" size={15} /></button>)}</div></div> : <div className="message-stack">{messages.map((message, index) => <div className={`message-row ${message.role === 'user' ? 'from-user' : 'from-assistant'}`} key={message.id ?? `${index}-${message.role}`}><div className="message-avatar">{message.role === 'user' ? (account.name || account.email || 'U').slice(0, 1).toUpperCase() : <Icon name="sparkle" size={15} />}</div><div className="message-body"><span className="message-author">{message.role === 'user' ? 'You' : 'ResolveAI'}</span><div className="message-bubble">{message.content}</div></div></div>)}{isSending && <div className="message-row from-assistant"><div className="message-avatar"><Icon name="sparkle" size={15} /></div><div className="message-body"><span className="message-author">ResolveAI</span><div className="message-bubble typing-indicator" aria-label="Waiting for response"><i /><i /><i /></div></div></div>}<div ref={messageEndRef} /></div>}
          </div>
          <div className="composer-wrap"><div className="composer-box"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onComposerKeyDown} placeholder="Ask about an order, refund, or anything else..." rows={2} disabled={isSending} aria-label="Message to support assistant" /><button className="send-button" onClick={() => void sendMessage()} disabled={!draft.trim() || isSending} aria-label="Send message"><Icon name="send" size={18} /></button></div>{chatError && <div className="composer-error" role="alert">{chatError}</div>}<div className="composer-caption"><span><kbd>Enter</kbd> to send <span className="caption-dot">·</span> <kbd>Shift + Enter</kbd> for a new line</span><span>Responses may take a moment</span></div></div>
        </section>}

        {section === 'conversations' && <section className="content-area list-view"><div className="page-heading"><div><p className="eyebrow">YOUR SUPPORT HISTORY</p><h1>Conversations</h1><p>Pick up where you left off.</p></div><button className="primary-button" onClick={beginNewChat}>New conversation <Icon name="plus" size={17} /></button></div>{conversationLoading ? <div className="conversation-list skeleton-list"><div /><div /><div /><div /></div> : conversationError ? <div className="notice error-notice" role="alert">{conversationError}</div> : conversations.length ? <div className="conversation-list full-list">{conversations.map((conversation) => <button className="conversation-row" key={conversation.id} onClick={() => void openConversation(conversation.id)}><span className="conversation-icon"><Icon name="message" size={18} /></span><span className="conversation-copy"><strong>{conversation.title || 'Support conversation'}</strong><span>Conversation · Updated {formatDate(conversation.updated_at)}</span></span><span className="row-open">Open <Icon name="arrow" size={15} /></span></button>)}</div> : <div className="empty-panel"><span className="empty-icon"><Icon name="message" size={22} /></span><h2>Your conversations will appear here</h2><p>Start a conversation with the support assistant to get help.</p><button className="primary-button" onClick={beginNewChat}>Start a conversation <Icon name="arrow" size={16} /></button></div>}</section>}

        {section === 'tickets' && <section className="content-area list-view"><div className="page-heading"><div><p className="eyebrow">HUMAN FOLLOW-UP</p><h1>Support tickets</h1><p>Review support requests available to your account.</p></div></div>{ticketLoading ? <div className="ticket-skeleton"><div /><div /><div /></div> : ticketError ? <div className="restricted-panel"><span className="restricted-icon"><Icon name="lock" size={21} /></span><div><h2>Tickets aren’t available for this account</h2><p>{ticketError.includes('403') || ticketError.toLowerCase().includes('admin') ? 'Ticket listings are restricted to support administrators. You can still ask ResolveAI for help from the assistant.' : ticketError}</p><button className="text-button" onClick={beginNewChat}>Ask the assistant <Icon name="arrow" size={15} /></button></div></div> : tickets.length ? <div className="ticket-table-wrap"><table className="ticket-table"><thead><tr><th>Ticket</th><th>Issue</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead><tbody>{tickets.map((ticket) => <tr key={ticket.id}><td><strong className="ticket-id">{ticket.ticket_id}</strong></td><td className="ticket-issue">{ticket.issue}</td><td><span className={`priority-badge ${ticket.priority.toLowerCase()}`}>{ticket.priority}</span></td><td><span className={`status-badge ${ticket.status.toLowerCase().replaceAll(' ', '-')}`}><i />{ticket.status}</span></td><td className="ticket-date">{formatDate(ticket.created_at)}</td></tr>)}</tbody></table></div> : <div className="empty-panel"><span className="empty-icon"><Icon name="ticket" size={22} /></span><h2>No support tickets to show</h2><p>When support tickets are available to your account, they’ll appear here.</p><button className="primary-button" onClick={beginNewChat}>Get support <Icon name="arrow" size={16} /></button></div>}</section>}
      </div>
    </main>
  );
}

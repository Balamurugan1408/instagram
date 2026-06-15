import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Bell, Bookmark, Compass, Heart, Home, ImagePlus, LogOut, MessageCircle, Moon, Search, Sun, UserPlus } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";

function useAuth() {
  const [tokens, setTokens] = useState(() => JSON.parse(localStorage.getItem("tokens") || "null"));
  const [user, setUser] = useState(null);

  const client = useMemo(() => {
    async function request(path, options = {}) {
      const headers = { ...(options.headers || {}) };
      if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
      if (tokens?.access) headers.Authorization = `Bearer ${tokens.access}`;
      const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
      if (!res.ok) throw new Error(await res.text());
      return res.status === 204 ? null : res.json();
    }
    return { request };
  }, [tokens]);

  useEffect(() => {
    if (!tokens?.access) return;
    client.request("/me/").then(setUser).catch(() => logout());
  }, [tokens?.access]);

  async function login(username, password) {
    const nextTokens = await client.request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) });
    localStorage.setItem("tokens", JSON.stringify(nextTokens));
    setTokens(nextTokens);
  }

  async function register(username, email, password) {
    await client.request("/auth/register/", { method: "POST", body: JSON.stringify({ username, email, password }) });
    await login(username, password);
  }

  function logout() {
    localStorage.removeItem("tokens");
    setTokens(null);
    setUser(null);
  }

  return { user, tokens, client, login, register, logout };
}

function AuthScreen({ onLogin, onRegister }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "login") await onLogin(form.username, form.password);
      else await onRegister(form.username, form.email, form.password);
    } catch {
      setError("Check your details and try again.");
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <h1>Anstagram</h1>
        <p>Share moments, follow creators, and keep up with your circle.</p>
        <form onSubmit={submit}>
          <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          {mode === "register" && <input placeholder="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />}
          <input placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {error && <small className="error">{error}</small>}
          <button>{mode === "login" ? "Log in" : "Create account"}</button>
        </form>
        <button className="text-button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Need an account?" : "Already have an account?"}
        </button>
      </section>
    </main>
  );
}

function App() {
  const auth = useAuth();
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  if (!auth.tokens) return <AuthScreen onLogin={auth.login} onRegister={auth.register} />;

  return <Shell auth={auth} dark={dark} setDark={setDark} />;
}

function Shell({ auth, dark, setDark }) {
  const [view, setView] = useState("home");
  const [posts, setPosts] = useState([]);
  const [stories, setStories] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);

  async function loadFeed(endpoint = "/posts/feed/") {
    const data = await auth.client.request(endpoint);
    setPosts(data.results || data);
  }

  useEffect(() => {
    loadFeed();
    auth.client.request("/stories/").then((data) => setStories(data.results || data)).catch(() => {});
    auth.client.request("/notifications/").then((data) => setNotifications(data.results || data)).catch(() => {});
  }, []);

  async function search(event) {
    event.preventDefault();
    if (!query.trim()) return setSearchResults(null);
    setSearchResults(await auth.client.request(`/search/?q=${encodeURIComponent(query)}`));
    setView("search");
  }

  const nav = [
    ["home", Home],
    ["explore", Compass],
    ["create", ImagePlus],
    ["inbox", MessageCircle],
    ["profile", UserPlus],
  ];

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Anstagram</h1>
        {nav.map(([key, Icon]) => (
          <button className={view === key ? "active" : ""} key={key} onClick={() => {
            setView(key);
            if (key === "explore") loadFeed("/posts/explore/");
          }}>
            <Icon size={20} /> <span>{key}</span>
          </button>
        ))}
        <button onClick={() => setDark(!dark)}>{dark ? <Sun size={20} /> : <Moon size={20} />} <span>theme</span></button>
        <button onClick={auth.logout}><LogOut size={20} /> <span>logout</span></button>
      </aside>

      <main className="content">
        <header className="topbar">
          <form className="search" onSubmit={search}>
            <Search size={18} />
            <input placeholder="Search users, posts, hashtags" value={query} onChange={(e) => setQuery(e.target.value)} />
          </form>
          <button className="icon-button" onClick={() => setView("notifications")}><Bell size={20} /><span>{notifications.filter((n) => !n.is_read).length}</span></button>
        </header>

        {view === "home" && <Feed posts={posts} stories={stories} client={auth.client} reload={loadFeed} />}
        {view === "explore" && <Feed posts={posts} stories={[]} client={auth.client} reload={() => loadFeed("/posts/explore/")} />}
        {view === "create" && <CreatePost client={auth.client} onCreated={() => { setView("home"); loadFeed(); }} />}
        {view === "profile" && <Profile user={auth.user} />}
        {view === "notifications" && <Notifications items={notifications} />}
        {view === "search" && <SearchResults results={searchResults} />}
        {view === "inbox" && <Inbox client={auth.client} />}
      </main>
    </div>
  );
}

function Stories({ stories }) {
  return (
    <section className="stories">
      {stories.map((story) => (
        <article key={story.id}>
          <img src={story.media} alt="" />
          <span>{story.author.username}</span>
        </article>
      ))}
    </section>
  );
}

function Feed({ posts, stories, client, reload }) {
  async function action(post, name) {
    await client.request(`/posts/${post.id}/${name}/`, { method: "POST" });
    await reload();
  }

  return (
    <>
      {stories.length > 0 && <Stories stories={stories} />}
      <section className="feed">
        {posts.map((post) => <PostCard key={post.id} post={post} action={action} client={client} reload={reload} />)}
      </section>
    </>
  );
}

function PostCard({ post, action, client, reload }) {
  const [comment, setComment] = useState("");

  async function addComment(event) {
    event.preventDefault();
    if (!comment.trim()) return;
    await client.request(`/posts/${post.id}/comments/`, { method: "POST", body: JSON.stringify({ text: comment }) });
    setComment("");
    await reload();
  }

  return (
    <article className="post-card">
      <header>
        <img className="avatar" src={post.author.profile?.avatar || `https://api.dicebear.com/8.x/initials/svg?seed=${post.author.username}`} alt="" />
        <div><strong>{post.author.username}</strong><span>{post.location}</span></div>
      </header>
      <img className="post-image" src={post.image} alt={post.caption} />
      <div className="actions">
        <button onClick={() => action(post, post.is_liked ? "unlike" : "like")}><Heart fill={post.is_liked ? "currentColor" : "none"} /></button>
        <button><MessageCircle /></button>
        <button onClick={() => action(post, "share")}>Share</button>
        <button onClick={() => action(post, post.is_saved ? "unsave" : "save")}><Bookmark fill={post.is_saved ? "currentColor" : "none"} /></button>
      </div>
      <p><strong>{post.likes_count}</strong> likes</p>
      <p><strong>{post.author.username}</strong> {post.caption}</p>
      <div className="comments">
        {post.comments.slice(-3).map((item) => <p key={item.id}><strong>{item.author.username}</strong> {item.text}</p>)}
      </div>
      <form className="comment-form" onSubmit={addComment}>
        <input placeholder="Add a comment" value={comment} onChange={(e) => setComment(e.target.value)} />
        <button>Post</button>
      </form>
    </article>
  );
}

function CreatePost({ client, onCreated }) {
  const [caption, setCaption] = useState("");
  const [location, setLocation] = useState("");
  const [image, setImage] = useState(null);

  async function submit(event) {
    event.preventDefault();
    const data = new FormData();
    data.append("caption", caption);
    data.append("location", location);
    data.append("image", image);
    await client.request("/posts/", { method: "POST", body: data });
    onCreated();
  }

  return (
    <section className="composer">
      <h2>Create post</h2>
      <form onSubmit={submit}>
        <input type="file" accept="image/*" onChange={(e) => setImage(e.target.files[0])} required />
        <input placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
        <textarea placeholder="Caption with #hashtags" value={caption} onChange={(e) => setCaption(e.target.value)} />
        <button>Publish</button>
      </form>
    </section>
  );
}

function Profile({ user }) {
  return (
    <section className="profile">
      <img className="profile-avatar" src={user?.profile?.avatar || `https://api.dicebear.com/8.x/initials/svg?seed=${user?.username}`} alt="" />
      <div>
        <h2>{user?.username}</h2>
        <p>{user?.profile?.bio || "No bio yet."}</p>
        <div className="stats">
          <span>{user?.profile?.posts_count || 0} posts</span>
          <span>{user?.profile?.followers_count || 0} followers</span>
          <span>{user?.profile?.following_count || 0} following</span>
        </div>
      </div>
    </section>
  );
}

function Notifications({ items }) {
  return (
    <section className="panel-list">
      <h2>Notifications</h2>
      {items.map((item) => <article key={item.id}>{item.actor.username} {item.verb} {item.post ? "your post" : "you"}</article>)}
    </section>
  );
}

function SearchResults({ results }) {
  return (
    <section className="panel-list">
      <h2>Search</h2>
      {results?.users?.map((user) => <article key={user.id}>{user.username}</article>)}
      {results?.posts?.map((post) => <article key={post.id}>{post.caption}</article>)}
    </section>
  );
}

function Inbox() {
  return (
    <section className="panel-list">
      <h2>Messages</h2>
      <article>Start a conversation through the conversations API.</article>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);

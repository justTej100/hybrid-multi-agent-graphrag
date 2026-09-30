import { NavLink, useLocation } from 'react-router-dom';
import { MeProvider, useMe } from '../me';

function NavBar() {
  const me = useMe();
  const path = useLocation().pathname;
  const searchActive = path === '/' || path === '/study';

  return (
    <nav className="nav">
      <span className="nav-brand">ARGUS</span>
      <div className="nav-links">
        <NavLink to="/" end className={searchActive ? 'active' : ''}>
          Search
        </NavLink>
        <NavLink to="/library" className={({ isActive }) => (isActive ? 'active' : '')}>
          Library
        </NavLink>
        <NavLink to="/quiz" className={({ isActive }) => (isActive ? 'active' : '')}>
          Quiz
        </NavLink>
        <NavLink to="/flashcards" className={({ isActive }) => (isActive ? 'active' : '')}>
          Flashcards
        </NavLink>
        <NavLink to="/graph" className={({ isActive }) => (isActive ? 'active' : '')}>
          Graph
        </NavLink>
        {me?.is_admin && (
          <NavLink to="/admin" className={({ isActive }) => (isActive ? 'active' : '')}>
            Database
          </NavLink>
        )}
        {me && (
          <span className="nav-user" title={me.email}>
            {me.is_admin ? me.email : 'Guest (rate limited)'}
          </span>
        )}
        <a href="/logout">Logout</a>
      </div>
    </nav>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <MeProvider>
      <div className="app-shell">
        <NavBar />
        <main className="main">{children}</main>
      </div>
    </MeProvider>
  );
}

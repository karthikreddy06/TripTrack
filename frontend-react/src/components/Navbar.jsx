import { useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import {
  Compass,
  Heart,
  Sparkles,
  Luggage,
  Home,
  Plus,
  LogOut,
  Menu,
  X,
  ArrowUpRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Navbar = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    if (!name) return 'TR';
    return name
      .split(' ')
      .filter(Boolean)
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <nav className="navbar">
      <div className="nav-content">
        <Link to="/" className="brand-logo">
          <span className="brand-dot" />
          <span>TravelTrack</span>
          <span className="brand-sub"> / explore</span>
        </Link>

        {isAuthenticated && (
          <div className={`nav-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Home size={14} className="nav-icon" />
              <span>Home</span>
            </NavLink>

            <NavLink
              to="/explore"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Compass size={14} className="nav-icon" />
              <span>Explore</span>
            </NavLink>

            <NavLink
              to="/trips"
              end
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Luggage size={14} className="nav-icon" />
              <span>Trips</span>
            </NavLink>

            <NavLink
              to="/wishlist"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Heart size={14} className="nav-icon" />
              <span>Wishlist</span>
            </NavLink>

            <NavLink
              to="/ai-planner"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Sparkles size={14} className="nav-icon" />
              <span>AI Assistant</span>
            </NavLink>

            <NavLink
              to="/profile"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} mobile-only-link`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Profile Settings
            </NavLink>
          </div>
        )}

        <div className="nav-user">
          {isAuthenticated ? (
            <>
              <Link
                to="/trips/new"
                className="btn btn-primary btn-sm desktop-create-btn"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', padding: '0.35rem 0.75rem' }}
              >
                <Plus size={13} />
                <span>New Trip</span>
              </Link>

              <Link
                to="/profile"
                className="user-pill"
                title={`Logged in as ${user?.email} • View Profile`}
              >
                <div className="user-avatar">
                  {getInitials(user?.name)}
                </div>
                <span>{user?.name ? user.name.split(' ')[0] : 'Traveler'}</span>
              </Link>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleLogout}
                title="Log out of TravelTrack"
              >
                <LogOut size={13} />
                <span>Logout</span>
              </button>

              <button
                type="button"
                className="mobile-menu-btn"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-label="Toggle navigation"
              >
                {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
            </>
          ) : (
            <div style={{ display: 'flex', gap: '0.6rem' }}>
              <Link to="/explore" className="btn btn-secondary btn-sm">
                <Compass size={13} />
                <span>Explore</span>
              </Link>
              <Link to="/login" className="btn btn-secondary btn-sm">
                Sign In
              </Link>
              <Link to="/register" className="btn btn-primary btn-sm">
                <span>Register</span>
                <ArrowUpRight size={13} />
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

import { useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { LogOut, Menu, X, ArrowUpRight } from 'lucide-react';
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
    if (!name) return 'KR';
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
          <span className="brand-sub"> / trips</span>
        </Link>

        {isAuthenticated && (
          <div className={`nav-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Dashboard
            </NavLink>

            <NavLink
              to="/trips"
              end
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              My Trips
            </NavLink>

            <NavLink
              to="/trips/new"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Create Trip
            </NavLink>
          </div>
        )}

        <div className="nav-user">
          {isAuthenticated ? (
            <>
              <div className="user-pill" title={`Logged in as ${user?.email}`}>
                <div className="user-avatar">
                  {getInitials(user?.name)}
                </div>
                <span>{user?.name || 'Traveler'}</span>
              </div>

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

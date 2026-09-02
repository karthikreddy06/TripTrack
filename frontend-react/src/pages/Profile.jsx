import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Mail,
  ArrowLeft,
  CheckCircle2,
  Save,
  Shield
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { profileAPI, tripsAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

const PREFERENCE_OPTIONS = [
  'Solo Exploration',
  'Cultural Heritage',
  'Culinary Tourism',
  'Outdoor Adventure',
  'Coastal / Beaches',
  'Photography',
  'Luxury Travel',
  'Budget Backpacking',
  'Eco-Tourism'
];

export const Profile = () => {
  const { user, updateUser } = useAuth();
  const { showSuccess, showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState({
    name: '',
    email: '',
    bio: '',
    travel_preferences: [],
    home_currency: 'USD',
  });
  const [tripsCount, setTripsCount] = useState(0);
  const [totalBudget, setTotalBudget] = useState(0);

  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState(null);

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState(null);

  useEffect(() => {
    const loadProfileAndStats = async () => {
      try {
        setLoading(true);
        const [profile, trips] = await Promise.all([
          profileAPI.getProfile(),
          tripsAPI.getTrips(user?.user_id),
        ]);

        setProfileData({
          name: profile.name || '',
          email: profile.email || '',
          bio: profile.bio || '',
          travel_preferences: profile.travel_preferences || [],
          home_currency: profile.home_currency || 'USD',
        });

        const tripList = Array.isArray(trips) ? trips : [];
        setTripsCount(tripList.length);
        const budgetSum = tripList.reduce((sum, t) => sum + (parseFloat(t.budget) || 0), 0);
        setTotalBudget(budgetSum);
      } catch (err) {
        setProfileError(extractErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    if (user?.user_id) {
      loadProfileAndStats();
    }
  }, [user?.user_id]);

  const togglePreference = (pref) => {
    setProfileData((prev) => {
      const exists = prev.travel_preferences.includes(pref);
      if (exists) {
        return { ...prev, travel_preferences: prev.travel_preferences.filter((p) => p !== pref) };
      }
      return { ...prev, travel_preferences: [...prev.travel_preferences, pref] };
    });
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    if (!profileData.name.trim()) {
      setProfileError('Full name cannot be empty.');
      return;
    }

    try {
      setSavingProfile(true);
      setProfileError(null);
      await profileAPI.updateProfile({
        name: profileData.name.trim(),
        bio: profileData.bio.trim(),
        travel_preferences: profileData.travel_preferences,
        home_currency: profileData.home_currency,
      });

      updateUser({ name: profileData.name.trim() });
      showSuccess('Profile information updated successfully!');
    } catch (err) {
      setProfileError(extractErrorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError(null);

    if (!passwordForm.current_password) {
      setPasswordError('Please enter your current password.');
      return;
    }

    if (passwordForm.new_password.length < 6) {
      setPasswordError('New password must be at least 6 characters long.');
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('New passwords do not match.');
      return;
    }

    try {
      setSavingPassword(true);
      await profileAPI.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });

      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      showSuccess('Password changed securely!');
    } catch (err) {
      setPasswordError(extractErrorMessage(err));
    } finally {
      setSavingPassword(false);
    }
  };

  const formatCurrency = (val) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);

  if (loading) {
    return (
      <div className="main-content">
        <div className="loading-container">
          <div className="spinner spinner-lg" />
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="main-content">
      <Link
        to="/dashboard"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          marginBottom: '1.5rem',
          color: 'var(--text-secondary)',
          fontWeight: 500,
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        <ArrowLeft size={14} />
        <span>Back to dashboard</span>
      </Link>

      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 06 / USER PROFILE
          </div>
          <h1>Profile & Preferences</h1>
          <p className="welcome-subtitle">
            Manage your traveler profile, default preferences, and account security.
          </p>
        </div>
      </div>

      {/* Profile Overview Card */}
      <div className="profile-overview-card card" style={{ marginBottom: '2.5rem' }}>
        <div className="profile-hero-left">
          <div className="profile-avatar-large">
            {profileData.name ? profileData.name.slice(0, 2).toUpperCase() : 'TT'}
          </div>
          <div>
            <h2 style={{ fontSize: '1.85rem', marginBottom: '0.2rem' }}>{profileData.name}</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Mail size={13} />
              <span>{profileData.email}</span>
            </p>
          </div>
        </div>

        <div className="profile-hero-stats">
          <div className="profile-stat-box">
            <span className="p-stat-num">{tripsCount}</span>
            <span className="p-stat-label">TOTAL TRIPS</span>
          </div>
          <div className="profile-stat-box">
            <span className="p-stat-num">{formatCurrency(totalBudget)}</span>
            <span className="p-stat-label">TOTAL BUDGET</span>
          </div>
        </div>
      </div>

      <div className="form-grid-two">
        {/* Left: Profile Info Form */}
        <div className="card">
          <div className="form-header" style={{ marginBottom: '1.5rem' }}>
            <div className="editorial-mark"><i></i> PERSONAL INFO</div>
            <h3 style={{ fontSize: '1.4rem' }}>Edit Details</h3>
          </div>

          {profileError && <Alert type="error" message={profileError} onClose={() => setProfileError(null)} />}

          <form onSubmit={handleUpdateProfile}>
            <div className="form-group">
              <label className="form-label" htmlFor="prof-name">
                FULL NAME <span style={{ color: 'var(--accent)' }}>*</span>
              </label>
              <input
                id="prof-name"
                type="text"
                className="form-input"
                value={profileData.name}
                onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="prof-email">
                EMAIL ADDRESS (READ-ONLY)
              </label>
              <input
                id="prof-email"
                type="email"
                className="form-input"
                value={profileData.email}
                disabled
                style={{ opacity: 0.7, cursor: 'not-allowed' }}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="prof-bio">
                TRAVEL BIO
              </label>
              <textarea
                id="prof-bio"
                className="form-input"
                rows={3}
                placeholder="Passionate globe-trotter exploring heritage trails and coffee capitals..."
                value={profileData.bio}
                onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">TRAVEL PREFERENCES</label>
              <div className="interest-tags-container">
                {PREFERENCE_OPTIONS.map((pref) => {
                  const isSelected = profileData.travel_preferences.includes(pref);
                  return (
                    <button
                      key={pref}
                      type="button"
                      className={`interest-tag-btn ${isSelected ? 'selected' : ''}`}
                      onClick={() => togglePreference(pref)}
                    >
                      {isSelected && <CheckCircle2 size={12} />}
                      <span>{pref}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem' }}
              disabled={savingProfile}
            >
              {savingProfile ? (
                <>
                  <span className="spinner" />
                  <span>Saving Changes...</span>
                </>
              ) : (
                <>
                  <Save size={14} />
                  <span>Save Profile</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right: Security Form */}
        <div className="card">
          <div className="form-header" style={{ marginBottom: '1.5rem' }}>
            <div className="editorial-mark"><i></i> SECURITY</div>
            <h3 style={{ fontSize: '1.4rem' }}>Change Password</h3>
          </div>

          {passwordError && <Alert type="error" message={passwordError} onClose={() => setPasswordError(null)} />}

          <form onSubmit={handleChangePassword}>
            <div className="form-group">
              <label className="form-label" htmlFor="curr-pass">
                CURRENT PASSWORD <span style={{ color: 'var(--accent)' }}>*</span>
              </label>
              <input
                id="curr-pass"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                required
                autoComplete="current-password"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="new-pass">
                NEW PASSWORD <span style={{ color: 'var(--text-muted)' }}>(min. 6 chars)</span>
              </label>
              <input
                id="new-pass"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                required
                autoComplete="new-password"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="conf-pass">
                CONFIRM NEW PASSWORD
              </label>
              <input
                id="conf-pass"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                required
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: '1.75rem' }}
              disabled={savingPassword}
            >
              {savingPassword ? (
                <>
                  <span className="spinner" />
                  <span>Updating Password...</span>
                </>
              ) : (
                <>
                  <Shield size={14} />
                  <span>Update Password</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

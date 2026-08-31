import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';

export const Register = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const { register, login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!formData.name.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (!formData.email.trim()) {
      setError('Please enter a valid email address.');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      await register({
        name: formData.name,
        email: formData.email,
        password: formData.password,
      });

      setSuccess('Account created successfully. Initializing workspace...');

      // Auto login after registration
      await login({
        email: formData.email,
        password: formData.password,
      });

      navigate('/dashboard');
    } catch (err) {
      setError(extractErrorMessage(err));
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-editorial-container">
        {/* Left Botanical Intro */}
        <div className="auth-editorial-intro">
          <div className="editorial-mark">
            <i></i> TRAVELTRACK
          </div>
          <h1>
            Begin your <br />
            <em>next journey.</em>
          </h1>
          <p>
            Create an account to start planning journeys, managing budgets, and keeping
            itineraries aligned in a calm, natural space.
          </p>
        </div>

        {/* Right Registration Card */}
        <div className="auth-card-wrapper">
          <div className="auth-card">
            <div className="auth-header">
              <div className="editorial-mark">
                <i></i> NEW ACCOUNT
              </div>
              <h2>Create Account</h2>
              <p>Enter your details to get started.</p>
            </div>

            {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
            {success && <Alert type="success" message={success} />}

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label" htmlFor="register-name">
                  Full Name
                </label>
                <input
                  id="register-name"
                  type="text"
                  name="name"
                  className="form-input"
                  placeholder="Karthik Reddy"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  autoComplete="name"
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="register-email">
                  Email Address
                </label>
                <input
                  id="register-email"
                  type="email"
                  name="email"
                  className="form-input"
                  placeholder="karthik@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  autoComplete="email"
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="register-password">
                  Password <span style={{ color: 'var(--text-muted)', textTransform: 'none' }}>(min. 6 chars)</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    id="register-password"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    className="form-input"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="input-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="register-confirm">
                  Confirm Password
                </label>
                <input
                  id="register-confirm"
                  type={showPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  className="form-input"
                  placeholder="••••••••"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '0.85rem' }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <>
                    <span>Create account</span>
                    <ArrowUpRight size={15} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer">
              Already have an account?{' '}
              <Link to="/login" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

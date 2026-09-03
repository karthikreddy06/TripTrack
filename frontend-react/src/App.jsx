import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { MyTrips } from './pages/MyTrips';
import { TripDetail } from './pages/TripDetail';
import { CreateTrip } from './pages/CreateTrip';
import { EditTrip } from './pages/EditTrip';
import { AIPlanner } from './pages/AIPlanner';
import { Profile } from './pages/Profile';
import { Explore } from './pages/Explore';
import { DestinationDetail } from './pages/DestinationDetail';
import { PlaceDetail } from './pages/PlaceDetail';
import { Wishlist } from './pages/Wishlist';
import { NotFound } from './pages/NotFound';
import { AIAssistantDrawer } from './components/AIAssistantDrawer';
import './styles/components.css';

// Public route helper that redirects authenticated users to dashboard
const PublicOnlyRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Root landing helper: sends authenticated users to /dashboard and guests to /explore
const RootRoute = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/explore" replace />;
};

export default function App() {
  return (
    <ToastProvider>
      <div className="app-container">
        <Navbar />
        <Routes>
          {/* Root dynamic redirect */}
          <Route path="/" element={<RootRoute />} />

          {/* Public auth routes */}
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <Login />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicOnlyRoute>
                <Register />
              </PublicOnlyRoute>
            }
          />

          {/* Explore routes (Accessible to both authenticated and browsing guests) */}
          <Route path="/explore" element={<Explore />} />
          <Route path="/explore/:destination" element={<DestinationDetail />} />
          <Route path="/explore/place/:placeId" element={<PlaceDetail />} />

          {/* Protected app routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips"
            element={
              <ProtectedRoute>
                <MyTrips />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips/new"
            element={
              <ProtectedRoute>
                <CreateTrip />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips/create"
            element={
              <ProtectedRoute>
                <CreateTrip />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips/:id"
            element={
              <ProtectedRoute>
                <TripDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trips/:id/edit"
            element={
              <ProtectedRoute>
                <EditTrip />
              </ProtectedRoute>
            }
          />
          <Route
            path="/wishlist"
            element={
              <ProtectedRoute>
                <Wishlist />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ai-planner"
            element={
              <ProtectedRoute>
                <AIPlanner />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />

          {/* 404 Catch-all */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <AIAssistantDrawer />
      </div>
    </ToastProvider>
  );
}

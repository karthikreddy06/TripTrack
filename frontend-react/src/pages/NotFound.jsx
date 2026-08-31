import { Link } from 'react-router-dom';
import { Compass, ArrowLeft } from 'lucide-react';

export const NotFound = () => {
  return (
    <div className="main-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '55vh' }}>
      <div className="empty-state" style={{ maxWidth: '480px' }}>
        <div className="empty-icon-wrapper">
          <Compass size={24} />
        </div>
        <div className="editorial-mark" style={{ justifyContent: 'center' }}>
          <i></i> 404 NOT FOUND
        </div>
        <h1 style={{ fontSize: '2.25rem', marginBottom: '0.65rem' }}>
          Page not found.
        </h1>
        <p className="empty-desc">
          The destination or itinerary you requested does not exist or has been relocated.
        </p>
        <Link to="/dashboard" className="btn btn-primary">
          <ArrowLeft size={14} />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    </div>
  );
};

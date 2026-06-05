import { useNavigate } from 'react-router-dom';
import { logout } from '../services/auth';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { ROLE_DEFAULT_ROUTES } from '../types';

export default function Unauthorized() {
  const navigate = useNavigate();
  const user = useCurrentUser();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="text-center max-w-sm">
        <div className="text-6xl mb-4">🚫</div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Access denied</h1>
        <p className="text-gray-500 mb-8 text-sm">
          You don't have permission to view this page.
          {user && (
            <span> You're signed in as <strong>{user.role.replace('_', ' ')}</strong>.</span>
          )}
        </p>
        <div className="flex flex-col gap-3">
          {user && (
            <button
              onClick={() => navigate(ROLE_DEFAULT_ROUTES[user.role], { replace: true })}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm
                         font-medium rounded-lg transition-colors"
            >
              Go to my dashboard
            </button>
          )}
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-gray-500 hover:text-gray-700 text-sm transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

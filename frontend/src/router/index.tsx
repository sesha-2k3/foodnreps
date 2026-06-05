/**
 * Application router — all route definitions.
 *
 * Route structure mirrors architecture amendment A6 exactly.
 * Every protected route is wrapped in the appropriate guard at definition
 * time — there is no runtime role-checking inside page components.
 *
 * Design choice — createBrowserRouter + RouterProvider (not BrowserRouter):
 *   The data router API (createBrowserRouter) enables route-level loaders
 *   and error boundaries, which will be used in Sprint 7+ for pre-fetching
 *   plan data. Starting with it now avoids a migration later.
 *   BrowserRouter is simpler but cannot be incrementally upgraded.
 *
 * Design choice — stub imports for Sprint 6+ pages:
 *   All feature pages are imported as stub components in Sprint 5.
 *   They are replaced in Sprints 7–9 without any change to this file.
 *   The router is the stable scaffold; the pages are the variable parts.
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RequireAuth, RequireRole } from './guards';

// ── Public pages ──────────────────────────────────────────────────────────────
import Login from '../pages/Login';
import Unauthorized from '../pages/Unauthorized';
import Dashboard from '../pages/Dashboard';

// ── Client pages ──────────────────────────────────────────────────────────────
import ClientDashboard from '../pages/client/ClientDashboard';
import ClientWorkoutView from '../pages/client/WorkoutView';
import ClientDietView from '../pages/client/DietView';

// ── Trainer pages ─────────────────────────────────────────────────────────────
import TrainerClientList from '../pages/trainer/ClientList';
import TrainerClientWorkout from '../pages/trainer/ClientWorkout';

// ── Nutritionist pages ────────────────────────────────────────────────────────
import NutritionistClientList from '../pages/nutritionist/ClientList';
import NutritionistClientDiet from '../pages/nutritionist/ClientDiet';

// ── Coach pages ───────────────────────────────────────────────────────────────
import CoachClientList from '../pages/coach/ClientList';
import CoachClientWorkout from '../pages/coach/ClientWorkout';
import CoachClientDiet from '../pages/coach/ClientDiet';

// ── Admin pages ───────────────────────────────────────────────────────────────
import AdminUserList from '../pages/admin/UserList';
import AdminUserDetail from '../pages/admin/UserDetail';

// ── Personal plan pages ───────────────────────────────────────────────────────
import PersonalWorkout from '../pages/personal/PersonalWorkout';
import PersonalDiet from '../pages/personal/PersonalDiet';

export const router = createBrowserRouter([
  // ── Public ──────────────────────────────────────────────────────────────────
  { path: '/login',        element: <Login /> },
  { path: '/unauthorized', element: <Unauthorized /> },

  // Root → Dashboard (role-based redirect)
  {
    path: '/',
    element: <RequireAuth><Dashboard /></RequireAuth>,
  },

  // ── Client ───────────────────────────────────────────────────────────────────
  {
    path: '/client/dashboard',
    element: <RequireRole roles={['client']}><ClientDashboard /></RequireRole>,
  },
  {
    path: '/client/workout',
    element: <RequireRole roles={['client']}><ClientWorkoutView /></RequireRole>,
  },
  {
    path: '/client/diet',
    element: <RequireRole roles={['client']}><ClientDietView /></RequireRole>,
  },

  // ── Trainer ──────────────────────────────────────────────────────────────────
  {
    path: '/trainer/clients',
    element: <RequireRole roles={['fitness_trainer']}><TrainerClientList /></RequireRole>,
  },
  {
    path: '/trainer/clients/:clientId/workout',
    element: <RequireRole roles={['fitness_trainer']}><TrainerClientWorkout /></RequireRole>,
  },

  // ── Nutritionist ─────────────────────────────────────────────────────────────
  {
    path: '/nutritionist/clients',
    element: <RequireRole roles={['nutritionist']}><NutritionistClientList /></RequireRole>,
  },
  {
    path: '/nutritionist/clients/:clientId/diet',
    element: <RequireRole roles={['nutritionist']}><NutritionistClientDiet /></RequireRole>,
  },

  // ── Master Coach ─────────────────────────────────────────────────────────────
  {
    path: '/coach/clients',
    element: <RequireRole roles={['master_coach']}><CoachClientList /></RequireRole>,
  },
  {
    path: '/coach/clients/:clientId/workout',
    element: <RequireRole roles={['master_coach']}><CoachClientWorkout /></RequireRole>,
  },
  {
    path: '/coach/clients/:clientId/diet',
    element: <RequireRole roles={['master_coach']}><CoachClientDiet /></RequireRole>,
  },

  // ── Personal plans (any authenticated role) ───────────────────────────────────
  {
    path: '/personal/workout',
    element: <RequireAuth><PersonalWorkout /></RequireAuth>,
  },
  {
    path: '/personal/diet',
    element: <RequireAuth><PersonalDiet /></RequireAuth>,
  },

  // ── Super Admin ───────────────────────────────────────────────────────────────
  {
    path: '/admin/users',
    element: <RequireRole roles={['super_admin']}><AdminUserList /></RequireRole>,
  },
  {
    path: '/admin/users/:userId',
    element: <RequireRole roles={['super_admin']}><AdminUserDetail /></RequireRole>,
  },

  // ── Catch-all ─────────────────────────────────────────────────────────────────
  { path: '*', element: <Navigate to="/" replace /> },
]);

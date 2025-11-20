import { createBrowserRouter, Navigate } from "react-router-dom";
import SignIn from "./pages/SignIn";
import SchedulesList from "./pages/SchedulesList";
import ScheduleForm from "./pages/schedules/ScheduleForm";
import Runs from "./pages/Runs";
import Settings from "./pages/Settings";
import SimulationLab from "./pages/SimulationLab";
import AdvancedSimulation from "./pages/AdvancedSimulation";
import { useAuth } from "./contexts/AuthContext";
import Navbar from "./components/Navbar";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8">Loading…</div>;
  if (!user) return <Navigate to="/signin" replace />;
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="p-4 max-w-5xl mx-auto w-full">{children}</main>
    </div>
  );
}

function Public({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="p-4 max-w-5xl mx-auto w-full">{children}</main>
    </div>
  );
}

export const router = createBrowserRouter(
  [
    { path: "/", element: <Navigate to="/schedules" replace /> },
    { path: "/signin", element: <SignIn /> },
    {
      path: "/demo",
      element: (
        <Public>
          <SimulationLab />
        </Public>
      ),
    },
    {
      path: "/schedules",
      element: (
        <Protected>
          <SchedulesList />
        </Protected>
      ),
    },
    {
      path: "/schedules/:id",
      element: (
        <Protected>
          <ScheduleForm />
        </Protected>
      ),
    },
    {
      path: "/runs/:scheduleId",
      element: (
        <Protected>
          <Runs />
        </Protected>
      ),
    },
    {
      path: "/settings",
      element: (
        <Protected>
          <Settings />
        </Protected>
      ),
    },
    {
      path: "/simulation",
      element: (
        <Protected>
          <AdvancedSimulation />
        </Protected>
      ),
    },
  ],
  {
    future: {
      v7_startTransition: true,
    },
  }
);

import { Link, NavLink, useNavigate } from "react-router-dom";
import { signOutUser } from "../lib/auth";
import { useAuth } from "../contexts/AuthContext";

export default function Navbar() {
  const nav = useNavigate();
  const { user } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-2">
        <Link to={user ? "/schedules" : "/demo"} className="text-base font-semibold">
          iflow-robot
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <NavLink
            to="/demo"
            className={({ isActive }) =>
              isActive ? "text-brand-600" : "text-gray-600"
            }
          >
            Demo
          </NavLink>
          {user && (
            <>
              <NavLink
                to="/schedules"
                className={({ isActive }) =>
                  isActive ? "text-brand-600" : "text-gray-600"
                }
              >
                Schedules
              </NavLink>
              <NavLink
                to="/simulation"
                className={({ isActive }) =>
                  isActive ? "text-brand-600" : "text-gray-600"
                }
              >
                Advanced Simulation
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) =>
                  isActive ? "text-brand-600" : "text-gray-600"
                }
              >
                Settings
              </NavLink>
              <button
                className="text-gray-600"
                onClick={async () => {
                  await signOutUser();
                  nav("/signin");
                }}
              >
                Sign out
              </button>
            </>
          )}
          {!user && (
            <NavLink
              to="/signin"
              className={({ isActive }) =>
                isActive ? "text-brand-600" : "text-gray-600"
              }
            >
              Sign in
            </NavLink>
          )}
        </nav>
      </div>
    </header>
  );
}

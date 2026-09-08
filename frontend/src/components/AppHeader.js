import { Link, useLocation, useNavigate } from "react-router-dom";
import { SignOut, User as UserIcon } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export default function AppHeader({ variant = "marketing" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthedPage = variant === "console";

  return (
    <header
      data-testid="app-header"
      className="sticky top-0 z-40 border-b border-[var(--tinted-grey-200)] bg-white/70 backdrop-blur-xl backdrop-saturate-150"
    >
      <div className="max-w-[1400px] mx-auto flex items-center justify-between px-6 lg:px-10 h-16">
        <Link to="/" className="flex items-center gap-2" data-testid="brand-link">
          <div className="h-7 w-7 bg-[var(--klein)] flex items-center justify-center rounded-[3px]">
            <span className="font-heading text-white font-black text-sm leading-none">S</span>
          </div>
          <span className="font-heading font-black tracking-tight text-lg">School OS</span>
          {isAuthedPage && user && (
            <span className="ml-3 overline hidden md:inline">
              {user.role === "platform_superadmin" ? "Platform Console" : "School Console"}
            </span>
          )}
        </Link>

        <nav className="hidden md:flex items-center gap-8 font-body text-sm">
          {variant === "marketing" && (
            <>
              <a href="#front-porch" className="klein-underline" data-testid="nav-front-porch">Front Porch</a>
              <a href="#main-house" className="klein-underline" data-testid="nav-main-house">Main House</a>
              <a href="#architecture" className="klein-underline" data-testid="nav-architecture">Architecture</a>
            </>
          )}
          {variant === "console" && user && (
            <div className="flex items-center gap-2 text-[var(--tinted-grey-500)]">
              <UserIcon size={16} weight="duotone" />
              <span data-testid="header-user-email" className="font-mono text-xs">{user.email}</span>
              <span className="px-2 py-0.5 bg-[var(--tinted-grey-100)] rounded text-[10px] font-semibold uppercase tracking-wider" data-testid="header-user-role">
                {user.role.replace(/_/g, " ")}
              </span>
            </div>
          )}
        </nav>

        <div className="flex items-center gap-3">
          {user && user !== false ? (
            <Button
              data-testid="header-logout-btn"
              variant="ghost"
              onClick={async () => { await logout(); navigate("/"); }}
              className="rounded-full"
            >
              <SignOut size={16} className="mr-2" /> Sign out
            </Button>
          ) : (
            <>
              {location.pathname !== "/login" && (
                <Link to="/login">
                  <Button variant="ghost" className="rounded-full" data-testid="header-login-btn">Sign in</Button>
                </Link>
              )}
              {location.pathname !== "/register" && (
                <Link to="/register">
                  <Button
                    className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors"
                    data-testid="header-register-btn"
                  >
                    Onboard a school
                  </Button>
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}

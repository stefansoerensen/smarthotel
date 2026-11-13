import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuthStore } from "./hooks/useAuthStore";
import LoginPage from "./pages/LoginPage";
import PropertiesPage from "./pages/PropertiesPage";
import PropertyPage from "./pages/PropertyPage";
import UsersPage from "./pages/UsersPage";
import { me } from "./services/auth";

export default function App() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const setSession = useAuthStore((s) => s.setSession);

  useEffect(() => {
    if (token && !user) {
      me()
        .then((u) => setSession(token, u))
        .catch(() => undefined);
    }
  }, [token, user, setSession]);

  if (!token) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/properties" replace />} />
        <Route path="/properties" element={<PropertiesPage />} />
        <Route path="/properties/:code" element={<PropertyPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="*" element={<Navigate to="/properties" replace />} />
      </Route>
    </Routes>
  );
}

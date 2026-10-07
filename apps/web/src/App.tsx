import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "./auth/session";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { DeviceDetail } from "./pages/DeviceDetail";
import { Devices } from "./pages/Devices";
import { HubStatus } from "./pages/HubStatus";
import { Login } from "./pages/Login";
import { Members } from "./pages/Members";
import { Rooms } from "./pages/Rooms";
import { Settings } from "./pages/Settings";

export function App() {
  const { t } = useTranslation();
  const { status, bootstrap } = useSession();
  useEffect(() => { void bootstrap(); }, [bootstrap]);
  if (status === "loading") return <main><p>{t("app.loading")}</p></main>;
  if (status === "anonymous") return <Login />;
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="rooms" element={<Rooms />} />
          <Route path="devices" element={<Devices />} />
          <Route path="devices/:id" element={<DeviceDetail />} />
          <Route path="hub" element={<HubStatus />} />
          <Route path="settings" element={<Settings />} />
          <Route path="members" element={<Members />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

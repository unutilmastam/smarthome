import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "./auth/session";
import { Layout } from "./components/Layout";
import { Automations } from "./pages/Automations";
import { Cameras } from "./pages/Cameras";
import { Dashboard } from "./pages/Dashboard";
import { DeviceDetail } from "./pages/DeviceDetail";
import { Devices } from "./pages/Devices";
import { Energy } from "./pages/Energy";
import { HubStatus } from "./pages/HubStatus";
import { Login } from "./pages/Login";
import { Members } from "./pages/Members";
import { More } from "./pages/More";
import { Events } from "./pages/Events";
import { Rooms } from "./pages/Rooms";
import { Security } from "./pages/Security";
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
          <Route path="energy" element={<Energy />} />
          <Route path="cameras" element={<Cameras />} />
          <Route path="hub" element={<HubStatus />} />
          <Route path="settings" element={<Settings />} />
          <Route path="members" element={<Members />} />
          <Route path="more" element={<More />} />
          <Route path="security" element={<Security />} />
          <Route path="events" element={<Events />} />
          <Route path="automations" element={<Automations />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

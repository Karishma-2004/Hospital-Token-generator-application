import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { api } from "./lib/api";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";

import HospitalRegister from "./pages/HospitalRegister";
import Hospitals from "./pages/Hospitals";
import HospitalDetails from "./pages/HospitalDetails";
import DoctorSlots from "./pages/DoctorSlots";

import Appointments from "./pages/Appointments";
import ApplicationAdmin from "./pages/ApplicationAdmin";
import AdminDashboard from "./pages/AdminDashboard";
import AdminUsers from "./pages/AdminUsers";
import AdminSettlements from "./pages/AdminSettlements";
import Receptionist from "./pages/Receptionist";
import ReceptionDesk from "./pages/ReceptionDesk";
import QueueBoard from "./pages/QueueBoard";
import DoctorDashboard from "./pages/DoctorDashboard";
import PrescriptionForm from "./pages/PrescriptionForm";
import PrescriptionView from "./pages/PrescriptionView";

import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";

import ResendVerification from "./pages/ResendVerification";
import VerifyEmail from "./pages/VerifyEmail";


function RoleRoute({ user, roles, children }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const role = user.effective_role || user.role;

  if (!roles.includes(role)) {
    return <Navigate to="/hospitals" replace />;
  }

  return children;
}


export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const access = localStorage.getItem("access");

    if (!access) {
      setLoading(false);
      return;
    }

    api
      .get("/auth/me/")
      .then((response) => {
        setUser(response.data);
      })
      .catch(() => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-green-600" />
          <p className="mt-4 text-sm text-slate-500">Loading Qenova...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      {/* PUBLIC */}
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login onLogin={setUser} />} />
      <Route path="/register" element={<Register />} />
      <Route path="/hospital-register" element={<HospitalRegister />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
      <Route path="/verify-email/:uid/:token" element={<VerifyEmail />} />
      <Route path="/resend-verification" element={<ResendVerification />} />

      {/* Lobby display (public, full screen, no navigation bar) */}
      <Route path="/queue-board/:hospitalId" element={<QueueBoard />} />

      {/* HOSPITALS + SLOTS */}
      <Route path="/hospitals" element={<Layout user={user}><Hospitals /></Layout>} />
      <Route path="/hospitals/:hospitalId" element={<Layout user={user}><HospitalDetails /></Layout>} />
      <Route path="/doctors/:doctorId/slots" element={<Layout user={user}><DoctorSlots user={user} /></Layout>} />

      {/* PATIENT */}
      <Route
        path="/appointments"
        element={
          <ProtectedRoute user={user}>
            <Layout user={user}><Appointments user={user} /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/prescriptions/:appointmentId"
        element={
          <RoleRoute user={user} roles={["USER", "DOCTOR"]}>
            <Layout user={user}><PrescriptionView /></Layout>
          </RoleRoute>
        }
      />

      {/* APPLICATION ADMIN */}
      <Route
        path="/admin"
        element={<RoleRoute user={user} roles={["ADMIN"]}><Layout user={user}><ApplicationAdmin /></Layout></RoleRoute>}
      />
      <Route
        path="/admin/dashboard"
        element={<RoleRoute user={user} roles={["ADMIN"]}><Layout user={user}><AdminDashboard /></Layout></RoleRoute>}
      />
      <Route
        path="/admin/users"
        element={<RoleRoute user={user} roles={["ADMIN"]}><Layout user={user}><AdminUsers /></Layout></RoleRoute>}
      />
      <Route
        path="/admin/settlements"
        element={<RoleRoute user={user} roles={["ADMIN"]}><Layout user={user}><AdminSettlements /></Layout></RoleRoute>}
      />

      {/* HOSPITAL STAFF */}
      <Route
        path="/reception"
        element={<RoleRoute user={user} roles={["RECEPTIONIST"]}><Layout user={user}><ReceptionDesk /></Layout></RoleRoute>}
      />
      <Route
        path="/receptionist"
        element={<RoleRoute user={user} roles={["RECEPTIONIST"]}><Layout user={user}><Receptionist /></Layout></RoleRoute>}
      />

      {/* DOCTOR */}
      <Route
        path="/doctor-dashboard"
        element={<RoleRoute user={user} roles={["DOCTOR"]}><Layout user={user}><DoctorDashboard /></Layout></RoleRoute>}
      />
      <Route
        path="/doctor/prescription/:appointmentId"
        element={<RoleRoute user={user} roles={["DOCTOR"]}><Layout user={user}><PrescriptionForm /></Layout></RoleRoute>}
      />

      {/* UNKNOWN URL */}
      <Route path="*" element={<Navigate to={user ? "/hospitals" : "/"} replace />} />
    </Routes>
  );
}
